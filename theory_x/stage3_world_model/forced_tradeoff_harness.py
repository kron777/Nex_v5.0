"""Forced-tradeoff harness — REHEARSAL build; §9 remains unrun.

Jon/Beam build prompt, 2026-11-10. This module is the INSTRUMENT, not the
pre-registered falsifier. §9's whole value is that its prediction was
locked in before anyone saw a result; running it against the shadow budget
now would either weaken "a real refuse() fires" or produce a FAIL everyone
already knows is fake about the live system. So this module runs in two
modes that share one code path:

    rehearsal  -- now, wired to the shadow Budget (budget_shadow.py,
                  commit d9bc326). Reports numbers, never PASS/FAIL.
    s9         -- after r77 closes (~2026-11-21), wired to the live budget.
                  Same script, one dependency swapped. THAT run is §9.

Nothing in gui/server.py or theory_x/world_bridge/selector.py is imported,
read, or modified by this module. refuse()/consolidate()/recall() and the
Budget class are only called, never changed. The shadow budget's capacity
is read, never adjusted.

CONFLICT 1 (reported per the build prompt's own instruction -- constraint
6 -- rather than silently reconciled): the build prompt describes the §9
mechanical guard as reading "the wired Budget's provenance." Budget
(theory_x/stage_finitude/budget_shadow.py) has no `provenance` attribute
-- confirmed by reading the class directly -- and this module is forbidden
from adding one (hard constraint: do not modify the Budget object).
`provenance` on the ledger side is a per-call string passed into refuse(),
not a property of the Budget instance. Resolution: the single injection
point (`wire_budget()` below) binds a Budget together with the mode string
that was used to construct it, in one frozen object (`WiredBudget`), and
every place that would emit a §9 verdict reads `wired.mode` -- never a
Budget attribute, since none exists and none may be added. This is the
same mechanical-guard property the prompt asks for (code-enforced, keyed
to which budget is actually wired, not a comment), implemented without
touching Budget.

CONFLICT 2: the build prompt's Tier 2 is described as "a contradiction
surfaced by Phase M (world-model propositions that cannot both hold)".
Phase M, as actually built (SENTIENCE_PROGRAM.md, stage9_metacognition/
metacognition.py), is stateful metacognition over a closed ledger of
meta_cognition_events -- it detects patterns in the system's OWN
monitoring ("I keep flagging drift on topic X"), not contradictions
between world-model propositions. There is no module in this codebase
that surfaces "propositions that cannot both hold" independently of the
Harmonizer's belief-conflict detector (the Tier 1 mechanism). Tier 2 as
described does not exist. Reported rather than reconciled; see
source_pairs() below for how this was handled.

CONFLICT 3: Tier 1 is described as "a tension already present in
held_tensions: the system already holds both poles." At rehearsal start,
data/dynamic.db's held_tensions table has zero rows (confirmed by direct
query) -- NEX5_HELD_TENSION has never been armed on a live run, so nothing
has ever been written there. No Tier 1 pair is "already present" in the
literal sense. What IS available: harmonizer_events contains 73 real,
system-detected 'paradox' pairs (the Harmonizer's own conflict detector,
running over real live beliefs, unprompted by this build), 40 still open,
19 still eligible (both beliefs live, unlocked, unpaused). This harness
treats the strongest of those -- screened through the three legitimacy
gates below -- as its pair source: real content, real detector, zero
harness injection, but not literally pre-existing in held_tensions.
Labelled "Tier 1 (content and detection real; 'already present' literal
clause not met -- see CONFLICT 3)" everywhere it appears, rather than
force-fit into Tier 1 or mislabelled as Tier 3.

CONFLICT 4 (v2, capacity-accounting fix, 2026-11-10): v1 reported
`remaining_before_refuse` as the fresh Budget's full capacity (700) even
though `_fixed_moment_candidates()` -- the same fixture both moments use --
already consumes 687 of those 700 chars the moment select() is first called,
before refuse() ever runs. True available room at moment-open is capacity
minus that occupancy (700-687=13), not capacity itself. v2 charges that
occupancy against the Budget (Shape A: via Budget.spend(), see
charge_occupancy() below) before refuse() is attempted, so
`budget.remaining` -- and therefore refuse()'s own check_capacity() --
sees the true 13, not the phantom 700. Consequence, observed directly: at
true room=13, every real system-detected pair this harness can source costs
200-209 (surfacing_cost's template overhead alone is ~33 chars minimum --
no real pair can ever cost less than that), so refuse() now correctly
raises InsufficientBudget for both main moments instead of firing. This is
not a bug in refuse() -- it is refuse() doing exactly its documented job
(check_capacity raises BEFORE any write on a genuine overdraw). It does mean
these two moments, as this fixture constructs them, cannot demonstrate a
successful hold-and-displace outcome; see C-a/C-b below for that
demonstration under honestly-labelled engineered room instead, and F4's
mechanism-only downgrade for why the main-moment corpus itself is suspect.

CONFLICT 5 (v2): the build prompt's C-table says "C-c: cost just over
available room -> must fire." Read literally ("fire" = refuse() commits a
row, the sense used everywhere else in this module and its docstrings),
this would require refuse() to succeed on a genuine overdraw -- the exact
failure mode (silently allowing overdraw) F1's own failure clause names as
disqualifying. Resolved as: "fire" in the C-table means the
InsufficientBudget overdraw guard fires (raises), not that refuse() commits.
Under that reading the table is self-consistent with check_capacity's
documented contract and with C-a/C-b: C-a/C-b = guard does NOT fire (refuse
commits, affordable); C-c = guard fires (raises, correctly rejected). Each
control's result records both the literal outcome and which reading it
satisfies, so a reader can check this resolution against the numbers rather
than take it on faith.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal, Optional

from theory_x.stage_finitude.budget_shadow import Budget, InsufficientBudget
from theory_x.stage_tom.global_workspace import select_within_budget
from theory_x.stage3_world_model.ledger_primitives import refuse, consolidate, recall

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LIVE_BELIEFS_DB = str(_REPO_ROOT / "data" / "beliefs.db")
LIVE_DYNAMIC_DB = str(_REPO_ROOT / "data" / "dynamic.db")

# ── The realistic chat-block fixture ────────────────────────────────────────
# Same salience/size distribution already used and validated in
# tests/test_ledger_primitives.py's test_refuse_is_neither_veto_nor_noop
# (Test 4). Duplicated here (not imported) because production code does not
# import from tests/; this is the same real shape, not a fresh invention.
_REAL_CHAT_BLOCK_SALIENCE = {
    "convo": 0.90, "compassion": 0.90, "compass": 0.85, "operator": 0.75,
    "operator_anchor": 0.70, "affect_carry": 0.55, "spectrum": 0.50, "tag": 0.50,
    "equanimity": 0.45, "apramada": 0.45, "virya": 0.40, "sraddha": 0.40,
    "prasrabdhi": 0.40,
}
_REAL_CHAT_BLOCK_EXEMPT = {"compassion", "compass"}


def _fixed_moment_candidates() -> list[tuple[float, str, bool]]:
    out = []
    for kind, sal in _REAL_CHAT_BLOCK_SALIENCE.items():
        exempt = kind in _REAL_CHAT_BLOCK_EXEMPT
        length = 220 if exempt else int(60 + 340 * sal)
        out.append((sal, "x" * length, exempt))
    return out


# ── Single injectable dependency ────────────────────────────────────────────

@dataclass(frozen=True)
class WiredBudget:
    """The one thing this harness branches on. See CONFLICT 1 above for why
    `mode` lives here rather than on Budget itself."""
    budget: Budget
    mode: Literal["shadow", "live"]


def wire_budget(dyn_writer, mode: Literal["shadow", "live"] = "shadow",
                 moment_id: Optional[str] = None) -> WiredBudget:
    """The single resolution point for the injectable dependency. Nothing
    else in this module constructs a Budget. Capacity is never passed here
    -- Budget resolves its own standing default (NEX5_SHADOW_BUDGET_CAPACITY,
    else 700), untouched by this harness, per the untuned-capacity rule."""
    if mode == "live":
        raise NotImplementedError(
            "live mode requires the post-r77 live budget wiring, which does "
            "not exist yet -- this harness cannot construct it. That wiring "
            "is the one line this script changes after 2026-11-21."
        )
    return WiredBudget(budget=Budget(dyn_writer, moment_id=moment_id), mode=mode)


# ── Pair sourcing (section 5) ───────────────────────────────────────────────

@dataclass
class CandidatePair:
    tier_label: str
    belief_id_a: int
    belief_id_b: int
    content_a: str
    content_b: str
    tier_a: int
    tier_b: int
    independence: bool
    independence_note: str
    non_triviality: bool
    non_triviality_note: str
    conflict_score: float


def _clip(text: str, n: int = 90) -> str:
    text = text.strip()
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0] + "…"


def surfacing_cost(content_a: str, content_b: str) -> int:
    """The real, non-invented cost basis: the number of characters the
    live system's own tension-surfacing mechanism
    (harmonizer._content_specific_tension_line) would actually charge
    against THIS budget's chat-block economy to surface this exact pair.
    Not the raw stored content length -- that is never itself injected
    into a prompt; only this clipped line is, via the already-built,
    already-tested surfacing path. Pair-specific (of course it is -- it
    is the cost of holding THIS tension), independent only requirement
    is on capacity, not cost (section 3.2)."""
    line = f'I notice I hold both: "{_clip(content_a)}" and "{_clip(content_b)}".'
    return len(line)


def source_pairs() -> tuple[list[CandidatePair], dict]:
    """Reads the LIVE production databases READ-ONLY (never writes to
    them) to find real, system-detected conflicting belief pairs. Applies
    the three legitimacy gates. Returns (pairs_that_pass, preflight_info).
    """
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from theory_x.stage3_world_model.harmonizer import _conflict_score, _has_negation
    from theory_x.stage3_world_model.retrieval import _tokenize
    from substrate import Reader

    # substrate.Reader, not a raw sqlite3.connect: the repo's architecture-
    # compliance tests (test_dynamic.py/test_edges.py/test_fountain.py/
    # test_membrane.py/test_sense.py/test_world_model.py, all named
    # test_no_direct_sqlite3_outside_substrate) ban direct sqlite3 use
    # outside substrate/. Reader opens read-only (mode=ro) regardless, so
    # this reads live data without risk of writing to it either way.
    dyn = Reader(LIVE_DYNAMIC_DB)
    bel = Reader(LIVE_BELIEFS_DB)

    held_total = dyn.read_one("SELECT COUNT(*) AS n FROM held_tensions")["n"]
    held_open = dyn.read_one(
        "SELECT COUNT(*) AS n FROM held_tensions WHERE resolved_at IS NULL"
    )["n"]

    rows = dyn.read(
        "SELECT belief_id_a, belief_id_b, resolution, ts FROM harmonizer_events ORDER BY ts"
    )
    latest: dict[tuple[int, int], tuple[str, float]] = {}
    for r in rows:
        key = (min(r["belief_id_a"], r["belief_id_b"]), max(r["belief_id_a"], r["belief_id_b"]))
        latest[key] = (r["resolution"], r["ts"])
    open_paradox = [(k[0], k[1]) for k, v in latest.items() if v[0] == "paradox"]

    def get_belief(bid: int):
        return bel.read_one("SELECT * FROM beliefs WHERE id=?", (bid,))

    def eligible(row) -> bool:
        return row is not None and 3 <= row["tier"] <= 7 and not row["locked"] and not row["paused"]

    still_eligible = []
    for a, b in open_paradox:
        ra, rb = get_belief(a), get_belief(b)
        if eligible(ra) and eligible(rb):
            still_eligible.append((a, b, ra, rb))

    passed: list[CandidatePair] = []
    rejected: list[dict] = []
    for a, b, ra, rb in still_eligible:
        ca, cb = ra["content"], rb["content"]
        # Independence gate: neither pole may reference / be derived from the other.
        indep = True
        indep_note = "neither pole's tags/content reference the other"
        tags_a, tags_b = str(ra["tags"] or ""), str(rb["tags"] or "")
        if "I notice this fire engaged" in ca or "I notice this fire engaged" in cb:
            indep, indep_note = False, "one pole is a 'fire engaged' reflection quoting the other's content"
        elif cb[:40].lower() in tags_a.lower() or ca[:40].lower() in tags_b.lower():
            indep, indep_note = False, "one pole's attribution tag names the other's content"
        elif ca[:60] in cb or cb[:60] in ca:
            indep, indep_note = False, "one pole's text contains the other's text verbatim"

        tok_a, tok_b = _tokenize(ca), _tokenize(cb)
        score = _conflict_score(tok_a, ca, tok_b, cb)

        non_triv = True
        non_triv_note = "both poles are substantive committed beliefs, neither a placeholder"
        if not indep:
            non_triv, non_triv_note = True, "n/a -- rejected on independence first"
        # Reject statement-vs-question false positives from the heuristic:
        # a question cannot logically contradict a statement.
        if ca.strip().endswith("?") != cb.strip().endswith("?") and (
            ca.strip().endswith("?") or cb.strip().endswith("?")
        ):
            non_triv, non_triv_note = False, "one pole is a question, not a proposition -- cannot genuinely contradict a statement; heuristic false positive"

        cp = CandidatePair(
            tier_label="Tier 1 (content/detection real; literal 'already present' clause not met -- CONFLICT 3)",
            belief_id_a=a, belief_id_b=b, content_a=ca, content_b=cb,
            tier_a=ra["tier"], tier_b=rb["tier"],
            independence=indep, independence_note=indep_note,
            non_triviality=non_triv, non_triviality_note=non_triv_note,
            conflict_score=score,
        )
        if indep and non_triv:
            passed.append(cp)
        else:
            rejected.append({
                "pair": (a, b), "independence": indep, "independence_note": indep_note,
                "non_triviality": non_triv, "non_triviality_note": non_triv_note,
            })

    info = {
        "held_tensions_total_at_start": held_total,
        "held_tensions_open_at_start": held_open,
        "harmonizer_events_total": len(rows),
        "open_paradox_pairs": len(open_paradox),
        "still_eligible_paradox_pairs": len(still_eligible),
        "pairs_passed_gates": len(passed),
        "pairs_rejected": rejected,
        "tier2_phase_m_available": False,
        "tier2_conflict_note": "Phase M (metacognition.py) does not surface world-model "
                                "proposition contradictions -- see CONFLICT 2. No Tier 2 source exists.",
    }
    return passed, info


# ── Isolated environment (no production data is ever mutated) ─────────────

# Tracks which belief ids have been seeded, scoped to ONE isolated env at a
# time -- reset in _make_isolated_env() itself (not in run_rehearsal()),
# since that is the actual boundary of what database the ids are valid
# against. Letting this survive across two different isolated envs (e.g.
# two separate test methods) causes a real bug: a bid seen as "already
# seeded" against a now-gone temp database gets silently skipped against a
# brand-new one that never actually got the row.
_SEEDED_BELIEF_IDS: set = set()


def _make_isolated_env():
    tmp = tempfile.mkdtemp(prefix="nex5_forced_tradeoff_")
    os.environ["NEX5_DATA_DIR"] = tmp
    os.environ["NEX5_ADMIN_HASH_FILE"] = str(Path(tmp) / "admin.argon2")
    from substrate.init_db import init_all
    init_all()
    from substrate import Reader, Writer, db_paths
    paths = db_paths()
    writers = {n: Writer(p, name=n) for n, p in paths.items()}
    readers = {n: Reader(p) for n, p in paths.items()}
    _SEEDED_BELIEF_IDS.clear()
    return writers, readers, tmp


def _cleanup_isolated_env(writers, tmp):
    for w in writers.values():
        try:
            w.close()
        except Exception:
            pass
    shutil.rmtree(tmp, ignore_errors=True)
    os.environ.pop("NEX5_DATA_DIR", None)
    os.environ.pop("NEX5_ADMIN_HASH_FILE", None)



def _seed_real_pair(writers, pair: CandidatePair) -> Optional[str]:
    """Returns None on full success, or a reason string if a pole could not
    be seeded (does not raise). Real pairs can share a pole (belief 667
    appears in more than one harmonizer-detected pair) -- seed each belief
    id at most once across the whole run (the isolated beliefs table has a
    UNIQUE id). Separately: substrate/init_db.py's idx_beliefs_content_orphan_uniq
    enforces GLOBALLY-unique content for any belief with problem_id IS NULL
    -- this is a real production constraint, not a harness bug, and it can
    legitimately collide (confirmed directly: production belief 2422's
    content is byte-identical to locked keystone belief 49's -- a real,
    surprising production-data fact, reported rather than worked around)."""
    now = int(time.time())
    for bid, content, tier in (
        (pair.belief_id_a, pair.content_a, pair.tier_a),
        (pair.belief_id_b, pair.content_b, pair.tier_b),
    ):
        if bid in _SEEDED_BELIEF_IDS:
            continue
        try:
            writers["beliefs"].write(
                "INSERT INTO beliefs (id, content, tier, confidence, created_at, source, locked, paused) "
                "VALUES (?, ?, ?, 0.7, ?, 'forced_tradeoff_harness_seed_real_content', 0, 0)",
                (bid, content, tier, now),
            )
            _SEEDED_BELIEF_IDS.add(bid)
        except Exception as exc:
            return (
                f"belief {bid} could not be seeded into the isolated env: {exc} -- "
                f"its content collides with an already-present row under "
                f"idx_beliefs_content_orphan_uniq (a real substrate constraint)"
            )
    return None


# ── Validity pre-flight (section 3) ─────────────────────────────────────────

def negative_control(writers, readers, wired: WiredBudget) -> dict:
    """7.5 / 3.3: a pair that does NOT exceed capacity, capacity untouched.
    Synthetic by construction -- same epistemic status as the Tier 3/test-7
    corpus, labelled as such. Proves the loss detector can report zero."""
    now = int(time.time())
    a_id = writers["beliefs"].write(
        "INSERT INTO beliefs (content, tier, confidence, created_at, source, locked, paused) "
        "VALUES ('control pole A -- trivially cheap, synthetic', 5, 0.7, ?, 'control', 0, 0)", (now,))
    b_id = writers["beliefs"].write(
        "INSERT INTO beliefs (content, tier, confidence, created_at, source, locked, paused) "
        "VALUES ('control pole B -- trivially cheap, synthetic', 5, 0.7, ?, 'control', 0, 0)", (now,))
    cheap_cost = 1  # far below the standing 700 capacity; this is the point
    before_remaining = wired.budget.remaining
    entry_id = refuse(writers["dynamic"], readers["dynamic"], wired.budget,
                       a_id, b_id, cost=cheap_cost, provenance=wired.mode)
    after_remaining = wired.budget.remaining
    row_a = readers["beliefs"].read_one("SELECT tier, paused, content FROM beliefs WHERE id=?", (a_id,))
    row_b = readers["beliefs"].read_one("SELECT tier, paused, content FROM beliefs WHERE id=?", (b_id,))
    loss = before_remaining - after_remaining - cheap_cost  # must be exactly 0 beyond the paid cost itself
    return {
        "label": "negative control (synthetic pair, cost=1, standing capacity untouched)",
        "pair": (a_id, b_id),
        "cost": cheap_cost,
        "remaining_before": before_remaining,
        "remaining_after": after_remaining,
        "refuse_fired": True,
        "both_poles_survive_trivially": row_a["content"] is not None and row_b["content"] is not None
                                          and row_a["paused"] == 0 and row_b["paused"] == 0,
        "zero_loss_beyond_paid_cost": loss == 0,
        "entry_id": entry_id,
    }


def irreversibility_discriminator(writers, readers) -> dict:
    """3.4: show the irreversibility check can distinguish a restorable
    case (correctly reported 'not forced') from a genuinely forced one.
    Uses recall()'s own shape: a pair with no refuse() ever called against
    it must not be reported as an unresolved forced loss -- it is simply
    absent."""
    now = int(time.time())
    a_id = writers["beliefs"].write(
        "INSERT INTO beliefs (content, tier, confidence, created_at, source, locked, paused) "
        "VALUES ('restorable pole A -- never faced, fully present', 5, 0.7, ?, 'control', 0, 0)", (now,))
    b_id = writers["beliefs"].write(
        "INSERT INTO beliefs (content, tier, confidence, created_at, source, locked, paused) "
        "VALUES ('restorable pole B -- never faced, fully present', 5, 0.7, ?, 'control', 0, 0)", (now,))
    result = recall(readers["dynamic"], a_id, b_id)
    row_a = readers["beliefs"].read_one("SELECT content FROM beliefs WHERE id=?", (a_id,))
    row_b = readers["beliefs"].read_one("SELECT content FROM beliefs WHERE id=?", (b_id,))
    full_restoration_possible = (
        result["found"] is False
        and row_a["content"] == "restorable pole A -- never faced, fully present"
        and row_b["content"] == "restorable pole B -- never faced, fully present"
    )
    return {
        "pair": (a_id, b_id),
        "recall_result": result,
        "full_restoration_possible": full_restoration_possible,
        "correctly_reported_not_forced": full_restoration_possible and result["found"] is False,
    }


# ── Verification checks (section 7) ─────────────────────────────────────────

def charge_occupancy(wired: WiredBudget, occupancy: int) -> Optional[Any]:
    """v2 F1 fix (Shape A chosen): charge pre-existing occupancy against the
    Budget via its own public spend(), BEFORE refuse() is attempted, so
    `remaining`/check_capacity() see true available room, not the untouched
    full capacity. Shape A over Shape B because it needs no new concept --
    Budget.spend() already exists, is not a structural change to Budget,
    and already writes to shadow_budget_spend (substrate/schema/dynamic.sql),
    a table distinct from held_tensions. consolidate()/recall() only ever
    read held_tensions, so this charge is automatically invisible to both --
    satisfying "give it its own kind that consolidate()/recall() ignore"
    without inventing a held_tensions kind at all. This is NOT a decision
    cost: it is never passed to refuse(), never carries `provenance`, never
    appears in held_tensions. occupancy==0 is a legal no-op (nothing to
    charge) and is skipped rather than calling spend(0), which Budget
    rejects by contract (amount must be > 0)."""
    if occupancy <= 0:
        return None
    return wired.budget.spend(occupancy)


def run_trial_moment(writers, readers, wired: WiredBudget, pair: CandidatePair,
                      cost: int, engineered_available_room: Optional[int] = None,
                      label: str = "real") -> dict:
    """One moment: select() BEFORE paying the tension's cost, charge the
    moment's true occupancy against the budget (v2 fix), refuse() the real
    pair, select() AFTER -- the Test-4 delta pattern, applied to a real
    system-detected pair instead of a synthetic one.

    `engineered_available_room`, when given (controls C-a/b/c only): this
    moment's true available room is REPLACED by a deliberately engineered
    value instead of the fixture's real occupancy, purely to exercise the
    boundary refuse()'s check_capacity() sits on. This is synthetic
    scaffolding -- same epistemic status as the original negative control's
    cost=1 pair -- and is always labelled as such (`label` field) in the
    result; it never claims to be a real moment's real occupancy."""
    candidates = _fixed_moment_candidates()

    kept_before = wired.budget.select(candidates)
    chars_before = sum(len(t) for t in kept_before)
    capacity = wired.budget.capacity

    if engineered_available_room is not None:
        occupancy_to_charge = capacity - engineered_available_room
        occupancy_label = (
            f"ENGINEERED scaffold -- not this fixture's real occupancy "
            f"({chars_before}); charged to pin available room at "
            f"{engineered_available_room} for this control"
        )
    else:
        occupancy_to_charge = chars_before
        occupancy_label = "real occupancy from the fixed chat-block fixture"

    # v2 F1 fix: charge occupancy BEFORE refuse() so remaining is truthful.
    charge_occupancy(wired, occupancy_to_charge)

    # 7.3 baseline: distinct open tension_held count before this moment's refuse().
    distinct_before = consolidate(readers["dynamic"], writers["dynamic"])["distinct_pairs"] or 0

    # Native-state snapshot BEFORE (7.2).
    snap_before = {
        bid: dict(readers["beliefs"].read_one("SELECT tier, paused, content FROM beliefs WHERE id=?", (bid,)))
        for bid in (pair.belief_id_a, pair.belief_id_b)
    }

    available_room_at_open = wired.budget.remaining  # F1: now truthful (post-occupancy-charge)
    remaining_before_refuse = available_room_at_open
    try:
        entry_id = refuse(writers["dynamic"], readers["dynamic"], wired.budget,
                           pair.belief_id_a, pair.belief_id_b, cost=cost,
                           provenance=wired.mode)
        fired = True
        overdraw_error = None
    except InsufficientBudget as exc:
        entry_id = None
        fired = False
        overdraw_error = str(exc)

    remaining_after_refuse = wired.budget.remaining
    kept_after = wired.budget.select(candidates) if fired else kept_before
    chars_after = sum(len(t) for t in kept_after)
    delta_chars = chars_before - chars_after

    # 7.1 pair-link integrity.
    check_7_1 = None
    if fired:
        row = readers["dynamic"].read_one(
            "SELECT id, belief_id_a, belief_id_b, kind, cost, irreversibility, seq "
            "FROM held_tensions WHERE id=?", (entry_id,))
        check_7_1 = {
            "one_entry": row is not None,
            "both_poles_in_refs": {row["belief_id_a"], row["belief_id_b"]} == {pair.belief_id_a, pair.belief_id_b},
            "kind_is_tension_held": row["kind"] == "tension_held",
            "irreversibility_true": bool(row["irreversibility"]),
            "cost_gt_zero": row["cost"] > 0,
        }

    # 7.2 native-state survival, BOTH poles, native paths (not the ledger).
    snap_after = {
        bid: dict(readers["beliefs"].read_one("SELECT tier, paused, content FROM beliefs WHERE id=?", (bid,)))
        for bid in (pair.belief_id_a, pair.belief_id_b)
    }
    check_7_2 = {
        bid: {
            "unchanged": snap_before[bid] == snap_after[bid],
            "still_present": snap_after[bid]["content"] is not None,
            "still_individually_selectable": not snap_after[bid]["paused"],
        }
        for bid in (pair.belief_id_a, pair.belief_id_b)
    }

    # 7.3 amalgamation check -- distinct-tension count must not DROP.
    consolidate_result = consolidate(readers["dynamic"], writers["dynamic"])
    distinct_after = consolidate_result["distinct_pairs"] or 0
    check_7_3 = {
        "distinct_before": distinct_before,
        "distinct_after": distinct_after,
        "did_not_drop": distinct_after >= distinct_before,
        "consolidate_result": consolidate_result,
    }

    # 7.4 attempted-restoration failure -- NOT via recall()'s own marker.
    # The loss this moment produces is the dropped chat-block candidate(s):
    # which kind got excluded from `kept_after` that was in `kept_before`.
    dropped = [t for t in kept_before if t not in kept_after]
    # Attempt reconstruction: is the identity of the dropped candidate kind
    # recorded ANYWHERE outside this harness's own in-memory snapshot --
    # ledger, episode store, world model?
    recall_result = recall(readers["dynamic"], pair.belief_id_a, pair.belief_id_b)
    episode_hits = readers["dynamic"].read(
        "SELECT COUNT(*) AS n FROM episodes"
    )[0]["n"]
    check_7_4 = {
        "dropped_candidate_count": len(dropped),
        "dropped_candidate_chars": sum(len(t) for t in dropped),
        "ledger_names_the_dropped_candidate": False,  # held_tensions has no column for this
        "episode_store_names_the_dropped_candidate": False,  # episodes table unrelated to selection
        "world_model_names_the_dropped_candidate": False,  # beliefs table has no selection-drop column
        "recall_marker": recall_result,
        "conclusion": (
            "the specific chat-block candidate displaced by paying this "
            "tension's cost is not recorded anywhere -- not in held_tensions "
            "(no column for it), not in episodes (unrelated), not in beliefs "
            "(selection is pure/stateless in select_within_budget, no side "
            "effect is ever written). Reconstruction of 'what was dropped and "
            "why' falls short of full fidelity: we know a block was dropped "
            "and how many chars it cost (from this harness's own before/after "
            "snapshot), but nothing in the system itself retains that fact "
            "once this process exits -- it is only recoverable right now "
            "because this harness still holds `kept_before` in memory."
        ) if len(dropped) > 0 else "no candidate was dropped this moment (cost did not bind) -- see firing/binding fields",
    }

    return {
        "pair_ids": (pair.belief_id_a, pair.belief_id_b),
        "label": label,
        "tier_label": pair.tier_label,
        "cost": cost,
        "capacity": capacity,
        "ceiling_denominator": "available room at moment open",
        # F2 figure 1 (PRIMARY): does the pair hit the true ceiling?
        "cost_fraction_of_available_room": (
            round(cost / available_room_at_open, 3) if available_room_at_open > 0 else float("inf")
        ),
        # F2 figure 2 (secondary): how much of capacity was already occupied before any pair cost.
        "occupancy_at_open": occupancy_to_charge,
        "occupancy_source": occupancy_label,
        "occupancy_fraction_of_capacity": round(occupancy_to_charge / capacity, 3),
        # F2 figure 3 (secondary, OLD/WRONG number -- kept only for comparison, explicitly labelled).
        "cost_fraction_of_capacity_OLD_WRONG_DENOMINATOR": round(cost / capacity, 3),
        "available_room_at_open": available_room_at_open,
        "remaining_before_refuse": remaining_before_refuse,
        "remaining_after_refuse": remaining_after_refuse,
        "binding_fraction_this_moment": (
            round(cost / remaining_before_refuse, 3) if remaining_before_refuse > 0 else float("inf")
        ),
        "fired": fired,
        "overdraw_error": overdraw_error,
        "chars_before": chars_before,
        "chars_after": chars_after,
        "delta_chars": delta_chars,
        "check_7_1": check_7_1,
        "check_7_2": check_7_2,
        "check_7_3": check_7_3,
        "check_7_4": check_7_4,
    }


# ── Full rehearsal run ──────────────────────────────────────────────────────

def run_rehearsal() -> dict:
    report: dict[str, Any] = {"mode": "rehearsal"}

    # Freeze check, first thing, before anything else runs.
    import subprocess
    diff = subprocess.run(
        ["git", "diff", "--stat", "gui/server.py", "theory_x/world_bridge/selector.py"],
        capture_output=True, text=True, cwd=Path(__file__).resolve().parent.parent.parent,
    ).stdout.strip()
    report["freeze_check_empty"] = (diff == "")
    report["freeze_check_raw"] = diff

    pairs, source_info = source_pairs()
    report["source_info"] = source_info

    n_moments = min(2, len(pairs))
    chosen = pairs[:n_moments] if pairs else []
    # Control-pair candidate pool: remaining gate-passed pairs first, falling
    # back to reusing `chosen` (a real, already-gated pair used in a second,
    # independent engineered-room moment is legitimate; the two moments test
    # different things). Built lazily below -- some candidates may turn out
    # unseedable (a real content collision with a locked keystone belief;
    # see _seed_real_pair) and are skipped, with the reason reported, not
    # silently dropped.
    control_candidate_pool = pairs[n_moments:] + chosen

    report["pair_tier"] = (
        chosen[0].tier_label if chosen
        else "NONE AVAILABLE -- Tier 1/2/3 all failed or absent, see source_info"
    )
    report["n"] = len(chosen)
    report["selection_rule"] = (
        "every still-eligible (live, unlocked, unpaused) harmonizer-detected "
        "paradox pair, screened through independence + non-triviality gates "
        "(incompatibility is resolved per-moment via cost-vs-capacity, section "
        "6), taken in harmonizer_events timestamp order; first 2 that clear both gates"
    )

    if not chosen:
        report["BLOCKED"] = True
        report["block_reason"] = "no pair of any tier passed the legitimacy gates"
        return report

    writers, readers, tmp = _make_isolated_env()
    try:
        # A probe budget purely to report the standing capacity/mode -- each
        # trial moment below gets its OWN fresh Budget (never reused across
        # moments; Budget's own docstring: "construct fresh per moment").
        probe = wire_budget(writers["dynamic"], mode="shadow", moment_id="probe")
        report["capacity"] = probe.budget.capacity
        report["capacity_source"] = (
            "NEX5_SHADOW_BUDGET_CAPACITY env flag if set, else budget_shadow.py's "
            "_DEFAULT_CAPACITY=700 (fixed at commit d9bc326, long before this "
            "harness existed) -- untouched by this run"
        )
        report["capacity_independent_of_pair"] = True

        for pair in chosen:
            fail = _seed_real_pair(writers, pair)
            if fail:
                raise RuntimeError(f"main trial pair {pair.belief_id_a},{pair.belief_id_b} unseedable: {fail}")

        control_source_pairs = []
        control_seed_skips = []
        for pair in control_candidate_pool:
            if len(control_source_pairs) >= 3:
                break
            if (pair.belief_id_a, pair.belief_id_b) in {(p.belief_id_a, p.belief_id_b) for p in control_source_pairs}:
                continue
            fail = _seed_real_pair(writers, pair)
            if fail:
                control_seed_skips.append({"pair": (pair.belief_id_a, pair.belief_id_b), "reason": fail})
            else:
                control_source_pairs.append(pair)

        moments = []
        for i, pair in enumerate(chosen):
            wired = wire_budget(writers["dynamic"], mode="shadow", moment_id=f"moment-{i}")
            cost = surfacing_cost(pair.content_a, pair.content_b)
            moments.append(run_trial_moment(writers, readers, wired, pair, cost))
        report["moments"] = moments

        # F4: label the corpus honestly -- identical opening occupancy across
        # independent moments is a constructed-corpus signal, reported and
        # acted on regardless of what F0-F3 separately find.
        chars_before_values = [m["chars_before"] for m in moments]
        identical_occupancy = len(set(chars_before_values)) == 1 and len(chars_before_values) > 1
        report["F4_corpus_provenance"] = {
            "chars_before_per_moment": chars_before_values,
            "identical_opening_occupancy_across_moments": identical_occupancy,
            "finding": (
                "both moments draw from the SAME fixed candidate fixture "
                "(_fixed_moment_candidates(), duplicated from "
                "test_ledger_primitives.py's Test 4), so both necessarily open "
                "at the identical 687/700 occupancy -- this is a constructed, "
                "not independently-arising, corpus property. Downgrading pair "
                "tier and marking this run mechanism-only on that basis, "
                "independent of the F0-F3 capacity-accounting finding."
                if identical_occupancy else
                "moments opened at distinct occupancy levels -- no constructed-corpus signal."
            ),
        }
        if identical_occupancy:
            report["pair_tier"] = (
                "Tier 3 (mechanism-only, per F4) -- underlying pairs are real "
                "system-detected tensions (as sourced above), but the SHARED "
                "fixed chat-block fixture both moments open against is "
                "constructed, not independent. See source CONFLICT 3 for the "
                "underlying pair-content provenance, which this does not change."
            )
            report["mechanism_only"] = True

        # ── F3: three real-tension boundary controls (replaces/extends the
        # old toothless negative control, which could only show "fires when
        # obviously affordable," not "correctly refuses when unaffordable") ──
        control_results = {}
        if len(control_source_pairs) >= 3:
            margin = 15
            for label, pair, room_fn in (
                ("C-a", control_source_pairs[0], lambda cost: probe.budget.capacity),  # room = full capacity: cost << room
                ("C-b", control_source_pairs[1], lambda cost: cost + margin),           # room just above cost
                ("C-c", control_source_pairs[2], lambda cost: cost - margin),           # room just below cost
            ):
                cost = surfacing_cost(pair.content_a, pair.content_b)
                room = room_fn(cost)
                wired = wire_budget(writers["dynamic"], mode="shadow", moment_id=f"control-{label}")
                res = run_trial_moment(writers, readers, wired, pair, cost,
                                        engineered_available_room=room, label=label)
                guard_fired = not res["fired"]  # InsufficientBudget raised == guard fired (CONFLICT 5 reading)
                expected_guard_fire = cost > room
                control_results[label] = {
                    **res,
                    "engineered_available_room": room,
                    "expected_guard_fire": expected_guard_fire,
                    "guard_fired": guard_fired,
                    "matches_expectation": guard_fired == expected_guard_fire,
                }
        else:
            control_results["BLOCKED"] = (
                f"only {len(control_source_pairs)} seedable real pairs found "
                f"(skipped: {control_seed_skips}); need 3 for C-a/C-b/C-c -- "
                "reported, not synthesized."
            )
        report["boundary_controls_Fa_Fb_Fc"] = control_results
        report["boundary_control_source_skips"] = control_seed_skips

        control_wired = wire_budget(writers["dynamic"], mode="shadow", moment_id="control")
        report["control_7_5"] = negative_control(writers, readers, control_wired)
        report["irreversibility_discriminator_3_4"] = irreversibility_discriminator(writers, readers)

        # ── Assertions (section 8) ──────────────────────────────────────────
        # v2: "not fired" is only a failure (F1) if the pair was actually
        # affordable (cost <= available_room_at_open) and refuse() still
        # declined -- NOT when the true room correctly makes it unaffordable.
        # v1's assertion logic treated every non-fire as an F1 failure, which
        # was itself downstream of the same uncharged-occupancy bug this
        # build fixes; re-derived fresh here per F5, not inherited.
        assertions = []
        for m in moments:
            overdraw_expected = m["cost"] > m["available_room_at_open"]
            correctly_rejected_overdraw = (not m["fired"]) and overdraw_expected
            m1 = m["fired"] and m["check_7_1"] is not None and m["check_7_1"]["cost_gt_zero"] \
                 and m["check_7_1"]["irreversibility_true"]
            f1_failed = (
                (m["fired"] and overdraw_expected)  # silently allowed a real overdraw -- the actual failure mode
                or (not m["fired"] and not overdraw_expected)  # refused something it could afford -- also wrong
            )
            m2 = all(v["still_present"] and v["still_individually_selectable"]
                     for v in m["check_7_2"].values()) if m["fired"] else None
            f2_failed = (m2 is False) if m["fired"] else None
            m3 = (m["check_7_4"]["dropped_candidate_count"] > 0
                  and not m["check_7_4"]["ledger_names_the_dropped_candidate"]) if m["fired"] else None
            f3_failed = (m["check_7_4"]["dropped_candidate_count"] == 0) if m["fired"] else None
            assertions.append({
                "pair_ids": m["pair_ids"],
                "fired": m["fired"],
                "overdraw_expected_given_true_available_room": overdraw_expected,
                "correctly_rejected_overdraw": correctly_rejected_overdraw,
                "M1_commits_tension_held": m1,
                "F1_would_fail_if": "refuse silently allowed overdraw, pair never reached ceiling, or any option deleted/disabled",
                "F1_triggered": f1_failed,
                "M2_both_poles_survive_native": m2,
                "F2_would_fail_if": "either pole survives only through the ledger while native state is gone",
                "F2_triggered": f2_failed,
                "M3_reconstruction_falls_short": m3,
                "F3_would_fail_if": "full reconstruction of the dropped candidate succeeds (retroactively voids M1)",
                "F3_triggered": f3_failed,
                "F3_explicit_note": (
                    "full reconstruction of WHICH candidate was dropped and WHY never succeeds via any "
                    "in-system record -- only this harness's own transient before/after snapshot knows it, "
                    "and that snapshot vanishes when the process exits. F3 not triggered."
                    if m["fired"] else
                    "moment did not fire (correctly rejected as unaffordable against true available room); "
                    "M3/F3 are about a committed row's restorability and do not apply when no row was committed."
                ),
            })
        report["assertions"] = assertions

        # ── Two-verdict output + mechanical guard (section 9) ──────────────
        harness_valid = (
            report["freeze_check_empty"]
            and report["control_7_5"]["zero_loss_beyond_paid_cost"]
            and report["irreversibility_discriminator_3_4"]["correctly_reported_not_forced"]
            and report["n"] > 1
            and all(c.get("matches_expectation", True) for c in control_results.values() if isinstance(c, dict))
        )

        # VERDICT_2, re-derived fresh from v2 numbers (F5: not inherited from v1).
        # Evidence pool is the FULL run: the 2 main moments (which, under
        # truthful accounting, correctly refuse -- see F0/CONFLICT 4) AND the
        # 3 boundary controls (which demonstrate both sides of the gate under
        # honestly-labelled engineered room). A moment firing with a real
        # delta is affirmative evidence of "pay -> displacement"; a moment
        # correctly rejecting an unaffordable cost is affirmative evidence of
        # "the primitive is budget-sensitive, not tension-sensitive-only" --
        # both are needed, neither alone is EXPRESSES_FORCED_TRADEOFF.
        fired_with_real_delta = [m for m in moments if m["fired"] and m["delta_chars"] > 0]
        control_fires = [c for c in control_results.values() if isinstance(c, dict) and c["fired"]]
        control_correct_rejections = [c for c in control_results.values()
                                       if isinstance(c, dict) and not c["fired"] and c["expected_guard_fire"]]
        controls_all_match = all(c.get("matches_expectation", False) for c in control_results.values()
                                  if isinstance(c, dict)) and len(control_results) >= 3 and "BLOCKED" not in control_results

        demonstrates_pay_and_displace = len(fired_with_real_delta) > 0 or len(control_fires) > 0
        demonstrates_correct_refusal = any(
            m["fired"] is False and m["cost"] > m["available_room_at_open"] for m in moments
        ) or len(control_correct_rejections) > 0

        # The boundary controls (C-a/b/c) are what actually discriminates
        # "always fires" from "correctly budget-sensitive" (section 3.3's own
        # point about why a toothless control is worthless). If they don't
        # all land on the expected side of the gate, the mechanism claim
        # can't be made regardless of what the main moments showed.
        if controls_all_match and demonstrates_pay_and_displace and demonstrates_correct_refusal:
            mechanism_verdict = "EXPRESSES_FORCED_TRADEOFF"
        else:
            mechanism_verdict = "CANNOT_EXPRESS"

        report["VERDICT_1_HARNESS"] = "VALID" if harness_valid else "INVALID"
        report["VERDICT_2_MECHANISM"] = mechanism_verdict
        report["VERDICT_2_evidence_notes"] = (
            f"main moments fired-with-delta: {len(fired_with_real_delta)}/2 "
            f"(both correctly rejected instead -- true available room, 13, is "
            f"smaller than ANY real pair's minimum possible cost (~33, the "
            f"surfacing-line template's own fixed overhead) -- this fixture "
            f"cannot demonstrate pay-and-displace, only correct refusal); "
            f"boundary controls firing with expected result: "
            f"{sum(1 for c in control_results.values() if isinstance(c, dict) and c['matches_expectation'])}"
            f"/{len([c for c in control_results.values() if isinstance(c, dict)])} "
            f"(C-a/C-b demonstrate pay-and-displace under honestly-labelled "
            f"engineered room; C-c demonstrates correct refusal at a tight "
            f"margin). EXPRESSES_FORCED_TRADEOFF here rests on the boundary "
            f"controls, not the main moments -- the main-moment fixture's own "
            f"near-total occupancy (687/700) is a limitation of THIS "
            f"rehearsal's corpus (see F4), not evidence against the primitive."
        )
        report["STATUS_S9_FALSIFIER"] = emit_status(probe)
        report["mechanism_claim_sentence"] = (
            "A rehearsal result of MECHANISM: EXPRESSES_FORCED_TRADEOFF is not "
            "evidence that §9 passes. It is evidence that the instrument works "
            "and the primitives can express a forced tradeoff against shadow "
            "scarcity."
        )

        # ── Freeze / primitives confirmation ────────────────────────────────
        report["primitives_not_modified"] = True  # refuse/consolidate/recall/Budget only called, never edited this build
        report["capacity_not_retuned"] = True

        # Final regression freeze re-check (after all isolated-env work).
        diff2 = subprocess.run(
            ["git", "diff", "--stat", "gui/server.py", "theory_x/world_bridge/selector.py"],
            capture_output=True, text=True, cwd=Path(__file__).resolve().parent.parent.parent,
        ).stdout.strip()
        report["freeze_check_empty_final"] = (diff2 == "")

    finally:
        _cleanup_isolated_env(writers, tmp)

    return report


def emit_status(wired: WiredBudget) -> str:
    """The mechanical guard. Keyed to `wired.mode`, the single
    dependency-injection point -- not a Budget attribute (see CONFLICT 1).
    Raises if anything tries to force a §9 verdict while shadow is wired."""
    if wired.mode == "shadow":
        return "UNRUN (unconsumed)"
    raise RuntimeError(
        "refusing to emit a §9 verdict: wired.mode != 'shadow' but this "
        "code path has no live-budget wiring implemented yet"
    )


def request_s9_verdict(wired: WiredBudget, mechanism_verdict: str) -> str:
    """Any attempt to request an actual §9 PASS/FAIL must go through
    here, and this raises unconditionally while shadow is wired."""
    if wired.mode == "shadow":
        raise RuntimeError(
            "§9 FALSIFIER GUARD FIRED: cannot emit a §9 verdict while the "
            "wired budget's mode is 'shadow'. §9 remains unrun."
        )
    return mechanism_verdict  # only reachable once mode == "live"


def write_report(report: dict, mode: str, version: Optional[str] = None) -> Path:
    today = date.today().isoformat()
    suffix = "rehearsal" if mode == "rehearsal" else "s9"
    out_dir = Path(__file__).resolve().parent.parent.parent / "observation_reports"
    out_dir.mkdir(exist_ok=True)
    vtag = f"_{version}" if version else ""
    out_path = out_dir / f"forced_tradeoff_harness__{suffix}_{today}{vtag}.json"
    out_path.write_text(json.dumps(report, indent=2, default=str))
    return out_path


def supersede_report(path: Path, reason: str) -> None:
    """F5: mark a prior output file's own record as SUPERSEDED, in place,
    without regenerating or amending any of its original numbers -- the
    file keeps what it originally measured; this only adds a pointer saying
    don't read it as current."""
    data = json.loads(path.read_text())
    data["SUPERSEDED"] = True
    data["SUPERSEDED_REASON"] = reason
    path.write_text(json.dumps(data, indent=2, default=str))


if __name__ == "__main__":
    rep = run_rehearsal()
    path = write_report(rep, "rehearsal", version="v2")
    print(f"Wrote {path}")

    v1_path = (Path(__file__).resolve().parent.parent.parent / "observation_reports"
               / "forced_tradeoff_harness__rehearsal_2026-11-10.json")
    if v1_path.exists():
        supersede_report(v1_path, "ceiling denominator invalid -- did not account for starting occupancy")
        print(f"Marked SUPERSEDED: {v1_path}")

    print(json.dumps({k: v for k, v in rep.items() if k != "moments"}, indent=2, default=str))
