"""Differential before/after analysis for relationships around changed capabilities."""
from rdo.graph import compare_adjacent_relationship_impacts


def _cycle(relationships, tension):
    nodes = sorted({endpoint for item in relationships if isinstance(item, dict)
                    for endpoint in (item.get("src"), item.get("dst"))
                    if isinstance(endpoint, str) and endpoint.strip()})
    return {
        "obligations": [{"key": key} for key in nodes],
        "relationships": relationships,
        "tension": tension,
    }


def _assessment(subject, verdict="unknown", dimensions=None, note=""):
    return {
        "level": "relationship",
        "subject": subject,
        "verdict": verdict,
        "inference": True,
        "evidence": [],
        "dimensions": dimensions or {},
        "note": note,
    }


def test_changed_capability_reports_incident_relationship_and_assessment_deltas():
    subject = "reader -depends_on-> store"
    before = _cycle(
        [{
            "src": "reader", "dst": "store", "kind": "depends_on",
            "interface_profile": {"latency": {"status": "unknown"}},
        }, {
            "src": "other", "dst": "unrelated", "kind": "depends_on",
        }],
        [_assessment(subject, dimensions={
            "profile_status": "supplied",
            "performance_margins": {"status": "not_supplied"},
        })],
    )
    after = _cycle(
        [{
            "src": "reader", "dst": "store", "kind": "depends_on",
            "interface_profile": {"latency": {"status": "measured", "value": 0.8}},
            "performance_margins": {"latency_utility": {"margin": 0.1}},
        }, {
            "src": "other", "dst": "unrelated", "kind": "depends_on",
        }],
        [_assessment(subject, dimensions={
            "profile_status": "supplied",
            "performance_margins": {"status": "evidence_recorded"},
        })],
    )

    report = compare_adjacent_relationship_impacts(before, after, ["store"])
    assert report["status"] == "compared"
    assert report["changed_capabilities"] == ["store"]
    assert len(report["affected_relationships"]) == 1
    item = report["affected_relationships"][0]
    assert item["identity"] == subject
    assert item["neighbours"] == ["reader"]
    assert item["relationship_status"] == "changed"
    assert item["assessment_status"] == "compared"
    assert item["assessment_changed"] is True
    assert item["verdict_changed"] is False
    assert "performance_margins" in item["changed_dimensions"]
    assert "not proof of causality" in report["note"]


def test_unchanged_relationship_can_still_have_changed_assessment():
    subject = "reader -depends_on-> store"
    relationships = [{"src": "reader", "dst": "store", "kind": "depends_on"}]
    before = _cycle(relationships, [_assessment(subject, dimensions={
        "operating_envelope": {"status": "unknown"},
    })])
    after = _cycle(relationships, [_assessment(subject, dimensions={
        "operating_envelope": {"status": "evidence_recorded"},
    })])

    report = compare_adjacent_relationship_impacts(before, after, ["store"])
    item = report["affected_relationships"][0]
    assert item["relationship_status"] == "unchanged"
    assert item["assessment_changed"] is True
    assert item["changed_dimensions"] == ["operating_envelope"]
    assert report["status"] == "compared"


def test_added_and_removed_neighbour_relationships_are_reported_separately():
    before = _cycle(
        [{"src": "old_reader", "dst": "store", "kind": "depends_on"}],
        [_assessment("old_reader -depends_on-> store")],
    )
    after = _cycle(
        [{"src": "new_reader", "dst": "store", "kind": "depends_on"}],
        [_assessment("new_reader -depends_on-> store")],
    )

    report = compare_adjacent_relationship_impacts(before, after, ["store"])
    by_identity = {item["identity"]: item for item in report["affected_relationships"]}
    assert by_identity["old_reader -depends_on-> store"]["relationship_status"] == "removed"
    assert by_identity["old_reader -depends_on-> store"]["assessment_status"] == "assessment_removed"
    assert by_identity["new_reader -depends_on-> store"]["relationship_status"] == "added"
    assert by_identity["new_reader -depends_on-> store"]["assessment_status"] == "newly_assessed"
    assert report["status"] == "compared"


def test_missing_assessment_keeps_differential_report_partial():
    relationships = [{"src": "reader", "dst": "store", "kind": "depends_on"}]
    before = _cycle(relationships, [_assessment("reader -depends_on-> store")])
    after = _cycle(relationships, [])

    report = compare_adjacent_relationship_impacts(before, after, ["store"])
    assert report["status"] == "partial"
    assert report["affected_relationships"][0]["assessment_status"] == "missing_after"


def test_non_incident_relationships_are_excluded_and_missing_scope_stays_unknown():
    before = _cycle(
        [{"src": "reader", "dst": "database", "kind": "depends_on"}],
        [_assessment("reader -depends_on-> database")],
    )
    after = before

    before["obligations"].append({"key": "store"})
    after["obligations"].append({"key": "store"})
    report = compare_adjacent_relationship_impacts(before, after, ["store"])
    assert report["status"] == "no_adjacent_relationships"
    assert report["affected_relationships"] == []

    no_scope = compare_adjacent_relationship_impacts(before, after, [])
    assert no_scope["status"] == "not_supplied"


def test_invalid_cycle_snapshots_fail_closed():
    report = compare_adjacent_relationship_impacts(
        {"relationships": "bad", "tension": []},
        {"relationships": [], "tension": []},
        ["store"],
    )
    assert report["status"] == "partial"
    assert report["invalid_relationship_records"] == 1


def test_missing_and_null_assessment_dimensions_are_distinguished():
    subject = "reader -depends_on-> store"
    edge = [{"src": "reader", "dst": "store", "kind": "depends_on"}]
    before = _cycle(edge, [_assessment(subject, dimensions={"latency": None})])
    after = _cycle(edge, [_assessment(subject, dimensions={})])
    report = compare_adjacent_relationship_impacts(before, after, ["store"])
    item = report["affected_relationships"][0]
    assert item["changed_dimensions"] == ["latency"]
    assert item["assessment_changed"] is True


def test_padded_changed_capability_key_is_not_silently_normalized():
    edge = [{"src": "reader", "dst": "store", "kind": "depends_on"}]
    cycle = _cycle(edge, [_assessment("reader -depends_on-> store")])
    report = compare_adjacent_relationship_impacts(cycle, cycle, [" store "])
    assert report["status"] == "partial"
    assert report["changed_capabilities"] == []
    assert report["invalid_capabilities"] == [" store "]


def test_removed_relationship_with_only_after_assessment_is_partial_orphan():
    before = _cycle(
        [{"src": "reader", "dst": "store", "kind": "depends_on"}],
        [],
    )
    after = _cycle(
        [],
        [_assessment("reader -depends_on-> store")],
    )
    report = compare_adjacent_relationship_impacts(before, after, ["store"])
    item = report["affected_relationships"][0]
    assert item["relationship_status"] == "removed"
    assert item["assessment_status"] == "orphaned_after"
    assert report["status"] == "partial"


def test_added_relationship_with_only_before_assessment_is_partial_orphan():
    before = _cycle(
        [],
        [_assessment("reader -depends_on-> store")],
    )
    after = _cycle(
        [{"src": "reader", "dst": "store", "kind": "depends_on"}],
        [],
    )
    report = compare_adjacent_relationship_impacts(before, after, ["store"])
    item = report["affected_relationships"][0]
    assert item["relationship_status"] == "added"
    assert item["assessment_status"] == "orphaned_before"
    assert report["status"] == "partial"


def test_unknown_changed_capability_is_not_misreported_as_isolated():
    cycle = _cycle(
        [{"src": "reader", "dst": "database", "kind": "depends_on"}],
        [_assessment("reader -depends_on-> database")],
    )
    report = compare_adjacent_relationship_impacts(cycle, cycle, ["typo-capability"])
    assert report["status"] == "partial"
    assert report["unknown_capabilities"] == ["typo-capability"]
    assert report["affected_relationships"] == []
