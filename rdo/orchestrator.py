"""The cycle driver — runs one complete, bounded development cycle:

  IDEA -> RECURSIVE EXPANSION -> RECONCILIATION -> DEDUPLICATION ->
  RELATIONSHIP MAPPING -> OPTIMAL FUNCTIONAL TENSION -> PRIORITISATION ->
  WORK PACKAGE -> VERIFICATION, then persists the record and feeds the
  learning loop.

Advisory only: it proposes bounded work packages; it never changes NEX.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

from watcher.evidence import utc_now

from . import prioritise, reconcile as recon_mod, tension
from .extrapolator import expand
from .knowledge import genius_tagger_idea, migration_defect_idea
from .memory import (CycleStore, PatternMemory, accuracy_series, compare,
                     derive_lessons, metrics_series, record_actual)
from .model import (ANTI_REQUIREMENT, MISSING, PARTIAL, REUSE_EXISTING, CycleRecord,
                    Obligation, Pattern)
from .reconcile import Signature


def run_cycle(cycle_id: str, objective: str, assumptions: List[str],
              seeds: List[Obligation], signatures: Dict[str, List[Signature]],
              repo_dir: str = ".", active_experiments: Optional[List[str]] = None,
              authorised_gates: Optional[set] = None,
              memory: Optional[PatternMemory] = None) -> Tuple[CycleRecord, dict]:
    applied = [p.key for p in memory.applicable(objective)] if memory else []

    # EXPAND (+ reconcile interleaved) -> DEDUP (done in expand) -> RECONCILE children
    reconciler = recon_mod.make_reconciler(repo_dir, signatures)
    obligations, relationships, frontier = expand(seeds, reconciler)

    # PRUNE false dependencies (a "build X first" on an already-existing X)
    pruned = recon_mod.prune_false_dependencies(obligations, relationships)

    # OPTIMAL FUNCTIONAL TENSION (node / relationship / system)
    node_t = [tension.assess_node(o) for o in obligations.values()]
    rel_t = [tension.assess_relationship(r, obligations) for r in relationships]
    sys_t = tension.assess_system(obligations, relationships)
    sufficiency = tension.recognize_sufficiency(obligations)

    # PRIORITISE -> WORK PACKAGES
    packages = prioritise.build_work_packages(obligations, relationships,
                                              active_experiments, authorised_gates)

    recon_buckets = recon_mod.summarize(obligations)
    reused = recon_buckets.get(REUSE_EXISTING, [])
    missing = recon_buckets.get(MISSING, []) + recon_buckets.get(PARTIAL, [])
    anti = [o.key for o in obligations.values() if o.classification == ANTI_REQUIREMENT]
    uncertainties = [f["key"] + ": " + f["reason"] for f in frontier
                     if "no reconciliation" in f["reason"] or "max_depth" in f["reason"]]

    # VERIFICATION — every reuse claim must be backed by real evidence
    backed = [k for k in reused if obligations[k].recon_evidence]
    verification = {
        "reuse_claims": len(reused),
        "reuse_claims_backed_by_file_evidence": len(backed),
        "all_reuse_backed": len(backed) == len(reused),
        "net_new_work_packages": sum(1 for p in packages),
        "blocked_work_packages": sum(1 for p in packages if p.eligibility == "blocked"),
        "unbacked_reuse_claims": [k for k in reused if k not in backed],
    }

    predicted = {
        "reused_count": len(reused),
        "net_new_count": len(missing),
        "effort": len(missing),  # 1 unit ~= one obligation to build (uncalibrated count)
        "note": "effort units are uncalibrated counts, not hours",
    }

    cycle = CycleRecord(
        id=cycle_id, objective=objective, assumptions=assumptions,
        obligations=[o.to_dict() for o in obligations.values()],
        relationships=[r.to_dict() for r in relationships],
        reused=reused, missing=missing, anti_requirements=anti,
        uncertainties=uncertainties + [f"applied_patterns={applied}"],
        tension=[t.to_dict() for t in (node_t + rel_t + sys_t)],
        work_packages=[p.to_dict() for p in packages],
        predicted=predicted, verification=verification,
    )
    summary = {
        "objective": objective,
        "discovered": len(obligations),
        "reused": reused,
        "rejected_or_deferred": anti + [f["key"] for f in frontier
                                        if "already satisfied" in f["reason"]],
        "recommended_work": [{"package": p.key, "eligibility": p.eligibility,
                              "blockers": p.blockers, "obligations": p.obligation_keys}
                             for p in packages],
        "sufficiency": sufficiency,
        "verification": verification,
        "false_dependencies_pruned": pruned,
        "system_tension": [t.to_dict() for t in sys_t],
    }
    return cycle, summary


# ---------- a source-grounded influence-AUTHORITY audit (OFT on the live tree) ----

def assess_signal_authority(repo_dir: str, signal: str = "genius") -> dict:
    """Assess the genius signal's influence AUTHORITY from the actual relationships,
    not the consumer count (RDO §6/§20). Each consumer in the grounded table
    (knowledge.genius_consumers) is grep-verified against its cited file so the
    classification cannot go stale, then `tension.assess_signal_authority`
    distinguishes read/behavioural, direct/indirect, conditional/unconditional,
    magnitude, safeguards and evidence class, and flags the material/unconditional
    path(s) + self-reinforcement risk rather than the raw file count."""
    from .knowledge import genius_consumers
    from .reconcile import _grep
    consumers = genius_consumers()
    for c in consumers:
        hits = _grep(c["anchor"], repo_dir, c["file"])
        c["verified"] = bool(hits)
        c["verified_evidence"] = hits[0] if hits else None
    return tension.assess_signal_authority(consumers, signal)


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
    # an honest, known overlap (restraint is part of OFT — flag, don't over-refactor)
    findings.append({"level": "node", "subject": "memory.py", "verdict": "minor_overlap",
                     "note": "accuracy_series overlaps metrics_series partially; metrics_series is "
                             "canonical. Both kept (distinct outputs + callers); removing one now is "
                             "not justified — a cleanup is also subject to OFT."})
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


# ------------------------- the demonstration ---------------------------------

def _seed_watcher_cycle(memory: PatternMemory, store: CycleStore) -> CycleRecord:
    """Record the just-completed Watcher development cycle as the FIRST real
    learning datapoint (genuine predicted-vs-actual)."""
    wc = CycleRecord(
        id="watcher_2026-11", objective="Build the external NEX Watcher (passive MVP + increments)",
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
    # the cross-cutting, high-value lesson (corroborated again by the genius cycle below)
    memory.add(Pattern(
        key="reconcile_stale_docs",
        statement="Planning docs and code docstrings older than HEAD routinely UNDERSTATE built "
                  "state; reconcile every obligation against the current tree before proposing work.",
        provenance="cycle:watcher_2026-11",
        applicability="deploy build watcher genius tagger integrate", confidence=0.3,
        exceptions=["a doc can also OVERstate state (claim built when absent) — reconcile both ways"]))
    return wc


def _run_one(cycle_id, idea, repo_dir, memory, store, active):
    objective, assumptions, seeds, signatures = idea
    cycle, summary = run_cycle(cycle_id, objective, assumptions, seeds, signatures,
                               repo_dir=repo_dir, active_experiments=active,
                               authorised_gates=set(), memory=memory)
    store.save(cycle)
    return cycle, summary


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
    out["optimal_functional_tension"]["signal_authority_audit"] = assess_signal_authority(
        repo_dir, "genius")
    out["generated_at"] = utc_now()
    return out


def run_catalogue(repo_dir: str = ".", workdir: str = "rdo/.cycles") -> dict:
    """Run TWO real cycles of DIFFERENT development patterns (feature-deploy +
    defect-remediation) into one shared store/memory, then report the comparable
    cross-cycle learning metrics. This is the generalisation test: the same engine,
    reconciliation, OFT, prioritisation and learning apply to both patterns; only
    the expansion rule set differs."""
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
    # the defect cycle also found applied fixes under a stale "open question" -> corroborate
    memory.add(Pattern(key="reconcile_stale_docs", provenance="cycle:migration_defect_2026-11",
                       statement="(corroboration)", applicability="migration defect"))

    cycles = [store.load(cid) for cid in store.list_ids()]
    metrics = metrics_series(cycles)
    learning = accuracy_series(cycles)
    return {
        "cycles": {
            "genius_tagger (feature-deploy pattern)": _six_outputs(g_cycle, g_sum, memory, learning),
            "migration_defect (defect-remediation pattern)": _six_outputs(d_cycle, d_sum, memory, learning),
        },
        "generalisation": {
            "patterns_exercised": ["feature-deploy (persistence/daemon/api/consumer)",
                                   "defect-remediation (reproduce/root_cause/fix/regression_test/verify)"],
            "engine_reused_unchanged": ["extrapolator", "reconcile", "tension", "prioritise",
                                        "memory/learning"],
            "note": "generalisation to a new pattern required ONE new expansion rule set "
                    "('defect'); the rest of the engine applied unchanged.",
        },
        "learning_metrics": metrics,
        "patterns": [p.to_dict() for p in memory.patterns()],
        "signal_authority_audit": assess_signal_authority(repo_dir, "genius"),
        "generated_at": utc_now(),
    }


def _active_experiments(repo_dir: str) -> List[str]:
    """Reuse the Watcher's registry to learn which experiment windows are active/
    pending, so the eligibility gate can protect them."""
    try:
        from watcher.registry import ingest_registry
        ev = ingest_registry(os.path.join(repo_dir, "observation_reports"))
        return list(ev.data.get("active_or_pending", []))
    except Exception:
        return []
