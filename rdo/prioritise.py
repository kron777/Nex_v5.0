"""Two-stage prioritisation and work-package generation (RDO spec v1.4 §23).

Stage 1 — ELIGIBILITY: hard constraints that a high priority can never override
(protected/active experiments, unbuilt necessary dependencies, and active
behavioural changes that need a preregistered gate).

Stage 2 — PRIORITISATION: compare eligible work along dimensions reported
SEPARATELY. A provisional weighted figure is included only for sorting and is
explicitly labelled uncalibrated — it is never presented as established science.

Work packages bundle unresolved build and semantic-review obligations and carry
their anti-requirements (what must deliberately NOT be built).
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .model import (ANTI_REQUIREMENT, FUTURE, MISSING, NECESSARY, OPTIONAL, PARTIAL,
                    RECON_UNKNOWN, REUSE_EXISTING, SIGNATURE_MATCHED, Obligation,
                    Relationship, WorkPackage, has_valid_reuse_review)

# obligation kinds that represent an active behavioural change to NEX and so
# require an explicit, preregistered gate before any execution.
GATED_KINDS = {"consumer", "bounded_influence", "gate"}
# kinds only the host can confirm (NEX runtime), never the cloud.
HOST_ONLY_KINDS = {"runtime_verification"}

_IMPORTANCE = {NECESSARY: 1.0, "conditional": 0.6, OPTIONAL: 0.3, FUTURE: 0.1,
               "hypothesis": 0.2, "unknown": 0.2, ANTI_REQUIREMENT: 0.0}


def _semantic_reuse_is_reviewed(ob: Obligation) -> bool:
    return ob.recon_status == REUSE_EXISTING and has_valid_reuse_review(ob)


def _indegree(relationships: List[Relationship]) -> Dict[str, int]:
    d: Dict[str, int] = {}
    for e in relationships:
        d[e.dst] = d.get(e.dst, 0) + 1
    return d


def priority_dimensions(ob: Obligation, indeg: Dict[str, int]) -> Dict[str, object]:
    """Separate, un-blended dimensions. The weighted figure is a sorting aid only."""
    importance = _IMPORTANCE.get(ob.classification, 0.3)
    centrality = min(indeg.get(ob.key, 0) / 5.0, 1.0)
    readiness = (0.0 if _semantic_reuse_is_reviewed(ob) else
                 {MISSING: 1.0, PARTIAL: 0.6}.get(ob.recon_status, 0.4))
    uncertainty = 1.0 if ob.confidence == "inferred" else (0.5 if ob.confidence == "stated" else 0.2)
    dims = {
        "importance": round(importance, 2),
        "dependency_centrality": round(centrality, 2),
        "readiness_to_build": round(readiness, 2),
        "uncertainty": round(uncertainty, 2),
        "reversibility": "flag_gated" if ob.kind in GATED_KINDS else "n/a",
    }
    # provisional, uncalibrated — NOT presented as validated (RDO §23)
    dims["_provisional_sort_score_uncalibrated"] = round(
        0.4 * importance + 0.3 * readiness + 0.2 * centrality - 0.1 * uncertainty, 3)
    return dims


def eligibility(ob: Obligation, obligations: Dict[str, Obligation],
                relationships: List[Relationship],
                active_experiments: Optional[List[str]] = None,
                authorised_gates: Optional[set] = None) -> Dict[str, object]:
    """Stage-1 hard-constraint check for a single obligation."""
    authorised_gates = authorised_gates or set()
    blockers: List[str] = []

    if ob.kind in GATED_KINDS and ob.key not in authorised_gates:
        blockers.append("active behavioural change — needs a preregistered, authorised gate")
    if ob.kind in HOST_ONLY_KINDS:
        blockers.append("runtime evidence is host-only (NEX must be running; cloud cannot confirm)")
    # None means the registry could not be established. It is distinct from
    # [] (a verified registry with no active/pending experiments).
    if active_experiments is None:
        blockers.append(
            "experiment registry unavailable or unverified — refusing to assume no active experiments"
        )
    else:
        for exp in active_experiments:
            if exp.lower() in (ob.title + ob.note).lower():
                blockers.append(f"touches protected/active experiment window '{exp}'")
    # blocking dependency on an unbuilt necessary mechanism
    for rel in relationships:
        if rel.kind == "depends_on" and rel.src == ob.key:
            dep = obligations.get(rel.dst)
            if dep is None:
                blockers.append(f"depends on unresolved necessary mechanism '{rel.dst}' (target absent)")
            elif dep.classification == NECESSARY and (
                    dep.recon_status in (MISSING, PARTIAL, RECON_UNKNOWN, SIGNATURE_MATCHED)
                    or (dep.recon_status == REUSE_EXISTING and
                        not _semantic_reuse_is_reviewed(dep))):
                state = ("unbuilt" if dep.recon_status == MISSING else
                         "semantic review required" if dep.recon_status == REUSE_EXISTING
                         else dep.recon_status)
                blockers.append(f"depends on necessary mechanism '{dep.key}' ({state})")
    return {"eligibility": "blocked" if blockers else "eligible", "blockers": blockers}


def build_work_packages(obligations: Dict[str, Obligation],
                        relationships: List[Relationship],
                        active_experiments: Optional[List[str]] = None,
                        authorised_gates: Optional[set] = None) -> List[WorkPackage]:
    """Bundle unresolved necessary/conditional obligations by root target.
    Signature-matched obligations are review work, not automatic rebuild claims."""
    indeg = _indegree(relationships)
    # global anti-requirements: explicit anti-reqs + "do not rebuild what exists"
    anti: List[str] = []
    for ob in obligations.values():
        if ob.classification == ANTI_REQUIREMENT:
            anti.append(f"{ob.key}: {ob.rationale}")
        elif _semantic_reuse_is_reviewed(ob):
            ev = ob.recon_evidence[0]
            anti.append(f"do NOT rebuild '{ob.key}' — semantic satisfaction reviewed ({ev})")

    # net-new/investigation work: MISSING/PARTIAL obligations, UNKNOWN obligations
    # without a signature, and SIGNATURE_MATCHED obligations whose full semantic
    # satisfaction has not been reviewed. Only explicitly reviewed REUSE_EXISTING
    # obligations are excluded. Runtime verification is host-only.
    net_new = [ob for ob in obligations.values()
               if ob.classification in (NECESSARY, "conditional")
               and (ob.recon_status in (MISSING, PARTIAL, RECON_UNKNOWN, SIGNATURE_MATCHED)
                    or (ob.recon_status == REUSE_EXISTING and
                        not _semantic_reuse_is_reviewed(ob))
                    or ob.kind in HOST_ONLY_KINDS)]

    # group by root target (key before first '.')
    groups: Dict[str, List[Obligation]] = {}
    for ob in net_new:
        groups.setdefault(ob.key.split(".")[0], []).append(ob)

    packages: List[WorkPackage] = []
    for root, obs in sorted(groups.items()):
        obs.sort(key=lambda o: -priority_dimensions(o, indeg)["_provisional_sort_score_uncalibrated"])
        blockers: List[str] = []
        for o in obs:
            elig = eligibility(o, obligations, relationships, active_experiments, authorised_gates)
            blockers += [f"{o.key}: {b}" for b in elig["blockers"]]
        dims = {o.key: priority_dimensions(o, indeg) for o in obs}
        reversible = all(o.kind in GATED_KINDS for o in obs) or None
        packages.append(WorkPackage(
            key=f"wp:{root}", title=f"Work package: {root}",
            obligation_keys=[o.key for o in obs],
            eligibility="blocked" if blockers else "eligible",
            blockers=sorted(set(blockers)), priority_dimensions=dims,
            anti_requirements=anti, reversible=reversible,
            note="unresolved build/review obligations; signature matches require semantic review, not automatic rebuild"))
    return packages
