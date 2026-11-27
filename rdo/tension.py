"""Optimal Functional Tension (OFT) assessment — RDO spec v1.4 Part II & §4.

Not a single magic score. A structured, three-level assessment (node /
relationship / system) where every verdict is either backed by reconciliation
evidence or explicitly marked as an inference, so uncertainty stays visible. The
assessor also recognises when further development is NOT justified — avoiding
over-development is as important as filling gaps.
"""
from __future__ import annotations

import dataclasses
import math
from typing import Dict, List

from .model import (ANTI_REQUIREMENT, CONDITIONAL, FUTURE, MISSING, NECESSARY,
                    OPTIONAL, OVERDEVELOPED, PARTIAL, RECON_UNKNOWN, REUSE_EXISTING, SIGNATURE_MATCHED,
                    SUFFICIENT, TENSION_UNKNOWN, UNDERDEVELOPED, Obligation,
                    InterfaceTensionProfile, Relationship, TensionAssessment,
                    has_valid_reuse_review, _has_traceable_evidence)
from .feedback_loop import FeedbackLoopAssessment


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
    if ob.recon_status == SIGNATURE_MATCHED:
        return TensionAssessment("node", ob.key, TENSION_UNKNOWN, inference=True,
                                 evidence=ev,
                                 note="configured source signature matched; semantic satisfaction "
                                      "has not been independently reviewed")
    if ob.recon_status == REUSE_EXISTING:
        if not has_valid_reuse_review(ob):
            return TensionAssessment("node", ob.key, TENSION_UNKNOWN, inference=True,
                                     evidence=ev,
                                     note="reuse status lacks independent semantic-review evidence")
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

def _evidence_value_valid(value, unit=None) -> bool:
    """Reject absent, non-finite or unitless numeric observations."""
    if isinstance(value, bool):
        return True
    if isinstance(value, int):
        return isinstance(unit, str) and bool(unit.strip())
    if isinstance(value, float):
        return math.isfinite(value) and isinstance(unit, str) and bool(unit.strip())
    if isinstance(value, str):
        return bool(value.strip())
    return False


def _interface_profile_evidence(rel: Relationship) -> dict:
    """Return a conservative summary without converting profile fields into scores."""
    profile = rel.interface_profile
    if profile is None:
        return {
            "profile_status": "not_supplied",
            "unknown_dimensions": ["interface_profile"],
            "dimensions": {},
        }
    if hasattr(profile, "to_dict"):
        profile = profile.to_dict()
    if not isinstance(profile, dict):
        return {
            "profile_status": "invalid_shape",
            "unknown_dimensions": ["interface_profile"],
            "dimensions": {},
        }

    dimensions = {}
    unknown = []
    metadata_fields = {"provider", "consumer", "purpose", "direction"}
    expected_dimensions = [
        field.name for field in dataclasses.fields(InterfaceTensionProfile)
        if field.name not in metadata_fields
    ]
    for name in expected_dimensions:
        item = profile.get(name)
        if not isinstance(item, dict) or "status" not in item:
            item = {}
        # A non-UNKNOWN label is not self-authenticating. Keep the raw evidence
        # fields visible, but require the later margin/threshold assessor before
        # any affirmative sufficiency verdict can be made. Omitted dimensions
        # in older/partial persisted dictionaries remain explicitly UNKNOWN.
        refs = item.get("evidence")
        confidence = item.get("confidence")
        reported_status = item.get("status", "unknown")
        status_valid = reported_status in INTERFACE_EVIDENCE_STATUSES
        evidence_status = reported_status if status_valid else "invalid"
        evidence_complete = (
            reported_status == "measured"
            and status_valid
            and _evidence_value_valid(item.get("value"), item.get("unit"))
            and _has_traceable_evidence(refs)
            and isinstance(confidence, str) and bool(confidence.strip())
        )
        dimensions[name] = {
            "status": evidence_status,
            "value": item.get("value"),
            "unit": item.get("unit"),
            "evidence": list(refs) if isinstance(refs, list) else [],
            "confidence": confidence,
            "evidence_complete": evidence_complete,
        }
        if not evidence_complete:
            unknown.append(name)
    return {
        "profile_status": "supplied",
        "unknown_dimensions": sorted(unknown),
        "dimensions": dimensions,
    }


def _operating_envelope_evidence(value) -> dict:
    """Summarise declared/assessed envelope evidence without inferring a class."""
    if value is None:
        return {"status": "not_supplied", "declared_state": "unknown",
                "assessed_state": None, "unknown_dimensions": [
                    "measured_load", "measured_capacity", "headroom",
                    "transition_evidence", "recovery_evidence", "assessment"],
                "evidence": []}
    to_dict = getattr(value, "to_dict", None)
    if to_dict is not None:
        if not callable(to_dict):
            return {"status": "invalid_shape", "declared_state": "unknown",
                    "assessed_state": None, "unknown_dimensions": ["operating_envelope"],
                    "evidence": []}
        try:
            value = to_dict()
        except Exception:
            return {"status": "invalid_shape", "declared_state": "unknown",
                    "assessed_state": None, "unknown_dimensions": ["operating_envelope"],
                    "evidence": []}
    if not isinstance(value, dict):
        return {"status": "invalid_shape", "declared_state": "unknown",
                "assessed_state": None, "unknown_dimensions": ["operating_envelope"],
                "evidence": []}

    declared = value.get("declared_state", "unknown")
    assessed = value.get("assessed_state")
    evidence = value.get("assessment_evidence", [])
    provenance = value.get("provenance", [])
    confidence = value.get("confidence")
    valid_states = {"normal", "busy", "degraded", "stress", "recovery"}
    declared_valid = (declared == "unknown" or
                      (isinstance(declared, str) and declared in valid_states))
    assessed_valid = (assessed is None or
                      (isinstance(assessed, str) and assessed in valid_states))
    verdict_evidence_valid = declared_valid and (
        assessed is None or (
            assessed_valid and _has_traceable_evidence(evidence)
            and _has_traceable_evidence(provenance)
            and isinstance(confidence, str) and bool(confidence.strip())
        )
    )
    if not declared_valid or not assessed_valid:
        status = "invalid_evidence"
    elif assessed is None:
        status = "unknown"
    else:
        status = "evidence_recorded" if verdict_evidence_valid else "invalid_evidence"
    unknown = []
    for key in ("measured_load", "measured_capacity", "headroom"):
        item = value.get(key)
        if dataclasses.is_dataclass(item):
            item = dataclasses.asdict(item)
        complete = (
            isinstance(item, dict)
            and item.get("status") == "measured"
            and _evidence_value_valid(item.get("value"), item.get("unit"))
            and _has_traceable_evidence(item.get("evidence"))
            and isinstance(item.get("confidence"), str)
            and bool(item.get("confidence").strip())
        )
        if not complete:
            unknown.append(key)
    for key in ("transition_evidence", "recovery_evidence"):
        if not _has_traceable_evidence(value.get(key)):
            unknown.append(key)
    if status != "evidence_recorded":
        unknown.append("assessment")
    return {
        "status": status,
        "declared_state": declared,
        "assessed_state": assessed,
        "unknown_dimensions": sorted(unknown),
        "assessment_evidence": list(evidence) if isinstance(evidence, list) else [],
        "provenance": list(provenance) if isinstance(provenance, list) else [],
        "confidence": confidence,
    }


def assess_relationship(rel: Relationship, obligations: Dict[str, Obligation]) -> TensionAssessment:
    subj = f"{rel.src} -{rel.kind}-> {rel.dst}"
    profile = _interface_profile_evidence(rel)
    envelope = _operating_envelope_evidence(rel.operating_envelope)
    assessment_dimensions = {**profile, "operating_envelope": envelope}
    if rel.kind == "influences" and rel.authority != "bounded":
        return TensionAssessment("relationship", subj, OVERDEVELOPED, inference=True,
                                 dimensions=assessment_dimensions,
                                 note="influence without a bounded-authority declaration "
                                      "(capability != authority)")
    if rel.kind == "depends_on":
        tgt = obligations.get(rel.dst)
        if tgt is not None and tgt.classification == NECESSARY:
            if tgt.recon_status in (MISSING, PARTIAL):
                return TensionAssessment("relationship", subj, UNDERDEVELOPED, inference=True,
                                         evidence=[f"target {tgt.recon_status}"],
                                         dimensions=assessment_dimensions,
                                         note="blocking dependency on an unresolved necessary mechanism")
            if tgt.recon_status in (RECON_UNKNOWN, SIGNATURE_MATCHED) or (
                    tgt.recon_status == REUSE_EXISTING and not has_valid_reuse_review(tgt)):
                return TensionAssessment("relationship", subj, TENSION_UNKNOWN, inference=True,
                                         evidence=[f"target {tgt.recon_status}"],
                                         dimensions=assessment_dimensions,
                                         note="dependency target has not been semantically established")

    evidence = [
        ref
        for dimension in profile["dimensions"].values()
        for ref in dimension["evidence"]
        if isinstance(ref, str) and ref.strip()
    ]
    return TensionAssessment(
        "relationship", subj, TENSION_UNKNOWN, inference=True,
        evidence=evidence,
        dimensions=assessment_dimensions,
        note=(
            "interface profile is absent; relationship sufficiency cannot be established"
            if profile["profile_status"] == "not_supplied" else
            "interface profile has an invalid shape; expected a typed profile or persisted dictionary"
            if profile["profile_status"] == "invalid_shape" else
            "interface evidence is recorded, but calibrated thresholds, margins and "
            "operating-envelope assessment are not yet implemented; retain UNKNOWN"
        ),
    )


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


def _classify_cycle(cycle: List[str], relationships: List[Relationship]) -> str:
    """Classify a detected cycle from edge evidence, retaining UNKNOWN when unclear:
      * prerequisite_cycle — every edge is `depends_on`: a circular build order that cannot
        be satisfied (must be broken);
      * feedback_loop      — the cycle runs through at least one `influences` edge: a candidate
        feedback loop that may be essential (examine gain/stability, do not auto-remove);
      * unknown            — the edges along the cycle cannot all be resolved (insufficient
        evidence to classify).
    `cycle` is a path like [A, B, C, A]."""
    kinds: List[str] = []
    pairs = set(zip(cycle, cycle[1:]))
    for a, b in pairs:
        ks = {r.kind for r in relationships if r.src == a and r.dst == b
              and r.kind in ("depends_on", "influences")}
        if not ks:
            return "unknown"               # an edge we cannot resolve -> do not over-claim
        kinds.extend(ks)
    if "influences" in kinds:
        return "feedback_loop"
    if kinds and all(k == "depends_on" for k in kinds):
        return "prerequisite_cycle"
    return "unknown"


def assess_system(obligations: Dict[str, Obligation],
                  relationships: List[Relationship]) -> List[TensionAssessment]:
    out: List[TensionAssessment] = []

    # Detect and classify graph cycles. A prerequisite cycle blocks build ordering;
    # an influence feedback loop is not automatically a defect; unresolved cycles
    # remain UNKNOWN.
    cycles = _find_cycles(relationships)
    if cycles:
        classified = [{"cycle": " -> ".join(path),
                       "classification": _classify_cycle(path, relationships)}
                      for path in cycles]
        labels = {item["classification"] for item in classified}
        verdict = UNDERDEVELOPED if "prerequisite_cycle" in labels else TENSION_UNKNOWN
        feedback_records = []
        for path, item in zip(cycles, classified):
            if item["classification"] != "feedback_loop":
                continue
            members = list(dict.fromkeys(path[:-1]))
            relationship_refs = []
            for src, dst in zip(path, path[1:]):
                for rel in relationships:
                    if rel.src == src and rel.dst == dst and rel.kind in ("depends_on", "influences"):
                        relationship_refs.append(f"{rel.src}:{rel.kind}:{rel.dst}")
            feedback_records.append(FeedbackLoopAssessment(
                loop_id="feedback-loop:" + item["cycle"],
                members=members,
                relationships=list(dict.fromkeys(relationship_refs)),
            ).to_dict())
        out.append(TensionAssessment(
            "system", "feedback_cycles", verdict, inference=True,
            evidence=[" -> ".join(path) for path in cycles],
            dimensions={"classified_cycles": classified,
                       "feedback_loop_assessments": feedback_records},
            note="cycle(s) detected and classified: prerequisite cycles must be broken; "
                 "feedback loops are represented with UNKNOWN stability evidence for review; "
                 "unknown cycles remain unknown"))

    # Resource concentration: high in-degree obligations (potential bottleneck).
    indeg: Dict[str, int] = {}
    for edge in relationships:
        indeg[edge.dst] = indeg.get(edge.dst, 0) + 1
    hot = sorted((key for key, count in indeg.items() if count >= 3),
                 key=lambda key: -indeg[key])
    if hot:
        out.append(TensionAssessment(
            "system", "resource_concentration", TENSION_UNKNOWN, inference=True,
            evidence=[f"{key} (in-degree {indeg[key]})" for key in hot],
            note="several obligations converge on one mechanism — confirm it is not a bottleneck"))

    # System readiness is affirmative, not default-positive. MISSING/PARTIAL
    # necessary obligations are underdeveloped. Unknown, signature-only and
    # unreviewed reuse states cannot be promoted to SUFFICIENT.
    necessary = {key: ob for key, ob in obligations.items()
                 if ob.classification == NECESSARY}
    missing_nec = [key for key, ob in necessary.items()
                   if ob.recon_status in (MISSING, PARTIAL)]
    unknown_nec = [key for key, ob in necessary.items()
                   if ob.recon_status in (RECON_UNKNOWN, SIGNATURE_MATCHED)
                   or (ob.recon_status == REUSE_EXISTING and not has_valid_reuse_review(ob))]
    if missing_nec:
        verdict = UNDERDEVELOPED
    elif unknown_nec or not necessary:
        verdict = TENSION_UNKNOWN
    else:
        verdict = SUFFICIENT
    evidence = [f"{key}: {ob.recon_status}" for key, ob in necessary.items()]
    out.append(TensionAssessment(
        "system", "integration_readiness", verdict,
        inference=bool(unknown_nec or any(necessary[key].recon_status == PARTIAL
                                          for key in missing_nec)),
        evidence=evidence[:10],
        note=(f"{len(missing_nec)} necessary obligation(s) missing or partial; "
              f"{len(unknown_nec)} unknown"
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
        if (ob.recon_status == REUSE_EXISTING and ob.classification not in (OPTIONAL, FUTURE)
                and has_valid_reuse_review(ob)):
            out.append({"key": ob.key, "reason": "semantic satisfaction reviewed; reuse, do not rebuild"})
        elif ob.recon_status == MISSING and ob.classification in (OPTIONAL, FUTURE, CONDITIONAL):
            out.append({"key": ob.key,
                        "reason": f"{ob.classification}; absence not currently a deficiency"})
    return out
