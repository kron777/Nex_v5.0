"""Relationship-level OFT must not infer sufficiency from absent interface evidence."""

from rdo.operating_envelope import BUSY, STRESS, OperatingEnvelopeAssessment
from rdo.model import (
    InterfaceEvidence,
    InterfaceTensionProfile,
    MISSING,
    NECESSARY,
    Obligation,
    Relationship,
    TENSION_UNKNOWN,
    UNDERDEVELOPED,
    OVERDEVELOPED,
)
from rdo.tension import assess_relationship


def test_relationship_without_interface_profile_is_unknown():
    rel = Relationship("consumer", "provider", "depends_on")

    result = assess_relationship(rel, {})

    assert result.verdict == TENSION_UNKNOWN
    assert result.inference is True
    assert result.dimensions["profile_status"] == "not_supplied"
    assert result.dimensions["unknown_dimensions"] == ["interface_profile"]
    assert result.evidence == []


def test_unknown_profile_dimensions_remain_unknown():
    rel = Relationship(
        "consumer",
        "provider",
        "depends_on",
        interface_profile=InterfaceTensionProfile(),
    )

    result = assess_relationship(rel, {})

    assert result.verdict == TENSION_UNKNOWN
    assert result.dimensions["profile_status"] == "supplied"
    assert "contract" in result.dimensions["unknown_dimensions"]
    assert "coupling" in result.dimensions["unknown_dimensions"]


def test_measured_interface_value_without_threshold_does_not_claim_sufficiency():
    profile = InterfaceTensionProfile(
        latency=InterfaceEvidence(
            status="measured",
            value=18.4,
            unit="ms",
            evidence=["test:latency-p95"],
            confidence="measured",
        )
    )
    rel = Relationship("consumer", "provider", "depends_on", interface_profile=profile)

    result = assess_relationship(rel, {})

    assert result.verdict == TENSION_UNKNOWN
    assert result.evidence == ["test:latency-p95"]
    assert result.dimensions["dimensions"]["latency"]["value"] == 18.4
    assert "thresholds, margins" in result.note


def test_relationship_profile_dict_from_persistence_is_supported():
    rel = Relationship(
        "consumer",
        "provider",
        "depends_on",
        interface_profile={
            "provider": "store",
            "consumer": "reader",
            "latency": {
                "status": "measured",
                "value": 10,
                "unit": "ms",
                "evidence": ["benchmark:1"],
                "confidence": "measured",
            },
        },
    )

    result = assess_relationship(rel, {})

    assert result.verdict == TENSION_UNKNOWN
    assert result.dimensions["dimensions"]["latency"]["status"] == "measured"
    assert "schema" in result.dimensions["unknown_dimensions"]
    assert "coupling" in result.dimensions["unknown_dimensions"]


def test_specific_dependency_defect_precedes_generic_profile_unknown():
    target = Obligation("db", "database", "persistence", classification=NECESSARY,
                        recon_status=MISSING)
    rel = Relationship("consumer", "db", "depends_on",
                       interface_profile=InterfaceTensionProfile())

    result = assess_relationship(rel, {"db": target})

    assert result.verdict == UNDERDEVELOPED


def test_unbounded_influence_remains_an_explicit_overdevelopment_finding():
    rel = Relationship("signal", "consumer", "influences", authority="strong")

    result = assess_relationship(rel, {})

    assert result.verdict == OVERDEVELOPED


def test_invalid_interface_profile_shape_is_reported_explicitly():
    rel = Relationship("consumer", "provider", "depends_on", interface_profile="not-a-profile")

    result = assess_relationship(rel, {})

    assert result.verdict == TENSION_UNKNOWN
    assert result.dimensions["profile_status"] == "invalid_shape"
    assert result.dimensions["unknown_dimensions"] == ["interface_profile"]
    assert "invalid shape" in result.note
    assert "evidence is recorded" not in result.note


def test_relationship_assessment_preserves_declared_operating_envelope_as_unknown():
    rel = Relationship("consumer", "provider", "depends_on",
        operating_envelope=OperatingEnvelopeAssessment(declared_state=BUSY))
    result = assess_relationship(rel, {})
    envelope = result.dimensions["operating_envelope"]
    assert envelope["status"] == "unknown"
    assert envelope["declared_state"] == BUSY
    assert envelope["assessed_state"] is None
    assert "headroom" in envelope["unknown_dimensions"]
    assert result.verdict == TENSION_UNKNOWN


def test_relationship_assessment_records_but_does_not_promote_envelope_evidence():
    envelope = OperatingEnvelopeAssessment(assessed_state=STRESS,
        assessment_evidence=["review:stress-1"],
        provenance=["reviewer:independent-1"], confidence="reviewed")
    rel = Relationship("consumer", "provider", "depends_on", operating_envelope=envelope)
    result = assess_relationship(rel, {})
    summary = result.dimensions["operating_envelope"]
    assert summary["status"] == "evidence_recorded"
    assert summary["assessed_state"] == STRESS
    assert "headroom" in summary["unknown_dimensions"]
    assert result.verdict == TENSION_UNKNOWN


def test_relationship_assessment_rejects_unbacked_persisted_envelope_verdict():
    rel = Relationship("consumer", "provider", "depends_on", operating_envelope={
        "declared_state": BUSY, "assessed_state": STRESS,
        "assessment_evidence": ["review:stress"], "provenance": [],
        "confidence": None,
    })
    result = assess_relationship(rel, {})
    assert result.dimensions["operating_envelope"]["status"] == "invalid_evidence"
    assert "assessment" in result.dimensions["operating_envelope"]["unknown_dimensions"]
    assert result.verdict == TENSION_UNKNOWN
