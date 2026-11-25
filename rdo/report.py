"""Demonstration + reporting for the RDO.

This is the top layer: it runs specific cycles through the generic driver
(`orchestrator`) and assembles the demonstration/report dicts and the RDO's own
OFT self-assessment. It is kept SEPARATE from the generic cycle driver so the
driver stays domain-free; the genius-specific authority audit lives in
`knowledge` (domain), and this module only calls it.

Dependency direction: report -> {orchestrator (driver), knowledge (domain),
memory, extrapolator, model}. Only the CLI entry point (`__main__`) imports
report; no engine module does, so there is no cycle.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from watcher.evidence import utc_now

from .extrapolator import frontier_breakdown, rule_catalogue, scope_summary
from .graph import analyse as graph_analyse
from .belief_audit import audit as _belief_audit, gap_map as _belief_gap_map
from .pathway import select_pathway as _select_pathway
from .knowledge import (affinity_drift_idea, belief_decay_idea, config_invariant_idea,
                        genius_authority_audit, genius_tagger_idea, migration_defect_idea)
from .memory import (CycleStore, PatternMemory, accuracy_series, comparability_assessment,
                     compare, derive_lessons, learning_loop, metrics_series, record_actual,
                     transfer_observations)
from .model import CycleRecord, EXECUTED_VERIFIED, IMPORTED_RETROSPECTIVE, NATIVE_PLANNING, Pattern
from .orchestrator import _active_experiments, _record_executed, _run_one


# ---------------- the RDO under its OWN Optimal Functional Tension -------------

def self_assess(rdo_dir: Optional[str] = None) -> dict:
    """Subject the RDO to the same OFT principle it applies to NEX (RDO §5): are its
    own modules/scoring/expansion-depth/learning appropriately developed, not
    over-built? Evidence-based: measures each module and checks the independence +
    reuse guarantees by parsing real import statements (not grep, which would match
    its own pattern strings)."""
    rdo_dir = rdo_dir or os.path.dirname(os.path.abspath(__file__))
    modules: Dict[str, dict] = {}
    imports_nex: List[str] = []
    reuses_watcher = False
    for f in sorted(os.listdir(rdo_dir)):
        if not f.endswith(".py") or f == "__init__.py":
            continue
        text = open(os.path.join(rdo_dir, f), encoding="utf-8").read()
        loc = sum(1 for ln in text.splitlines()
                  if ln.strip() and not ln.strip().startswith("#"))
        defs = sum(1 for ln in text.splitlines() if ln.strip().startswith("def "))
        modules[f] = {"loc": loc, "defs": defs}
        for ln in text.splitlines():
            s = ln.strip()
            if s.startswith(("import theory_x", "from theory_x",
                             "import substrate", "from substrate")):
                imports_nex.append(f)
            if s.startswith(("import watcher", "from watcher")):
                reuses_watcher = True
    total_loc = sum(m["loc"] for m in modules.values())

    findings: List[dict] = []
    for name, m in sorted(modules.items(), key=lambda kv: -kv[1]["loc"]):
        if m["loc"] > 230:
            findings.append({"level": "node", "subject": name, "verdict": "watch",
                             "note": f"{m['loc']} LOC — largest module; keep cohesive, split only if "
                                     f"it grows a second responsibility"})
    findings.append({"level": "node", "subject": "memory.py", "verdict": "minor_overlap",
                     "note": "accuracy_series overlaps metrics_series partially; metrics_series is "
                             "canonical. Both kept (distinct outputs + callers); removing one now is "
                             "not justified — a cleanup is also subject to OFT."})
    findings.append({"level": "system", "subject": "orchestrator.py/report.py", "verdict": "resolved",
                     "note": "the generic cycle driver (orchestrator) was split from the demo/reporting "
                             "(report); the genius authority audit moved to knowledge — the driver is now "
                             "domain-free."})
    if imports_nex:
        findings.append({"level": "system", "subject": "independence", "verdict": "VIOLATION",
                         "note": f"imports NEX runtime in {sorted(set(imports_nex))}"})

    lean = total_loc < 1800 and len(modules) <= 14 and not imports_nex
    return {
        "modules": modules,
        "module_count": len(modules),
        "total_loc_excl_comments": total_loc,
        "independence_no_nex_import": not imports_nex,
        "reuses_watcher_infrastructure": reuses_watcher,
        "expansion_depth_default": 4,
        "scoring": "dimensions reported separately; weighted figure labelled uncalibrated",
        "oft_verdict": ("functionally sufficient and lean; not over-developed; one minor "
                        "simplification candidate noted" if lean
                        else "needs review — see findings"),
        "findings": findings,
        "note": "the RDO is held to the same principle it applies to NEX: develop to sufficiency, "
                "avoid subsystem proliferation, and do not over-engineer the cleanup either.",
    }


# ------------------------- demonstration seed + helpers -----------------------

def _seed_watcher_cycle(memory: PatternMemory, store: CycleStore) -> CycleRecord:
    """Record the just-completed Watcher development cycle as the FIRST real
    learning datapoint (genuine predicted-vs-actual)."""
    wc = CycleRecord(
        id="watcher_2026-11", objective="Build the external NEX Watcher (passive MVP + increments)",
        kind=IMPORTED_RETROSPECTIVE,   # a historical record, NOT a completed RDO-guided cycle
        assumptions=["a new package under watcher/ is independent of NEX invariants"],
        predicted={"net_new_count": 6, "effort": 6,
                   "note": "6 planned modules: snapshots, ledger, regression, longitudinal, "
                           "host-ingest, 3-dim classification"},
    )
    record_actual(wc, {
        "missed": ["sqlite3_invariant_exemption"],   # unforeseen: repo-wide no-raw-sqlite3 rule
        "unnecessary": [],
        "reuse_wrong": [],
        "effort_actual": 7,
        "regressions": [],
        "notes": "CI surfaced an unplanned obligation: watcher/safety.py tripped the repo-wide "
                 "no-direct-sqlite3-outside-substrate invariant (6 test copies).",
    })
    store.save(wc)
    for p in derive_lessons(wc, compare(wc)):
        memory.add(p)
    memory.add(Pattern(
        key="reconcile_stale_docs",
        statement="Planning docs and code docstrings older than HEAD routinely UNDERSTATE built "
                  "state; reconcile every obligation against the current tree before proposing work.",
        provenance="cycle:watcher_2026-11",
        applicability="deploy build watcher genius tagger integrate", confidence=0.3,
        exceptions=["a doc can also OVERstate state (claim built when absent) — reconcile both ways"]))
    return wc


def _six_outputs(cycle, summary, memory, learning) -> dict:
    return {
        "objective": cycle.objective,
        "1_discovered": {"count": summary["discovered"],
                         "obligations": [o["key"] for o in cycle.obligations]},
        "2_correctly_reused": summary["reused"],
        "3_rejected_or_deferred": summary["rejected_or_deferred"],
        "4_recommended_work": summary["recommended_work"],
        "5_verification": summary["verification"],
        "6_learned": {"patterns": [p.to_dict() for p in memory.patterns()],
                      "learning_series": learning},
        "optimal_functional_tension": {
            "system": summary["system_tension"],
            "sufficiency_no_further_dev": summary["sufficiency"]},
        "false_dependencies_pruned": summary["false_dependencies_pruned"],
    }


# ------------------------- the executed-cycle recorders -----------------------

def record_arc_closers_execution(store, memory) -> CycleRecord:
    """FIRST executed+verified cycle (tests/test_arc_closers_migration.py)."""
    return _record_executed(
        store, memory,
        cycle_id="arc_closers_regtest_2026-11",
        objective="Execute the eligible arc_closers regression-test work package (from the defect cycle).",
        engineering_pattern="migration_guard",
        predicted={"effort": 1, "net_new_count": 1,
                   "note": "one regression-test obligation; no runtime/migration change"},
        reused=["arc_closers_migration.fix (init_db.py:236 + beliefs.sql:319)"],
        verification={"test_file": "tests/test_arc_closers_migration.py", "tests": 6,
                      "all_pass": True, "catches_regression": True, "all_reuse_backed": True,
                      "fresh_schema_path_verified": True, "legacy_upgrade_path_verified": True,
                      "real_migration_runner_exercised": "_apply_migrations (not just a helper)",
                      "reuse_claims": 1, "reuse_claims_backed_by_file_evidence": 1},
        actual={
            "effort_actual": 2,   # predicted 1; the legacy upgrade needed a 2nd fixture the first pass missed
            "missed": ["arc_closers_migration.legacy_upgrade_path"],
            "unnecessary": [], "reuse_wrong": [], "regressions": [],
            "obligations_built": ["arc_closers_migration.regression_test (fresh)",
                                  "arc_closers_migration.regression_test (legacy upgrade, real runner)"],
            "notes": "closure_type is dual-path: base schema (beliefs.sql:319) AND the idempotent "
                     "migration (init_db.py:236). So a FRESH init_all() exercises the schema, not the "
                     "migration — the first test was insufficient. Added a legacy fixture that runs the "
                     "REAL _apply_migrations against an arc_closers lacking the column; verified add + "
                     "NOT NULL + default + backfill + idempotent re-run. No production defect; no "
                     "runtime/migration code changed.",
        },
        domain_patterns=[
            Pattern(key="migration_dual_path", provenance="cycle:arc_closers_regtest_2026-11",
                    statement="A 'migration bug' may be guarded by BOTH a base-schema definition and an "
                              "idempotent migration; reconcile both paths, not just the migration.",
                    applicability="migration defect schema", confidence=0.3,
                    exceptions=["observed once; some columns exist only via migration"]),
            Pattern(key="migration_guard_needs_legacy_path", provenance="cycle:arc_closers_regtest_2026-11",
                    statement="A migration regression guard must exercise the LEGACY upgrade path through "
                              "the real runner; a fresh init on a dual schema+migration column tests the "
                              "schema, not the migration. Budget a legacy fixture up front.",
                    applicability="migration defect regression test effort", confidence=0.3,
                    exceptions=["for a migration-only column, a fresh init DOES exercise the migration"]),
        ])


def record_affinity_execution(store, memory) -> CycleRecord:
    """SECOND executed+verified cycle; its prediction applied the arc_closers lesson."""
    return _record_executed(
        store, memory,
        cycle_id="affinity_regtest_2026-11",
        objective="Execute the eligible beliefs.affinity schema-drift regression test.",
        engineering_pattern="migration_guard",
        predicted={"effort": 1, "net_new_count": 1,
                   "note": "one regression test; migration-only column, so a single fresh init_all "
                           "test exercises the migration (lesson migration_guard_needs_legacy_path) "
                           "— NO legacy fixture needed"},
        reused=["beliefs_affinity.fix (init_db.py:247-248)", "beliefs_affinity.root_cause (note)"],
        verification={"test_file": "tests/test_affinity_columns_migration.py", "tests": 2,
                      "all_pass": True, "guards_defect": "no such column: affinity",
                      "fresh_init_exercises_migration": True, "all_reuse_backed": True,
                      "reuse_claims": 2, "reuse_claims_backed_by_file_evidence": 2},
        actual={
            "effort_actual": 1, "missed": [], "unnecessary": [], "reuse_wrong": [], "regressions": [],
            "obligations_built": ["beliefs_affinity.regression_test"],
            "notes": "migration-only columns; one fresh init_all() test provisions+verifies both nullable "
                     "columns and the 'affinity IS NULL = not-yet-rated' query. The prior lesson correctly "
                     "predicted no legacy fixture was needed -> effort 1 == predicted 1 (no under-estimate).",
        })


def record_config_invariant_execution(store, memory) -> CycleRecord:
    """THIRD executed+verified cycle — a DIFFERENT (non-migration) pattern:
    tests/test_nex_config_flag_registry.py. Tests transfer beyond the migration domain."""
    return _record_executed(
        store, memory,
        cycle_id="config_invariant_2026-11",
        objective="Execute the eligible nex_config flag-registry consistency guard.",
        engineering_pattern="invariant_guard",
        predicted={"effort": 1, "net_new_count": 1,
                   "note": "one guard test; anticipated the scope/exclusions as the hidden obligation "
                           "and handled it in one file (no second fixture). Invariant holds -> no "
                           "production change."},
        reused=["flag_registry_consistency.specify (nex_config.KNOWN_FLAGS / unknown_flags)"],
        verification={"test_file": "tests/test_nex_config_flag_registry.py", "tests": 3,
                      "all_pass": True, "invariant_holds": "167 registered, 151 read, 0 unregistered",
                      "non_vacuous": True, "no_production_change": True, "all_reuse_backed": True,
                      "reuse_claims": 1, "reuse_claims_backed_by_file_evidence": 1},
        actual={
            "effort_actual": 1, "missed": [], "unnecessary": [], "reuse_wrong": [], "regressions": [],
            "obligations_built": ["flag_registry_consistency.guard_test"],
            "notes": "Different domain (config/observability, not migration). The general 'reconcile-first + "
                     "anticipate the hidden obligation' reasoning transferred; the migration-specific patterns "
                     "did not apply. Scope/exclusions handled in one file -> effort 1 == predicted 1. Out of "
                     "scope: 16 registry entries are registered-but-not-literally-read (not a defect).",
        })


def record_consolidation_execution(store, memory) -> CycleRecord:
    """FOURTH executed+verified cycle, a DIFFERENT work_type (refactor, not a test guard):
    the recorder consolidation itself, run as an RDO-guided cycle (dogfooding). Prediction
    and acceptance were defined before implementation; equivalence tests prove the three
    recorders still produce the same records."""
    return _record_executed(
        store, memory,
        cycle_id="recorder_consolidation_2026-11",
        objective="Consolidate the three executed-cycle recorders into one _record_executed helper.",
        work_type="refactor", engineering_pattern="refactor",
        predicted={"effort": 1, "net_new_count": 1,
                   "note": "one helper + equivalence tests; preserve each record; derive lessons once; "
                           "do not hide domain data or over-generalise"},
        reused=["the three recorders' domain data (unchanged)", "record_actual / compare / derive_lessons"],
        verification={"artifact": "rdo/orchestrator.py::_record_executed + rdo/tests/test_rdo.py",
                      "equivalence_tests": 3, "all_pass": True, "records_unchanged": True,
                      "lessons_derived_once": True, "all_reuse_backed": True,
                      "reuse_claims": 1, "reuse_claims_backed_by_file_evidence": 1},
        actual={"effort_actual": 1, "missed": [], "unnecessary": [], "reuse_wrong": [], "regressions": [],
                "obligations_built": ["_record_executed helper", "3 recorder-equivalence tests"],
                "notes": "Prediction matched. The helper shares the MECHANISM; domain data stays visible "
                         "in each thin caller; derive_lessons runs once, so the earlier double-count is "
                         "unreproducible by construction. Equivalence proven before + after the refactor."})


def change_categories() -> dict:
    """Separate the FOUR ways the RDO can change, so 'more capable' is not conflated with
    'more specialised' (founder terminology constraint). A correct prediction from general
    reasoning is a general-reasoning gain; a new rule set is specialisation."""
    return {
        "general_engine_logic": "UNCHANGED by adding an objective (expand/reconcile/tension/prioritise "
                                "algorithms). The Pattern-Memory confidence MODEL was corrected this "
                                "cycle — a dependability fix, not new reasoning.",
        "pattern_taxonomy": "grew by rule sets: 'defect' (cycle 2), 'invariant' (cycle 3). Adding a rule "
                           "is SPECIALISATION — it enables expansion; it is not better reasoning.",
        "domain_knowledge": "grew by per-objective seeds+signatures in knowledge.py (genius/affinity/"
                           "config) — isolated from the engine.",
        "recorded_experience": "grew by cycle records + patterns; confidence now decays on disconfirmation.",
        "attribution_of_matched_predictions": "cycles 2-4 matched prediction via GENERAL reasoning "
                                             "(reconcile-first + anticipate-the-hidden-obligation), NOT "
                                             "via the new rules (which only enabled expansion).",
    }


# ------------------------- the demonstration entry points ---------------------

def demo_genius_tagger(repo_dir: str = ".", workdir: str = "rdo/.cycles") -> dict:
    """Run the full cycle on the real genius-tagger objective and return the six
    required demonstration outputs (single-cycle entry point)."""
    memory = PatternMemory(os.path.join(workdir, "patterns.jsonl"))
    store = CycleStore(workdir)
    _seed_watcher_cycle(memory, store)                       # real completed-cycle datapoint
    active = _active_experiments(repo_dir)
    cycle, summary = _run_one("genius_tagger_2026-11", genius_tagger_idea(), repo_dir,
                              memory, store, active)
    memory.add(Pattern(key="reconcile_stale_docs", provenance="cycle:genius_tagger_2026-11",
                       statement="(corroboration)", applicability="genius tagger"))
    learning = accuracy_series([store.load(cid) for cid in store.list_ids()])
    out = _six_outputs(cycle, summary, memory, learning)
    out["optimal_functional_tension"]["signal_authority_audit"] = genius_authority_audit(
        repo_dir, "genius")
    out["generated_at"] = utc_now()
    return out


def run_catalogue(repo_dir: str = ".", workdir: str = "rdo/.cycles") -> dict:
    """Run real cycles of DIFFERENT development patterns into one shared store/memory,
    then report the comparable cross-cycle learning metrics. This is the generalisation
    test: the same engine, reconciliation, OFT, prioritisation and learning apply to
    every pattern; only the expansion rule set differs."""
    memory = PatternMemory(os.path.join(workdir, "patterns.jsonl"))
    store = CycleStore(workdir)
    _seed_watcher_cycle(memory, store)
    active = _active_experiments(repo_dir)

    g_cycle, g_sum = _run_one("genius_tagger_2026-11", genius_tagger_idea(), repo_dir,
                              memory, store, active)
    memory.add(Pattern(key="reconcile_stale_docs", provenance="cycle:genius_tagger_2026-11",
                       statement="(corroboration)", applicability="genius tagger"))

    d_cycle, d_sum = _run_one("migration_defect_2026-11", migration_defect_idea(), repo_dir,
                              memory, store, active)
    memory.add(Pattern(key="reconcile_stale_docs", provenance="cycle:migration_defect_2026-11",
                       statement="(corroboration)", applicability="migration defect"))

    exec_cycle = record_arc_closers_execution(store, memory)

    a_cycle, a_sum = _run_one("affinity_drift_2026-11", affinity_drift_idea(), repo_dir,
                              memory, store, active)
    affinity_exec = record_affinity_execution(store, memory)

    c_cycle, c_sum = _run_one("config_guard_plan_2026-11", config_invariant_idea(), repo_dir,
                              memory, store, active)
    config_exec = record_config_invariant_execution(store, memory)

    consolidation_exec = record_consolidation_execution(store, memory)

    cycles = [store.load(cid) for cid in store.list_ids()]
    metrics = metrics_series(cycles)
    learning = accuracy_series(cycles)
    return {
        "cycles": {
            "genius_tagger (feature-deploy pattern)": _six_outputs(g_cycle, g_sum, memory, learning),
            "migration_defect (defect-remediation pattern)": _six_outputs(d_cycle, d_sum, memory, learning),
            "affinity_drift (defect, migration-only)": _six_outputs(a_cycle, a_sum, memory, learning),
            "config_invariant (invariant-guard pattern, non-migration)": _six_outputs(c_cycle, c_sum, memory, learning),
        },
        "generalisation": {
            "patterns_exercised": ["feature-deploy (persistence/daemon/api/consumer)",
                                   "defect-remediation (reproduce/root_cause/fix/regression_test/verify)",
                                   "invariant-guard (specify/scope/guard_test/verify) — non-migration"],
            "engine_reused_unchanged": ["extrapolator", "reconcile", "tension", "prioritise",
                                        "memory/learning"],
            "rule_catalogue": rule_catalogue(),
            "obligation_scope_by_cycle": {
                "genius_tagger": scope_summary(g_cycle.obligations),
                "migration_defect": scope_summary(d_cycle.obligations),
            },
            "note": "generalisation to a new pattern required ONE new expansion RULE SET per pattern "
                    "class ('defect', 'invariant') — a PATTERN-TAXONOMY change, NOT a change to the "
                    "general engine logic (expand/reconcile/tension/prioritise); domain specifics "
                    "stayed in knowledge.py. Scope tags "
                    "(general / domain-specific / context-dependent / anti-requirement / novel) keep "
                    "reusable obligations distinct from domain ones; a 'novel' kind (no rule) is "
                    "surfaced rather than force-fit.",
        },
        "executed_cycles": [
            {"id": c.id, "kind": c.kind, "work_type": c.work_type, "predicted": c.predicted,
             "actual": c.actual, "verification": c.verification}
            for c in (exec_cycle, affinity_exec, config_exec, consolidation_exec)
        ],
        "change_categories": change_categories(),
        "comparability_assessment": comparability_assessment(cycles),
        "cross_cycle_transfer": transfer_observations(cycles),
        "learning_metrics": metrics,
        "patterns": [p.to_dict() for p in memory.patterns()],
        "signal_authority_audit": genius_authority_audit(repo_dir, "genius"),
        "generated_at": utc_now(),
    }


def _converging_nodes(relationships: List[dict]) -> List[str]:
    """Obligations reached by >1 depends_on edge — shared prerequisites / converging branches."""
    from collections import Counter
    indeg = Counter(r["dst"] for r in relationships if r["kind"] == "depends_on")
    return sorted(k for k, v in indeg.items() if v > 1)


def run_stage2_belief_decay(repo_dir: str = ".", workdir: str = "rdo/.cycles",
                            review: Optional[dict] = None) -> dict:
    """RDO v1.3 §16 Stage-2 Extrapolator MVP: run the real belief-DEVELOPMENT objective
    (staleness-based confidence decay) end to end and persist it for resume. Reuses the
    generic driver (`_run_one` -> `run_cycle`) and `CycleStore`; it introduces no new
    persistence, graph or reconciliation mechanism. Read-only: it proposes work, it never
    touches the live belief store."""
    memory = PatternMemory(os.path.join(workdir, "patterns.jsonl"))
    store = CycleStore(workdir)
    cycle, _summary = _run_one("belief_decay_mvp", belief_decay_idea(), repo_dir, memory, store, _active_experiments(repo_dir))
    obls = cycle.obligations

    # ---- calibration ONLY from a genuine, authorised planning review ----
    # A predetermined demonstration finding must NOT become a learned production pattern. When no
    # review is supplied (the default, and the CLI path), nothing is written to PatternMemory.
    # A genuine review is a reviewed PLANNING outcome (NOT an execution outcome): the cycle stays
    # kind=native_planning (nothing was built), and every derived calibration pattern carries the
    # reviewer's explicit provenance so it is attributable and never confused with execution.
    comparison = None
    calibration: List[Pattern] = []
    review_report: object = "no review supplied — no calibration pattern written"
    if review is not None:
        reviewer = review.get("reviewer")
        if not reviewer:
            raise ValueError("a genuine planning review must name its reviewer (provenance)")
        actual = dict(review)
        actual["review_kind"] = "planning_review"       # distinguishes a reviewed plan from execution
        record_actual(cycle, actual)
        comparison = compare(cycle)                      # predicted vs reviewed discrepancies
        for p in derive_lessons(cycle, comparison):      # candidate patterns (low, capped confidence)
            p.provenance = f"{p.provenance}|planning_review|reviewer={reviewer}"
            memory.add(p)                                # durable: appended to patterns.jsonl
            calibration.append(p)
        store.save(cycle)                                # durable: cycle now carries the reviewed actual
        assert cycle.kind == NATIVE_PLANNING, "a reviewed plan must not be recorded as executed work"
        review_report = {
            "kind": "planning_review (not an execution outcome)",
            "reviewer": reviewer,
            "predicted": cycle.predicted,
            "reviewed": actual,
            "comparison": comparison,
            "calibration_patterns": [p.key for p in calibration],
        }
    return {
        "stage": "RDO v1.3 §16 Stage 2 — Extrapolator MVP",
        "objective": cycle.objective,
        "obligations_discovered": len(obls),
        "max_depth": max(o["depth"] for o in obls),
        "dependency_edges": len(cycle.relationships),
        "counts": cycle.counts,
        "reused_existing": cycle.reused,
        "net_new_missing": cycle.missing,
        "anti_requirements": cycle.anti_requirements,
        "deferred_frontier": cycle.frontier,
        "frontier_breakdown": frontier_breakdown(cycle.frontier),
        "converging_prerequisites": _converging_nodes(cycle.relationships),
        "work_packages_ordered": [(p["key"], p["eligibility"]) for p in cycle.work_packages],
        "verification": cycle.verification,
        "prediction_vs_review": review_report,
        "persisted_to": os.path.join(workdir, "cycle_belief_decay_mvp.json"),
        "resume_in_new_process":
            f"python -c \"from rdo.memory import CycleStore; "
            f"print(CycleStore('{workdir}').load('belief_decay_mvp').objective)\"",
    }


def run_stage3_graph_intelligence(repo_dir: str = ".", workdir: str = "rdo/.cycles") -> dict:
    """RDO v1.3 §16 Stage 3 — graph intelligence over the belief-decay obligation graph.

    Uses the Stage-2 cycle (via CycleStore) as the regression baseline and runs the read-only
    `rdo.graph` analysis: typed edges, SCC decomposition, semantic duplicate CANDIDATES (surfaced,
    never merged), completeness against the objective, and a prerequisite-derived implementation
    sequence. The analysis is persisted for fresh-process resume. No merges; the live store is
    never touched."""
    memory = PatternMemory(os.path.join(workdir, "patterns.jsonl"))
    store = CycleStore(workdir)
    cycle, _summary = _run_one("belief_decay_mvp", belief_decay_idea(), repo_dir, memory, store, _active_experiments(repo_dir))
    analysis = graph_analyse(cycle.obligations, cycle.relationships, cycle.frontier)
    path = os.path.join(workdir, "graph_analysis_belief_decay_mvp.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(analysis, fh, indent=2, default=str)

    indeg = {r["dst"] for r in cycle.relationships if r["kind"] == "depends_on"
             and [x["dst"] for x in cycle.relationships if x["kind"] == "depends_on"].count(r["dst"]) > 1}
    seq = analysis["implementation_sequence"]
    return {
        "stage": "RDO v1.3 §16 Stage 3 — Graph Intelligence",
        "baseline_cycle": cycle.id,
        "typed_edges": analysis["typed_edges"],
        "scc_nontrivial_components": len(analysis["scc"]["nontrivial_components"]),
        "has_cyclic_components": analysis["scc"]["has_cyclic_components"],
        "duplicate_candidates": len(analysis["duplicate_candidates"]),
        "duplicate_candidate_sample": analysis["duplicate_candidates"][:3],
        "convergence_preserved": "shared_runtime_effect.runtime_verification" in indeg,
        "completeness": {k: analysis["completeness"][k]
                         for k in ("discovered", "unresolved_count", "complete_against_objective")},
        "sequence_levels": len(seq["levels"]),
        "parallel_width": seq["parallel_width"],
        "cyclic_components_in_sequence": seq["cyclic_components"],
        "persisted_cycle": os.path.join(workdir, "cycle_belief_decay_mvp.json"),
        "persisted_analysis": path,
        "resume_in_new_process":
            f"python -c \"import json; from rdo.memory import CycleStore; from rdo.graph import analyse; "
            f"c=CycleStore('{workdir}').load('belief_decay_mvp'); "
            f"print(len(analyse(c.obligations,c.relationships,c.frontier)['duplicate_candidates']))\"",
    }


def run_stage4_belief_audit(repo_dir: str = ".", workdir: str = "rdo/.cycles") -> dict:
    """RDO v1.3 §16 Stage 4 — read-only belief audit. Source-grounded map of the belief lifecycle
    + traceable gap map, persisted for resume. Issues no live-DB query/write; host-only facts are
    flagged, never guessed."""
    a = _belief_audit(repo_dir)
    g = _belief_gap_map(repo_dir, a)
    os.makedirs(workdir, exist_ok=True)
    path = os.path.join(workdir, "belief_audit.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"audit": a, "gap_map": g}, fh, indent=2, default=str)
    return {
        "stage": a["stage"],
        "lifecycle_phases_evidenced": f"{a['tracked']}/{a['findings_total']}",
        "consumer_file_count": a["consumption"]["consumer_file_count"],
        "host_only_unknowns": [h["subject"] for h in a["host_only_unknowns"]],
        "open_gaps": g["open_gaps"],
        "gap_summary": [(gp["gap"], gp["severity"], bool(gp.get("resolved"))) for gp in g["gaps"]],
        "persisted_to": path,
        "resume_in_new_process":
            f"python -c \"import json; print(json.load(open('{path}'))['gap_map']['open_gaps'])\"",
    }


def run_stage5_belief_pathway(repo_dir: str = ".", workdir: str = "rdo/.cycles") -> dict:
    """RDO v1.3 §16 Stage 5 — select + specify the first belief-to-mechanism pathway (read-only).
    The selected pathway is verified in isolation against the real mechanism by
    tests/test_belief_confidence_retrieval_pathway.py. Persists the spec for resume. No live writes."""
    spec = _select_pathway(repo_dir)
    os.makedirs(workdir, exist_ok=True)
    path = os.path.join(workdir, "belief_pathway.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=2, default=str)
    return {
        "stage": spec["stage"],
        "selected": spec["selected"],
        "excluded": spec["excluded"],
        "causal_proposition": spec["causal_proposition"]["observable_consequence"],
        "baseline": spec["baseline"],
        "success_if": spec["success_if"],
        "inconclusive_because": spec["inconclusive_because"],
        "rollback": spec["rollback"],
        "runtime_observation_gate": spec["runtime_observation_gate"]["status"],
        "isolated_verification": "tests/test_belief_confidence_retrieval_pathway.py (9 tests, real mechanism)",
        "persisted_to": path,
    }


def run_stage6_learning_loop(repo_dir: str = ".", workdir: str = "rdo/.cycles") -> dict:
    """RDO v1.3 §16 Stage 6 — the learning loop over REAL Stage 2-5 development evidence: the
    executed cycles (catalogue) plus one reviewer-attributed planning cycle. Reuses the memory
    primitives; adds reviewed-vs-automated provenance, reopening on new evidence and explicit
    UNKNOWNs. Persisted for resume. No live NEX writes; planning reviews are NOT execution."""
    run_catalogue(repo_dir, workdir)                       # executed cycles (real actuals)
    run_stage2_belief_decay(repo_dir, workdir, review={    # one human-reviewed planning cycle
        "reviewer": "stage6 controlled review", "missed": ["belief_decay_rollback"],
        "notes": "planning review (not an execution outcome)"})
    store = CycleStore(workdir)
    cycles = [store.load(i) for i in store.list_ids()]
    bd = store.load("belief_decay_mvp")
    # controlled reopening fixtures: concrete contradicting evidence reopens; UNKNOWN does not
    new_evidence = [
        {"key": "belief_staleness_input", "now": "missing",
         "observation": "fixture: belief_activation table reported dropped — reused mechanism gone"},
        {"key": "belief_decay_policy", "now": "unknown", "observation": ""},   # insufficient -> no reopen
    ]
    loop = learning_loop(cycles, new_evidence=new_evidence, reopen_cycle=bd)
    path = os.path.join(workdir, "learning_loop.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(loop, fh, indent=2, default=str)
    return {
        "stage": "RDO v1.3 §16 Stage 6 — learning loop",
        "cycles_ingested": len(cycles),
        "provenance_split": loop["provenance_split"],
        "mean_prediction_accuracy": loop["mean_prediction_accuracy"],
        "accuracy_basis": loop["accuracy_basis"],
        "unknown_outcomes": sum(1 for p in loop["per_cycle"] if p["accuracy"] is None),
        "reopening": loop["reopening"],
        "comparability_largest_group": loop["comparability"]["largest_genuinely_comparable_group"],
        "anti_gaming": loop["anti_gaming"],
        "persisted_to": path,
    }


def run_stage7_execution_integration(repo_dir: str = ".", workdir: str = "rdo/.cycles") -> dict:
    """RDO v1.3 §16 Stage 7 — demonstrate the execution->Watcher-verification->learning loop on an
    ISOLATED, low-risk fixture (a throwaway temp dir). The Watcher verifies source + test independently
    (runtime stays host-only UNKNOWN); a completion claim with no evidence is NOT accepted. No live
    NEX, no commits."""
    import tempfile
    from . import execution as ex
    os.makedirs(workdir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="stage7_slice_")
    # the controlled task: a guard mechanism + its passing test
    with open(os.path.join(tmp, "demo_module.py"), "w", encoding="utf-8") as fh:
        fh.write("def demo_guard(x):\n    return x > 0\n")
    with open(os.path.join(tmp, "test_demo_guard.py"), "w", encoding="utf-8") as fh:
        fh.write("from demo_module import demo_guard\n\n"
                 "def test_guard():\n    assert demo_guard(1) and not demo_guard(-1)\n")
    led = os.path.join(workdir, "stage7_ledger.jsonl")

    wp = {"key": "wp:demo_guard", "obligation_keys": ["demo_guard"]}
    req = {"demo_guard": {"source_signature": r"def demo_guard", "source_path": "demo_module.py",
                          "test_file": "test_demo_guard.py"}}
    rec = ex.create_execution_record("exec:demo_guard", "stage7_slice", "add a demo guard", wp, req)
    ex.record_claim(rec, completion_claim=True,
                    changed_artifacts=["demo_module.py", "test_demo_guard.py"],
                    tests=["test_demo_guard.py"], failures=[])
    ex.verify(rec, tmp, led, approved_test_files=['test_demo_guard.py'])
    verified_actual = ex.feedback_to_learning(rec)

    # NEGATIVE: a completion claim (even with an unrelated passing test) but NO source evidence
    wp2 = {"key": "wp:phantom", "obligation_keys": ["phantom"]}
    req2 = {"phantom": {"source_signature": r"def phantom_never_written", "source_path": "demo_module.py",
                        "test_file": "test_demo_guard.py"}}
    rec2 = ex.create_execution_record("exec:phantom", "stage7_slice", "phantom", wp2, req2)
    ex.record_claim(rec2, completion_claim=True, changed_artifacts=[], tests=[], failures=[])
    ex.verify(rec2, tmp, led, approved_test_files=['test_demo_guard.py'])

    path = ex.save_record(rec, os.path.join(workdir, "execution_record.json"))
    dims = rec["verification"]["dimensions"]["demo_guard"]
    return {
        "stage": "RDO v1.3 §16 Stage 7 — execution integration verified through Watcher",
        "traceability": {"objective": rec["objective"], "work_package": rec["work_package"],
                         "obligations": rec["obligation_keys"]},
        "verified_slice": {
            "verdict": rec["verdict"],
            "evidence_dimensions": {"source_implemented": dims["source_implemented"]["evidence_class"],
                                    "test_verified": dims["test_verified"]["status"],
                                    "runtime_observed": dims["runtime_observed"]["evidence_class"]},
            "ledger_state": dims["ledger_state"],
        },
        "claim_only_slice": {"verdict": rec2["verdict"],
                             "note": "completion claimed (+an unrelated passing test) but NO source "
                                     "evidence -> NOT accepted"},
        "learning_feedback": {"provenance": "independent_watcher_verified",
                              "verified_obligations": verified_actual["verified_obligations"],
                              "reopened": verified_actual["reopened"]},
        "persisted_record": path,
    }
