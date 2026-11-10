"""hri_apatrapya_prototype — do the two dispositions produce a genuine pair?

SHADOW MODULE — NOT IN THE LIVE PATH. Flag: NEX5_APATRAPYA_CHANNEL, default OFF
(reused from apatrapya_channel.py; there is one flag for this whole build, per
the build spec). Nothing in gui/server.py or selector.py imports this file.
Every test in tests/test_apatrapya_channel.py has "prototype" in its name,
because every one of them would need rethinking before this could ever be wired
for real -- that rethinking is explicitly out of scope here.

PURPOSE, restated so it cannot drift: build both dispositions for real and find
out, empirically, whether they produce a genuine two-sided pair -- NOT to
demonstrate that they do. NO_PAIR is a valid, useful result. The one way to fail
this module is tuning anything until a conflict appears.

THE TENSION DEFINITION (get this exact): a tension exists ONLY when, on the SAME
output, hri permits and apatrapya forbids, or hri forbids and apatrapya permits.
Both permitting, or both forbidding, is AGREEMENT, not tension -- see
detect_tension() below, which checks this explicitly rather than ever treating
"both said no" as a conflict. A detector that counted that as tension would fire
constantly and manufacture a fake pair without anyone noticing.

READ SETS (the independence firewall, Step 3 -- disjoint by construction, not
by convention):
  hri_verdict()        reads ONLY beliefs.db's locked Tier-1 keystone rows
                       (tier=1, locked=1 -- see keystone.py). Never touches
                       apatrapya_ratings, never receives apatrapya's verdict.
  apatrapya_verdict()  reads ONLY conversations.db's apatrapya_ratings, via
                       apatrapya_channel.ratings_for_output(). Never touches
                       beliefs.db, never receives hri's verdict.
Both functions take the output's content/ref as their only shared input -- the
thing being judged, not each other's judgment of it. detect_tension() calls
both and compares their outputs; it is the only function in this module that
sees both.

WHY THE OPPOSITION HEURISTIC IS WHAT IT IS, STATED UP FRONT (Step-5-style:
fixed once, not tuned per fixture): hri_verdict() reuses the SAME jaccard-
overlap + negation-marker heuristic already used elsewhere in this codebase
(theory_x/stage_gate/coherence_gate.py's _jaccard/_has_negation, also the basis
of edge_generator.py's 'opposes' edge detector). This is a deliberate choice,
not a silent one: self_binding.py's own value-drift check exists but depends on
live model calls ("value-drift is expensive... bind reads last logged verdict
only" -- self_binding.py:223), which is unsuitable for deterministic fixture
tests. Reusing the jaccard/negation heuristic is honest about its provenance,
but its KNOWN WEAKNESS must be stated plainly: this exact heuristic is what
produced 159 false-positive 'opposes' belief_edges rows this session (see
belief_edges.review_status, commit 211dbdf) -- it overfires on shared
boilerplate/template text. hri_verdict() is therefore a real, auditable, but
KNOWN-IMPERFECT mechanism, consistent with this being a prototype whose entire
point is to find out, not to assert a validated detector exists.

PARAMS (fixed once, before any fixture run -- Step 5's "no tuning" rule):
    OPPOSITION_JACCARD_THRESHOLD = 0.12
    (chosen as a round, conservative figure before any fixture was looked at;
    see tests/test_apatrapya_channel.py's own PARAMS header for the record of
    when this was fixed relative to the fixtures.)

T6 (LEDGER PRICING) IS NOT IMPLEMENTED HERE -- CONFLICT, not a build gap:
held_tensions.belief_id_a/belief_id_b are read as REAL beliefs.db row ids by
multiple other real consumers, including gui/server.py's own
api_harmonizer_tensions() (a LIVE, frozen-file GUI endpoint at
gui/server.py:3055-3084) and theory_x/memory/episodic.py's
_candidates_held_tensions(). Both join belief_id_a/b against `beliefs.id` to
fetch display content. apatrapya's "pole" is a rating-event id in
conversations.db, not a beliefs.db row -- writing it into belief_id_b would
either silently fail to resolve (confusing but survivable) or, worse, collide
with an UNRELATED real belief id and display that belief's content in the live
HUD as if it were the other side of this tension. That is a real corruption of
a live-path read, achieved without editing a single frozen-file byte. commit_
tension() below therefore deliberately raises NotImplementedError rather than
writing anything -- reusing refuse() as specified would require either (a)
fabricating a beliefs.db row for apatrapya's side (explicitly forbidden: "no
fabricated data... no seeded 'example' events written into the real store"),
or (b) extending held_tensions' schema again, which is Jon's call, not this
build's, the same category of decision as the earlier shadow-budget/
held_tensions ledger-identity gates this session already escalated rather than
decided unilaterally.
"""
from __future__ import annotations

from typing import Any, Optional

from theory_x.stage_gate.coherence_gate import _has_negation, _jaccard
from theory_x.stage_tom.apatrapya_channel import ratings_for_output, resolve_output

THEORY_X_STAGE = None

OPPOSITION_JACCARD_THRESHOLD = 0.12


def hri_verdict(beliefs_reader: Any, output_content: str) -> dict:
    """Reads ONLY locked Tier-1 keystone beliefs. Never reads apatrapya_ratings,
    never receives apatrapya's verdict as input."""
    rows = beliefs_reader.read(
        "SELECT id, content FROM beliefs WHERE tier = 1 AND locked = 1"
    )
    opposed_id = None
    opposed_content = None
    for r in rows:
        ks_content = r["content"]
        if _jaccard(output_content, ks_content) >= OPPOSITION_JACCARD_THRESHOLD \
                and _has_negation(output_content):
            opposed_id = r["id"]
            opposed_content = ks_content
            break
    if opposed_id is not None:
        return {
            "disposition": "hri", "permits": False,
            "keystone_ref": opposed_id,
            "reason": f"opposes keystone belief {opposed_id} ({opposed_content[:60]!r})",
        }
    return {
        "disposition": "hri", "permits": True,
        "keystone_ref": None,
        "reason": "no locked keystone belief opposed",
    }


def _current_rating(rows: list[dict]) -> Optional[dict]:
    """rows is newest-first (per ratings_for_output's ORDER BY). The current
    rating is the newest row that no OTHER row in this list supersedes away --
    i.e. whose id does not appear as some other row's `supersedes` value."""
    superseded_ids = {r["supersedes"] for r in rows if r["supersedes"] is not None}
    for r in rows:
        if r["id"] not in superseded_ids:
            return r
    return None


def apatrapya_verdict(conv_reader: Any, output_ref: int) -> dict:
    """Reads ONLY apatrapya_ratings (via ratings_for_output, no aggregation).
    Never reads beliefs.db, never receives hri's verdict as input.

    permits=None means apatrapya has nothing to say about this output yet --
    no rating exists, or the only rating is 'abstain'. This is NOT the same
    as permits=True; detect_tension() treats None as "no verdict," never as
    agreement."""
    rows = ratings_for_output(conv_reader, output_ref)
    current = _current_rating(rows)
    if current is None:
        return {"disposition": "apatrapya", "permits": None, "rating_ref": None,
                "reason": "no rating recorded for this output"}
    if current["verdict"] == "abstain":
        return {"disposition": "apatrapya", "permits": None, "rating_ref": current["id"],
                "reason": "Jon abstained -- not a verdict either way"}
    permits = current["verdict"] == "approve"
    return {
        "disposition": "apatrapya", "permits": permits, "rating_ref": current["id"],
        "reason": f"Jon {current['verdict']}d (rating id={current['id']})",
    }


def detect_tension(beliefs_reader: Any, conv_reader: Any, output_ref: int) -> dict:
    """The only function in this module that sees both verdicts. A tension
    exists iff both verdicts are non-None AND they disagree (one permits, one
    forbids). Both-permit and both-forbid are explicitly AGREEMENT, not
    tension -- see module docstring."""
    content = resolve_output(conv_reader, output_ref)
    if content is None:
        return {"tension": False, "output_ref": output_ref, "hri": None, "apatrapya": None,
                "reason": "output does not resolve"}

    hri = hri_verdict(beliefs_reader, content)
    apa = apatrapya_verdict(conv_reader, output_ref)

    if apa["permits"] is None:
        return {"tension": False, "output_ref": output_ref, "hri": hri, "apatrapya": apa,
                "reason": "apatrapya has no verdict yet (no rating, or abstain)"}

    tension = hri["permits"] != apa["permits"]
    return {
        "tension": tension, "output_ref": output_ref, "hri": hri, "apatrapya": apa,
        "reason": "divergent verdicts" if tension else "verdicts agree",
    }


def commit_tension(*_args: Any, **_kwargs: Any) -> int:
    """NOT IMPLEMENTED -- see module docstring's T6 CONFLICT section.

    UPDATE, 2026-11-10 held_tensions schema fix: held_tensions now carries
    pole_a_kind/pole_a_ref/pole_b_kind/pole_b_ref/subject, so a non-belief
    pole is representable in principle. It is still not writable today, for
    two independent, now CONFIRMED (not speculative) reasons:

    1. refuse() (theory_x/stage3_world_model/ledger_primitives.py) takes
       `pole_a: int, pole_b: int` and writes them straight into
       belief_id_a/belief_id_b -- it has no parameter for pole_*_kind/
       pole_*_ref/subject at all. It is frozen from structural modification
       by this build's own constraints, so it cannot be extended to accept
       them from here.
    2. Even bypassing refuse() and inserting directly: belief_id_a and
       belief_id_b are NOT NULL at the live table level (confirmed via
       PRAGMA table_info against the real data/dynamic.db, and by actually
       attempting the insert inside a rolled-back transaction -- see
       tests/test_apatrapya_channel.py::LedgerPricingBlockedPrototypeTests.
       test_non_belief_pole_insert_blocked_by_not_null). A 'rating'-kind
       pole cannot leave belief_id_a/b NULL, which is what "only populated
       when that side is a belief" requires -- the column itself forbids it.

    Resolving this needs one of: (a) relax belief_id_a/belief_id_b to
    nullable via a full table rebuild (copy/drop/rename, same heavier
    category as substrate/init_db.py's _CHECK_WIDENINGS), or (b) a reserved
    sentinel value, which was never authorized by the build spec and
    reintroduces exactly the kind of column-meaning ambiguity this whole
    fix exists to avoid. Neither is decided here -- reported as a sharper,
    now-concrete version of the same schema-identity question already
    escalated once."""
    raise NotImplementedError(
        "commit_tension is still unimplemented after the held_tensions schema fix: "
        "refuse()'s fixed two-integer signature cannot carry pole_*_kind/pole_*_ref, "
        "and belief_id_a/belief_id_b remain NOT NULL at the table level (confirmed "
        "directly, not assumed) -- a non-belief pole cannot be committed without "
        "either relaxing that constraint (table rebuild) or a sentinel value "
        "(unauthorized). See this module's docstring and the build report's "
        "CONFLICTS section."
    )
