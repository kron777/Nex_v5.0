"""Tests for the local host collector; subprocesses are mocked, never run on this machine."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from watcher import host_runner


def test_collector_executes_only_fixed_request_commands_and_records_provenance(monkeypatch, tmp_path):
    requests = [
        SimpleNamespace(
            id="runtime_identity",
            read_only_commands=["printf 'process_candidates=NONE\\n'", "printf 'service=inactive\\n'"],
        ),
        SimpleNamespace(
            id="classify_unknown_tools",
            read_only_commands=["grep -nE 'INSERT|UPDATE' source.py"],
        ),
    ]
    monkeypatch.setattr(host_runner, "host_requests", lambda: requests)
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(
            returncode=0,
            stdout=f"mock output {len(calls)}",
            stderr="",
        )

    monkeypatch.setattr(host_runner.subprocess, "run", fake_run)
    result = host_runner.collect_host_evidence(timeout=17, repo_root=tmp_path)

    assert len(calls) == 3
    assert all(call[0][:4] == ["bash", "--noprofile", "--norc", "-c"] for call in calls)
    assert all(call[1]["timeout"] == 17 for call in calls)
    assert all(call[1]["cwd"] == str(tmp_path) for call in calls)
    assert result["runtime_identity"]["evidence_class"] == "measured"
    assert result["classify_unknown_tools"]["evidence_class"] == "static"
    assert result["runtime_identity"]["source_ref"]
    assert result["runtime_identity"]["data"]["commands"][0]["stdout"] == "mock output 1"


def test_host_collect_cli_passes_explicit_repo_root(monkeypatch, tmp_path, capsys):
    requested_root = tmp_path / "verified-nex"
    requested_root.mkdir()
    observed = {}

    def fake_collect(**kwargs):
        observed.update(kwargs)
        return {"_meta": {}, "runtime_identity": {"data": {"failed_command_count": 0}}}

    monkeypatch.setattr(host_runner, "collect_host_evidence", fake_collect)
    monkeypatch.setattr(host_runner, "write_results", lambda results, output, force=False: Path(output))
    from watcher.__main__ import main

    code = main([
        "host-collect",
        "--repo-root", str(requested_root),
        "--out", str(tmp_path / "host.json"),
        "--skip-artifact-hashes",
    ])

    assert code == 0
    assert observed["repo_root"] == requested_root.resolve()
    assert observed["include_artifact_hashes"] is False
    assert "wrote" in capsys.readouterr().out


def test_collector_marks_hashing_skip_as_unknown_not_empty(monkeypatch, tmp_path):
    request = SimpleNamespace(id="runtime_artifact_hashes", read_only_commands=["must not run"])
    monkeypatch.setattr(host_runner, "host_requests", lambda: [request])

    def forbidden_run(*args, **kwargs):
        raise AssertionError("skipped artifact hashing must not execute commands")

    monkeypatch.setattr(host_runner.subprocess, "run", forbidden_run)
    result = host_runner.collect_host_evidence(
        include_artifact_hashes=False,
        repo_root=tmp_path,
    )

    row = result["runtime_artifact_hashes"]
    assert row["data"]["status"] == "SKIPPED_BY_OPERATOR"
    assert row["evidence_class"] == "unknown"
    assert "empty" in row["note"].lower() or "inventory" in row["note"].lower()


def test_collector_retains_nonzero_exit_and_timeout(monkeypatch, tmp_path):
    request = SimpleNamespace(id="phase0_environment", read_only_commands=["false", "slow"])
    monkeypatch.setattr(host_runner, "host_requests", lambda: [request])
    outcomes = iter([
        SimpleNamespace(returncode=2, stdout="", stderr="permission denied"),
        __import__("subprocess").TimeoutExpired("slow", 5, output=b"partial", stderr=b"still running"),
    ])

    def fake_run(*args, **kwargs):
        outcome = next(outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(host_runner.subprocess, "run", fake_run)
    result = host_runner.collect_host_evidence(timeout=5, repo_root=tmp_path)
    data = result["phase0_environment"]["data"]

    assert data["status"] == "COLLECTED_WITH_ERRORS"
    assert data["failed_command_count"] == 2
    assert data["commands"][0]["stderr"] == "permission denied"
    assert data["commands"][1]["timed_out"] is True
    assert data["commands"][1]["stdout"] == "partial"


def test_write_results_refuses_overwrite_unless_forced(tmp_path):
    target = tmp_path / "host_results.json"
    host_runner.write_results({"one": {"data": 1}}, target)
    with pytest.raises(FileExistsError):
        host_runner.write_results({"two": {"data": 2}}, target)

    host_runner.write_results({"two": {"data": 2}}, target, force=True)
    assert json.loads(target.read_text(encoding="utf-8")) == {"two": {"data": 2}}


def test_collector_rejects_invalid_timeout():
    with pytest.raises(ValueError):
        host_runner.collect_host_evidence(timeout=0)
