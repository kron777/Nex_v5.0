"""Regression tests for trustworthy mind-map source-drift verification."""
from datetime import datetime
from types import SimpleNamespace

import pytest

from mind_map import mind_map


def _doc():
    return {
        "meta": {"doctrine": []},
        "arms": [],
        "nodes": [{
            "id": "probe",
            "label": "Probe",
            "layer": "ring",
            "role_note": "A source-verification fixture.",
            "evidence": "static",
            "dark": False,
            "blocked": False,
            "falsifier_status": "unrun",
            "source": {"kind": "file", "ref": "mind_map/mind_map.py:1"},
            "last_verified": "2026-11-10",
        }],
    }


def test_git_history_complete_detects_shallow_checkout(monkeypatch):
    def fake_run(args, **kwargs):
        assert args == ["git", "rev-parse", "--is-shallow-repository"]
        return SimpleNamespace(stdout="true\n")

    monkeypatch.setattr(mind_map.subprocess, "run", fake_run)
    assert mind_map.git_history_complete() is False


def test_git_history_complete_accepts_full_checkout(monkeypatch):
    def fake_run(args, **kwargs):
        assert args == ["git", "rev-parse", "--is-shallow-repository"]
        return SimpleNamespace(stdout="false\n")

    monkeypatch.setattr(mind_map.subprocess, "run", fake_run)
    assert mind_map.git_history_complete() is True


def test_shallow_checkout_skips_false_stale_dates(monkeypatch):
    monkeypatch.setattr(mind_map, "check_descriptive_only", lambda doc, root: [])
    monkeypatch.setattr(mind_map, "git_history_complete", lambda: False)

    def unexpected_log(_rel):
        pytest.fail("path history must not be queried in a shallow checkout")

    monkeypatch.setattr(mind_map, "last_commit_ts", unexpected_log)
    errors, warnings = mind_map.check(_doc())

    assert errors == []
    assert any("Git history is shallow or unavailable" in warning for warning in warnings)
    assert not any("STALE" in warning for warning in warnings)


def test_full_history_still_reports_a_real_stale_source(monkeypatch):
    monkeypatch.setattr(mind_map, "check_descriptive_only", lambda doc, root: [])
    monkeypatch.setattr(mind_map, "git_history_complete", lambda: True)
    changed = datetime(2026, 11, 11, 12, 0).timestamp()
    monkeypatch.setattr(mind_map, "last_commit_ts", lambda _rel: changed)

    errors, warnings = mind_map.check(_doc())

    assert errors == []
    assert any("STALE" in warning and "mind_map/mind_map.py" in warning
               for warning in warnings)
