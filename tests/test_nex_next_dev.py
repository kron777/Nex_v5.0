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
