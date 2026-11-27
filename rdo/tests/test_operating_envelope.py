"""Operating-envelope labels must not be confused with measured capacity or proof."""
import pytest

from rdo.model import InterfaceEvidence
from rdo.operating_envelope import (
    BUSY,
    DEGRADED,
    ENVELOPE_STATES,
    NORMAL,
    RECOVERY,
    STRESS,
    UNKNOWN,
    OperatingEnvelopeAssessment,
)


def test_all_five_documented_envelopes_are_representable():
    assert ENVELOPE_STATES == (NORMAL, BUSY, DEGRADED, STRESS, RECOVERY)


def test_empty_assessment_stays_unknown_and_does_not_invent_capacity():
    assessment = OperatingEnvelopeAssessment()

    assert assessment.declared_state == UNKNOWN
    assert assessment.assessed_state is None
    assert assessment.classification_status == "unknown"
    assert assessment.measured_load.value is None
    assert assessment.measured_capacity.value is None
    assert assessment.headroom.value is None
    assert assessment.to_dict()["classification_status"] == "unknown"


def test_declared_label_is_not_promoted_to_assessed_state():
    assessment = OperatingEnvelopeAssessment(declared_state=BUSY)

    assert assessment.declared_state == BUSY
    assert assessment.assessed_state is None
    assert assessment.classification_status == "unknown"


def test_measured_capacity_and_headroom_remain_separate_evidence_dimensions():
    assessment = OperatingEnvelopeAssessment(
        declared_state=DEGRADED,
        measured_load=InterfaceEvidence(
            status="measured", value=72, unit="percent",
            evidence=["telemetry:load-7"], confidence="measured",
        ),
        measured_capacity=InterfaceEvidence(
            status="unknown", evidence=[], confidence=None,
        ),
        headroom=InterfaceEvidence(),
    )

    assert assessment.measured_load.value == 72
    assert assessment.measured_capacity.value is None
    assert assessment.headroom.value is None
    assert assessment.assessed_state is None


def test_assessed_state_requires_traceable_assessment_evidence():
    with pytest.raises(ValueError, match="requires traceable assessment evidence"):
        OperatingEnvelopeAssessment(assessed_state=STRESS)


def test_assessed_state_can_be_recorded_without_claiming_recovery_or_headroom():
    assessment = OperatingEnvelopeAssessment(
        assessed_state=RECOVERY,
        assessment_evidence=["assessment:review-12"],
        provenance=["reviewer:independent-assessment"],
        confidence="reviewed",
    )

    assert assessment.assessed_state == RECOVERY
    assert assessment.classification_status == "evidence_recorded"
    assert assessment.recovery_evidence == []
    assert assessment.headroom.value is None


def test_invalid_states_and_blank_evidence_references_are_rejected():
    with pytest.raises(ValueError, match="invalid declared"):
        OperatingEnvelopeAssessment(declared_state="overloaded")
    with pytest.raises(ValueError, match="invalid assessed"):
        OperatingEnvelopeAssessment(assessed_state="overloaded", assessment_evidence=["review:1"])
    with pytest.raises(ValueError, match="non-blank"):
        OperatingEnvelopeAssessment(transition_evidence=[" "])


def test_assessed_state_requires_nonblank_confidence_and_traceable_provenance():
    base = dict(assessed_state=STRESS, assessment_evidence=["review:stress"])
    with pytest.raises(ValueError, match="confidence label"):
        OperatingEnvelopeAssessment(**base, provenance=["reviewer:1"])
    with pytest.raises(ValueError, match="provenance"):
        OperatingEnvelopeAssessment(**base, confidence="reviewed")
    with pytest.raises(ValueError, match="confidence label"):
        OperatingEnvelopeAssessment(**base, confidence=" ", provenance=["reviewer:1"])
    with pytest.raises(ValueError, match="provenance"):
        OperatingEnvelopeAssessment(**base, confidence="reviewed", provenance=[" "])


def test_unknown_envelope_can_retain_partial_assessment_metadata():
    assessment = OperatingEnvelopeAssessment(declared_state=BUSY,
        assessment_evidence=[], provenance=[], confidence=None)
    assert assessment.assessed_state is None
    assert assessment.classification_status == "unknown"
