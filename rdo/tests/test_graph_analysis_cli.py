"""CLI access to persisted, read-only Stage-3 graph analyses."""

import json

from rdo.__main__ import main
from rdo.memory import CycleStore
from rdo.model import CycleRecord


def _save(store, cycle_id, *, relationships, tension, obligations):
    cycle = CycleRecord(
        id=cycle_id,
        objective="CLI graph-analysis fixture",
        obligations=obligations,
        relationships=relationships,
        tension=tension,
    )
    store.save(cycle)


def _assessment(subject, *, dimensions=None):
    return {
        "level": "relationship",
        "subject": subject,
        "verdict": "unknown",
        "inference": True,
        "evidence": [],
        "dimensions": dimensions or {},
        "note": "fixture",
    }


def test_failure_propagation_cli_reads_cycle_and_reports_candidates(tmp_path, capsys):
    store = CycleStore(str(tmp_path))
    _save(
        store,
        "failure-case",
        obligations=[{"key": "store"}, {"key": "reader"}, {"key": "api"}],
        relationships=[
            {"src": "reader", "dst": "store", "kind": "depends_on"},
            {"src": "api", "dst": "reader", "kind": "depends_on"},
        ],
        tension=[],
    )

    status = main([
        "failure-propagation",
        "--cycle-id", "failure-case",
        "--failed-key", "store",
        "--dir", str(tmp_path),
    ])

    output = json.loads(capsys.readouterr().out)
    assert status == 0
    assert output["status"] == "candidate_only"
    assert [item["key"] for item in output["affected"]] == ["reader", "api"]
    assert output["affected"][1]["path"] == ["store", "reader", "api"]


def test_failure_propagation_cli_keeps_unknown_root_partial(tmp_path, capsys):
    store = CycleStore(str(tmp_path))
    _save(
        store,
        "known-cycle",
        obligations=[{"key": "store"}],
        relationships=[],
        tension=[],
    )

    status = main([
        "failure-propagation",
        "--cycle-id", "known-cycle",
        "--failed-key", "typo",
        "--dir", str(tmp_path),
    ])

    output = json.loads(capsys.readouterr().out)
    assert status == 1
    assert output["status"] == "partial"
    assert output["unknown_roots"] == ["typo"]


def test_impact_cli_compares_persisted_cycle_snapshots(tmp_path, capsys):
    store = CycleStore(str(tmp_path))
    subject = "reader -depends_on-> store"
    relationships = [{"src": "reader", "dst": "store", "kind": "depends_on"}]
    obligations = [{"key": "reader"}, {"key": "store"}]
    _save(
        store,
        "before",
        obligations=obligations,
        relationships=relationships,
        tension=[_assessment(subject, dimensions={"latency": {"status": "unknown"}})],
    )
    _save(
        store,
        "after",
        obligations=obligations,
        relationships=relationships,
        tension=[_assessment(subject, dimensions={"latency": {"status": "measured"}})],
    )

    status = main([
        "impact",
        "--before-cycle-id", "before",
        "--after-cycle-id", "after",
        "--changed-capability", "store",
        "--dir", str(tmp_path),
    ])

    output = json.loads(capsys.readouterr().out)
    assert status == 0
    assert output["status"] == "compared"
    item = output["affected_relationships"][0]
    assert item["relationship_status"] == "unchanged"
    assert item["assessment_changed"] is True
    assert item["changed_dimensions"] == ["latency"]


def test_impact_cli_returns_partial_for_missing_relationship_assessment(tmp_path, capsys):
    store = CycleStore(str(tmp_path))
    relationships = [{"src": "reader", "dst": "store", "kind": "depends_on"}]
    obligations = [{"key": "reader"}, {"key": "store"}]
    _save(
        store, "before", obligations=obligations, relationships=relationships,
        tension=[_assessment("reader -depends_on-> store")],
    )
    _save(
        store, "after", obligations=obligations, relationships=relationships,
        tension=[],
    )

    status = main([
        "impact",
        "--before-cycle-id", "before",
        "--after-cycle-id", "after",
        "--changed-capability", "store",
        "--dir", str(tmp_path),
    ])

    output = json.loads(capsys.readouterr().out)
    assert status == 1
    assert output["status"] == "partial"
    assert output["affected_relationships"][0]["assessment_status"] == "missing_after"


def test_graph_analysis_cli_reports_missing_cycle_without_writing(tmp_path, capsys):
    status = main([
        "failure-propagation",
        "--cycle-id", "missing",
        "--failed-key", "store",
        "--dir", str(tmp_path),
    ])

    error = capsys.readouterr().err
    assert status == 2
    assert "No such file" in error or "not found" in error.lower()



def test_graph_analysis_cli_does_not_create_a_missing_cycle_directory(tmp_path, capsys):
    missing_dir = tmp_path / "not-created"
    status = main([
        "failure-propagation",
        "--cycle-id", "missing",
        "--failed-key", "store",
        "--dir", str(missing_dir),
    ])

    assert status == 2
    assert not missing_dir.exists()
    assert "cycle store directory does not exist" in capsys.readouterr().err
