from __future__ import annotations

import math

import pytest

from rdo.model import (
    OVERDEVELOPED,
    SUFFICIENT,
    TENSION_UNKNOWN,
    UNDERDEVELOPED,
    InterfaceTensionProfile,
    PerformanceMargin,
    Relationship,
)
from rdo.tension import assess_relationship


def _profile(**overrides):
    values = {
        "provider": "belief-store-writer",
        "consumer": "belief-reader",
        "purpose": "persist and retrieve a bounded evidence record",
        "direction": "provider_to_consumer",
        "contract_schema": "beliefs.schema.v1",
        "provenance_quality": "measured",
        "timing": "periodic",
        "latency_ms": 8.0,
        "frequency_hz": 0.5,
        "influence_magnitude": "low",
        "failure_semantics": "defined",
        "observability": "observed",
        "capacity": 100.0,
        "headroom": 25.0,
        "feedback_sufficiency": "sufficient",
        "feedback_stability": "stable",
        "duplication": "none",
        "failure_propagation": "bounded",
        "operating_envelope": "normal",
        "margins": [
            PerformanceMargin(
                metric="throughput",
                q=120.0,
                tau=100.0,
                unit="records/min",
                confidence="measured",
                evidence=["metrics/writer-throughput.json:4"],
            )
        ],
        "evidence": ["architecture/interface-contract.md#belief-store"],
    }
    values.update(overrides)
    return InterfaceTensionProfile(**values)


def test_performance_margin_uses_q_minus_tau_and_requires_measured_evidence():
    met = PerformanceMargin(
        metric="throughput", q=12, tau=10, unit="records/s",
        confidence="measured", evidence=["metrics:line-4"],
    )
    below = PerformanceMargin(
        metric="latency-budget", q=7, tau=8, unit="ms",
        confidence="measured", evidence=["trace:span-9"],
    )
    inferred = PerformanceMargin(
        metric="estimated-capacity", q=12, tau=10,
        confidence="inferred", evidence=["model-estimate:2"],
    )
    assert met.margin == 2 and met.status == "met"
    assert below.margin == -1 and below.status == "below_threshold"
    assert inferred.margin == 2 and inferred.status == TENSION_UNKNOWN


def test_relationship_without_interface_profile_is_unknown_not_sufficient():
    rel = Relationship("writer", "reader", "depends_on")
    result = assess_relationship(rel, {})
    assert result.verdict == TENSION_UNKNOWN
    assert result.inference is True
    assert "no InterfaceTensionProfile" in result.note


def test_complete_measured_interface_profile_can_be_sufficient():
    rel = Relationship(
        "writer", "reader", "depends_on", authority="bounded", reversible=True,
        interface_profile=_profile(),
    )
    result = assess_relationship(rel, {})
    assert result.verdict == SUFFICIENT
    assert result.inference is False
    assert result.dimensions["margins"][0]["margin"] == 20.0
    assert result.dimensions["missing_dimensions"] == []


def test_below_threshold_performance_margin_is_underdeveloped():
    profile = _profile(margins=[
        PerformanceMargin(
            metric="throughput", q=80, tau=100, unit="records/min",
            confidence="measured", evidence=["metrics/writer-throughput.json:4"],
        )
    ])
    rel = Relationship(
        "writer", "reader", "depends_on", authority="bounded", reversible=True,
        interface_profile=profile,
    )
    result = assess_relationship(rel, {})
    assert result.verdict == UNDERDEVELOPED
    assert result.inference is False
    assert result.dimensions["margins"][0]["margin"] == -20


def test_unmeasured_margin_remains_unknown_even_when_numeric_values_exist():
    profile = _profile(margins=[
        PerformanceMargin(
            metric="throughput", q=120, tau=100, unit="records/min",
            confidence="inferred", evidence=["model-estimate:1"],
        )
    ])
    rel = Relationship(
        "writer", "reader", "depends_on", authority="bounded", reversible=True,
        interface_profile=profile,
    )
    result = assess_relationship(rel, {})
    assert result.verdict == TENSION_UNKNOWN
    assert "measured_margin_evidence" in result.dimensions["missing_dimensions"]


def test_negative_headroom_is_underdeveloped():
    rel = Relationship(
        "producer", "consumer", "depends_on", authority="bounded", reversible=True,
        interface_profile=_profile(headroom=-5.0),
    )
    result = assess_relationship(rel, {})
    assert result.verdict == UNDERDEVELOPED
    assert "negative" in result.note


def test_unstable_or_insufficient_feedback_is_underdeveloped():
    for overrides in (
        {"feedback_stability": "unstable"},
        {"feedback_sufficiency": "insufficient"},
    ):
        rel = Relationship(
            "producer", "consumer", "influences", authority="bounded", reversible=True,
            interface_profile=_profile(**overrides),
        )
        result = assess_relationship(rel, {})
        assert result.verdict == UNDERDEVELOPED


def test_unbounded_failure_propagation_is_overdeveloped():
    rel = Relationship(
        "producer", "consumer", "depends_on", authority="bounded", reversible=True,
        interface_profile=_profile(failure_propagation="unbounded"),
    )
    result = assess_relationship(rel, {})
    assert result.verdict == OVERDEVELOPED


def test_unbounded_influence_authority_remains_overdeveloped():
    rel = Relationship(
        "producer", "consumer", "influences", authority="strong", reversible=True,
        interface_profile=_profile(influence_magnitude="high"),
    )
    result = assess_relationship(rel, {})
    assert result.verdict == OVERDEVELOPED
    assert "bounded-authority" in result.note


def test_missing_interface_dimensions_remain_unknown():
    profile = _profile(
        contract_schema="",
        operating_envelope="unknown",
        not_applicable=["latency_ms", "frequency_hz", "capacity", "headroom"],
    )
    rel = Relationship(
        "writer", "reader", "depends_on", authority="bounded", reversible=True,
        interface_profile=profile,
    )
    result = assess_relationship(rel, {})
    assert result.verdict == TENSION_UNKNOWN
    assert {"contract_schema", "operating_envelope"} <= set(result.dimensions["missing_dimensions"])


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf, True])
def test_performance_margin_rejects_non_finite_or_boolean_values(bad):
    with pytest.raises(ValueError, match="finite number"):
        PerformanceMargin(metric="capacity", q=bad, tau=1)


def test_profile_serializes_as_part_of_existing_relationship_without_losing_legacy_shape():
    legacy = Relationship("a", "b", "depends_on")
    assert legacy.to_dict()["interface_profile"] is None

    profiled = Relationship(
        "a", "b", "depends_on", authority="bounded", reversible=True,
        interface_profile=_profile(),
    )
    data = profiled.to_dict()
    assert data["interface_profile"]["provider"] == "belief-store-writer"
    assert data["interface_profile"]["margins"][0]["margin"] == 20.0
    assert data["interface_profile"]["margins"][0]["status"] == "met"
