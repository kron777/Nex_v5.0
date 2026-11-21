"""Optimal Functional Tension (OFT) assessment — RDO spec v1.4 Part II & §4.

Not a single magic score. A structured, three-level assessment (node /
relationship / system) where every verdict is either backed by reconciliation
evidence or explicitly marked as an inference, so uncertainty stays visible. The
assessor also recognises when further development is NOT justified — avoiding
over-development is as important as filling gaps.
"""
from __future__ import annotations

from typing import Dict, List

from .model import (ANTI_REQUIREMENT, CONDITIONAL, FUTURE, MISSING, NECESSARY,
                    OPTIONAL, OVERDEVELOPED, PARTIAL, RECON_UNKNOWN, REUSE_EXISTING,
                    SUFFICIENT, TENSION_UNKNOWN, UNDERDEVELOPED, Obligation,
                    Relationship, TensionAssessment)


# ---- node-level ----

def assess_node(ob: Obligation) -> TensionAssessment:
    ev = list(ob.recon_evidence)
    if ob.classification == ANTI_REQUIREMENT:
        return TensionAssessment("node", ob.key, SUFFICIENT, inference=False,
                                 evidence=ev, note="anti-requirement: must NOT be built")
    if ob.recon_status == MISSING:
        if ob.classification == NECESSARY:
            return TensionAssessment("node", ob.key, UNDERDEVELOPED, inference=False,
                                     evidence=["reconciled MISSING in tree"],
                                     note="necessary obligation has no mechanism")
        return TensionAssessment("node", ob.key, SUFFICIENT, inference=False,
                                 evidence=["reconciled MISSING"],
                                 note=f"{ob.classification}: absence is acceptable")
    if ob.recon_status == REUSE_EXISTING:
        if ob.classification in (OPTIONAL, FUTURE):
            return TensionAssessment("node", ob.key, OVERDEVELOPED, inference=True,
                                     evidence=ev,
                                     note="an optional/future capability already exists — "
                                          "confirm it earns its complexity")
        return TensionAssessment("node", ob.key, SUFFICIENT, inference=False, evidence=ev,
                                 note="satisfied by an existing mechanism")
    if ob.recon_status == PARTIAL:
        return TensionAssessment("node", ob.key, UNDERDEVELOPED, inference=True, evidence=ev,
                                 note="only partial evidence of the mechanism")
    return TensionAssessment("node", ob.key, TENSION_UNKNOWN, inference=True, evidence=ev,
                             note="no reconciliation signature; cannot assess from evidence")


# ---- relationship-level ----

def assess_relationship(rel: Relationship, obligations: Dict[str, Obligation]) -> TensionAssessment:
    subj = f"{rel.src} -{rel.kind}-> {rel.dst}"
    if rel.kind == "influences" and rel.authority != "bounded":
        return TensionAssessment("relationship", subj, OVERDEVELOPED, inference=True,
                                 note="influence without a bounded-authority declaration "
                                      "(capability != authority)")
    if rel.kind == "depends_on":
        tgt = obligations.get(rel.dst)
        if tgt is not None and tgt.recon_status == MISSING and tgt.classification == NECESSARY:
            return TensionAssessment("relationship", subj, UNDERDEVELOPED, inference=False,
                                     evidence=["target MISSING"],
                                     note="blocking dependency on an unbuilt necessary mechanism")
    return TensionAssessment("relationship", subj, SUFFICIENT, inference=True,
                             note="no relationship tension detected")


# ---- system-level ----

def _find_cycles(edges: List[Relationship]) -> List[List[str]]:
    adj: Dict[str, List[str]] = {}
    for e in edges:
        if e.kind in ("depends_on", "influences"):
            adj.setdefault(e.src, []).append(e.dst)
    cycles: List[List[str]] = []
    seen = set()

    def dfs(start, node, path, onstack):
        for nxt in adj.get(node, []):
            if nxt == start and path:
                key = frozenset(path)
                if key not in seen:
                    seen.add(key)
                    cycles.append(path + [start])
            elif nxt not in onstack:
                dfs(start, nxt, path + [nxt], onstack | {nxt})

    for n in list(adj):
        dfs(n, n, [n], {n})
    return cycles


def assess_system(obligations: Dict[str, Obligation],
                  relationships: List[Relationship]) -> List[TensionAssessment]:
    out: List[TensionAssessment] = []

    # stability: feedback cycles among obligations
    cycles = _find_cycles(relationships)
    if cycles:
        out.append(TensionAssessment(
            "system", "feedback_cycles", TENSION_UNKNOWN, inference=True,
            evidence=[" -> ".join(c) for c in cycles],
            note="feedback cycle(s) among obligations — examine stability/gain before building; "
                 "do not auto-remove (some cycles are essential)"))

    # resource concentration: high in-degree obligations (potential bottleneck)
    indeg: Dict[str, int] = {}
    for e in relationships:
        indeg[e.dst] = indeg.get(e.dst, 0) + 1
    hot = sorted((k for k, v in indeg.items() if v >= 3), key=lambda k: -indeg[k])
    if hot:
        out.append(TensionAssessment(
            "system", "resource_concentration", TENSION_UNKNOWN, inference=True,
            evidence=[f"{k} (in-degree {indeg[k]})" for k in hot],
            note="several obligations converge on one mechanism — confirm it is not a bottleneck"))

    # integration: unbuilt necessary obligations
    missing_nec = [k for k, o in obligations.items()
                   if o.recon_status == MISSING and o.classification == NECESSARY]
    verdict = UNDERDEVELOPED if missing_nec else SUFFICIENT
    out.append(TensionAssessment(
        "system", "integration_readiness", verdict, inference=False,
        evidence=missing_nec[:10],
        note=f"{len(missing_nec)} necessary obligation(s) unbuilt" if missing_nec
             else "all necessary obligations reconcile to existing mechanisms"))
    return out


def recognize_sufficiency(obligations: Dict[str, Obligation]) -> List[dict]:
    """Where further development is NOT justified (the restraint half of OFT)."""
    out: List[dict] = []
    for ob in obligations.values():
        if ob.recon_status == REUSE_EXISTING and ob.classification not in (OPTIONAL, FUTURE):
            out.append({"key": ob.key, "reason": "already sufficient; reuse, do not rebuild"})
        elif ob.recon_status == MISSING and ob.classification in (OPTIONAL, FUTURE, CONDITIONAL):
            out.append({"key": ob.key,
                        "reason": f"{ob.classification}; absence not currently a deficiency"})
    return out
