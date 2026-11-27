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
from .extrapolator import expand, frontier_breakdown
from .memory import PatternMemory, compare, derive_lessons, record_actual
from .model import (ANTI_REQUIREMENT, EXECUTED_VERIFIED, MISSING, PARTIAL, RECON_UNKNOWN,
                    REUSE_EXISTING, SIGNATURE_MATCHED, CycleRecord, Obligation, Relationship)
from .reconcile import Signature


def run_cycle(cycle_id: str, objective: str, assumptions: List[str],
              seeds: List[Obligation], signatures: Dict[str, List[Signature]],
              repo_dir: str = ".", active_experiments: Optional[List[str]] = None,
              authorised_gates: Optional[set] = None,
              memory: Optional[PatternMemory] = None,
              max_depth: int = 4,
              initial_relationships: Optional[List[Relationship]] = None,
              objective_input: Optional[Dict] = None,
              objective_context: Optional[Dict] = None) -> Tuple[CycleRecord, dict]:
    applied = [p.key for p in memory.applicable(objective)] if memory else []

    # EXPAND (+ reconcile interleaved) -> DEDUP (done in expand) -> RECONCILE children.
    # max_depth is the expansion budget; items stopped at the budget stay on the frontier.
    reconciler = recon_mod.make_reconciler(repo_dir, signatures)
    obligations, relationships, frontier = expand(seeds, reconciler, max_depth=max_depth)
    # Preserve externally supplied, typed seed relationships alongside rule-derived edges.
    if initial_relationships:
        relationships = list(initial_relationships) + relationships

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

    # Objective context is a separate contract from the seed graph. Do not infer
    # that free-text scope/constraints/exclusions/acceptance criteria were obeyed
    # merely because seed obligations were expanded. Until each item is mapped to
    # obligations and evidence, retain it as UNKNOWN and block execution readiness.
    objective_context = dict(objective_context or {})
    context_items = []

    def _context_values(value):
        # Scalar contract fields (notably intent) are one item, never an iterable
        # of characters. Lists remain lists; malformed shapes stay unexpanded.
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return value
        return []

    for value in _context_values(objective_context.get("intent")):
        if isinstance(value, str) and value.strip():
            context_items.append({"kind": "intent", "text": value, "status": "unmapped", "evidence": []})
    context_scope = objective_context.get("scope", {})
    if isinstance(context_scope, dict):
        for value in _context_values(context_scope.get("in_scope")):
            if isinstance(value, str) and value.strip():
                context_items.append({"kind": "scope", "text": value, "status": "unmapped", "evidence": []})
        for value in _context_values(context_scope.get("affected_paths")):
            if isinstance(value, str) and value.strip():
                context_items.append({"kind": "affected_path", "text": value, "status": "unmapped", "evidence": []})
    for field, kind in (("assumptions", "assumption"), ("constraints", "constraint"),
                        ("exclusions", "exclusion"),
                        ("acceptance_criteria", "acceptance_criterion")):
        for value in _context_values(objective_context.get(field)):
            if isinstance(value, str) and value.strip():
                context_items.append({"kind": kind, "text": value, "status": "unmapped", "evidence": []})
    context_assessment = {
        "status": "unmapped" if context_items else "not_supplied",
        "review_required": bool(context_items),
        "items": context_items,
        "note": ("Objective context has not yet been mapped to obligations and independent evidence."
                 if context_items else "No structured objective context was supplied."),
    }
    context_assessment["execution_readiness"] = (
        "blocked" if context_items else "unknown"
    )
    context_assessment["handoff_readiness"] = (
        "reviewable" if context_items else "not_applicable"
    )
    if context_items:
        # Keep Stage-1 work-package eligibility distinct from execution readiness.
        # A reviewable proposal may proceed to bounded human scope review, but
        # unmapped context must never be interpreted as permission to execute.
        context_exclusions = [
            f"objective exclusion (mapping still unverified): {item['text']}"
            for item in context_items if item["kind"] == "exclusion"
        ]
        for package in packages:
            package.anti_requirements = list(dict.fromkeys(
                package.anti_requirements + context_exclusions
            ))

    recon_buckets = recon_mod.summarize(obligations)
    reused = recon_buckets.get(REUSE_EXISTING, [])
    signature_matches = recon_buckets.get(SIGNATURE_MATCHED, [])
    unknowns = recon_buckets.get(RECON_UNKNOWN, [])
    missing = recon_buckets.get(MISSING, []) + recon_buckets.get(PARTIAL, [])
    anti = [o.key for o in obligations.values() if o.classification == ANTI_REQUIREMENT]
    uncertainties = [f["key"] + ": " + f["reason"] for f in frontier
                     if ("no reconciliation" in f["reason"] or "max_depth" in f["reason"]
                         or "semantic satisfaction unreviewed" in f["reason"]
                         or "lacks semantic-review evidence" in f["reason"])] + [
        f"{key}: reconciliation unknown; investigate" for key in unknowns
    ]

    # VERIFICATION — every reuse claim must be backed by real evidence
    backed = [k for k in reused if obligations[k].recon_evidence]
    signature_matches_backed = [
        k for k in signature_matches if obligations[k].recon_evidence
    ]
    verification = {
        "reuse_claims": len(reused),
        "signature_matches": len(signature_matches),
        "signature_matches_backed_by_file_evidence": len(signature_matches_backed),
        "all_signature_matches_have_file_evidence": (
            len(signature_matches_backed) == len(signature_matches)),
        "reuse_claims_backed_by_file_evidence": len(backed),
        "all_semantic_reuse_claims_have_file_evidence": len(backed) == len(reused),
        "all_reuse_backed": len(backed) == len(reused),
        "net_new_work_packages": sum(1 for p in packages),
        "blocked_work_packages": sum(1 for p in packages if p.eligibility == "blocked"),
        "unbacked_reuse_claims": [k for k in reused if k not in backed],
    }

    predicted = {
        "reused_count": len(reused),
        "signature_matches_requiring_semantic_review": len(signature_matches),
        "net_new_count": len(missing),
        "signature_review_count": len(signature_matches),
        "unknown_investigation_count": len(unknowns),
        "effort": len(missing) + len(signature_matches) + len(unknowns),
        "note": "uncalibrated count of unresolved build, semantic-review and investigation obligations; not hours",
    }

    # COMPLETE ACCOUNTING — six counts with explicit, internally consistent definitions:
    #   discovered  = distinct obligation nodes in the graph (post-merge)
    #   unique      = distinct canonical keys (== discovered proves no silent key collision)
    #   reuse       = reconciled to an existing mechanism (REUSE_EXISTING)
    #   net_new     = to be built (MISSING or PARTIAL)
    #   deferred    = GENUINELY unexpanded frontier items only (budget/no-rule) — NOT the whole
    #                 frontier: anti-requirement stops count under anti_requirements and
    #                 already-satisfied stops count under reuse, so nothing is double-counted
    #   unresolved  = no reconciliation signature (RECON_UNKNOWN — an honest gap, candidate work)
    keys = [o.key for o in obligations.values()]
    fbreak = frontier_breakdown(frontier)   # {deferred, anti_requirement, already_satisfied, other}
    counts = {
        "discovered": len(obligations),
        "unique": len(set(keys)),
        "reuse": len(reused),
        "net_new": len(missing),
        "deferred": fbreak["deferred"],
        "unresolved": sum(1 for o in obligations.values() if o.recon_status == RECON_UNKNOWN),
        # the complete frontier is retained on CycleRecord.frontier; this names each stop reason
        "frontier_total": len(frontier),
        "frontier_anti_requirement": fbreak["anti_requirement"],
        "frontier_already_satisfied": fbreak["already_satisfied"],
        "frontier_other": fbreak["other"],
    }

    cycle = CycleRecord(
        id=cycle_id, objective=objective, assumptions=assumptions,
        obligations=[o.to_dict() for o in obligations.values()],
        relationships=[r.to_dict() for r in relationships],
        reused=reused, signature_matches=signature_matches, missing=missing,
        anti_requirements=anti,
        uncertainties=uncertainties + [f"applied_patterns={applied}"],
        frontier=list(frontier), counts=counts,
        tension=[t.to_dict() for t in (node_t + rel_t + sys_t)],
        work_packages=[p.to_dict() for p in packages],
        predicted=predicted, verification=verification,
        objective_input=dict(objective_input or {}),
        objective_context=objective_context,
        context_assessment=context_assessment,
    )
    summary = {
        "objective": objective,
        "discovered": len(obligations),
        "reused": reused,
        "signature_matches": signature_matches,
        "unknowns": unknowns,
        "rejected_or_deferred": anti + [f["key"] for f in frontier
                                        if ("already satisfied" in f["reason"]
                                            or "semantic satisfaction independently reviewed" in f["reason"])],
        "recommended_work": [{"package": p.key, "eligibility": p.eligibility,
                              "blockers": p.blockers, "obligations": p.obligation_keys}
                             for p in packages],
        "sufficiency": sufficiency,
        "objective_context": context_assessment,
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


def _active_experiments(repo_dir: str) -> Optional[List[str]]:
    """Read the Watcher registry without turning uncertainty into permission."""
    try:
        from watcher.registry import ingest_registry
        ev = ingest_registry(os.path.join(repo_dir, "observation_reports"))
        if ev.evidence_class != "measured" or not isinstance(ev.data, dict):
            return None
        active = ev.data.get("active_or_pending")
        if not isinstance(active, list) or any(
            not isinstance(item, str) or not item.strip() for item in active
        ):
            return None
        return [item.strip() for item in active]
    except Exception:
        return None
