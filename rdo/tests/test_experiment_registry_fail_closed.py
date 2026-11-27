"""Fail-closed tests for RDO's protected-experiment eligibility boundary.

Unknown registry state is distinct from a successfully read empty registry.
These tests use synthetic Evidence records and never inspect or modify live NEX state.
"""
from types import SimpleNamespace

from rdo.orchestrator import _active_experiments
from rdo.prioritise import eligibility
from rdo.model import Obligation
from watcher import registry
from watcher.evidence import Evidence


def _evidence(data, evidence_class="measured"):
    return Evidence(
        subject="experiment_registry",
        data=data,
        origin="cloud",
        evidence_class=evidence_class,
        source_ref="isolated test fixture",
    )


def test_unknown_registry_blocks_eligibility():
    ob = Obligation("docs", "documentation-only change", "documentation")
    result = eligibility(ob, {}, [], active_experiments=None)
    assert result["eligibility"] == "blocked"
    assert any("registry unavailable or unverified" in item for item in result["blockers"])


def test_verified_empty_registry_does_not_add_registry_blocker():
    ob = Obligation("docs", "documentation-only change", "documentation")
    result = eligibility(ob, {}, [], active_experiments=[])
    assert result["eligibility"] == "eligible"
    assert not result["blockers"]


def test_matching_active_experiment_blocks_eligibility():
    ob = Obligation("docs", "update r77 report", "documentation")
    result = eligibility(ob, {}, [], active_experiments=["r77"])
    assert result["eligibility"] == "blocked"
    assert any("r77" in item for item in result["blockers"])


def test_active_experiment_reader_accepts_measured_empty_registry(monkeypatch, tmp_path):
    monkeypatch.setattr(
        registry, "ingest_registry",
        lambda _path: _evidence({"active_or_pending": []}),
    )
    assert _active_experiments(str(tmp_path)) == []


def test_active_experiment_reader_preserves_unknown_registry(monkeypatch, tmp_path):
    monkeypatch.setattr(
        registry, "ingest_registry",
        lambda _path: _evidence(None, evidence_class="unknown"),
    )
    assert _active_experiments(str(tmp_path)) is None


def test_active_experiment_reader_rejects_malformed_registry(monkeypatch, tmp_path):
    monkeypatch.setattr(
        registry, "ingest_registry",
        lambda _path: _evidence({"experiments": {}}),
    )
    assert _active_experiments(str(tmp_path)) is None


def test_active_experiment_reader_fails_closed_on_read_error(monkeypatch, tmp_path):
    def fail(_path):
        raise PermissionError("fixture: registry unreadable")

    monkeypatch.setattr(registry, "ingest_registry", fail)
    assert _active_experiments(str(tmp_path)) is None
