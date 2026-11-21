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

import os
from typing import Dict, List, Optional

from watcher.evidence import utc_now

from .extrapolator import rule_catalogue, scope_summary
from .knowledge import (affinity_drift_idea, config_invariant_idea, genius_authority_audit,
                        genius_tagger_idea, migration_defect_idea)
from .memory import (CycleStore, PatternMemory, accuracy_series, comparability_assessment,
                     compare, derive_lessons, metrics_series, record_actual, transfer_observations)
from .model import CycleRecord, EXECUTED_VERIFIED, IMPORTED_RETROSPECTIVE, Pattern
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

    lean = total_loc < 1800 and len(modules) <= 12 and not imports_nex
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
