"""Evidence model for operating-envelope observations.

This module records envelope labels and their supporting observations. It does
not classify load, calculate capacity/headroom, infer transitions, or decide
whether recovery is complete. Those conclusions remain UNKNOWN until calibrated
evidence and assessment logic exist.
"""
from __future__ import annotations

import dataclasses
from typing import Any, List, Optional

from .model import InterfaceEvidence, _has_traceable_evidence

NORMAL = "normal"
BUSY = "busy"
DEGRADED = "degraded"
STRESS = "stress"
RECOVERY = "recovery"
ENVELOPE_STATES = (NORMAL, BUSY, DEGRADED, STRESS, RECOVERY)
UNKNOWN = "unknown"


@dataclasses.dataclass
class OperatingEnvelopeAssessment:
    """Separate declared state, assessed state, and raw evidence.

    A declared state is a report/label, not proof. An assessed state is only
    accepted when accompanied by traceable assessment evidence. Load, capacity,
    headroom, transition and recovery evidence remain independent dimensions.
    """

    scope: Optional[str] = None
    declared_state: str = UNKNOWN
    assessed_state: Optional[str] = None
    measured_load: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    measured_capacity: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    headroom: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    transition_evidence: List[str] = dataclasses.field(default_factory=list)
    recovery_evidence: List[str] = dataclasses.field(default_factory=list)
    assessment_evidence: List[str] = dataclasses.field(default_factory=list)
    provenance: List[str] = dataclasses.field(default_factory=list)
    confidence: Optional[str] = None
    observed_at: Optional[str] = None
    note: str = ""

    def __post_init__(self) -> None:
        if self.declared_state not in (*ENVELOPE_STATES, UNKNOWN):
            raise ValueError(f"invalid declared operating envelope: {self.declared_state!r}")
        if self.assessed_state is not None and self.assessed_state not in ENVELOPE_STATES:
            raise ValueError(f"invalid assessed operating envelope: {self.assessed_state!r}")
        if self.assessed_state is not None:
            if not _has_traceable_evidence(self.assessment_evidence):
                raise ValueError("an assessed state requires traceable assessment evidence")
            if not isinstance(self.confidence, str) or not self.confidence.strip():
                raise ValueError("an assessed state requires a non-blank confidence label")
            if not _has_traceable_evidence(self.provenance):
                raise ValueError("an assessed state requires traceable provenance")
        for field_name in ("transition_evidence", "recovery_evidence",
                           "assessment_evidence", "provenance"):
            values = getattr(self, field_name)
            if not isinstance(values, list) or any(
                not isinstance(value, str) or not value.strip() for value in values
            ):
                raise ValueError(f"{field_name} must contain non-blank text references")

    @property
    def classification_status(self) -> str:
        return "unknown" if self.assessed_state is None else "evidence_recorded"

    def to_dict(self) -> dict:
        data = dataclasses.asdict(self)
        data["classification_status"] = self.classification_status
        return data
