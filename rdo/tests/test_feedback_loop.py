"""Feedback-loop evidence stays distinct from graph-cycle detection and verdicts."""
import json

import pytest

from rdo.feedback_loop import (
    STABILITY_STATES,
    UNKNOWN,
    FeedbackLoopAssessment,
)
from rdo.model import InterfaceEvidence


def test_feedback_loop_defaults_to_unknown_without_invented_stability():
    loop = FeedbackLoopAssessment(
        loop_id="loop-1",
        members=["A", "B"],
        relationships=["A-influences-B", "B-influences-A"],
    )

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
        members=["A"],
        relationships=["A-influences-A"],
        stability_state="conditionally_stable",
        assessment_evidence=["review:stability-2"],
        provenance=["reviewer:independent-assessment"],
        confidence="reviewed",
    )

    assert loop.assessment_status == "evidence_recorded"
    assert loop.to_dict()["assessment_status"] == "evidence_recorded"


def test_stability_verdict_requires_assessment_evidence():
    with pytest.raises(ValueError, match="traceable assessment evidence"):
        FeedbackLoopAssessment(
            loop_id="loop-3",
            members=["A"],
            relationships=["A-influences-A"],
            stability_state="stable",
        )


def test_feedback_loop_rejects_invalid_state_and_blank_identity():
    with pytest.raises(ValueError, match="invalid feedback stability"):
        FeedbackLoopAssessment(
            loop_id="loop-4", members=["A"], relationships=["A-influences-A"],
            stability_state="safe",
        )
    with pytest.raises(ValueError, match="loop_id"):
        FeedbackLoopAssessment(loop_id=" ")
    with pytest.raises(ValueError, match="non-blank"):
        FeedbackLoopAssessment(
            loop_id="loop-5", members=["A"], relationships=[" "]
        )


def test_feedback_loop_requires_topology_and_unique_members():
    with pytest.raises(ValueError, match="at least one member"):
        FeedbackLoopAssessment(loop_id="loop-6", relationships=["A->B"])
    with pytest.raises(ValueError, match="at least one relationship"):
        FeedbackLoopAssessment(loop_id="loop-7", members=["A"])
    with pytest.raises(ValueError, match="members must be unique"):
        FeedbackLoopAssessment(
            loop_id="loop-8", members=["A", "A"], relationships=["A->A"]
        )


def test_operating_envelope_is_context_not_a_stability_verdict():
    loop = FeedbackLoopAssessment(
        loop_id="loop-9",
        members=["A"],
        relationships=["A-influences-A"],
        operating_envelope="stress",
    )

    assert loop.operating_envelope == "stress"
    assert loop.stability_state == UNKNOWN


def test_non_unknown_stability_requires_confidence_and_provenance():
    base = dict(loop_id="loop-evidence", members=["A"], relationships=["A->A"],
                stability_state="stable", assessment_evidence=["review:stable"])
    with pytest.raises(ValueError, match="confidence label"):
        FeedbackLoopAssessment(**base, provenance=["reviewer:1"])
    with pytest.raises(ValueError, match="provenance"):
        FeedbackLoopAssessment(**base, confidence="reviewed")
    with pytest.raises(ValueError, match="confidence label"):
        FeedbackLoopAssessment(**base, confidence=" ", provenance=["reviewer:1"])
    with pytest.raises(ValueError, match="provenance"):
        FeedbackLoopAssessment(**base, confidence="reviewed", provenance=[])


def test_unknown_stability_can_preserve_partial_or_missing_verdict_evidence():
    loop = FeedbackLoopAssessment(loop_id="loop-unknown", members=["A"],
        relationships=["A->A"], stability_state=UNKNOWN, assessment_evidence=[],
        confidence=None, provenance=[])
    assert loop.assessment_status == "unknown"



def test_cycle_detector_preserves_distinct_directed_cycles_with_same_members():
    from rdo.model import Relationship
    from rdo.tension import _find_cycles

    edges = [
        Relationship("A", "B", "influences"),
        Relationship("B", "C", "influences"),
        Relationship("C", "D", "influences"),
        Relationship("D", "A", "influences"),
        Relationship("A", "C", "influences"),
        Relationship("C", "B", "influences"),
        Relationship("B", "D", "influences"),
    ]

    cycles = _find_cycles(edges)

    def canonical(path):
        nodes = path[:-1]
        return min(tuple(nodes[index:] + nodes[:index]) for index in range(len(nodes)))

    cycle_set = {canonical(cycle) for cycle in cycles}
    assert ("A", "B", "C", "D") in cycle_set
    assert ("A", "C", "B", "D") in cycle_set

    # Rotations of one directed loop deduplicate; different traversals do not.
    four_member_cycles = {
        canonical(cycle) for cycle in cycles
        if len(cycle) == 5 and set(cycle[:-1]) == {"A", "B", "C", "D"}
    }
    assert len(four_member_cycles) == 2



def test_system_assessment_retains_each_distinct_overlapping_feedback_loop():
    from rdo.model import Obligation, Relationship
    from rdo.tension import assess_system

    keys = ("A", "B", "C", "D")
    obligations = {key: Obligation(key, key, "component") for key in keys}
    relationships = [
        Relationship("A", "B", "influences"),
        Relationship("B", "C", "influences"),
        Relationship("C", "D", "influences"),
        Relationship("D", "A", "influences"),
        Relationship("A", "C", "influences"),
        Relationship("C", "B", "influences"),
        Relationship("B", "D", "influences"),
    ]

    assessment = next(
        item for item in assess_system(obligations, relationships)
        if item.subject == "feedback_cycles"
    )
    loops = assessment.dimensions["feedback_loop_assessments"]
    four_member = [loop for loop in loops if len(loop["members"]) == 4]

    assert len(four_member) == 2
    assert len({tuple(loop["relationships"]) for loop in four_member}) == 2
    assert all(loop["stability_state"] == "unknown" for loop in four_member)
    assert assessment.verdict == "unknown"



def test_cycle_detector_output_is_stable_when_relationship_order_changes():
    from rdo.model import Relationship
    from rdo.tension import _find_cycles

    edges = [
        Relationship("A", "B", "influences"),
        Relationship("B", "C", "influences"),
        Relationship("C", "D", "influences"),
        Relationship("D", "A", "influences"),
        Relationship("A", "C", "influences"),
        Relationship("C", "B", "influences"),
        Relationship("B", "D", "influences"),
    ]

    assert _find_cycles(edges) == _find_cycles(list(reversed(edges)))


def test_cycle_detector_skips_exponential_acyclic_path_space():
    from rdo.model import Relationship
    from rdo.tension import _find_cycles

    # A layered DAG has exponentially many simple paths but no cycles.
    layers = [[f"L{level}-{index}" for index in range(2)] for level in range(19)]
    edges = [
        Relationship(src, dst, "depends_on")
        for previous, current in zip(layers, layers[1:])
        for src in previous
        for dst in current
    ]

    assert _find_cycles(edges) == []


def test_cycle_detector_handles_deep_cycle_without_recursion():
    from rdo.model import Relationship
    from rdo.tension import _find_cycles

    count = 1050
    nodes = [f"node-{index:04d}" for index in range(count)]
    edges = [
        Relationship(nodes[index], nodes[index + 1], "influences")
        for index in range(count - 1)
    ]
    edges.append(Relationship(nodes[-1], nodes[0], "influences"))

    cycles = _find_cycles(edges)

    assert len(cycles) == 1
    assert len(cycles[0]) == count + 1
    assert cycles[0][0] == cycles[0][-1]
    assert set(cycles[0][:-1]) == set(nodes)



def _cycle_with_feedback_loop():
    from rdo.model import CycleRecord

    loop = FeedbackLoopAssessment(
        loop_id="loop.alpha",
        members=["node_a", "node_b"],
        relationships=["node_a->node_b", "node_b->node_a"],
    )
    cycle = CycleRecord(
        id="cycle-feedback-001",
        objective="feedback loop evidence test",
        tension=[{
            "dimensions": {
                "feedback_loop_assessments": [loop.to_dict()],
            }
        }],
    )
    return cycle


def _loop_record(cycle):
    return cycle.tension[0]["dimensions"]["feedback_loop_assessments"][0]


def test_measured_dimensions_require_finite_numeric_values_and_traceable_metadata():
    with pytest.raises(ValueError, match="finite numeric"):
        FeedbackLoopAssessment(
            loop_id="loop.bad", members=["a"], relationships=["a->b"],
            gain=InterfaceEvidence(
                status="measured", value="high", unit="ratio",
                evidence=["lab:gain"], confidence="medium",
            ),
        )
    with pytest.raises(ValueError, match="gain.unit"):
        FeedbackLoopAssessment(
            loop_id="loop.bad", members=["a"], relationships=["a->b"],
            gain=InterfaceEvidence(
                status="measured", value=0.8, unit="",
                evidence=["lab:gain"], confidence="medium",
            ),
        )
    with pytest.raises(ValueError, match="gain.evidence"):
        FeedbackLoopAssessment(
            loop_id="loop.bad", members=["a"], relationships=["a->b"],
            gain=InterfaceEvidence(
                status="measured", value=0.8, unit="ratio",
                evidence=[], confidence="medium",
            ),
        )


def test_measurement_event_updates_dimension_without_changing_topology_or_stability(tmp_path):
    from rdo.feedback_loop import FeedbackLoopEvidenceStore
    from rdo.memory import CycleStore

    cycle = _cycle_with_feedback_loop()
    original_topology = {
        "loop_id": _loop_record(cycle)["loop_id"],
        "members": list(_loop_record(cycle)["members"]),
        "relationships": list(_loop_record(cycle)["relationships"]),
    }
    ledger = FeedbackLoopEvidenceStore(str(tmp_path / "feedback_loop_evidence.jsonl"))
    cycles = CycleStore(str(tmp_path / "cycles"))
    cycles.save(cycle)  # durable pre-update snapshot for crash/replay coverage
    event = ledger.record_measurement(
        cycle, "loop.alpha", "gain", 0.72, "ratio",
        ["lab:gain-run-004"], "medium", ["experiment:run-004"],
        operating_envelope="stress",
    )

    loop = _loop_record(cycle)
    assert loop["gain"]["status"] == "measured"
    assert loop["gain"]["value"] == 0.72
    assert loop["gain"]["unit"] == "ratio"
    assert loop["stability_state"] == "unknown"
    assert loop["assessment_status"] == "unknown"
    assert {
        "loop_id": loop["loop_id"],
        "members": loop["members"],
        "relationships": loop["relationships"],
    } == original_topology
    assert event["event_kind"] == "measurement_recorded"
    assert cycle.feedback_loop_evidence_events[0]["operating_envelope"] == "stress"

    restored = cycles.load(cycle.id)  # old snapshot; ledger contains the newer event
    ledger.apply(restored)
    assert _loop_record(restored)["gain"]["value"] == 0.72
    assert restored.feedback_loop_evidence_events == cycle.feedback_loop_evidence_events


def test_stability_state_changes_only_after_explicit_evidence_review(tmp_path):
    from rdo.feedback_loop import FeedbackLoopEvidenceStore

    cycle = _cycle_with_feedback_loop()
    ledger = FeedbackLoopEvidenceStore(str(tmp_path / "feedback_loop_evidence.jsonl"))
    ledger.record_stability_review(
        cycle, "loop.alpha", "conditionally_stable",
        "independent reviewer", "review:stability-assessment-12",
        ["test:closed-loop-response", "trace:operating-envelope"],
        "medium", note="Stable only inside the measured envelope.",
    )

    loop = _loop_record(cycle)
    assert loop["stability_state"] == "conditionally_stable"
    assert loop["assessment_status"] == "evidence_recorded"
    assert loop["provenance"] == [
        "reviewer:independent reviewer",
        "source:review:stability-assessment-12",
    ]
    assert loop["assessment_evidence"] == [
        "test:closed-loop-response", "trace:operating-envelope"
    ]


def test_new_measurement_invalidates_older_stability_review_until_re_reviewed(tmp_path):
    from rdo.feedback_loop import FeedbackLoopEvidenceStore

    cycle = _cycle_with_feedback_loop()
    ledger = FeedbackLoopEvidenceStore(str(tmp_path / "feedback_loop_evidence.jsonl"))
    ledger.record_stability_review(
        cycle, "loop.alpha", "stable", "reviewer", "review:stable",
        ["test:stable-response"], "high",
    )
    assert _loop_record(cycle)["stability_state"] == "stable"

    ledger.record_measurement(
        cycle, "loop.alpha", "delay", 120.0, "ms",
        ["trace:delay-120ms"], "high", ["experiment:delay-run"],
        operating_envelope="busy",
    )
    loop = _loop_record(cycle)
    assert loop["delay"]["value"] == 120.0
    assert loop["stability_state"] == "unknown"
    assert loop["assessment_status"] == "unknown"
    assert loop["assessment_evidence"] == []
    assert loop["provenance"] == []


def test_feedback_review_requires_reviewer_source_and_assessment_evidence(tmp_path):
    from rdo.feedback_loop import FeedbackLoopEvidenceStore

    cycle = _cycle_with_feedback_loop()
    ledger = FeedbackLoopEvidenceStore(str(tmp_path / "feedback_loop_evidence.jsonl"))
    with pytest.raises(ValueError, match="reviewer"):
        ledger.record_stability_review(
            cycle, "loop.alpha", "stable", "", "review:stable",
            ["test:stable-response"], "high",
        )
    with pytest.raises(ValueError, match="assessment_evidence"):
        ledger.record_stability_review(
            cycle, "loop.alpha", "stable", "reviewer", "review:stable",
            [], "high",
        )
    assert _loop_record(cycle)["stability_state"] == "unknown"
    assert cycle.feedback_loop_evidence_events == []


def test_feedback_evidence_cannot_be_replayed_against_changed_loop_topology(tmp_path):
    from rdo.feedback_loop import FeedbackLoopEvidenceStore

    cycle = _cycle_with_feedback_loop()
    ledger = FeedbackLoopEvidenceStore(str(tmp_path / "feedback_loop_evidence.jsonl"))
    ledger.record_measurement(
        cycle, "loop.alpha", "gain", 0.5, "ratio",
        ["lab:gain"], "medium", ["experiment:gain"],
    )
    _loop_record(cycle)["members"] = ["node_a", "node_c"]
    with pytest.raises(ValueError, match="topology changed"):
        ledger.apply(cycle)


def test_feedback_evidence_ledger_detects_tampering_and_replay_is_durable(tmp_path):
    from rdo.feedback_loop import FeedbackLoopEvidenceStore

    path = tmp_path / "feedback_loop_evidence.jsonl"
    cycle = _cycle_with_feedback_loop()
    ledger = FeedbackLoopEvidenceStore(str(path))
    ledger.record_measurement(
        cycle, "loop.alpha", "oscillation", 3, "cycles",
        ["trace:oscillation-count"], "high", ["experiment:oscillation"],
    )
    lines = path.read_text(encoding="utf-8").splitlines()
    event = json.loads(lines[0])
    event["data"]["value"] = 999
    lines[0] = json.dumps(event)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="digest mismatch"):
        ledger.events(cycle.id)


def test_cycle_record_legacy_construction_defaults_feedback_event_history():
    from rdo.model import CycleRecord

    legacy = CycleRecord(id="legacy-feedback-cycle", objective="legacy")
    assert legacy.feedback_loop_evidence_events == []



def test_cycle_snapshot_cannot_claim_feedback_events_when_ledger_is_missing(tmp_path):
    from rdo.feedback_loop import FeedbackLoopEvidenceStore

    path = tmp_path / "feedback_loop_evidence.jsonl"
    cycle = _cycle_with_feedback_loop()
    ledger = FeedbackLoopEvidenceStore(str(path))
    ledger.record_measurement(
        cycle, "loop.alpha", "gain", 0.6, "ratio",
        ["lab:gain"], "medium", ["experiment:gain"],
    )
    path.unlink()
    with pytest.raises(ValueError, match="does not match the append-only ledger"):
        ledger.apply(cycle)


def test_topology_drift_is_rejected_before_another_event_is_appended(tmp_path):
    from rdo.feedback_loop import FeedbackLoopEvidenceStore

    cycle = _cycle_with_feedback_loop()
    path = tmp_path / "feedback_loop_evidence.jsonl"
    ledger = FeedbackLoopEvidenceStore(str(path))
    ledger.record_measurement(
        cycle, "loop.alpha", "gain", 0.5, "ratio",
        ["lab:gain-1"], "medium", ["experiment:gain-1"],
    )
    before = path.read_bytes()
    _loop_record(cycle)["members"] = ["node_a", "node_c"]

    with pytest.raises(ValueError, match="topology changed"):
        ledger.record_measurement(
            cycle, "loop.alpha", "delay", 120, "ms",
            ["trace:delay-2"], "medium", ["experiment:delay-2"],
        )

    assert path.read_bytes() == before
    assert len(ledger.events(cycle.id)) == 1


def test_stability_review_preflights_existing_topology_before_append(tmp_path):
    from rdo.feedback_loop import FeedbackLoopEvidenceStore

    cycle = _cycle_with_feedback_loop()
    path = tmp_path / "feedback_loop_evidence.jsonl"
    ledger = FeedbackLoopEvidenceStore(str(path))
    ledger.record_measurement(
        cycle, "loop.alpha", "gain", 0.5, "ratio",
        ["lab:gain-1"], "medium", ["experiment:gain-1"],
    )
    before = path.read_bytes()
    _loop_record(cycle)["relationships"] = ["node_a->node_c", "node_c->node_a"]

    with pytest.raises(ValueError, match="topology changed"):
        ledger.record_stability_review(
            cycle, "loop.alpha", "stable", "reviewer", "review:stable",
            ["test:stable-response"], "high",
        )

    assert path.read_bytes() == before
    assert len(ledger.events(cycle.id)) == 1


def test_missing_ledger_is_detected_before_a_new_event_can_recreate_it(tmp_path):
    from rdo.feedback_loop import FeedbackLoopEvidenceStore

    cycle = _cycle_with_feedback_loop()
    path = tmp_path / "feedback_loop_evidence.jsonl"
    ledger = FeedbackLoopEvidenceStore(str(path))
    ledger.record_measurement(
        cycle, "loop.alpha", "gain", 0.5, "ratio",
        ["lab:gain-1"], "medium", ["experiment:gain-1"],
    )
    path.unlink()

    with pytest.raises(ValueError, match="does not match the append-only ledger"):
        ledger.record_stability_review(
            cycle, "loop.alpha", "stable", "reviewer", "review:stable",
            ["test:stable-response"], "high",
        )
    assert not path.exists()


def test_feedback_evidence_ledger_rejects_blank_lines_and_duplicate_json_keys(tmp_path):
    from rdo.feedback_loop import FeedbackLoopEvidenceStore

    path = tmp_path / "feedback_loop_evidence.jsonl"
    cycle = _cycle_with_feedback_loop()
    ledger = FeedbackLoopEvidenceStore(str(path))
    ledger.record_measurement(
        cycle, "loop.alpha", "gain", 0.5, "ratio",
        ["lab:gain"], "medium", ["experiment:gain"],
    )
    path.write_text(path.read_text(encoding="utf-8") + "\\n", encoding="utf-8")
    with pytest.raises(ValueError, match="blank or unterminated"):
        ledger.events(cycle.id)

    path.write_text(
        '{"schema_version":"rdo.feedback_loop_evidence.v1",'
        '"schema_version":"rdo.feedback_loop_evidence.v1"}\\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate JSON key"):
        ledger.events(cycle.id)


def test_feedback_evidence_ledger_enforces_byte_and_event_limits(tmp_path, monkeypatch):
    import rdo.feedback_loop as feedback_module
    from rdo.feedback_loop import FeedbackLoopEvidenceStore

    path = tmp_path / "feedback_loop_evidence.jsonl"
    path.write_text("x" * 32, encoding="utf-8")
    monkeypatch.setattr(feedback_module, "_MAX_LEDGER_BYTES", 16)
    with pytest.raises(ValueError, match="size limit"):
        FeedbackLoopEvidenceStore(str(path)).events()

    path.unlink()
    monkeypatch.setattr(feedback_module, "_MAX_LEDGER_BYTES", 1024 * 1024)
    monkeypatch.setattr(feedback_module, "_MAX_LEDGER_EVENTS", 0)
    cycle = _cycle_with_feedback_loop()
    ledger = FeedbackLoopEvidenceStore(str(path))
    with pytest.raises(ValueError, match="event limit"):
        ledger.record_measurement(
            cycle, "loop.alpha", "gain", 0.5, "ratio",
            ["lab:gain"], "medium", ["experiment:gain"],
        )
    assert not path.read_text(encoding="utf-8")


def test_feedback_evidence_ledger_validates_deterministic_event_identity(tmp_path):
    import rdo.feedback_loop as feedback_module
    from rdo.feedback_loop import FeedbackLoopEvidenceStore

    path = tmp_path / "feedback_loop_evidence.jsonl"
    cycle = _cycle_with_feedback_loop()
    ledger = FeedbackLoopEvidenceStore(str(path))
    ledger.record_measurement(
        cycle, "loop.alpha", "gain", 0.5, "ratio",
        ["lab:gain"], "medium", ["experiment:gain"],
    )
    event = json.loads(path.read_text(encoding="utf-8"))
    event["data"]["event_id"] = "fle_" + "0" * 24
    event["event_sha256"] = feedback_module._event_digest(event)
    path.write_text(json.dumps(event) + "\\n", encoding="utf-8")

    with pytest.raises(ValueError, match="event identity digest mismatch"):
        ledger.events(cycle.id)
