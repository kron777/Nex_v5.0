"""q/tau margin arithmetic remains UNKNOWN without normalized, compatible evidence."""

import pytest

from rdo.model import PerformanceMargin


def test_margin_is_unknown_without_inputs_or_normalization():
    margin = PerformanceMargin(metric="latency")
    assert margin.margin is None
    assert margin.margin_state == "unknown"
    assert not margin.evidence_complete


def test_margin_computes_q_minus_tau_only_for_same_declared_normalization():
    margin = PerformanceMargin(
        metric="normalized_quality",
        q=0.82,
        tau=0.75,
        unit="normalized_quality",
        normalization="higher_is_better_0_to_1",
        q_evidence=["measurement:quality-run-4"],
        tau_evidence=["requirement:quality-spec-2"],
        q_confidence="measured",
        tau_confidence="approved_requirement",
    )
    assert margin.margin == pytest.approx(0.07)
    assert margin.margin_state == "above_requirement"
    assert margin.evidence_complete


def test_negative_margin_is_below_requirement():
    margin = PerformanceMargin(
        metric="normalized_quality", q=0.6, tau=0.7,
        unit="normalized_quality", normalization="higher_is_better_0_to_1",
    )
    assert margin.margin == pytest.approx(-0.1)
    assert margin.margin_state == "below_requirement"


def test_exact_zero_is_boundary_not_automatically_sufficient():
    margin = PerformanceMargin(
        metric="normalized_quality", q=0.7, tau=0.7,
        unit="normalized_quality", normalization="higher_is_better_0_to_1",
    )
    assert margin.margin == 0.0
    assert margin.margin_state == "boundary"


def test_invalid_nonfinite_and_boolean_values_remain_unknown():
    for value in (float("nan"), float("inf"), True, "0.8"):
        margin = PerformanceMargin(
            metric="quality", q=value, tau=0.7, unit="quality",
            normalization="higher_is_better",
        )
        assert margin.margin is None
        assert margin.margin_state == "unknown"


def test_no_unit_or_normalization_means_no_comparable_margin():
    for kwargs in ({"unit": None, "normalization": "higher"},
                   {"unit": "ms", "normalization": None}):
        margin = PerformanceMargin(metric="latency", q=0.8, tau=0.7, **kwargs)
        assert margin.margin is None


def test_evidence_is_not_complete_without_comparable_margin_values():
    margin = PerformanceMargin(
        metric="quality",
        q_evidence=["measurement:q-1"],
        tau_evidence=["requirement:t-1"],
        q_confidence="measured",
        tau_confidence="approved",
        unit="quality",
        normalization="higher_is_better",
    )
    assert margin.margin is None
    assert not margin.evidence_complete


def test_blank_confidence_and_normalization_do_not_complete_margin():
    margin = PerformanceMargin(
        metric="quality", q=0.8, tau=0.7, unit="quality",
        normalization=" ", q_evidence=["measurement:q-1"],
        tau_evidence=["requirement:t-1"], q_confidence="measured",
        tau_confidence="approved",
    )
    assert margin.margin is None
    assert not margin.evidence_complete

    margin.normalization = "higher_is_better"
    margin.tau_confidence = " "
    assert margin.margin == pytest.approx(0.1)
    assert not margin.evidence_complete
