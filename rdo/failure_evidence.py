"""Traceable observations linking structural dependency paths to real failure evidence.

This is an evidence container, not a propagation model. It reuses Watcher's
Evidence record for each endpoint so origin, evidence class, source and
collection time remain independently attributable. Association defaults to
UNKNOWN; co-observation and temporal association are not causal attribution.
"""
from __future__ import annotations

import dataclasses
import datetime
import json
from typing import List, Optional

from watcher.evidence import Evidence
from .model import CycleRecord, _has_traceable_evidence
from .operating_envelope import OperatingEnvelopeAssessment

ASSOCIATION_STATES = (
    "unknown",
    "co_observed",
    "temporal_association",
    "causally_attributed",
)
def _aware_timestamp(value: str, field_name: str) -> datetime.datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-blank ISO-8601 timestamp")
    try:
        parsed = datetime.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone offset")
    return parsed


def _validate_endpoint_evidence(evidence: Evidence, subject: str, field_name: str):
    if not isinstance(evidence, Evidence):
        raise ValueError(f"{field_name} must be a Watcher Evidence record")
    if evidence.subject != subject:
        raise ValueError(f"{field_name}.subject must match its canonical obligation key")
    if not isinstance(evidence.source_ref, str) or not evidence.source_ref.strip():
        raise ValueError(f"{field_name}.source_ref must be non-blank")
    if evidence.evidence_class != "measured":
        raise ValueError(f"{field_name} must use measured event evidence, not {evidence.evidence_class!r}")
    if evidence.data is None:
        raise ValueError(f"{field_name} measured evidence must retain raw data")
    return _aware_timestamp(evidence.collected_at, f"{field_name}.collected_at")


def _validate_refs(values, field_name: str, *, required: bool = True) -> None:
    if not isinstance(values, list) or (required and not values) or any(
        not isinstance(value, str) or not value.strip() for value in values
    ):
        raise ValueError(f"{field_name} must contain non-blank traceable references")


@dataclasses.dataclass(frozen=True)
class FailurePropagationObservation:
    """Evidence record for one canonical dependency edge.

    RDO's edge orientation is consumer/src depends_on prerequisite/dst. Thus
    failed_key must equal dst and affected_key must equal src. Each endpoint's
    Watcher Evidence is separate; no inference is made from topology alone.
    """

    observation_id: str
    incident_id: str
    failed_key: str
    affected_key: str
    relationship_src: str
    relationship_dst: str
    relationship_kind: str
    observation_window_start: str
    observation_window_end: str
    failed_evidence: Evidence
    operating_envelope: OperatingEnvelopeAssessment = dataclasses.field(
        default_factory=OperatingEnvelopeAssessment
    )
    affected_evidence: Optional[Evidence] = None
    association_state: str = "unknown"
    assessment_evidence: List[str] = dataclasses.field(default_factory=list)
    assessment_provenance: List[str] = dataclasses.field(default_factory=list)
    confidence: Optional[str] = None
    interpretation: Optional[str] = None

    def __post_init__(self) -> None:
        for name in (
            "observation_id", "incident_id", "failed_key", "affected_key",
            "relationship_src", "relationship_dst",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-blank")
        if self.relationship_kind != "depends_on":
            raise ValueError("failure propagation observations require a depends_on relationship")
        if self.failed_key != self.relationship_dst:
            raise ValueError("failed_key must identify the depends_on prerequisite (relationship dst)")
        if self.affected_key != self.relationship_src:
            raise ValueError("affected_key must identify the depends_on consumer (relationship src)")
        if not isinstance(self.operating_envelope, OperatingEnvelopeAssessment):
            raise ValueError("operating_envelope must be an OperatingEnvelopeAssessment")
        if self.association_state not in ASSOCIATION_STATES:
            raise ValueError("invalid association_state")

        start = _aware_timestamp(self.observation_window_start, "observation_window_start")
        end = _aware_timestamp(self.observation_window_end, "observation_window_end")
        if start > end:
            raise ValueError("observation window start must not be after its end")

        if self.operating_envelope.observed_at is not None:
            envelope_time = _aware_timestamp(
                self.operating_envelope.observed_at, "operating_envelope.observed_at"
            )
            if not start <= envelope_time <= end:
                raise ValueError("operating_envelope.observed_at must fall within the observation window")

        failed_time = _validate_endpoint_evidence(
            self.failed_evidence, self.failed_key, "failed_evidence"
        )
        if not start <= failed_time <= end:
            raise ValueError("failed_evidence.collected_at must fall within the observation window")

        affected_time = None
        if self.affected_evidence is not None:
            affected_time = _validate_endpoint_evidence(
                self.affected_evidence, self.affected_key, "affected_evidence"
            )
            if not start <= affected_time <= end:
                raise ValueError("affected_evidence.collected_at must fall within the observation window")

        if self.association_state in ("co_observed", "temporal_association", "causally_attributed"):
            if self.affected_evidence is None:
                raise ValueError(f"{self.association_state} requires separate affected_evidence")
            if (self.failed_evidence.evidence_class != "measured"
                    or self.affected_evidence.evidence_class != "measured"):
                raise ValueError(
                    f"{self.association_state} requires measured evidence for both endpoints"
                )
        if self.association_state == "causally_attributed":
            if not _has_traceable_evidence(self.assessment_evidence):
                raise ValueError("causal attribution requires traceable assessment_evidence")
            if not _has_traceable_evidence(self.assessment_provenance):
                raise ValueError("causal attribution requires traceable assessment_provenance")
            if not isinstance(self.confidence, str) or not self.confidence.strip():
                raise ValueError("causal attribution requires a non-blank confidence label")

        _validate_refs(self.assessment_evidence, "assessment_evidence", required=False)
        _validate_refs(self.assessment_provenance, "assessment_provenance", required=False)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


def record_failure_observation(
    cycle: CycleRecord,
    observation: FailurePropagationObservation,
) -> CycleRecord:
    """Append an observation to its cycle, requiring an exact existing edge.

    Replaying the same observation_id with identical content is idempotent.
    Reusing that ID for different content is rejected rather than overwritten.
    """
    if not isinstance(cycle, CycleRecord):
        raise TypeError("cycle must be a CycleRecord")
    if not isinstance(observation, FailurePropagationObservation):
        raise TypeError("observation must be a FailurePropagationObservation")
    if not isinstance(cycle.relationships, list):
        raise ValueError("cycle relationships must be a list")
    matching_edge = any(
        isinstance(edge, dict)
        and edge.get("src") == observation.relationship_src
        and edge.get("dst") == observation.relationship_dst
        and edge.get("kind") == observation.relationship_kind
        for edge in cycle.relationships
    )
    if not matching_edge:
        raise ValueError("observation relationship does not exist in this cycle")

    if not isinstance(cycle.obligations, list):
        raise ValueError("cycle obligations must be a list")
    obligation_keys = {
        item.get("key") for item in cycle.obligations
        if isinstance(item, dict) and isinstance(item.get("key"), str)
    }
    if (observation.relationship_src not in obligation_keys
            or observation.relationship_dst not in obligation_keys):
        raise ValueError("observation relationship endpoints must exist in cycle obligations")

    records = cycle.observed_failure_evidence
    if not isinstance(records, list):
        raise ValueError("cycle observed_failure_evidence must be a list")
    # Match CycleStore's JSON normalization so replay remains idempotent after reload.
    payload = json.loads(json.dumps(observation.to_dict(), default=str))
    seen_ids = set()
    matching_existing = None
    for existing in records:
        if not isinstance(existing, dict):
            raise ValueError("existing observed_failure_evidence entries must be dictionaries")
        existing_id = existing.get("observation_id")
        if not isinstance(existing_id, str) or not existing_id.strip():
            raise ValueError("existing observed_failure_evidence entry has no valid observation_id")
        if existing_id in seen_ids:
            raise ValueError("cycle contains duplicate observed-failure observation IDs")
        seen_ids.add(existing_id)
        if existing_id == observation.observation_id:
            matching_existing = existing
    if matching_existing is not None:
        if matching_existing != payload:
            raise ValueError("observation_id already exists with different evidence")
    else:
        records.append(payload)
    return cycle
