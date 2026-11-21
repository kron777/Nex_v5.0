"""The cycle driver — runs one complete, bounded development cycle:

  IDEA -> RECURSIVE EXPANSION -> RECONCILIATION -> DEDUPLICATION ->
  RELATIONSHIP MAPPING -> OPTIMAL FUNCTIONAL TENSION -> PRIORITISATION ->
  WORK PACKAGE -> VERIFICATION, then persists the record and feeds the
  learning loop.

Advisory only: it proposes bounded work packages; it never changes NEX.
"""
from __future__ import annotations

import os
import subprocess
from typing import Dict, List, Optional, Tuple

from watcher.evidence import utc_now

from . import prioritise, reconcile as recon_mod, tension
from .extrapolator import expand
from .knowledge import genius_tagger_idea
from .memory import (CycleStore, PatternMemory, accuracy_series, compare,
                     derive_lessons, record_actual)
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


# ---------- a real influence-authority audit (OFT on the live tree) ----------

def assess_signal_influence(repo_dir: str, signal: str = "genius",
                            subtree: str = "theory_x") -> dict:
    """Count how many subsystems consume a signal (capability != authority, §6/§20).
    Evidence-backed: lists the actual files. A high count is flagged for an
    influence-authority review, as an inference (not a verdict)."""
    target = os.path.join(repo_dir, subtree)
    files: List[str] = []
    if os.path.exists(target):
        try:
            res = subprocess.run(
                ["grep", "-rlI", "-E", f"{signal}_tags|{signal}_score|{signal}_modulation",
                 "--include=*.py", "--exclude-dir=__pycache__", target],
                capture_output=True, text=True, timeout=30)
            files = sorted({ln.replace(repo_dir.rstrip("/") + "/", "", 1)
                            for ln in res.stdout.splitlines() if ln.strip()
                            and "/genius/" not in ln})  # exclude the producer package
        except (OSError, subprocess.SubprocessError):
            files = []
    return {
        "signal": signal,
        "consumer_files": files,
        "consumer_count": len(files),
        "finding": ("influence concentration: one signal is consumed by several subsystems — "
                    "recommend an influence-authority review (bounded? reversible? gated?)"
                    if len(files) >= 4 else "influence appears contained"),
        "inference": True,
        "note": "capability != authority; this is an advisory flag, not a verdict",
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


def demo_genius_tagger(repo_dir: str = ".", workdir: str = "rdo/.cycles") -> dict:
    """Run the full cycle on the real genius-tagger objective and return a summary
    with the six required demonstration outputs."""
    memory = PatternMemory(os.path.join(workdir, "patterns.jsonl"))
    store = CycleStore(workdir)

    # 1) seed the learning loop with the completed Watcher cycle (real data)
    _seed_watcher_cycle(memory, store)

    # 2) run the genius-tagger cycle, consulting learned patterns
    objective, assumptions, seeds, signatures = genius_tagger_idea()
    # protected/active experiment windows, from the Watcher's registry if present
    active = _active_experiments(repo_dir)
    cycle, summary = run_cycle("genius_tagger_2026-11", objective, assumptions, seeds,
                               signatures, repo_dir=repo_dir, active_experiments=active,
                               authorised_gates=set(), memory=memory)

    # 3) corroborate the stale-doc lesson (reconciliation found the May doc understated build)
    memory.add(Pattern(key="reconcile_stale_docs", provenance="cycle:genius_tagger_2026-11",
                       statement="(corroboration)", applicability="genius tagger"))

    # 4) a real OFT influence audit on the live tree
    influence = assess_signal_influence(repo_dir, "genius", "theory_x")

    # 5) learning status across cycles (no acceleration claim)
    cycles = [store.load(cid) for cid in store.list_ids()]
    learning = accuracy_series(cycles)

    store.save(cycle)
    return {
        "1_discovered": {"count": summary["discovered"],
                         "obligations": [o["key"] for o in cycle.obligations]},
        "2_correctly_reused": summary["reused"],
        "3_rejected_or_deferred": summary["rejected_or_deferred"],
        "4_recommended_work": summary["recommended_work"],
        "5_verification": summary["verification"],
        "6_learned": {
            "patterns": [p.to_dict() for p in memory.patterns()],
            "learning_series": learning,
        },
        "optimal_functional_tension": {
            "system": summary["system_tension"],
            "sufficiency_no_further_dev": summary["sufficiency"],
            "signal_influence_audit": influence,
        },
        "false_dependencies_pruned": summary["false_dependencies_pruned"],
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
