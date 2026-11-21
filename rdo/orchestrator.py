"""The generic cycle DRIVER — runs one complete, bounded development cycle:

  IDEA -> RECURSIVE EXPANSION -> RECONCILIATION -> DEDUPLICATION ->
  RELATIONSHIP MAPPING -> OPTIMAL FUNCTIONAL TENSION -> PRIORITISATION ->
  WORK PACKAGE -> VERIFICATION, then persists the record and feeds the learning loop.

This module is DOMAIN-FREE: it names no particular signal, schema, or objective. The
demonstration + reporting live in `rdo/report.py`; the domain-specific authority
audit lives in `rdo/knowledge.py`. Advisory only: it proposes bounded work packages;
it never changes NEX.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

from . import prioritise, reconcile as recon_mod, tension
from .extrapolator import expand
from .memory import PatternMemory, compare, derive_lessons, record_actual
from .model import (ANTI_REQUIREMENT, EXECUTED_VERIFIED, MISSING, PARTIAL, REUSE_EXISTING,
                    CycleRecord, Obligation)
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


def _run_one(cycle_id, idea, repo_dir, memory, store, active):
    """Run one cycle through the pipeline and persist it. Generic helper."""
    objective, assumptions, seeds, signatures = idea
    cycle, summary = run_cycle(cycle_id, objective, assumptions, seeds, signatures,
                               repo_dir=repo_dir, active_experiments=active,
                               authorised_gates=set(), memory=memory)
    store.save(cycle)
    return cycle, summary


def _record_executed(store, memory, *, cycle_id, objective, predicted, reused, verification,
                     actual, work_type="test_guard", engineering_pattern="unspecified",
                     domain_patterns=()) -> CycleRecord:
    """Shared mechanism for an executed+verified cycle: build the record, attach actuals,
    persist, add any domain-specific patterns, then derive lessons EXACTLY once. The domain
    DATA stays in each caller (in report.py) — nothing domain-specific is hidden here, and the
    single derive_lessons call makes the earlier double-count defect unreproducible."""
    c = CycleRecord(id=cycle_id, objective=objective, kind=EXECUTED_VERIFIED, work_type=work_type,
                    engineering_pattern=engineering_pattern,
                    predicted=predicted, reused=list(reused), verification=verification)
    record_actual(c, actual)
    store.save(c)
    for p in domain_patterns:
        memory.add(p)
    for p in derive_lessons(c, compare(c)):   # exactly once
        memory.add(p)
    return c


def _active_experiments(repo_dir: str) -> List[str]:
    """Reuse the Watcher's registry to learn which experiment windows are active/
    pending, so the eligibility gate can protect them."""
    try:
        from watcher.registry import ingest_registry
        ev = ingest_registry(os.path.join(repo_dir, "observation_reports"))
        return list(ev.data.get("active_or_pending", []))
    except Exception:
        return []
