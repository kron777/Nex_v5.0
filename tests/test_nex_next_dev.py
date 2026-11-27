"""Regression tests for the sentience-DAG development CLI."""
import json

import nex_next_dev


def test_buildable_cli_reports_unproven_and_terminal_prerequisite_caveats(
    tmp_path, monkeypatch, capsys
):
    dag = {
        "nodes": {
            "unproven_floor": {
                "status": "live_unproven",
                "prereqs": [],
                "note": "Evidence remains incomplete.",
            },
            "terminal_floor": {
                "status": "terminal",
                "prereqs": [],
                "note": "The tested mechanism reached a terminal null.",
            },
            "candidate": {
                "status": "gap",
                "prereqs": ["unproven_floor", "terminal_floor"],
                "note": "Candidate development node.",
            },
        }
    }
    path = tmp_path / "sentience_dag.json"
    path.write_text(json.dumps(dag), encoding="utf-8")
    monkeypatch.setattr(nex_next_dev, "DAG_PATH", str(path))

    nex_next_dev.main(["--buildable"])

    output = capsys.readouterr().out
    assert "candidate" in output
    assert "leans on unproven: unproven_floor" in output
    assert "rests on terminal null: terminal_floor" in output


def test_buildable_rule_still_treats_unproven_and_terminal_as_satisfied():
    nodes = {
        "unproven_floor": {"status": "live_unproven", "prereqs": []},
        "terminal_floor": {"status": "terminal", "prereqs": []},
        "candidate": {
            "status": "gap",
            "prereqs": ["unproven_floor", "terminal_floor"],
        },
    }

    classified = nex_next_dev.classify(nodes)

    assert classified["buildable_now"] == [
        ("candidate", ["unproven_floor"], ["terminal_floor"])
    ]
    assert classified["blocked"] == []


def test_full_report_describes_unproven_status_as_caveat_not_hard_gate(capsys):
    dag = {
        "nodes": {
            "unproven_floor": {
                "status": "live_unproven",
                "prereqs": [],
                "note": "Still needs evidence.",
            },
            "candidate": {
                "status": "gap",
                "prereqs": ["unproven_floor"],
                "note": "Candidate development node.",
            },
        }
    }

    nex_next_dev.report(dag)

    output = capsys.readouterr().out
    assert "not hard blockers under the current DAG rule" in output
    assert "unproven_floor" in output
    assert "THE ONE GATE RIGHT NOW" not in output
    assert "dependency-satisfied caveats; not validated" in output
    assert "at least one prerequisite is outside the DAG satisfied set" in output



def test_unknown_prerequisite_is_rejected_by_classification():
    nodes = {
        "candidate": {
            "status": "gap",
            "prereqs": ["missing_node"],
        },
    }

    import pytest

    with pytest.raises(
        ValueError,
        match=r"unknown DAG prerequisite reference\(s\): candidate -> missing_node",
    ):
        nex_next_dev.classify(nodes)


def test_unknown_prerequisite_is_rejected_by_topological_sort():
    nodes = {
        "candidate": {
            "status": "gap",
            "prereqs": ["missing_node"],
        },
    }

    import pytest

    with pytest.raises(
        ValueError,
        match=r"unknown DAG prerequisite reference\(s\): candidate -> missing_node",
    ):
        nex_next_dev.topo_sort(nodes)


def test_current_sentience_dag_has_no_unresolved_prerequisites():
    nodes = nex_next_dev.load()["nodes"]

    assert nex_next_dev.validate_prerequisites(nodes) is None



def test_duplicate_prerequisite_is_rejected_by_topological_sort():
    nodes = {
        "foundation": {"status": "built", "prereqs": []},
        "candidate": {
            "status": "gap",
            "prereqs": ["foundation", "foundation"],
        },
    }

    import pytest

    with pytest.raises(
        ValueError,
        match=r"duplicate DAG prerequisite reference\(s\): candidate -> foundation",
    ):
        nex_next_dev.topo_sort(nodes)


def test_duplicate_prerequisite_is_rejected_by_classification():
    nodes = {
        "foundation": {"status": "built", "prereqs": []},
        "candidate": {
            "status": "gap",
            "prereqs": ["foundation", "foundation"],
        },
    }

    import pytest

    with pytest.raises(
        ValueError,
        match=r"duplicate DAG prerequisite reference\(s\): candidate -> foundation",
    ):
        nex_next_dev.classify(nodes)


def test_unknown_node_status_is_rejected_by_classification():
    nodes = {
        "candidate": {
            "status": "future_status_typo",
            "prereqs": [],
        },
    }

    import pytest

    with pytest.raises(
        ValueError,
        match=r"unknown DAG node status value\(s\): candidate \[future_status_typo\]",
    ):
        nex_next_dev.classify(nodes)


def test_missing_node_status_is_rejected_by_classification():
    nodes = {
        "candidate": {
            "prereqs": [],
        },
    }

    import pytest

    with pytest.raises(
        ValueError,
        match=r"unknown DAG node status value\(s\): candidate \[<missing>\]",
    ):
        nex_next_dev.classify(nodes)

def test_non_object_node_definition_is_rejected():
    import pytest

    with pytest.raises(
        ValueError,
        match=r"malformed DAG node definition\(s\): candidate: node definition must be an object",
    ):
        nex_next_dev.classify({"candidate": None})


def test_non_list_prerequisites_are_rejected():
    import pytest

    with pytest.raises(
        ValueError,
        match=r"malformed DAG node definition\(s\): candidate: prereqs must be a list",
    ):
        nex_next_dev.classify({
            "candidate": {"status": "gap", "prereqs": "foundation"}
        })


def test_non_string_prerequisite_is_rejected_before_reference_validation():
    import pytest

    with pytest.raises(
        ValueError,
        match=r"prerequisite at index 0 must be a non-empty string",
    ):
        nex_next_dev.classify({
            "candidate": {"status": "gap", "prereqs": [None]}
        })


def test_empty_node_id_is_rejected():
    import pytest

    with pytest.raises(
        ValueError,
        match=r"node ID must be a non-empty string",
    ):
        nex_next_dev.classify({
            "": {"status": "gap", "prereqs": []}
        })


def test_non_object_nodes_container_is_rejected():
    import pytest

    with pytest.raises(
        ValueError,
        match=r"DAG nodes must be an object mapping node IDs to node objects",
    ):
        nex_next_dev.classify([])


def test_non_string_status_is_rejected():
    import pytest

    with pytest.raises(
        ValueError,
        match=r"candidate: status must be a string",
    ):
        nex_next_dev.classify({
            "candidate": {"status": ["gap"], "prereqs": []}
        })
