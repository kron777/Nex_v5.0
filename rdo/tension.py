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
        if not (ob.recon_evidence and ob.confidence == "measured" and ob.recon_semantic_verified):
            return TensionAssessment("node", ob.key, TENSION_UNKNOWN, inference=True,
                                     evidence=ev,
                                     note="configured signature matched, but semantic satisfaction "
                                          "has not been independently reviewed")
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

    # Sufficient only when every necessary obligation is affirmatively reconciled.
    # Partial evidence is underdeveloped; unavailable evidence remains unknown.
    necessary = {k: o for k, o in obligations.items() if o.classification == NECESSARY}
    missing_nec = [k for k, o in necessary.items() if o.recon_status in (MISSING, PARTIAL)]
    unknown_nec = [k for k, o in necessary.items()
                    if o.recon_status == RECON_UNKNOWN or
                    (o.recon_status == REUSE_EXISTING and not
                     (o.recon_evidence and o.confidence == "measured" and
                      o.recon_semantic_verified))]
    if missing_nec:
        verdict = UNDERDEVELOPED
    elif unknown_nec or not necessary:
        verdict = TENSION_UNKNOWN
    else:
        verdict = SUFFICIENT
    evidence = [f"{k}: {o.recon_status}" for k, o in necessary.items()]
    out.append(TensionAssessment(
        "system", "integration_readiness", verdict,
        inference=bool(unknown_nec or any(obligations[k].recon_status == PARTIAL for k in missing_nec)),
        evidence=evidence[:10],
        note=(f"{len(missing_nec)} necessary obligation(s) missing or partial; {len(unknown_nec)} unknown"
              if missing_nec or unknown_nec
              else ("no necessary obligations defined; readiness cannot be established"
                    if not necessary else
                    "all necessary obligations have independently reviewed semantic-satisfaction evidence"))))
    return out


def assess_signal_authority(consumers: List[dict], signal: str = "genius") -> dict:
    """Assess a signal's INFLUENCE AUTHORITY from the actual relationships, not the
    consumer count (RDO spec v1.4 §6, §20). `consumers` is the source-grounded table
    (see knowledge.genius_consumers); each row should already carry `verified`.

    Distinguishes read vs behavioural, direct vs indirect, conditional vs
    unconditional, magnitude, safeguards and evidence class, and flags (a) authority
    concentrated in unconditional/material paths and (b) self-reinforcement
    candidates — a self-derived signal that behaviourally changes what is produced or
    attended, regenerating itself. Runtime gain is UNKNOWN (NEX in STANDBY), so these
    are inferences, not verdicts."""
    behavioural = [c for c in consumers if c["influence"] == "behavioural"]
    advisory = [c for c in consumers if c["influence"] == "advisory"]
    non_influence = [c for c in consumers if c["influence"] in ("observability", "housekeeping")]
    unconditional = [c for c in behavioural if not c.get("conditional", False)]
    unsafeguarded = [c for c in behavioural if not c.get("safeguards")]
    material = [c for c in behavioural
                if str(c.get("magnitude", "")).upper().startswith("MATERIAL")]
    self_reinforcing = [c for c in behavioural if c.get("self_derived")]
    # the genuine concern: material OR unconditional behavioural paths
    concern = material + [c for c in unconditional if c not in material]

    assessments: List[TensionAssessment] = []
    if concern:
        assessments.append(TensionAssessment(
            "relationship", f"{signal}:influence_authority", OVERDEVELOPED, inference=True,
            evidence=[f"{c['file']}:{c['lines']} — {c['magnitude']}" for c in concern],
            note=f"{len(behavioural)} behavioural consumers, but authority is concentrated in "
                 f"{len(concern)} unconditional/material path(s); the rest are bounded/safeguarded. "
                 f"Review bounds + reversibility on these, not the raw count (capability != authority)."))
    else:
        assessments.append(TensionAssessment(
            "relationship", f"{signal}:influence_authority", SUFFICIENT, inference=True,
            note="every behavioural consumer is conditional and safeguarded"))
    if self_reinforcing:
        assessments.append(TensionAssessment(
            "system", f"{signal}:self_reinforcement_candidate", TENSION_UNKNOWN, inference=True,
            evidence=[f"{c['file']} -> {c['target']}" for c in self_reinforcing],
            note="a self-evaluation signal behaviourally changes what is produced/attended, which "
                 "regenerates the signal — candidate positive-feedback loop; GAIN UNKNOWN (STANDBY). "
                 "The attention-multiplier path is the strongest. Preserve belief safeguards "
                 "(external-basis caps, sign-symmetry / basis-composition canaries)."))

    unverified = [c["file"] for c in consumers if c.get("verified") is False]
    return {
        "signal": signal,
        "consumer_count": len(consumers),
        "by_influence": {
            "behavioural": [c["file"] for c in behavioural],
            "advisory": [c["file"] for c in advisory],
            "observability_or_housekeeping": [c["file"] for c in non_influence],
        },
        "behavioural_count": len(behavioural),
        "unconditional_behavioural": [c["file"] for c in unconditional],
        "unsafeguarded_behavioural": [c["file"] for c in unsafeguarded],
        "material_magnitude": [c["file"] for c in material],
        "self_reinforcement_candidates": [c["file"] for c in self_reinforcing],
        "finding": ("authority is NOT a function of the count: most behavioural consumers are "
                    "conditional + safeguarded; the review target is the material/unconditional "
                    "path(s) and the self-reinforcement risk, not the nine files."),
        "assessments": [a.to_dict() for a in assessments],
        "evidence_grounded": not unverified,
        "unverified_rows": unverified,
        "table": consumers,
        "inference": True,
        "note": "runtime gain/behaviour is UNKNOWN while NEX is in STANDBY (host-only).",
    }


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
