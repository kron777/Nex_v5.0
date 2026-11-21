"""Stage 5 (RDO v1.3 §16) — first belief-to-mechanism pathway SPECIFICATION.

The RDO selects and specifies ONE low-risk, falsifiable belief-to-mechanism pathway from the
Stage-4 evidence. This module is read-only and does NOT import `theory_x`/`substrate` (RDO stays
independent); it cites evidence by file:line via grep. The selected pathway is VERIFIED in
isolation, against the REAL mechanism, by `tests/test_belief_confidence_retrieval_pathway.py`.

It does not mistake source presence or a passing isolated test for verified LIVE runtime behaviour:
live confirmation is a host-only gate, kept explicitly UNKNOWN here.
"""
from __future__ import annotations

from typing import Dict, List

from .belief_audit import _grep   # the read-only, .sql-aware evidence grep


# Candidate belief-to-mechanism pathways, evaluated for a FIRST vertical slice.
def _candidates(repo_dir: str) -> List[dict]:
    return [
        {
            "pathway": "confidence -> world-model retrieval (eligibility + relevance ordering)",
            "mechanism": "theory_x/stage3_world_model/retrieval.py :: BeliefRetriever.retrieve",
            "evidence_quality": "high", "functional_significance": "high",
            "risk": "low", "reversibility": "high", "suitability_as_first_slice": "high",
            "evidence": _grep(r"locked = 1 OR confidence >= 0\.15|overlap.*confidence|\* row\[.confidence",
                              repo_dir, "theory_x/stage3_world_model/retrieval.py"),
            "selected": True,
            "why": "deterministic (pure SQL + keyword*confidence), highly evidenced, feeds generation, "
                   "testable in isolation with no live DB, and clearly falsifiable",
        },
        {
            "pathway": "belief_edges (typed) -> spreading activation in retrieval",
            "mechanism": "retrieval spreading-activation blend (belief_edges)",
            "evidence_quality": "high", "functional_significance": "medium",
            "risk": "medium", "reversibility": "high", "suitability_as_first_slice": "medium",
            "selected": False,
            "why": "richer but more complex (edge traversal + 60/40 blend); deferred — not the smallest "
                   "first slice",
        },
        {
            "pathway": "belief_activation recency -> retrieval candidate pool",
            "mechanism": "recency pool (last_touched_at / created_at ordering)",
            "evidence_quality": "medium", "functional_significance": "medium",
            "risk": "low", "reversibility": "high", "suitability_as_first_slice": "medium",
            "selected": False,
            "why": "plausible but weaker, time-dependent evidence; a confidence floor is a cleaner first "
                   "causal proposition",
        },
        {
            "pathway": "belief_boost -> priority lever",
            "mechanism": "belief_boost",
            "evidence_quality": "n/a", "functional_significance": "n/a",
            "risk": "n/a", "reversibility": "n/a", "suitability_as_first_slice": "excluded",
            "evidence": _grep(r"decision-INERT|do NOT build", repo_dir, "tools/check_belief_headroom.py"),
            "selected": False,
            "why": "EXCLUDED by instruction and by its documented decision-INERT 'do NOT build' status; "
                   "not an implementation candidate",
        },
    ]


def select_pathway(repo_dir: str = ".") -> dict:
    """The Stage-5 pathway specification: the selected causal proposition, baseline, the conditions
    for success / failure / inconclusive, rollback requirements, and the host-only runtime gate."""
    cands = _candidates(repo_dir)
    selected = next(c for c in cands if c.get("selected"))
    R = "theory_x/stage3_world_model/retrieval.py"
    return {
        "stage": "RDO v1.3 §16 Stage 5 — first belief-to-mechanism pathway",
        "candidates": cands,
        "excluded": [c["pathway"] for c in cands if c["suitability_as_first_slice"] == "excluded"],
        "selected": selected["pathway"],
        "causal_proposition": {
            "belief_information": "a belief's `confidence` value (and `locked`/`paused`/`tier` gates)",
            "mechanism": "BeliefRetriever.retrieve (world-model relevance retrieval)",
            "relationship": "confidence gates ELIGIBILITY and multiplies the RELEVANCE SCORE",
            "rule_eligibility": "tier<=6 AND paused=0 AND (locked=1 OR confidence>=0.15)",
            "rule_score": "score = keyword_overlap_fraction * confidence",
            "observable_consequence": "an unlocked belief below 0.15 is ABSENT from retrieval; raising "
                                      "its confidence above the floor ADMITS it; among equally "
                                      "keyword-matched beliefs, higher confidence RANKS higher and is "
                                      "more likely to reach generation",
            "evidence": _grep(r"locked = 1 OR confidence >= 0\.15", repo_dir, R)
                        + _grep(r"\* row\[.confidence", repo_dir, R),
        },
        "baseline": "On an isolated fixture of the REAL belief schema, a query-relevant belief at "
                    "confidence 0.10 (unlocked, unpaused, tier 1) is NOT retrieved. This pre-intervention "
                    "state is the baseline (tests/test_belief_confidence_retrieval_pathway.py).",
        "success_if": [
            "below-floor unlocked beliefs are excluded from retrieval",
            "raising confidence above 0.15 admits the belief (in-fixture intervention)",
            "confidence multiplies relevance: higher confidence ranks first among equal keyword matches",
            "locked overrides the floor; paused and tier>6 are excluded",
        ],
        "unsuccessful_if": [
            "an unlocked below-floor belief is retrieved, or confidence does not affect eligibility",
            "confidence does not affect relevance ordering among equal keyword matches",
        ],
        "inconclusive_because": "the isolated test verifies the DOCUMENTED CONTRACT against the real "
                                "mechanism; it does NOT confirm LIVE runtime behaviour on the running "
                                "system with the real belief population. That is host-only and remains UNKNOWN.",
        "rollback": "None required: the Stage-5 work is read-only + isolated (throwaway fixture); no "
                    "live NEX state is changed, so there is nothing to roll back. A future LIVE "
                    "intervention (changing a real belief's confidence to observe retrieval change) "
                    "would require experiment-specific approval, a read-only before snapshot, and a "
                    "documented revert that restores the original confidence.",
        "runtime_observation_gate": {
            "status": "host-only — NOT performed (unauthorised; NEX in standby)",
            "what": "on the running machine, read-only observe retrieval-pool membership + ordering for "
                    "a fixed query, before/after a single belief's confidence crosses 0.15, and confirm "
                    "the predicted admission/ranking change",
            "requires": "host access + experiment-specific approval; read-only (mode=ro) DB reads only",
        },
        "authority_note": "read-only inspection + isolated reversible development only; no live writes, "
                          "injections, flag/config changes, restarts or experiment modifications.",
    }
