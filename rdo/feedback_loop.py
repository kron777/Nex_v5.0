"""Evidence model for system-level feedback-loop stability.

A graph cycle is topology, not a stability verdict. This record captures the
measurements needed to investigate a loop without assuming that feedback is
harmful or that a loop should be removed. It deliberately performs no stability
calculation and defaults all conclusions to UNKNOWN.
"""
from __future__ import annotations

import dataclasses
from typing import List, Optional

from .model import InterfaceEvidence, _has_traceable_evidence

STABILITY_STATES = ("stable", "unstable", "conditionally_stable")
UNKNOWN = "unknown"


@dataclasses.dataclass
class FeedbackLoopAssessment:
    """Evidence record for one identified feedback loop.

    Members and relationships identify the loop under observation. Gain,
    delay, damping, oscillation, overshoot and recovery are independent evidence
    dimensions: absence of one must not be mistaken for a safe value. A recorded
    stability state is an assessor's conclusion, not an automatically derived
    result, and therefore requires traceable assessment evidence.
    """

    loop_id: str
    members: List[str] = dataclasses.field(default_factory=list)
    relationships: List[str] = dataclasses.field(default_factory=list)
    scope: Optional[str] = None
    gain: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    delay: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    damping: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    oscillation: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    overshoot: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    recovery: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    observation_window: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    operating_envelope: str = UNKNOWN
    stability_state: str = UNKNOWN
    assessment_evidence: List[str] = dataclasses.field(default_factory=list)
    provenance: List[str] = dataclasses.field(default_factory=list)
    confidence: Optional[str] = None
    note: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.loop_id, str) or not self.loop_id.strip():
            raise ValueError("loop_id must be non-blank")
        for field_name in ("members", "relationships", "assessment_evidence", "provenance"):
            values = getattr(self, field_name)
            if not isinstance(values, list) or any(
                not isinstance(value, str) or not value.strip() for value in values
            ):
                raise ValueError(f"{field_name} must contain non-blank references")
        if not self.members:
            raise ValueError("a feedback loop requires at least one member")
        if not self.relationships:
            raise ValueError("a feedback loop requires at least one relationship")
        if len(set(self.members)) != len(self.members):
            raise ValueError("feedback loop members must be unique")
        if len(set(self.relationships)) != len(self.relationships):
            raise ValueError("feedback loop relationships must be unique")
        if self.stability_state not in (*STABILITY_STATES, UNKNOWN):
            raise ValueError(f"invalid feedback stability state: {self.stability_state!r}")
        if self.stability_state != UNKNOWN:
            if not _has_traceable_evidence(self.assessment_evidence):
                raise ValueError(
                    "a non-UNKNOWN stability state requires traceable assessment evidence"
                )
            if not isinstance(self.confidence, str) or not self.confidence.strip():
                raise ValueError(
                    "a non-UNKNOWN stability state requires a non-blank confidence label"
                )
            if not _has_traceable_evidence(self.provenance):
                raise ValueError(
                    "a non-UNKNOWN stability state requires traceable provenance"
                )
        if self.operating_envelope not in (
            "normal", "busy", "degraded", "stress", "recovery", UNKNOWN
        ):
            raise ValueError(f"invalid operating envelope: {self.operating_envelope!r}")

    @property
    def assessment_status(self) -> str:
        return "unknown" if self.stability_state == UNKNOWN else "evidence_recorded"

    def to_dict(self) -> dict:
        data = dataclasses.asdict(self)
        data["assessment_status"] = self.assessment_status
        return data
