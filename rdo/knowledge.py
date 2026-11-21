"""Domain knowledge for the demonstration cycle.

This is the ONE place where LLM/human reasoning seeds the engine: the idea is
decomposed into top-level obligations, and each gets a *reconciliation signature*
— a read-only pattern that proves whether a real mechanism exists. The engine
then expands, reconciles against the actual tree, assesses and prioritises
deterministically. Seeds are proposals; the tree is the authority (RDO §22).

Test case: WHATS_NEXT.md §3b / GENIUS_SCORE_v2.md §7 — "deploy the genius
auto-tagger and its consumers." Chosen because the priority doc is from May 2026,
so reconciliation against HEAD is the whole point.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from .model import ANTI_REQUIREMENT, NECESSARY, Obligation
from .reconcile import Signature


def genius_tagger_idea() -> Tuple[str, List[str], List[Obligation], Dict[str, List[Signature]]]:
    objective = ("Deploy the calibrated genius v2 score as an auto-tagger and its "
                 "consumers (WHATS_NEXT.md §3b / GENIUS_SCORE_v2.md §7a-7e + consumers).")
    assumptions = [
        "WHATS_NEXT.md (last updated 2026-05) reflects current state",
        "the v2 score is calibrated and must not be re-fit",
        "consumers (retrieval bias, fountain prompt context) are not yet built "
        "(per tagger.py docstring)",
    ]
    seeds = [
        Obligation("genius_tags", "genius_tags output table (§7a)", "persistence",
                   rationale="auto-tagger needs a place to write scores"),
        Obligation("genius_tagger", "genius tagger daemon (§7b/§7c)", "daemon",
                   rationale="score every fountain fire continuously"),
        Obligation("genius_api", "/api/genius/recent + HUD panel (§7d/§7e)", "api",
                   rationale="surface recent tags"),
        Obligation("genius_score", "calibrated v2 score", "score",
                   rationale="the signal being deployed"),
        Obligation("genius_consumer_fountain", "fountain prompt reads recent tags (consumer B)",
                   "consumer", rationale="bias generation toward striking material"),
        Obligation("genius_consumer_retrieval", "retrieval favours high-score fires (consumer A)",
                   "consumer", rationale="weight fetch/selection by genius score"),
        Obligation("genius_runtime_verification", "observe tagger+consumers firing at runtime",
                   "runtime_verification", classification=NECESSARY,
                   rationale="source existence does not prove runtime behaviour"),
        # anti-requirements (deliberately NOT to be built)
        Obligation("anti_second_score", "do not build a second genius score", "anti_requirement",
                   classification=ANTI_REQUIREMENT,
                   rationale="v2 is calibrated (97.1% training acc, GENIUS_SCORE_v2.md); a "
                             "competing score would duplicate and could de-calibrate"),
        Obligation("anti_duplicate_tags_store", "do not create a second tags store",
                   "anti_requirement", classification=ANTI_REQUIREMENT,
                   rationale="genius_tags already persists in conversations.db; a second store "
                             "would fragment provenance"),
    ]
    signatures: Dict[str, List[Signature]] = {
        "genius_tags": [
            Signature(r"CREATE TABLE IF NOT EXISTS genius_tags", "substrate/init_db.py",
                      "genius_tags table DDL (§7a)")],
        "genius_tagger": [
            Signature(r"class GeniusTagger", "theory_x/genius", "GeniusTagger daemon (§7b)"),
            Signature(r"Wiring genius tagger", "run.py", "boot wiring (§7c)")],
        "genius_api": [
            Signature(r"api/genius/recent", "gui/server.py", "/api/genius/recent route (§7d)"),
            Signature(r"def overview", "theory_x/genius/panel.py", "HUD panel (§7e)")],
        "genius_score": [
            Signature(r"WEIGHTS_PATH|def .*score", "theory_x/genius/score_v2.py", "v2 score module"),
            Signature(r"genius_score_weights", None, "fitted weights file")],
        "genius_consumer_fountain": [
            Signature(r"FROM genius_tags", "theory_x/stage6_fountain/generator.py",
                      "generation reads genius_tags (consumer B)")],
        "genius_consumer_retrieval": [
            Signature(r"genius.{0,40}(focus_num|branch_temp|_retrieve_context|retriev).{0,40}weight"
                      r"|retriev.{0,40}genius.{0,20}(score|weight|boost)",
                      "theory_x/stage6_fountain",
                      "retrieval/fetch weighted by genius score (consumer A)")],
    }
    return objective, assumptions, seeds, signatures


def migration_defect_idea() -> Tuple[str, List[str], List[Obligation], Dict[str, List[Signature]]]:
    """A DIFFERENT development pattern from the genius deploy cycle: defect
    remediation. Objective = the two pre-existing migration bugs listed under
    WHATS_NEXT.md "Open questions" (arc_closers column; beliefs.content UNIQUE
    dedup). Tests whether the Extrapolator generalises to a fix/guard pattern.
    Signatures live on the defect CHILDREN (fix/migration/regression_test/...),
    so each defect seed expands and every sub-obligation reconciles on its own."""
    objective = ("Remediate + guard the pre-existing migration defects (beliefs.content "
                 "UNIQUE dedup; arc_closers column) — WHATS_NEXT.md open questions.")
    assumptions = [
        "the migration bugs listed in WHATS_NEXT.md (2026-05) are still open",
        "a fix may already be applied but unguarded by a regression test",
    ]
    seeds = [
        Obligation("beliefs_content_uniq", "beliefs.content UNIQUE dedup defect", "defect",
                   rationale="duplicate orphan/problem beliefs were possible before the unique index"),
        Obligation("arc_closers_migration", "arc_closers closure_type column defect", "defect",
                   rationale="arc_closers table needed a closure_type column migration"),
    ]
    signatures: Dict[str, List[Signature]] = {
        # --- beliefs.content UNIQUE dedup ---
        "beliefs_content_uniq.fix": [
            Signature(r"idx_beliefs_content_(orphan|problem)_uniq", "substrate/init_db.py",
                      "UNIQUE index fix applied")],
        "beliefs_content_uniq.migration": [
            Signature(r"rows removed|migration applied|oldest row kept", "substrate/init_db.py",
                      "dedup migration applied (comment)")],
        "beliefs_content_uniq.root_cause": [
            Signature(r"UNIQUE constraint on beliefs\.content is EXPECTED", "substrate/writer.py",
                      "root cause handled in writer")],
        "beliefs_content_uniq.regression_test": [
            Signature(r"idx_beliefs_content|IntegrityError.*content|UNIQUE.*beliefs.*content",
                      "tests", "DB-level dedup regression test")],
        # --- arc_closers column migration ---
        "arc_closers_migration.fix": [
            Signature(r"ALTER TABLE arc_closers ADD COLUMN", "substrate/init_db.py",
                      "arc_closers migration applied")],
        "arc_closers_migration.regression_test": [
            Signature(r"arc_closers", "tests", "arc_closers regression test")],
    }
    return objective, assumptions, seeds, signatures


def genius_consumers() -> List[dict]:
    """Source-grounded classification of every consumer of the genius signal.

    Built by READING each file (not counting). Each row cites a grep anchor + line
    range so `tension.assess_signal_authority` can verify it still holds, and
    records the dimensions the founder asked to distinguish: access (direct read /
    indirect-via-file / inline compute / status / threshold), influence (behavioural
    / advisory / observability / housekeeping), conditional, magnitude, safeguards,
    and evidence_class (implemented / tested / inferred / unknown). Runtime gain is
    'unknown' everywhere — NEX is in STANDBY, so no behaviour has been observed.
    """
    return [
        {"file": "theory_x/stage_affect/affect_state.py", "anchor": "SELECT class FROM genius_tags",
         "access": "direct_read", "influence": "behavioural", "target": "mood polarity",
         "conditional": True, "magnitude": "bounded: weight 0.30, nudge+result clamped [-1,1]",
         "safeguards": ["try/except -> 0.0", "clamped"], "evidence_class": "implemented",
         "lines": "371-383", "self_derived": True},
        {"file": "theory_x/stage6_fountain/readiness.py", "anchor": "_genius_modulation",
         "access": "direct_read", "influence": "behavioural", "target": "fountain readiness/cadence",
         "conditional": True, "magnitude": "bounded: _GENIUS_MAX_PENALTY, subtractive, linear",
         "safeguards": ["opt-in flag (modulation_disabled)", "min-sample guard", "subtractive only"],
         "evidence_class": "implemented", "lines": "95-176", "self_derived": True},
        {"file": "theory_x/stage6_fountain/generator.py", "anchor": "FROM genius_tags",
         "access": "direct_read", "influence": "behavioural", "target": "generation (anti-template)",
         "conditional": True, "magnitude": "prompt-level bias (not a clamp-absorbed scalar)",
         "safeguards": ["read-only select"], "evidence_class": "implemented",
         "lines": "2700,3174", "self_derived": True},
        {"file": "theory_x/stage6_fountain/crystallizer.py", "anchor": "_genius_score",
         "access": "inline_compute", "influence": "behavioural", "target": "belief crystallisation (upgrade)",
         "conditional": True, "magnitude": "gated: upgrades only if strictly higher score",
         "safeguards": ["strict-improvement gate"], "evidence_class": "implemented",
         "lines": "608-649", "self_derived": True},
        {"file": "theory_x/stage_throw_net/voice_engine.py", "anchor": "_enrich_with_genius",
         "access": "direct_read", "influence": "behavioural", "target": "belief-candidate ranking",
         "conditional": True, "magnitude": "bounded: neutral 0.5 default -> no shift if unscored",
         "safeguards": ["neutral default", "try/except -> error logged, no crash"],
         "evidence_class": "implemented", "lines": "208-232", "self_derived": True},
        {"file": "theory_x/stage_tom/quality_synthesis.py", "anchor": "genius score",
         "access": "indirect_file", "influence": "behavioural", "target": "attention magnitude multiplier",
         "conditional": False, "magnitude": "MATERIAL: 1.20x amplify / 0.82x dampen per branch",
         "safeguards": ["5-min recompute cadence"], "evidence_class": "implemented",
         "lines": "3-13,52", "self_derived": True,
         "note": "strongest, least-bounded, unconditional; feeds attention -> self-reinforcement candidate"},
        {"file": "theory_x/stage_self_narrative/self_narrative.py", "anchor": "genius_tags",
         "access": "direct_read", "influence": "advisory", "target": "rut-notice into narrative_log",
         "conditional": True, "magnitude": "indirect: surfaces a note; she decides, no mechanical change",
         "safeguards": ["throttled >=2h", "reflective loop decides"], "evidence_class": "implemented",
         "lines": "122-156", "self_derived": False},
        {"file": "theory_x/stage6_fountain/__init__.py", "anchor": "genius_modulation",
         "access": "status", "influence": "observability", "target": "status dict (wired/disabled)",
         "conditional": False, "magnitude": "none", "safeguards": [], "evidence_class": "implemented",
         "lines": "66", "self_derived": False},
        {"file": "theory_x/snapshots/snapshots.py", "anchor": "_TIER_GENIUS",
         "access": "threshold", "influence": "housekeeping", "target": "retention tier (genius kept forever)",
         "conditional": False, "magnitude": "none (retention only)", "safeguards": [],
         "evidence_class": "implemented", "lines": "38-46", "self_derived": False},
    ]
