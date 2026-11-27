"""Backward-compatible, UNKNOWN-first interface-profile model tests."""

from rdo.model import (
    InterfaceEvidence,
    InterfaceTensionProfile,
    Relationship,
)


def test_legacy_relationship_shape_remains_valid_and_serialisable():
    relationship = Relationship("consumer", "provider", "depends_on")

    assert relationship.interface_profile is None
    assert relationship.to_dict() == {
        "src": "consumer",
        "dst": "provider",
        "kind": "depends_on",
        "authority": "none",
        "reversible": None,
        "note": "",
        "interface_profile": None,
        "operating_envelope": None,
        "performance_margins": None,
    }


def test_interface_profile_dimensions_default_to_unknown_without_values_or_evidence():
    profile = InterfaceTensionProfile(
        provider="belief_store",
        consumer="belief_reader",
        purpose="read belief state",
        direction="provider_to_consumer",
    )

    data = profile.to_dict()
    assert data["provider"] == "belief_store"
    assert data["consumer"] == "belief_reader"
    assert data["purpose"] == "read belief state"
    assert data["direction"] == "provider_to_consumer"

    dimensions = [
        "contract", "schema", "provenance", "data_quality", "timing",
        "latency", "frequency", "freshness", "influence_magnitude",
        "authority_boundary", "coupling", "reversibility", "error_handling", "fallback",
        "recovery", "observability", "capacity", "headroom",
        "feedback_sufficiency", "feedback_stability", "duplication",
        "failure_propagation",
    ]
    for name in dimensions:
        assert data[name] == {
            "status": "unknown",
            "value": None,
            "unit": None,
            "evidence": [],
            "confidence": None,
        }


def test_interface_profile_preserves_measured_margin_inputs_without_scoring():
    latency = InterfaceEvidence(
        status="measured",
        value=18.4,
        unit="ms",
        evidence=["tests/interface_latency.py::test_p95_latency"],
        confidence="measured",
    )
    profile = InterfaceTensionProfile(latency=latency)
    relationship = Relationship(
        "reader", "store", "depends_on", interface_profile=profile
    )

    stored = relationship.to_dict()["interface_profile"]
    assert stored["latency"] == {
        "status": "measured",
        "value": 18.4,
        "unit": "ms",
        "evidence": ["tests/interface_latency.py::test_p95_latency"],
        "confidence": "measured",
    }
    # No threshold was supplied, so no margin or sufficiency verdict is fabricated.
    assert stored["latency"]["status"] == "measured"
    assert stored["latency"]["evidence"]
    assert stored["headroom"]["status"] == "unknown"
    assert stored["headroom"]["value"] is None


def test_interface_profiles_do_not_share_mutable_default_evidence():
    first = InterfaceTensionProfile()
    second = InterfaceTensionProfile()

    first.latency.evidence.append("fixture")
    assert second.latency.evidence == []


def test_legacy_positional_relationship_constructor_keeps_interface_profile_slot():
    profile = InterfaceTensionProfile()
    relationship = Relationship("consumer", "provider", "depends_on",
                                "none", True, "legacy note", profile)
    assert relationship.interface_profile is profile
    assert relationship.operating_envelope is None


def test_interface_evidence_rejects_unsupported_status_values():
    import pytest

    for status in ("observed", "measurd", "", None, 1):
        with pytest.raises(ValueError, match="invalid interface evidence status"):
            InterfaceEvidence(status=status)


def test_interface_evidence_accepts_documented_nonmeasurement_states():
    for status in ("measured", "implemented", "static", "inferred", "unknown"):
        evidence = InterfaceEvidence(status=status)
        assert evidence.status == status


def test_legacy_relationship_positional_constructor_keeps_trailing_optional_margin_field():
    profile = InterfaceTensionProfile()
    relationship = Relationship("consumer", "provider", "depends_on",
                                "none", True, "legacy note", profile, None)
    assert relationship.interface_profile is profile
    assert relationship.operating_envelope is None
    assert relationship.performance_margins is None


def test_relationship_serializes_typed_performance_margins_with_computed_evidence_state():
    from rdo.model import PerformanceMargin

    margin = PerformanceMargin(
        metric="latency_utility",
        q=0.6,
        tau=0.7,
        unit="normalized_quality",
        normalization="higher_is_better",
        q_evidence=["benchmark:p95"],
        tau_evidence=["contract:latency-limit"],
        q_confidence="measured",
        tau_confidence="approved_requirement",
    )
    relationship = Relationship(
        "reader", "store", "depends_on",
        performance_margins={"latency_utility": margin},
    )

    persisted = relationship.to_dict()["performance_margins"]["latency"]
    assert persisted["margin"] == pytest.approx(-0.1)
    assert persisted["margin_state"] == "below_requirement"
    assert persisted["evidence_complete"] is True
