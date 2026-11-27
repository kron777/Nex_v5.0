"""Adversarial tests for traceable observed-failure evidence."""
import json

import pytest

from rdo.failure_evidence import (
    FailurePropagationObservation,
    record_failure_observation,
)
from rdo.memory import CycleStore
from rdo.model import CycleRecord
from rdo.operating_envelope import OperatingEnvelopeAssessment
from watcher.evidence import Evidence


def _cycle():
    return CycleRecord(
        id="failure-evidence",
        objective="test observed failure evidence",
        obligations=[{"key": "consumer"}, {"key": "prerequisite"}],
        relationships=[{
            "src": "consumer",
            "dst": "prerequisite",
            "kind": "depends_on",
        }],
    )


def _evidence(subject, source_ref, collected_at="2026-11-28T10:05:00Z", **overrides):
    values = dict(
        subject=subject,
        data={"state": "failure_observed", "raw": ("sample-a", "sample-b")},
        origin="host",
        evidence_class="measured",
        source_ref=source_ref,
        collected_at=collected_at,
    )
    values.update(overrides)
    return Evidence(**values)


def _observation(**overrides):
    values = dict(
        observation_id="obs-001",
        incident_id="incident-001",
        failed_key="prerequisite",
        affected_key="consumer",
        relationship_src="consumer",
        relationship_dst="prerequisite",
        relationship_kind="depends_on",
        observation_window_start="2026-11-28T10:00:00+00:00",
        observation_window_end="2026-11-28T10:10:00+00:00",
        failed_evidence=_evidence("prerequisite", "trace:prerequisite-001"),
        operating_envelope=OperatingEnvelopeAssessment(declared_state="busy"),
    )
    values.update(overrides)
    return FailurePropagationObservation(**values)


def test_observation_defaults_to_unknown_and_does_not_claim_causality():
    item = _observation()
    assert item.association_state == "unknown"
    assert item.affected_evidence is None
    assert item.to_dict()["confidence"] is None
    assert item.to_dict()["assessment_evidence"] == []


def test_observation_requires_canonical_depends_on_orientation():
    with pytest.raises(ValueError, match="prerequisite"):
        _observation(failed_key="consumer")
    with pytest.raises(ValueError, match="consumer"):
        _observation(affected_key="prerequisite")
    with pytest.raises(ValueError, match="depends_on"):
        _observation(relationship_kind="influences")
    with pytest.raises(ValueError, match="depends_on"):
        _observation(relationship_kind="requires")


def test_observation_requires_timezone_aware_window_and_in_window_evidence():
    with pytest.raises(ValueError, match="timezone"):
        _observation(
            failed_evidence=_evidence(
                "prerequisite", "trace:1", collected_at="2026-11-28T10:05:00"
            )
        )
    with pytest.raises(ValueError, match="within the observation window"):
        _observation(
            failed_evidence=_evidence(
                "prerequisite", "trace:1", collected_at="2026-11-28T10:11:00Z"
            )
        )
    with pytest.raises(ValueError, match="must not be after"):
        _observation(
            observation_window_start="2026-11-28T10:10:00Z",
            observation_window_end="2026-11-28T10:00:00Z",
        )


def test_endpoint_evidence_must_match_canonical_subject():
    with pytest.raises(ValueError, match="canonical obligation key"):
        _observation(failed_evidence=_evidence("consumer", "trace:wrong-subject"))


def test_co_observation_requires_independent_evidence_for_both_endpoints():
    with pytest.raises(ValueError, match="affected_evidence"):
        _observation(association_state="co_observed")
    item = _observation(
        association_state="co_observed",
        affected_evidence=_evidence("consumer", "trace:consumer-001"),
    )
    assert item.association_state == "co_observed"
    assert item.affected_evidence.subject == "consumer"


def test_temporal_association_requires_both_endpoint_observations():
    item = _observation(
        association_state="temporal_association",
        affected_evidence=_evidence(
            "consumer", "trace:consumer-001", collected_at="2026-11-28T10:07:00Z"
        ),
    )
    assert item.association_state == "temporal_association"


def test_causal_attribution_requires_separate_assessment_evidence():
    with pytest.raises(ValueError, match="affected_evidence"):
        _observation(association_state="causally_attributed")
    with pytest.raises(ValueError, match="assessment_evidence"):
        _observation(
            association_state="causally_attributed",
            affected_evidence=_evidence("consumer", "trace:consumer-001"),
        )
    item = _observation(
        association_state="causally_attributed",
        affected_evidence=_evidence("consumer", "trace:consumer-001"),
        assessment_evidence=["review:causal-analysis-001"],
        assessment_provenance=["reviewer:independent"],
        confidence="reviewed",
    )
    assert item.association_state == "causally_attributed"


def test_static_evidence_cannot_be_recorded_as_an_observed_failure_event():
    with pytest.raises(ValueError, match="measured event evidence"):
        _observation(
            failed_evidence=_evidence(
                "prerequisite", "github:source-snapshot",
                origin="cloud", evidence_class="static",
            )
        )


def test_measured_cloud_evidence_remains_cloud_not_host_runtime_evidence():
    item = _observation(
        failed_evidence=_evidence(
            "prerequisite", "ci:failure-trace",
            origin="cloud", evidence_class="measured",
        )
    )
    assert item.failed_evidence.origin == "cloud"
    assert item.failed_evidence.evidence_class == "measured"
    assert item.association_state == "unknown"


def test_operating_envelope_uses_typed_evidence_and_preserves_unknown_assessment():
    item = _observation()
    assert isinstance(item.operating_envelope, OperatingEnvelopeAssessment)
    assert item.operating_envelope.declared_state == "busy"
    assert item.operating_envelope.assessed_state is None


def test_operating_envelope_assessment_requires_evidence_and_stays_in_window():
    with pytest.raises(ValueError, match="assessment evidence"):
        _observation(
            operating_envelope=OperatingEnvelopeAssessment(
                declared_state="busy", assessed_state="busy"
            )
        )
    with pytest.raises(ValueError, match="within the observation window"):
        _observation(
            operating_envelope=OperatingEnvelopeAssessment(
                declared_state="busy",
                observed_at="2026-11-28T10:11:00Z",
            )
        )
    item = _observation(
        operating_envelope=OperatingEnvelopeAssessment(
            declared_state="busy",
            assessed_state="busy",
            assessment_evidence=["review:envelope-001"],
            provenance=["watcher:host-trace-001"],
            confidence="reviewed",
            observed_at="2026-11-28T10:05:00Z",
        )
    )
    assert item.operating_envelope.assessed_state == "busy"


def test_record_requires_exact_relationship_in_cycle():
    cycle = _cycle()
    item = _observation(relationship_src="other", affected_key="other")
    with pytest.raises(ValueError, match="does not exist"):
        record_failure_observation(cycle, item)
    assert cycle.observed_failure_evidence == []


def test_record_is_idempotent_but_rejects_observation_id_collision():
    cycle = _cycle()
    item = _observation()
    record_failure_observation(cycle, item)
    record_failure_observation(cycle, item)
    assert len(cycle.observed_failure_evidence) == 1

    changed = _observation(operating_envelope=OperatingEnvelopeAssessment(declared_state="stress"))
    with pytest.raises(ValueError, match="different evidence"):
        record_failure_observation(cycle, changed)
    assert len(cycle.observed_failure_evidence) == 1


def test_record_rejects_malformed_existing_evidence_entries():
    cycle = _cycle()
    cycle.observed_failure_evidence.append({"missing": "observation_id"})
    with pytest.raises(ValueError, match="no valid observation_id"):
        record_failure_observation(cycle, _observation())


def test_record_rejects_duplicate_existing_observation_ids():
    cycle = _cycle()
    payload = _observation().to_dict()
    cycle.observed_failure_evidence.extend([payload, dict(payload)])
    with pytest.raises(ValueError, match="duplicate observed-failure observation IDs"):
        record_failure_observation(cycle, _observation())


def test_cycle_store_round_trips_observed_failure_evidence(tmp_path):
    cycle = _cycle()
    item = _observation(
        association_state="co_observed",
        affected_evidence=_evidence("consumer", "trace:consumer-001"),
    )
    record_failure_observation(cycle, item)
    store = CycleStore(str(tmp_path))
    store.save(cycle)

    loaded = store.load(cycle.id)
    record_failure_observation(loaded, item)

    assert loaded.observed_failure_evidence == cycle.observed_failure_evidence
    assert loaded.observed_failure_evidence[0]["relationship_src"] == "consumer"
    assert loaded.observed_failure_evidence[0]["failed_key"] == "prerequisite"
    assert loaded.observed_failure_evidence[0]["affected_evidence"]["subject"] == "consumer"


def test_legacy_cycle_without_observed_failure_field_still_loads(tmp_path):
    path = tmp_path / "cycle_legacy.json"
    path.write_text(json.dumps({
        "id": "legacy",
        "objective": "legacy cycle",
        "relationships": [],
        "obligations": [],
    }), encoding="utf-8")

    loaded = CycleStore(str(tmp_path)).load("legacy")

    assert loaded.observed_failure_evidence == []


def test_record_rejects_relationship_edges_with_missing_cycle_obligation_endpoints():
    cycle = _cycle()
    cycle.relationships[0]["dst"] = "missing-prerequisite"
    item = _observation(
        failed_key="missing-prerequisite",
        relationship_dst="missing-prerequisite",
        failed_evidence=_evidence("missing-prerequisite", "trace:missing-prerequisite"),
    )

    with pytest.raises(ValueError, match="endpoints must exist in cycle obligations"):
        record_failure_observation(cycle, item)

    assert cycle.observed_failure_evidence == []
