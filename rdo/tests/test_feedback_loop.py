"""Feedback-loop evidence stays distinct from graph-cycle detection and verdicts."""
import pytest

from rdo.feedback_loop import (
    STABILITY_STATES,
    UNKNOWN,
    FeedbackLoopAssessment,
)
from rdo.model import InterfaceEvidence


def test_feedback_loop_defaults_to_unknown_without_invented_stability():
    loop = FeedbackLoopAssessment(loop_id="loop-1", members=["A", "B"])

    assert loop.stability_state == UNKNOWN
    assert loop.assessment_status == "unknown"
    assert loop.gain.value is None
    assert loop.delay.value is None
    assert loop.damping.value is None
    assert loop.oscillation.value is None
    assert loop.overshoot.value is None
    assert loop.recovery.value is None
    assert loop.observation_window.value is None


def test_feedback_loop_preserves_topology_and_measured_dimensions_independently():
    loop = FeedbackLoopAssessment(
        loop_id="loop-AB",
        members=["A", "B"],
        relationships=["A-influences-B", "B-influences-A"],
        gain=InterfaceEvidence(
            status="measured", value=0.7, unit="ratio",
            evidence=["trace:gain-1"], confidence="measured",
        ),
        delay=InterfaceEvidence(
            status="measured", value=120, unit="ms",
            evidence=["trace:delay-1"], confidence="measured",
        ),
    )

    assert loop.members == ["A", "B"]
    assert len(loop.relationships) == 2
    assert loop.gain.value == 0.7
    assert loop.delay.value == 120
    assert loop.damping.value is None
    assert loop.stability_state == UNKNOWN


def test_feedback_stability_states_are_explicit_but_not_automatically_inferred():
    assert STABILITY_STATES == ("stable", "unstable", "conditionally_stable")
    loop = FeedbackLoopAssessment(
        loop_id="loop-2",
        stability_state="conditionally_stable",
        assessment_evidence=["review:stability-2"],
    )

    assert loop.assessment_status == "evidence_recorded"
    assert loop.to_dict()["assessment_status"] == "evidence_recorded"


def test_stability_verdict_requires_assessment_evidence():
    with pytest.raises(ValueError, match="requires assessment evidence"):
        FeedbackLoopAssessment(loop_id="loop-3", stability_state="stable")


def test_feedback_loop_rejects_invalid_state_and_blank_identity():
    with pytest.raises(ValueError, match="invalid feedback stability"):
        FeedbackLoopAssessment(loop_id="loop-4", stability_state="safe")
    with pytest.raises(ValueError, match="loop_id"):
        FeedbackLoopAssessment(loop_id=" ")
    with pytest.raises(ValueError, match="non-blank"):
        FeedbackLoopAssessment(loop_id="loop-5", relationships=[" "])


def test_operating_envelope_is_context_not_a_stability_verdict():
    loop = FeedbackLoopAssessment(
        loop_id="loop-6",
        operating_envelope="stress",
    )

    assert loop.operating_envelope == "stress"
    assert loop.stability_state == UNKNOWN
