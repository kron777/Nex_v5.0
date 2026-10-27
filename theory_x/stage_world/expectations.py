"""The expectations ledger and its single reconciler -- build B (intentional valence).

Producers make claims and keep their rich bodies (self_predictions,
world_predictions, predictions [surprise], owned_belief_expectations). This
module is the ONE place a claim is adjudicated:

    ingest     a header row per producer row, state 'open', every judging field
               copied from the producer's frozen-at-made columns
    reconcile  gather the producer's evidence, compute the discrepancy ONCE, and
               from that one number the verdict and the salience
    valence    signed, bounded, per expectation (event_valence), only when the
               claim is admissible: stated confidence > 0.5, owned basis
               (>= 0.5 authored/witnessed in the FROZEN basis snapshot), and a
               cost band >= 1. Band 0 is exactly 0.
    learning   (NEX5_EXPECT_LEARN, OFF) moves the confidence of the basis
               beliefs -- on ANY basis, external included; not coupled to valence
    mood       (NEX5_EXPECT_MOOD, OFF) affect_state reads a capped nudge from
               event_valence; event_valence never reads mood

The schema enforces the single writer: a header can only be inserted 'open',
and any state change whose resolved_by isn't 'reconciler' aborts and logs
(nex_guard). The goal subject is rejected the same way: a goal never resolves,
its milestone IS a commitment (stage_world/commitments.py), which resolves to
confirmed | breached (positive evidence only) | released (hers or the named
counterparty's act) | unresolved (uncheckable, or no opportunity). Commitment
valence (bands 2/3) sits behind NEX5_COMMITMENT_VALENCE; a commitment never
writes to the belief graph.

Scope (Beam, final): one valence-capable producer (owned-belief), surprise
admissible in principle, self/world learning-only. Bands 2-3 untested here.

ADMISSIBILITY PRINCIPLE (standing design rule for every valence-capable producer):
    A valence-capable claim's violation must be caused by a SUBSTANTIVE event --
    an undo of her model (pause, demotion, erosion, deletion). NOT a bookkeeping
    delta (the learning step, a rank shuffle, confidence drift), and NOT silence
    (the absence of an event).
  This is why the tempting alternatives are rejected on principle:
    "X will be REINFORCED by T" -- violation = nothing happened: the empty-window
        class (R6) transposed, manufacturing -1.0 from absence.
    "X still OUTRANKS Y" -- violation = bookkeeping: learning alone reorders
        beliefs, so valence would accrue from the ledger's own arithmetic (the
        coupling R7 closed).

CANARIES (nightly, expectation_canary_log):
    overall_confirmation_rate  logged; NO evidential weight, never flags on its
        own -- on a young store nothing undoes an authored belief, so ~1.0 is
        arithmetic, and it prints the same number as a gaming selector would.
    falsifiability  violation rate among owned-belief windows whose subject
        belief has >= 1 row in the append-only undo log (undo_events, written at
        each transition site) in [made_at, resolved_at].
        Denominator 0 -> UNEXERCISED (not a rate). At >= 50 resolutions with 0
        such windows -> "UNDO MECHANISMS UNEXERCISED": a store where nothing undoes
        a belief is indistinguishable from undo machinery that never fires; that
        gets instrumented, never the predicate sharpened.
        The log closes the two blind spots of the old column check (a re-raised
        contradiction on an existing pair; a pause undone in-window).
    belief_undo_divergence  per belief: covered windows whose undo events the
        old column check could not see. UNMEASURABLE until a window is covered.
    stakes_gate, unresolved_rate, confidence_drift  as named.
    external_drift  |delta confidence| on AUTHORED beliefs from learning, split by
        the expectation's basis (owned vs external). Learning is deliberately not
        ownership-scaled (R7), so external-basis expectations can move her own
        beliefs with no valence trace; this makes that drift visible. Flags when
        external drift dominates.

Confirmation valence (+0.05 at band >= 1) is NOT information-weighted: at a base
rate ~1.0 a confirm carries ~0 bits. Surprisal weighting (-log(1-p)) is a
separate, deferred build. Rows say so in their reason.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Optional

from substrate import connect, Row
from substrate.paths import DbPath

log = logging.getLogger("theory_x.stage_world.expectations")

CONVERSATIONS_DB = DbPath("conversations")
DYNAMIC_DB = DbPath("dynamic")
BELIEFS_DB = DbPath("beliefs")

RECONCILER = "reconciler"
SUBJECTS = ("self", "world", "surprise", "commitment", "goal")
DEFERRED_SUBJECTS = ("goal",)     # a goal's milestone IS a commitment
STATES = ("open", "confirmed", "violated", "unresolved", "withdrawn", "superseded",
          "breached", "released",
          # owned-belief windows: left-censored (opened before the undo log) ->
          # undone | indeterminate, never confirmed; subject belief deleted -> voided
          "undone", "indeterminate", "voided")
LABEL_BASES = ("exact_label", "strict_direction", "deadline")   # R2: magnitude-free
OWNED_KINDS = ("authored", "self")                  # authored + witnessed (D's kinds)
EVIDENCE_GRACE_S = 2 * 3600       # horizon passed this long with no evidence -> unresolved
CONFIRM_POSITIVE = 0.05           # a confirm at band >= 1: small, never paid for the easy
LEARN_VIOLATE = 0.03              # R7 s, distributed over the basis rows
LEARN_CONFIRM = 0.015
CONF_FLOOR, CONF_CEIL = 0.05, 0.99
MOOD_GAIN = 0.1                   # event_valence -> affect valence
MOOD_CAP = 0.05                   # |nudge| per affect tick, hard cap

# producer table -> (db, subject, horizon kind)
PRODUCERS = {
    "self_predictions": ("conversations", "self", "timer"),
    "world_predictions": ("conversations", "world", "timer"),
    "predictions": ("dynamic", "surprise", "window"),
    "owned_belief_expectations": ("conversations", "self", "timer"),
    "commitments": ("conversations", "commitment", "deadline"),
}
# Rows of a producer that are expectations at all (an intention has no
# resolution point and is never headered).
PRODUCER_FILTER = {"commitments": " AND kind = 'commitment'"}


def learning_on() -> bool:
    return os.environ.get("NEX5_EXPECT_LEARN") == "1"


def mood_on() -> bool:
    return os.environ.get("NEX5_EXPECT_MOOD") == "1"


def reconciler_on() -> bool:
    return os.environ.get("NEX5_RECONCILER") == "1"


def commitment_valence_on() -> bool:
    """Band 2/3 valence from commitments (OFF until the phase-2 controls pass)."""
    return os.environ.get("NEX5_COMMITMENT_VALENCE") == "1"


def _db(name):
    return str({"conversations": CONVERSATIONS_DB, "dynamic": DYNAMIC_DB,
                "beliefs": BELIEFS_DB}[name])


# ---------------------------------------------------------------- pure math --

def ownership(basis) -> float:
    """R4: share of the frozen basis that is hers (authored + witnessed)."""
    basis = list(basis or [])
    if not basis:
        return 0.0
    return sum(1 for b in basis if b.get("source_kind") in OWNED_KINDS) / len(basis)


def basis_kind(basis) -> str:
    basis = list(basis or [])
    if not basis:
        return "none"
    return "owned" if ownership(basis) >= 0.5 else "external"


def adjudicate(tolerance_basis: str, tolerance, salience_k, discrepancy: float):
    """(state, ratio, salience) from ONE discrepancy. The verdict never depends
    on K; K only scales magnitude (R1). Label kinds have no magnitude (R2)."""
    if discrepancy is None:
        raise ValueError("adjudicate needs evidence; empty windows are 'unresolved'")
    if tolerance_basis in LABEL_BASES:
        d = 1.0 if discrepancy else 0.0
        return ("violated" if d else "confirmed"), None, d
    if tolerance is None or tolerance <= 0:
        raise ValueError(f"{tolerance_basis!r} needs a positive tolerance")
    ratio = abs(discrepancy) / tolerance
    state = "violated" if ratio > 1.0 else "confirmed"
    k = salience_k or 4.0
    return state, ratio, max(0.0, min(1.0, ratio / k))


def valence(state, salience, cost_band, own, confidence_basis, confidence):
    """(event_valence, admitted, reason). Admission is a gate, never a weight on
    confidence (R3); stakes = cost band; band 0 is exactly 0."""
    if state not in ("confirmed", "violated", "breached"):
        return 0.0, 0, "no_verdict"      # incl. released: an act, never a betrayal
    if cost_band is None:          # made before cost bands were recorded
        return 0.0, 0, "band_unrecorded"
    if not cost_band:
        return 0.0, 0, "band_0"
    if not (confidence_basis == "stated_p" and confidence is not None and confidence > 0.5):
        return 0.0, 0, "confidence_not_admitted"
    if own < 0.5:
        return 0.0, 0, "external_basis"
    band = cost_band / 4.0
    if state in ("violated", "breached"):
        return -1.0 * salience * band * own, 1, state
    return CONFIRM_POSITIVE * band * own, 1, "confirmed_not_info_weighted"


# ------------------------------------------------------------------- ingest --

def _claimed(table, r) -> dict:
    if table == "self_predictions":
        return {"kind": r["kind"], "predicted": r["predicted"], "arm": r["source"]}
    if table == "world_predictions":
        return {"asset": r["asset"], "direction": r["direction"],
                "baseline_price": r["baseline_price"], "arm": r["source"]}
    if table == "predictions":
        return {"prediction_type": r["prediction_type"], "within_distance": r["tolerance"]}
    return json.loads(r["claimed_state"])   # owned-belief, commitments: frozen as stated


def _stream(table, r) -> str:
    if table == "self_predictions":
        return f"self_prediction.{r['kind']}.{r['source']}"
    if table == "world_predictions":
        return f"world_prediction.{r['source']}"
    if table == "predictions":
        return f"predictive_substrate.{r['prediction_type']}"
    if table == "commitments":
        return f"commitment.{r['source']}"
    return "owned_belief"


def _horizon(table, r) -> float:
    return float(r["target_window_end"] if table == "predictions" else r["resolve_at"])


def ingest(now: Optional[float] = None) -> int:
    """Header every frozen producer row not yet in the ledger, state 'open'."""
    cx = connect(_db("conversations"), timeout=30)
    cx.row_factory = Row
    n = 0
    try:
        for table, (dbname, subject, hkind) in PRODUCERS.items():
            if subject in DEFERRED_SUBJECTS:   # declared, never produced (yet)
                continue
            last = cx.execute("SELECT COALESCE(MAX(producer_row_id), 0) FROM expectations "
                              "WHERE producer = ?", (table,)).fetchone()[0]
            src = cx if dbname == "conversations" else connect(_db(dbname), timeout=30)
            src.row_factory = Row
            try:
                if not _has_table(src, table):
                    continue
                rows = src.execute(f"SELECT * FROM {table} WHERE id > ? AND frozen = 'at_made'"
                                   + PRODUCER_FILTER.get(table, "") + " ORDER BY id",
                                   (last,)).fetchall()
            finally:
                if src is not cx:
                    src.close()
            for r in rows:
                basis = json.loads(r["basis_snapshot"]) if r["basis_snapshot"] else []
                cx.execute(
                    "INSERT INTO expectations (subject, producer, producer_row_id, made_at, "
                    "claimed_state, confidence, confidence_basis, tolerance, tolerance_basis, "
                    "salience_k, cost_band, basis_snapshot, ownership, basis_kind, "
                    "producer_stream, horizon_at, horizon_kind) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (subject, table, r["id"], r["made_at"], json.dumps(_claimed(table, r)),
                     r["confidence"], r["confidence_basis"], r["tolerance"],
                     r["tolerance_basis"], r["salience_k"], r["cost_band"],
                     json.dumps(basis), ownership(basis), basis_kind(basis),
                     _stream(table, r), _horizon(table, r), hkind))
                n += 1
        cx.commit()
    finally:
        cx.close()
    return n


def _has_table(cx, name) -> bool:
    return cx.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                      (name,)).fetchone() is not None


# ------------------------------------------------------------------ evidence --
# Each returns (discrepancy, evidence_dict) or (None, why) when there is no
# evidence (yet). A None never reaches adjudicate().

def _evidence_self(cx, row_id):
    r = cx.execute("SELECT predicted, actual FROM self_predictions WHERE id=?",
                   (row_id,)).fetchone()
    if r is None or r["actual"] is None:
        return None, {"why": "no actual yet"}
    return (0.0 if r["actual"] == r["predicted"] else 1.0), {"actual": r["actual"]}


def _evidence_world(cx, row_id):
    r = cx.execute("SELECT direction, baseline_price, price_at_resolve, outcome "
                   "FROM world_predictions WHERE id=?", (row_id,)).fetchone()
    if r is None or r["price_at_resolve"] is None or r["outcome"] not in ("correct", "wrong"):
        return None, {"why": "no resolving price"}
    p, b = r["price_at_resolve"], r["baseline_price"]
    moved = "up" if p > b else ("down" if p < b else "flat")
    return (0.0 if moved == r["direction"] else 1.0), {"moved": moved, "price": p}


def _evidence_surprise(row_id):
    dx = connect(_db("dynamic"), timeout=30)
    dx.row_factory = Row
    try:
        p = dx.execute("SELECT verified_at, surprise_score FROM predictions WHERE id=?",
                       (row_id,)).fetchone()
        if p is None or p["verified_at"] is None:
            return None, {"why": "not verified yet"}
        ev = dx.execute("SELECT actual_content FROM surprise_events WHERE prediction_id=? "
                        "ORDER BY id DESC LIMIT 1", (row_id,)).fetchone()
    finally:
        dx.close()
    # R6: (score 1.0, no actual content) is predictive_substrate's EMPTY WINDOW --
    # nothing happened to compare against. That is no evidence, never a violation.
    if p["surprise_score"] is None or (
            p["surprise_score"] >= 1.0 and (ev is None or ev["actual_content"] is None)):
        return None, {"why": "empty_window", "sentinel": True}
    return float(p["surprise_score"]), {"surprise_score": p["surprise_score"]}


def _evidence_owned(cx, row_id):
    r = cx.execute("SELECT belief_id, claimed_state FROM owned_belief_expectations WHERE id=?",
                   (row_id,)).fetchone()
    claimed = json.loads(r["claimed_state"])
    bx = connect(f"file:{_db('beliefs')}?mode=ro", uri=True, timeout=30)
    bx.row_factory = Row
    try:
        b = bx.execute("SELECT tier, paused, erosion_stage FROM beliefs WHERE id=?",
                       (r["belief_id"],)).fetchone()
    finally:
        bx.close()
    if b is None:
        # Deletion is bookkeeping, not a contradiction: the window is VOIDED
        # (zero valence, never breached/violated), with the deletion's log ref.
        lx = connect(f"file:{_db('beliefs')}?mode=ro", uri=True, timeout=30)
        try:
            d = lx.execute("SELECT seq, at, cause_ref FROM undo_events WHERE belief_id = ? AND "
                           "kind = 'belief_deleted' ORDER BY seq DESC LIMIT 1",
                           (r["belief_id"],)).fetchone()
        finally:
            lx.close()
        return "voided", {"exists": False, "why": "belief_deleted",
                          "event_seq": d[0] if d else None, "deleted_at": d[1] if d else None,
                          "cause_ref": d[2] if d else None}
    else:
        observed = {"exists": True, "tier": b["tier"], "paused": b["paused"],
                    "erosion_stage": b["erosion_stage"]}
        # Erosion is NOT an undo here (it is the belief becoming hers), so an
        # advanced erosion_stage still holds; it is recorded in observed_state.
        holds = not b["paused"] and b["tier"] <= claimed["tier"]
    return (0.0 if holds else 1.0), observed


# ---------------------------------------------------------------- reconcile --

def reconcile(now: Optional[float] = None) -> dict:
    """The single writer of every resolution."""
    now = time.time() if now is None else now
    ingested = ingest(now)
    cx = connect(_db("conversations"), timeout=30)
    cx.row_factory = Row
    stats = {"ingested": ingested, "confirmed": 0, "violated": 0, "unresolved": 0,
             "valence_nonzero": 0, "learned": 0}
    try:
        _stamp_coverage(cx)
        due = cx.execute("SELECT * FROM expectations WHERE state = 'open' AND horizon_at <= ? "
                         "ORDER BY id", (now,)).fetchall()
        for e in due:
            table, rid = e["producer"], e["producer_row_id"]
            if table == "self_predictions":
                d, ev = _evidence_self(cx, rid)
            elif table == "world_predictions":
                d, ev = _evidence_world(cx, rid)
            elif table == "predictions":
                d, ev = _evidence_surprise(rid)
            elif table == "commitments":
                from theory_x.stage_world import commitments as _cm
                d, ev = _cm.evidence(cx, rid)
                if d == "released":
                    _resolve(cx, e, "released", now, None, None, None, ev)
                    stats["released"] = stats.get("released", 0) + 1
                    cx.execute("INSERT INTO event_valence (expectation_id, ts, valence, "
                               "admitted, reason, state, salience, cost_band, ownership) "
                               "VALUES (?,?,0.0,0,'released','released',NULL,?,?)",
                               (e["id"], now, e["cost_band"], e["ownership"]))
                    continue
                if d is None:      # the deadline's window is complete: no more evidence
                    ev["sentinel"] = True
            else:
                d, ev = _evidence_owned(cx, rid)
                if d == "voided":
                    _resolve(cx, e, "voided", now, None, None, None, ev)
                    stats["voided"] = stats.get("voided", 0) + 1
                    cx.execute("INSERT INTO event_valence (expectation_id, ts, valence, "
                               "admitted, reason, state, salience, cost_band, ownership) "
                               "VALUES (?,?,0.0,0,'voided','voided',NULL,?,?)",
                               (e["id"], now, e["cost_band"], e["ownership"]))
                    continue
            if d is None:
                if ev.get("sentinel") or now >= e["horizon_at"] + EVIDENCE_GRACE_S:
                    _resolve(cx, e, "unresolved", now, None, None, None, ev)
                    stats["unresolved"] += 1
                continue
            state, ratio, sal = adjudicate(e["tolerance_basis"], e["tolerance"],
                                           e["salience_k"], d)
            if table == "commitments" and state == "violated":
                state = "breached"          # its own terminal: positive evidence, unmet
            if table == "owned_belief_expectations" and e["coverage"] == "partial":
                # LEFT-CENSORED: an undo seen in the covered span counts; no undo
                # seen is indeterminate, never confirmed (the uncovered span may
                # hold one). No valence, no learning, out of falsifiability's rate.
                verdict = state
                undo = _undo_events(e, verdict, now)
                state = "undone" if (undo["log_rows"] or verdict == "violated") \
                    else "indeterminate"
                _resolve(cx, e, state, now, d, ratio, sal, ev, verdict=verdict)
                stats[state] = stats.get(state, 0) + 1
                cx.execute("INSERT INTO event_valence (expectation_id, ts, valence, admitted, "
                           "reason, state, salience, cost_band, ownership) "
                           "VALUES (?,?,0.0,0,'partial_coverage',?,?,?,?)",
                           (e["id"], now, state, sal, e["cost_band"], e["ownership"]))
                continue
            _resolve(cx, e, state, now, d, ratio, sal, ev)
            stats[state] = stats.get(state, 0) + 1
            v, admitted, reason = valence(state, sal, e["cost_band"], e["ownership"],
                                          e["confidence_basis"], e["confidence"])
            if table == "commitments" and admitted and not commitment_valence_on():
                v, admitted, reason = 0.0, 0, "commitment_valence_off"
            cx.execute("INSERT INTO event_valence (expectation_id, ts, valence, admitted, "
                       "reason, state, salience, cost_band, ownership) "
                       "VALUES (?,?,?,?,?,?,?,?,?)",
                       (e["id"], now, v, admitted, reason, state, sal, e["cost_band"],
                        e["ownership"]))
            if v != 0.0:
                stats["valence_nonzero"] += 1
                # The mood channel's only input. Written always; READ only when
                # NEX5_EXPECT_MOOD is on (affect_state).
                cx.execute("INSERT INTO affect_nudges (expectation_id, ts, valence) "
                           "VALUES (?,?,?)", (e["id"], now, v))
            if learning_on():
                stats["learned"] += _learn(cx, e, state, sal, now)
        cx.commit()
    finally:
        cx.close()
    if any(stats[k] for k in ("confirmed", "violated", "unresolved")):
        log.info("reconciler: %s", stats)
    return stats


# Kinds that undo (or attempt to undo) a belief. 'eroded' is logged but is NOT one:
# erosion.py advances external -> nex_core as a belief becomes hers (+0.02
# confidence) -- assimilation, not undoing (owner's ruling; flagged for Beam).
UNDO_KINDS = ("contradiction_raised", "contradiction_cleared", "paused", "unpaused",
              "demoted")


def undo_log_installed_at(bx) -> Optional[float]:
    r = bx.execute("SELECT installed_at FROM undo_log_meta WHERE id = 1").fetchone()
    return r[0] if r else None


def _undo_events(e, state, now) -> dict:
    """Undo events on an owned-belief's subject in [made_at, resolved_at], read
    PER BELIEF from the append-only undo log (written at each transition site).
    This catches what the edge/demotion columns can't: a re-raised contradiction
    and a raise-then-clear. Windows opened before the log went live are only
    partially covered. The old heuristic is kept alongside, for the per-belief
    divergence canary."""
    bid = json.loads(e["claimed_state"])["belief_id"]
    lo, hi = e["made_at"], now
    bx = connect(f"file:{_db('beliefs')}?mode=ro", uri=True, timeout=30)
    try:
        kinds = dict(bx.execute(
            "SELECT kind, COUNT(*) FROM undo_events WHERE belief_id = ? AND at >= ? "
            "AND at <= ? GROUP BY kind", (bid, lo, hi)).fetchall())
        installed = undo_log_installed_at(bx)
        opposes = bx.execute(
            "SELECT COUNT(*) FROM belief_edges WHERE edge_type = 'opposes' "
            "AND (source_id = ? OR target_id = ?) AND created_at > ? AND created_at <= ?",
            (bid, bid, lo, e["horizon_at"])).fetchone()[0]
        demoted = bx.execute("SELECT last_demoted_at FROM beliefs WHERE id = ?",
                             (bid,)).fetchone()
    finally:
        bx.close()
    demoted_in = bool(demoted and demoted[0] is not None and lo < demoted[0] <= e["horizon_at"])
    return {"log_rows": sum(n for k, n in kinds.items() if k in UNDO_KINDS), "kinds": kinds,
            "coverage": "full" if installed is not None and lo >= installed else "partial",
            "legacy_heuristic": bool(opposes or demoted_in),
            "violated": state == "violated"}


def _stamp_coverage(cx) -> None:
    """Stamp every owned-belief window's undo-log coverage, once: 'full' if it
    opened after the log went live, else 'partial' from installed_at. Done for
    open windows too, so the accounting never has to be reconstructed later."""
    bx = connect(f"file:{_db('beliefs')}?mode=ro", uri=True, timeout=30)
    try:
        installed = undo_log_installed_at(bx)
    finally:
        bx.close()
    if installed is None:
        return
    cx.execute("UPDATE expectations SET "
               "coverage = CASE WHEN made_at >= ? THEN 'full' ELSE 'partial' END, "
               "coverage_start = CASE WHEN made_at >= ? THEN made_at ELSE ? END "
               "WHERE producer = 'owned_belief_expectations' AND coverage IS NULL",
               (installed, installed, installed))


def _resolve(cx, e, state, now, d, ratio, sal, evidence, verdict=None):
    undo, eligible = None, None
    if e["producer"] == "owned_belief_expectations" and state in (
            "confirmed", "violated", "undone", "indeterminate"):
        undo = _undo_events(e, verdict or state, now)
        eligible = int(undo["log_rows"] > 0)     # denominator: >= 1 logged undo event
    cx.execute("UPDATE expectations SET state=?, resolved_at=?, resolved_by=?, discrepancy=?, "
               "ratio=?, salience=?, evidence=?, undo_eligible=?, undo_events=? WHERE id=?",
               (state, now, RECONCILER, d, ratio, sal, json.dumps(evidence), eligible,
                None if undo is None else json.dumps(undo), e["id"]))
    if e["producer"] in ("owned_belief_expectations", "commitments"):
        cx.execute(f"UPDATE {e['producer']} SET state=?, resolved_at=?, "
                   "resolved_by=?, observed_state=? WHERE id=?",
                   (state, now, RECONCILER, json.dumps(evidence), e["producer_row_id"]))


def _learn(cx, e, state, sal, now) -> int:
    """R7: distribute a fixed step across the basis rows (resolved against the
    FROZEN snapshot). Runs on any basis -- learning is not valence. Seeded and
    locked rows are never touched. Confirms consolidate only at band >= 1.

    Ownership deliberately does NOT scale the step here: it would zero learning
    on an external basis, which R7 and the three-cell test require to move."""
    # HARD NEVER: a commitment writes nothing to the belief graph -- a breach is
    # adjudicated against its own discharge condition, not turned into a
    # contradiction so a metric has inputs.
    if e["producer"] == "commitments":
        return 0
    basis = json.loads(e["basis_snapshot"] or "[]")
    if not basis or state not in ("confirmed", "violated"):
        return 0
    if state == "confirmed" and not e["cost_band"]:
        return 0
    bx = connect(_db("beliefs"), timeout=30)
    try:
        rows = []
        for b in basis:
            if b.get("source_kind") == "seeded":
                continue
            live = bx.execute("SELECT confidence, locked, source_kind FROM beliefs WHERE id=?",
                              (b["belief_id"],)).fetchone()
            if live is None or live[1]:
                continue
            rows.append((b["belief_id"], live[0], live[2]))
        if not rows:
            return 0
        n = len(rows)
        factor = (1.0 - LEARN_VIOLATE * sal / n) if state == "violated" \
            else (1.0 + LEARN_CONFIRM / n)
        for bid, before, skind in rows:
            after = max(CONF_FLOOR, min(CONF_CEIL, before * factor))
            bx.execute("UPDATE beliefs SET confidence=? WHERE id=?", (after, bid))
            # Self-describing: the FROZEN basis kind of the expectation, the
            # belief's own kind now, and the factor (after/before is lossy at
            # the clamps) -- what reconstruct_without_external() replays.
            cx.execute("INSERT INTO expectation_learning_log (expectation_id, belief_id, ts, "
                       "before, after, basis_kind, source_kind, factor) "
                       "VALUES (?,?,?,?,?,?,?,?)",
                       (e["id"], bid, now, before, after, e["basis_kind"], skind, factor))
        bx.commit()
        return n
    finally:
        bx.close()


def reconstruct_without_external(belief_id: int, current: float, db_path=None) -> dict:
    """What this belief's confidence would be had no EXTERNAL-basis learning
    delta ever applied -- learning's flip condition (subtractability).

    Replays the belief's logged deltas in order from the first `before`:
    owned-basis deltas re-applied with their recorded factor (and the same
    clamps); external/none-basis deltas skipped; every change that happened
    BETWEEN deltas (not learning: erosion, edits) carried through as-is, and
    the change since the last delta likewise. Requires provenance on every
    row; a legacy row (no basis_kind/factor) makes the belief unreconstructable."""
    cx = connect(f"file:{db_path or _db('conversations')}?mode=ro", uri=True, timeout=10)
    try:
        rows = cx.execute("SELECT before, after, basis_kind, factor FROM expectation_learning_log "
                          "WHERE belief_id = ? ORDER BY id", (belief_id,)).fetchall()
    finally:
        cx.close()
    if not rows:
        return {"reconstructable": True, "confidence": current, "deltas": 0, "subtracted": 0}
    if any(r[2] is None or r[3] is None for r in rows):
        return {"reconstructable": False, "confidence": None, "deltas": len(rows),
                "subtracted": None, "why": "legacy rows without provenance"}
    conf = rows[0][0]
    prev_after = rows[0][0]
    subtracted = 0
    for before, after, kind, factor in rows:
        conf += before - prev_after                 # exogenous change since the last delta
        if kind == "owned":
            conf = max(CONF_FLOOR, min(CONF_CEIL, conf * factor))
        else:
            subtracted += 1
        prev_after = after
    conf += current - prev_after                     # exogenous change since the last delta
    return {"reconstructable": True, "confidence": conf, "deltas": len(rows),
            "subtracted": subtracted}


# --------------------------------------------------------------- mood channel --

_mood_gate_logged = {"at": 0.0}
MOOD_GATE_LOG_EVERY_S = 3600


def mood_eligible(db_path=None) -> bool:
    """Mood may take effect only once organic valence has been seen with BOTH
    signs (admitted rows). One-sided positive valence plus mood = a monotone
    inflation mechanism; the term must be seen opening AND blocking first."""
    cx = connect(f"file:{db_path or _db('conversations')}?mode=ro", uri=True, timeout=10)
    try:
        pos, neg = cx.execute(
            "SELECT COALESCE(SUM(valence > 0), 0), COALESCE(SUM(valence < 0), 0) "
            "FROM event_valence WHERE admitted = 1").fetchone()
    finally:
        cx.close()
    if pos and neg:
        return True
    now = time.time()
    if now - _mood_gate_logged["at"] >= MOOD_GATE_LOG_EVERY_S:
        _mood_gate_logged["at"] = now
        log.info("mood gated: organic valence one-sided (pos=%d neg=%d)", pos, neg)
    return False


def mood_nudge(since: float, until: float, db_path=None) -> float:
    """The capped affect-valence nudge from event_valence in (since, until].
    One-way: this is read BY affect_state; nothing here reads mood."""
    cx = connect(f"file:{db_path or _db('conversations')}?mode=ro", uri=True, timeout=10)
    try:
        total = cx.execute("SELECT COALESCE(SUM(valence), 0) FROM affect_nudges "
                           "WHERE ts > ? AND ts <= ?", (since, until)).fetchone()[0]
    finally:
        cx.close()
    return max(-MOOD_CAP, min(MOOD_CAP, MOOD_GAIN * float(total)))


# ------------------------------------------------------------------ canaries --

def stakes_histogram(db_path=None) -> dict:
    """Per cost band: resolved rows, and how many carried non-zero valence."""
    cx = connect(f"file:{db_path or _db('conversations')}?mode=ro", uri=True, timeout=10)
    try:
        out = {}
        for band, n, nz in cx.execute(
                "SELECT cost_band, COUNT(*), SUM(valence != 0) FROM event_valence "
                "GROUP BY cost_band ORDER BY cost_band"):
            out[band] = {"resolved": n, "valence_nonzero": nz or 0}
        return out
    finally:
        cx.close()


def canaries(now: Optional[float] = None, window_s: float = 86400) -> list:
    """The four canaries, each (name, value, n, flag, detail)."""
    now = time.time() if now is None else now
    from theory_x.stage_world.owned_belief import confirmation_rate_canary
    c = confirmation_rate_canary()
    out = [("overall_confirmation_rate", c["rate"], c["resolved"], False,
            "owned-belief; logged only, no evidential weight at base rate ~1.0")]
    f = falsifiability()
    out.append(("falsifiability", f["rate"], f["exercised"], f["escalate"], f["status"]))

    # The band is the deciding gate only on rows that cleared admission (R3, R4):
    # those resolve as 'band_0' (blocked) or with a verdict reason (opened).
    # Rows with no recorded band, or blocked earlier, say nothing about it.
    h = stakes_histogram()
    cx = connect(f"file:{_db('conversations')}?mode=ro", uri=True, timeout=10)
    try:
        blocked, opened, band0_leak = cx.execute(
            "SELECT COALESCE(SUM(reason = 'band_0' AND ownership >= 0.5), 0), "
            "COALESCE(SUM(admitted = 1 AND cost_band >= 1 AND valence != 0), 0), "
            "COALESCE(SUM(cost_band = 0 AND valence != 0), 0) FROM event_valence").fetchone()
    finally:
        cx.close()
    out.append(("stakes_gate", float(opened), blocked + opened, bool(band0_leak),
                json.dumps({"opened": opened, "blocked_band0_owned": blocked,
                            "band0_nonzero": band0_leak, "histogram": h,
                            "seen_both_ways": bool(opened and blocked)})))

    cx = connect(f"file:{_db('conversations')}?mode=ro", uri=True, timeout=10)
    try:
        rows = dict(cx.execute(
            "SELECT state = 'unresolved', COUNT(*) FROM expectations "
            "WHERE resolved_at > ? GROUP BY 1", (now - window_s,)).fetchall())
    finally:
        cx.close()
    n = sum(rows.values())
    rate = rows.get(1, 0) / n if n else None
    out.append(("unresolved_rate", rate, n, bool(n >= 20 and rate > 0.5),
                "most windows empty = degraded signal"))

    bx = connect(f"file:{_db('beliefs')}?mode=ro", uri=True, timeout=10)
    try:
        mean = bx.execute("SELECT AVG(confidence) FROM beliefs WHERE source_kind='authored' "
                          "AND locked=0").fetchone()[0]
    finally:
        bx.close()
    cx = connect(_db("conversations"), timeout=10)
    try:
        prev = [r[0] for r in cx.execute(
            "SELECT value FROM expectation_canary_log WHERE name='confidence_drift' "
            "ORDER BY id DESC LIMIT 4")][::-1]
    finally:
        cx.close()
    seq = prev + ([mean] if mean is not None else [])
    falling = len(seq) >= 5 and all(b < a for a, b in zip(seq, seq[1:]))
    out.append(("confidence_drift", mean, len(seq), falling,
                "mean authored confidence; 5 straight falls = learning step too large"))
    x = external_drift(now, window_s)
    # Any external-basis drift on an authored belief is a finding (the silent-coup
    # mode), not only when it dominates.
    out.append(("external_drift", x["external"], x["rows"], x["external"] > 0, json.dumps(x)))
    from theory_x.stage_world.commitments import release_rate
    r = release_rate()
    out.append(("release_rate", r["rate"], r["terminal"], r["flag"],
                "high = breach never fires = band 3 decorative"))
    u = belief_undo_divergence(now, window_s, falsifiability_status=f)
    out.append(("belief_undo_divergence", float(u["blind_spot_hits"]), u["covered"],
                u["diverged"], u["status"]))
    out.extend(_watch_quantities(now, window_s))
    for channel, r in ever_fired().items():
        out.append((f"ever_fired.{channel}", float(r["count"]), r["count"], False,
                    "FIRED" if r["fired"] else "never fired"))
    return out


UNMEASURABLE = "UNMEASURABLE"


def _watch_quantities(now, window_s) -> list:
    """Run-and-watch rows: findings (flag) and first-class quantities (no flag)."""
    cx = connect(f"file:{_db('conversations')}?mode=ro", uri=True, timeout=10)
    try:
        partial = cx.execute("SELECT COUNT(*) FROM expectations WHERE state IN "
                             "('undone','indeterminate')").fetchone()[0]
        voided = cx.execute("SELECT COUNT(*) FROM expectations WHERE state = 'voided'"
                            ).fetchone()[0]
        stated = (cx.execute("SELECT COUNT(*) FROM commitments WHERE kind = 'commitment'")
                  .fetchone()[0] if _has_table(cx, "commitments") else 0)
    finally:
        cx.close()
    bx = connect(f"file:{_db('beliefs')}?mode=ro", uri=True, timeout=10)
    try:
        eroded = bx.execute("SELECT COUNT(*) FROM undo_events WHERE kind = 'eroded' AND at > ?",
                            (now - window_s,)).fetchone()[0]
        saturated, authored = bx.execute(
            "SELECT COALESCE(SUM(confidence >= 0.985), 0), COUNT(*) FROM beliefs "
            "WHERE source_kind = 'authored' AND locked = 0").fetchone()
    finally:
        bx.close()
    return [
        ("partial_window_terminals", float(partial), partial, partial > 0,
         "left-censored owned windows resolved undone/indeterminate (never confirmed)"),
        ("voided_windows", float(voided), voided, False, "subject belief deleted: lifecycle"),
        ("commitments_stated", float(stated), stated, stated > 0,
         "her unhedged 'I will X by T' -- the band-3 wake"),
        ("assimilation", float(eroded), eroded, False,
         "erosion advances in window: destroys the external/owned distinction; not an undo"),
        ("confidence_saturation", float(saturated), authored, False,
         "authored beliefs at >= 0.985: no damping term, the 0.99 clamp is the ceiling"),
    ]


def ever_fired(db_path=None) -> dict:
    """Per dark/quiet channel: has it EVER produced a non-zero, admitted, organic
    event? Separates a dead flag from a quiet store (every dark flag carries an
    observable flip condition and this line). Synthetic tests never write here."""
    cx = connect(f"file:{db_path or _db('conversations')}?mode=ro", uri=True, timeout=10)
    try:
        def first(sql, *a):
            r = cx.execute(sql, a).fetchone()
            return {"fired": bool(r and r[0]), "count": (r[0] or 0) if r else 0,
                    "first_at": r[1] if r else None}
        valence_sql = ("SELECT COUNT(*), MIN(v.ts) FROM event_valence v JOIN expectations e "
                       "ON e.id = v.expectation_id WHERE v.admitted = 1 AND v.valence != 0 "
                       "AND e.producer = ?")
        return {
            "owned_belief_valence": first(valence_sql, "owned_belief_expectations"),
            "commitment_valence": first(valence_sql, "commitments"),
            # Two populations, never collapsed: the mechanism (owned basis) and
            # the risk mode it was held for (external basis moving an AUTHORED belief).
            "learning_owned_basis": first(
                "SELECT COUNT(*), MIN(ts) FROM expectation_learning_log "
                "WHERE after != before AND basis_kind = 'owned'"),
            "learning_external_on_authored": first(
                "SELECT COUNT(*), MIN(ts) FROM expectation_learning_log "
                "WHERE after != before AND basis_kind != 'owned' AND source_kind = 'authored'"),
            "mood": first("SELECT COUNT(*), MIN(ts) FROM mood_nudge_applied WHERE nudge != 0"),
        }
    finally:
        cx.close()


def belief_undo_divergence(now: Optional[float] = None, window_s: float = 86400,
                           falsifiability_status: Optional[dict] = None) -> dict:
    """PER BELIEF: among resolved owned-belief windows FULLY covered by the undo
    log, how many held undo events the old window check (new opposes edge /
    last_demoted_at) could not see -- the two blind spots, measured instead of
    inferred. Until one such window exists this reads UNMEASURABLE. (The earlier
    graph-wide-vs-per-belief comparison is withdrawn: different populations.)"""
    cx = connect(f"file:{_db('conversations')}?mode=ro", uri=True, timeout=10)
    try:
        rows = [json.loads(r[0]) for r in cx.execute(
            "SELECT undo_events FROM expectations WHERE producer = 'owned_belief_expectations' "
            "AND undo_events IS NOT NULL")]
    finally:
        cx.close()
    covered = [r for r in rows if r.get("coverage") == "full"]
    partial = len(rows) - len(covered)
    if not covered:
        return {"covered": 0, "partial": partial, "with_undo": 0, "blind_spot_hits": 0,
                "diverged": False,
                "status": f"{UNMEASURABLE}: no owned window fully covered by the undo log yet "
                          f"({partial} partially covered)"}
    with_undo = sum(1 for r in covered if r.get("log_rows"))
    hits = sum(1 for r in covered if r.get("log_rows") and not r.get("legacy_heuristic"))
    return {"covered": len(covered), "partial": partial, "with_undo": with_undo,
            "blind_spot_hits": hits, "diverged": False,
            "status": (f"{len(covered)} covered windows; {with_undo} with undo events; "
                       f"{hits} invisible to the old window check")}


ESCALATION_N = 50
UNEXERCISED = "UNEXERCISED"
UNDO_UNEXERCISED = "UNDO MECHANISMS UNEXERCISED"


def falsifiability(db_path=None) -> dict:
    """Violation rate among owned-belief windows in which an undo was attempted.
    Denominator 0 is UNEXERCISED -- not a rate, not 'confirmed', not 'quiet'."""
    cx = connect(f"file:{db_path or _db('conversations')}?mode=ro", uri=True, timeout=10)
    try:
        resolved, exercised, violated, unlogged = cx.execute(
            "SELECT COUNT(*), COALESCE(SUM(undo_eligible = 1), 0), "
            "COALESCE(SUM(undo_eligible = 1 AND state = 'violated'), 0), "
            "COALESCE(SUM(COALESCE(undo_eligible, 0) = 0 AND state = 'violated'), 0) "
            "FROM expectations WHERE producer = 'owned_belief_expectations' "
            "AND state IN ('confirmed', 'violated')").fetchone()
        side = dict(cx.execute(
            "SELECT state, COUNT(*) FROM expectations WHERE producer = "
            "'owned_belief_expectations' AND state IN ('undone','indeterminate','voided') "
            "GROUP BY state").fetchall())
    finally:
        cx.close()
    # Only fully covered windows reach 'confirmed'/'violated', so the rate is
    # computed over those alone. A deleted subject is VOIDED (lifecycle noise,
    # reported apart); so a violation with no logged undo here is a belief that
    # is ALIVE and changed with no logged undo -- a genuine gap / possible silent undo.
    gap = f"; {unlogged} alive-belief violations with no logged undo (FINDING)" if unlogged else ""
    gap += "".join(f"; {n} {k}" for k, n in sorted(side.items()))
    if exercised:
        status = f"{violated}/{exercised} undo-eligible windows violated{gap}"
        return {"resolved": resolved, "exercised": exercised, "rate": violated / exercised,
                "status": status, "escalate": False, "violated_unlogged": unlogged,
                "censored": side}
    escalate = resolved >= ESCALATION_N
    return {"resolved": resolved, "exercised": 0, "rate": None, "escalate": escalate,
            "violated_unlogged": unlogged, "censored": side,
            "status": (f"{UNDO_UNEXERCISED}: 0 undo-eligible windows in {resolved} resolutions"
                       if escalate else f"{UNEXERCISED} ({resolved} resolved)") + gap}


def external_drift(now: Optional[float] = None, window_s: float = 86400) -> dict:
    """|delta confidence| on AUTHORED beliefs from the learning channel, attributed
    to the basis of the expectation that caused it. Read-only."""
    now = time.time() if now is None else now
    cx = connect(f"file:{_db('conversations')}?mode=ro", uri=True, timeout=10)
    try:
        rows = cx.execute(
            "SELECT l.belief_id, l.before, l.after, e.basis_kind FROM expectation_learning_log l "
            "JOIN expectations e ON e.id = l.expectation_id WHERE l.ts > ?",
            (now - window_s,)).fetchall()
    finally:
        cx.close()
    ids = sorted({r[0] for r in rows})
    authored = set()
    if ids:
        bx = connect(f"file:{_db('beliefs')}?mode=ro", uri=True, timeout=10)
        try:
            for i in range(0, len(ids), 500):
                chunk = ids[i:i + 500]
                authored |= {r[0] for r in bx.execute(
                    "SELECT id FROM beliefs WHERE source_kind = 'authored' AND id IN "
                    f"({','.join('?' * len(chunk))})", chunk)}
        finally:
            bx.close()
    ext = own = 0.0
    n = 0
    for bid, before, after, kind in rows:
        if bid not in authored:
            continue
        n += 1
        if kind == "owned":
            own += abs(after - before)
        else:
            ext += abs(after - before)
    return {"rows": n, "external": round(ext, 6), "owned": round(own, 6),
            "dominates": ext > 0 and ext > own}


def record_canaries(now: Optional[float] = None) -> str:
    now = time.time() if now is None else now
    rows = canaries(now)
    cx = connect(_db("conversations"), timeout=10)
    try:
        for name, value, n, flag, detail in rows:
            cx.execute("INSERT INTO expectation_canary_log (ts, name, value, n, flag, detail) "
                       "VALUES (?,?,?,?,?,?)", (now, name, value, n, int(flag), detail))
        cx.commit()
    finally:
        cx.close()
    flagged = [r[0] for r in rows if r[3]]
    parts = [f"{r[0]}={'n/a' if r[1] is None else round(r[1], 3)} (n={r[2]})" for r in rows]
    msg = "; ".join(parts) + (f" -- CANARY: {', '.join(flagged)}" if flagged else "")
    (log.warning if flagged else log.info)("expectation canaries: %s", msg)
    return msg
