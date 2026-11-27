"""Relationship-level OFT must not infer sufficiency from absent interface evidence."""

import pytest

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
        "assessment_evidence": ["review:stress"], "provenance": [], "confidence": None,
    })
    result = assess_relationship(rel, {})
    assert result.dimensions["operating_envelope"]["status"] == "invalid_evidence"
    assert "assessment" in result.dimensions["operating_envelope"]["unknown_dimensions"]
    assert result.verdict == TENSION_UNKNOWN


def test_relationship_assessment_fails_closed_on_non_string_envelope_state():
    rel = Relationship("consumer", "provider", "depends_on", operating_envelope={
        "declared_state": BUSY, "assessed_state": {"unexpected": "shape"},
        "assessment_evidence": ["review:stress"], "provenance": ["reviewer:1"],
        "confidence": "reviewed",
    })
    result = assess_relationship(rel, {})
    assert result.dimensions["operating_envelope"]["status"] == "invalid_evidence"
    assert result.verdict == TENSION_UNKNOWN


def test_explicit_relationship_defect_retains_operating_envelope_context():
    rel = Relationship("signal", "consumer", "influences", authority="strong",
        operating_envelope=OperatingEnvelopeAssessment(declared_state=BUSY))
    result = assess_relationship(rel, {})
    assert result.verdict == OVERDEVELOPED
    assert result.dimensions["operating_envelope"]["declared_state"] == BUSY
    assert result.dimensions["operating_envelope"]["status"] == "unknown"


def test_invalid_declared_envelope_state_is_not_treated_as_valid_context():
    rel = Relationship("consumer", "provider", "depends_on", operating_envelope={
        "declared_state": {"not": "a state"}, "assessed_state": None,
    })
    result = assess_relationship(rel, {})
    assert result.dimensions["operating_envelope"]["status"] == "invalid_evidence"


def test_interface_dimension_with_blank_reference_or_confidence_remains_unknown():
    profile = InterfaceTensionProfile(
        latency=InterfaceEvidence(status="measured", value=12, unit="ms",
            evidence=[" "], confidence="measured"),
        freshness=InterfaceEvidence(status="measured", value=1, unit="seconds",
            evidence=["trace:freshness"], confidence=" "),
    )
    result = assess_relationship(Relationship("consumer", "provider", "depends_on",
        interface_profile=profile), {})
    dimensions = result.dimensions["dimensions"]
    assert not dimensions["latency"]["evidence_complete"]
    assert not dimensions["freshness"]["evidence_complete"]
    assert "latency" in result.dimensions["unknown_dimensions"]
    assert "freshness" in result.dimensions["unknown_dimensions"]
    assert result.verdict == TENSION_UNKNOWN


def test_envelope_measurement_value_without_traceable_evidence_stays_unknown():
    envelope = OperatingEnvelopeAssessment(
        measured_load=InterfaceEvidence(status="measured", value=70, unit="percent"),
    )
    result = assess_relationship(Relationship("consumer", "provider", "depends_on",
        operating_envelope=envelope), {})
    assert "measured_load" in result.dimensions["operating_envelope"]["unknown_dimensions"]
    assert result.verdict == TENSION_UNKNOWN


def test_malformed_envelope_measurement_object_does_not_crash_assessment():
    envelope = {"declared_state": BUSY, "assessed_state": None,
                "measured_load": object()}
    result = assess_relationship(Relationship("consumer", "provider", "depends_on",
        operating_envelope=envelope), {})
    assert "measured_load" in result.dimensions["operating_envelope"]["unknown_dimensions"]
    assert result.verdict == TENSION_UNKNOWN

def test_relationship_profile_dict_and_unknown_values_remain_compatible():
    rel = Relationship("consumer", "provider", "depends_on", interface_profile={
        "latency": {"status": "measured", "value": 10, "unit": "ms",
                    "evidence": ["benchmark:1"], "confidence": "measured"},
    })
    result = assess_relationship(rel, {})
    assert result.dimensions["dimensions"]["latency"]["evidence_complete"] is True
    assert result.verdict == TENSION_UNKNOWN


def test_numeric_interface_evidence_requires_finite_value_and_unit():
    profile = InterfaceTensionProfile(
        latency=InterfaceEvidence(status="measured", value=12, unit=None,
            evidence=["trace:latency"], confidence="measured"),
        frequency=InterfaceEvidence(status="measured", value=float("nan"), unit="Hz",
            evidence=["trace:frequency"], confidence="measured"),
    )
    result = assess_relationship(Relationship("consumer", "provider", "depends_on",
        interface_profile=profile), {})
    dimensions = result.dimensions["dimensions"]
    assert not dimensions["latency"]["evidence_complete"]
    assert not dimensions["frequency"]["evidence_complete"]


def test_numeric_envelope_measurements_require_units_and_finite_values():
    envelope = OperatingEnvelopeAssessment(
        measured_load=InterfaceEvidence(status="measured", value=70,
            evidence=["trace:load"], confidence="measured"),
        measured_capacity=InterfaceEvidence(status="measured", value=float("inf"),
            unit="percent", evidence=["trace:capacity"], confidence="measured"),
    )
    result = assess_relationship(Relationship("consumer", "provider", "depends_on",
        operating_envelope=envelope), {})
    unknown = result.dimensions["operating_envelope"]["unknown_dimensions"]
    assert "measured_load" in unknown
    assert "measured_capacity" in unknown


def test_relationship_operating_envelope_round_trips_through_serialized_record():
    envelope = OperatingEnvelopeAssessment(
        declared_state=BUSY,
        measured_load=InterfaceEvidence(status="measured", value=70, unit="percent",
            evidence=["telemetry:load-1"], confidence="measured"),
    )
    original = Relationship("consumer", "provider", "depends_on",
        operating_envelope=envelope)
    persisted = original.to_dict()
    assert persisted["operating_envelope"]["declared_state"] == BUSY
    assert persisted["operating_envelope"]["measured_load"]["value"] == 70

    restored = Relationship("consumer", "provider", "depends_on",
        operating_envelope=persisted["operating_envelope"])
    result = assess_relationship(restored, {})
    summary = result.dimensions["operating_envelope"]
    assert summary["declared_state"] == BUSY
    assert summary["status"] == "unknown"
    assert "measured_load" not in summary["unknown_dimensions"]
    assert result.verdict == TENSION_UNKNOWN


def test_malformed_envelope_serializer_fails_closed():
    class BrokenEnvelope:
        to_dict = "not-callable"
    result = assess_relationship(Relationship("consumer", "provider", "depends_on",
        operating_envelope=BrokenEnvelope()), {})
    summary = result.dimensions["operating_envelope"]
    assert summary["status"] == "invalid_shape"
    assert result.verdict == TENSION_UNKNOWN


def test_malformed_interface_profile_serializer_fails_closed():
    class NonCallableProfile:
        to_dict = "not-callable"

    class RaisingProfile:
        def to_dict(self):
            raise RuntimeError("profile serialization failed")

    for profile in (NonCallableProfile(), RaisingProfile()):
        result = assess_relationship(
            Relationship("consumer", "provider", "depends_on",
                         interface_profile=profile),
            {},
        )
        assert result.verdict == TENSION_UNKNOWN
        assert result.dimensions["profile_status"] == "invalid_shape"
        assert result.dimensions["unknown_dimensions"] == ["interface_profile"]
        assert "invalid shape" in result.note
        assert "evidence is recorded" not in result.note


def test_persisted_interface_dimension_with_unknown_status_fails_closed():
    rel = Relationship("consumer", "provider", "depends_on", interface_profile={
        "latency": {
            "status": "measurd",
            "value": 12,
            "unit": "ms",
            "evidence": ["trace:latency"],
            "confidence": "measured",
        },
    })

    result = assess_relationship(rel, {})
    latency = result.dimensions["dimensions"]["latency"]
    assert latency["status"] == "invalid"
    assert latency["evidence_complete"] is False
    assert "latency" in result.dimensions["unknown_dimensions"]
    assert result.verdict == TENSION_UNKNOWN


def test_operating_envelope_measurement_with_unrecognized_status_stays_unknown():
    rel = Relationship("consumer", "provider", "depends_on", operating_envelope={
        "declared_state": BUSY,
        "assessed_state": None,
        "measured_load": {
            "status": "observed",
            "value": 70,
            "unit": "percent",
            "evidence": ["telemetry:load-1"],
            "confidence": "measured",
        },
    })

    result = assess_relationship(rel, {})
    envelope = result.dimensions["operating_envelope"]
    assert "measured_load" in envelope["unknown_dimensions"]
    assert result.verdict == TENSION_UNKNOWN


def test_implemented_interface_evidence_is_preserved_without_promoting_relationship():
    rel = Relationship("consumer", "provider", "depends_on", interface_profile={
        "contract": {
            "status": "implemented",
            "value": "versioned-json-contract",
            "evidence": ["source:contract-definition"],
            "confidence": "reviewed",
        },
    })

    result = assess_relationship(rel, {})
    contract = result.dimensions["dimensions"]["contract"]
    assert contract["status"] == "implemented"
    assert contract["evidence_complete"] is True
    assert "contract" not in result.dimensions["unknown_dimensions"]
    assert result.verdict == TENSION_UNKNOWN


def test_relationship_assessment_exposes_typed_performance_margin_evidence_without_verdict():
    from rdo.model import PerformanceMargin

    margin = PerformanceMargin(
        metric="latency_utility",
        q=0.6,
        tau=0.7,
        unit="normalized_latency_utility",
        normalization="higher_is_better_0_to_1",
        q_evidence=["benchmark:latency-utility"],
        tau_evidence=["contract:latency-utility-limit"],
        q_confidence="measured",
        tau_confidence="approved_requirement",
    )
    rel = Relationship("consumer", "provider", "depends_on",
                      performance_margins={"latency_utility": margin})

    result = assess_relationship(rel, {})
    summary = result.dimensions["performance_margins"]
    assert summary["status"] == "evidence_recorded"
    assert summary["metrics"]["latency_utility"]["margin"] == pytest.approx(-0.1)
    assert summary["metrics"]["latency_utility"]["margin_state"] == "below_requirement"
    assert summary["metrics"]["latency_utility"]["evidence_complete"] is True
    assert result.evidence == ["benchmark:latency-utility", "contract:latency-utility-limit"]
    # A metric margin is evidence; no calibrated aggregation into relationship tension exists.
    assert result.verdict == TENSION_UNKNOWN


def test_relationship_assessment_recomputes_persisted_margin_and_ignores_tampered_computed_fields():
    persisted = {
        "latency_utility": {
            "metric": "latency_utility",
            "q": 0.6,
            "tau": 0.7,
            "unit": "normalized_latency_utility",
            "normalization": "higher_is_better_0_to_1",
            "q_evidence": ["benchmark:latency-utility"],
            "tau_evidence": ["contract:latency-utility-limit"],
            "q_confidence": "measured",
            "tau_confidence": "approved_requirement",
            "margin": 999,
            "margin_state": "above_requirement",
            "evidence_complete": True,
        },
    }
    result = assess_relationship(Relationship("consumer", "provider", "depends_on",
        performance_margins=persisted), {})
    metric = result.dimensions["performance_margins"]["metrics"]["latency_utility"]
    assert metric["margin"] == pytest.approx(-0.1)
    assert metric["margin_state"] == "below_requirement"
    assert metric["evidence_complete"] is True
    assert result.verdict == TENSION_UNKNOWN


def test_incomplete_or_boundary_margin_evidence_is_preserved_without_claiming_sufficiency():
    from rdo.model import PerformanceMargin

    incomplete = PerformanceMargin(
        metric="latency_utility", q=0.6, tau=0.7,
        unit="normalized_latency_utility",
        normalization="higher_is_better_0_to_1",
    )
    boundary = PerformanceMargin(
        metric="quality", q=0.8, tau=0.8, unit="normalized",
        normalization="higher_is_better",
        q_evidence=["measurement:quality"],
        tau_evidence=["requirement:quality"],
        q_confidence="measured",
        tau_confidence="approved",
    )
    result = assess_relationship(Relationship("consumer", "provider", "depends_on",
        performance_margins={"latency_utility": incomplete, "quality": boundary}), {})
    summary = result.dimensions["performance_margins"]
    assert summary["status"] == "partial"
    assert summary["unknown_metrics"] == ["latency_utility"]
    assert summary["metrics"]["latency_utility"]["margin_state"] == "below_requirement"
    assert summary["metrics"]["latency_utility"]["evidence_complete"] is False
    assert summary["metrics"]["quality"]["margin_state"] == "boundary"
    assert summary["metrics"]["quality"]["evidence_complete"] is True
    assert result.verdict == TENSION_UNKNOWN


def test_malformed_persisted_performance_margin_fails_closed():
    result = assess_relationship(Relationship("consumer", "provider", "depends_on",
        performance_margins={
            "latency": {"metric": "other", "q": 12, "tau": 15},
            "capacity": ["not", "a", "margin"],
            "": {"metric": "blank-key"},
        }), {})
    summary = result.dimensions["performance_margins"]
    assert summary["status"] == "invalid_evidence"
    assert summary["metrics"] == {}
    assert summary["invalid_metrics"] == ["", "capacity", "latency"]
    assert result.verdict == TENSION_UNKNOWN


def test_explicit_relationship_defect_retains_performance_margin_context():
    from rdo.model import PerformanceMargin

    margin = PerformanceMargin(
        metric="authority-impact",
        q=0.9,
        tau=0.5,
        unit="normalized",
        normalization="higher_is_better",
        q_evidence=["measurement:authority"],
        tau_evidence=["policy:authority-bound"],
        q_confidence="measured",
        tau_confidence="approved",
    )
    result = assess_relationship(Relationship(
        "signal", "consumer", "influences", authority="strong",
        performance_margins={"authority-impact": margin},
    ), {})
    assert result.verdict == OVERDEVELOPED
    assert result.dimensions["performance_margins"]["status"] == "evidence_recorded"
    assert result.dimensions["performance_margins"]["metrics"]["authority-impact"]["margin"] == pytest.approx(0.4)


def test_mutated_typed_performance_margin_fails_closed_on_reassessment():
    from rdo.model import PerformanceMargin

    margin = PerformanceMargin(metric="latency", q=0.8, tau=0.7,
        unit="normalized", normalization="higher_is_better")
    margin.operating_envelope = "overloaded"

    result = assess_relationship(Relationship("consumer", "provider", "depends_on",
        performance_margins={"latency": margin}), {})
    summary = result.dimensions["performance_margins"]
    assert summary["status"] == "invalid_evidence"
    assert summary["metrics"] == {}
    assert summary["invalid_metrics"] == ["latency"]
    assert result.verdict == TENSION_UNKNOWN


def test_malformed_mutable_margin_evidence_refs_are_not_promoted_to_sources():
    from rdo.model import PerformanceMargin

    margin = PerformanceMargin(metric="latency", q=0.8, tau=0.7,
        unit="normalized", normalization="higher_is_better",
        q_evidence=["benchmark:latency"], tau_evidence=["limit:latency"])
    margin.q_evidence = "not-a-reference-list"

    result = assess_relationship(Relationship("consumer", "provider", "depends_on",
        performance_margins={"latency": margin}), {})
    summary = result.dimensions["performance_margins"]
    assert summary["metrics"]["latency"]["evidence_complete"] is False
    assert summary["unknown_metrics"] == ["latency"]
    assert result.evidence == []
    assert result.verdict == TENSION_UNKNOWN
