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


def genius_feedback_hypothesis() -> dict:
    """The complete POTENTIAL feedback path for the genius-signal -> attention
    authority concern, documented as a HYPOTHESIS. It stays a hypothesis until the
    whole path is demonstrated by runtime evidence; the multipliers are NOT changed.
    Source-grounded from theory_x/stage_tom/quality_synthesis.py (writes the signal)
    and attention._magnitude_for (applies the multiplier)."""
    return {
        "classification": "HYPOTHESIS",
        "status": "unverified — NEX in STANDBY; no runtime gain measured",
        "path": [
            "1. a fountain fire is scored by genius v2; the tagger writes genius_tags",
            "2. quality_synthesis.py pulls recent genius-tagged fires, joins hot_branch "
            "(dynamic.db), computes mean genius score per branch -> data/quality_signal.json",
            "3. attention._magnitude_for reads quality_signal.json (~5 min) and applies "
            "1.20x amplify (high-genius branch) / 0.82x dampen (low-genius) to sense events",
            "4. amplified branches accumulate focus_num faster -> fire more often",
            "5. more fires on that branch -> more genius-tagged fires for it -> can raise its "
            "mean genius score -> back to step 2 (candidate POSITIVE feedback)",
        ],
        "gain_variables": [
            "amplify/dampen factors (1.20x / 0.82x) = per-cycle loop gain",
            "quality_signal recompute cadence (~5 min) = loop delay",
            "KEY UNKNOWN: is the genius score content-driven (same content -> same score, "
            "regardless of fire rate) or branch-correlated? content-driven => self-limiting; "
            "branch-correlated => self-confirming",
            "mean-over-window averaging (sample size / window) = damping of per-fire noise",
            "focus_num saturation at fire time (r80: 96% of fires >=0.90 readiness) may cap effect",
        ],
        "existing_safeguards": [
            "bonsai.py diversity_recency (cools hot branches) + diversity_starvation (lifts cold "
            "branches toward parity) — a countervailing force against runaway concentration",
            "the dampen side (0.82x) is bounded and does not run away",
            "belief-learning safeguards (external-basis caps, sign-symmetry / basis-composition "
            "canaries, subtractable provenance) guard the belief arm of any loop",
            "cadence + windowed mean damp high-frequency feedback",
        ],
        "runtime_observations_needed": [
            "controlled gain measurement: a branch's mean genius score BEFORE vs AFTER its "
            "amplifier is applied, multiplier on vs off — flat => not self-reinforcing",
            "branch concentration over time (HHI / firing-branch coverage) with quality_synthesis "
            "on vs off — does amplification reduce diversity beyond what diversity_starvation corrects?",
            "monotonic vs stabilising fire-share trajectory for high-genius branches over many cycles",
            "confirm the score is content-driven (same content scores equally regardless of branch)",
            "use a blind primary (coverage/HHI), NOT p_on_subject (definitional) — matches the "
            "DAG's existing falsifier discipline",
        ],
        "decision_rule": "self-reinforcing only if measured loop gain exceeds the combined damping "
                         "(diversity mechanisms + windowed averaging) across cycles; until then, HYPOTHESIS.",
        "do_not": "do NOT change the 1.20x/0.82x multipliers or any influence behaviour before this "
                  "is established by runtime evidence (host-only).",
    }


def affinity_drift_idea() -> Tuple[str, List[str], List[Obligation], Dict[str, List[Signature]]]:
    """Third objective, a fresh discovery cycle: guard the beliefs.affinity schema-drift
    defect. affinity / affinity_updated_at were read+written by affinity_loop but defined
    in NO schema file — they exist only via an init_db migration, so a fresh init_all()
    once produced a beliefs table without them ("no such column: affinity"). Unlike
    arc_closers, these columns are MIGRATION-ONLY (not in the base schema), so a single
    fresh-init test genuinely exercises the migration — applying the
    `migration_guard_needs_legacy_path` lesson, no separate legacy fixture is needed."""
    objective = ("Guard the beliefs.affinity / affinity_updated_at schema-drift migration "
                 "(init_db.py:247-248) with a regression test: a fresh init_all() must provision "
                 "both columns as nullable (affinity IS NULL = not-yet-rated).")
    assumptions = [
        "the affinity columns are migration-only (not in beliefs.sql) — confirmed",
        "affinity_loop depends on 'affinity IS NULL' meaning not-yet-rated",
    ]
    seeds = [
        Obligation("beliefs_affinity", "beliefs.affinity schema-drift defect", "defect",
                   rationale="columns read/written by affinity_loop but in no schema -> 'no such "
                             "column: affinity' on a fresh init before the migration was added"),
    ]
    signatures: Dict[str, List[Signature]] = {
        "beliefs_affinity.fix": [
            Signature(r"ALTER TABLE beliefs ADD COLUMN affinity REAL", "substrate/init_db.py",
                      "affinity migration present")],
        "beliefs_affinity.root_cause": [
            Signature(r"no such column|out-of-band|affinity IS NULL", "substrate/init_db.py",
                      "root cause documented in the migration note")],
        "beliefs_affinity.regression_test": [
            Signature(r"def test_init_all_provisions_affinity", "tests",
                      "fresh-init affinity-provisioning regression test")],
    }
    return objective, assumptions, seeds, signatures


def config_invariant_idea() -> Tuple[str, List[str], List[Obligation], Dict[str, List[Signature]]]:
    """Third objective, a genuinely different pattern (config/observability, NOT a
    migration): guard the nex_config flag-registry forward-consistency. Every NEX5_
    flag READ in NEX source must be registered in KNOWN_FLAGS, else unknown_flags()
    silently mis-flags a real flag as a typo. Reconciled: 167 registered, 151 read,
    0 read-but-unregistered — the invariant holds, so this is a proactive guard."""
    objective = ("Guard nex_config flag-registry forward-consistency: every NEX5_ flag read in "
                 "NEX source must be registered in KNOWN_FLAGS (so unknown_flags() cannot "
                 "mis-flag a real flag as a typo).")
    assumptions = [
        "KNOWN_FLAGS (nex_config.py) is the authoritative registry",
        "flag reads use literal os.environ.get/getenv/environ[] patterns",
        "the invariant currently holds (reconciled: 0 read-but-unregistered)",
    ]
    seeds = [
        Obligation("flag_registry_consistency", "every read NEX5_ flag is registered", "invariant",
                   rationale="a read flag missing from the registry is silently mis-flagged as a "
                             "typo by unknown_flags(); the registry can drift from usage"),
    ]
    signatures: Dict[str, List[Signature]] = {
        "flag_registry_consistency.specify": [
            Signature(r"def unknown_flags|def is_known", "nex_config.py",
                      "detection mechanism (KNOWN_FLAGS registry) exists")],
        "flag_registry_consistency.guard_test": [
            Signature(r"def test_every_read_flag_is_registered", "tests",
                      "registry/usage consistency guard test")],
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
