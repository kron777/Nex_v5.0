"""Regression tests for the corpus snapshot git safety boundary."""
import subprocess
from pathlib import Path

import pytest

from scripts import nexsnap


def test_git_commit_commits_locally_without_push(monkeypatch, tmp_path):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[-2:] == ["branch", "--show-current"]:
            return subprocess.CompletedProcess(command, 0, stdout="feature/work\n", stderr="")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(nexsnap, "REPO", tmp_path)
    monkeypatch.setattr(nexsnap.subprocess, "run", fake_run)

    nexsnap.git_commit(tmp_path / "CORPUS.md", tmp_path / "snapshot.json")

    assert calls[0][-2:] == ["branch", "--show-current"]
    assert calls[1][0:5] == ["git", "-C", str(tmp_path), "add"]
    assert calls[2][0:4] == ["git", "-C", str(tmp_path), "commit"]
    assert not any(command[4] == "push" for command in calls if len(command) > 4)


def test_git_push_targets_current_branch(monkeypatch, tmp_path):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="engineering/fix\n", stderr="")

    monkeypatch.setattr(nexsnap, "REPO", tmp_path)
    monkeypatch.setattr(nexsnap.subprocess, "run", fake_run)

    nexsnap.git_push("engineering/fix")

    assert calls[-1] == ["git", "-C", str(tmp_path), "push", "origin", "engineering/fix"]


def test_git_push_refuses_branch_change(monkeypatch, tmp_path):
    monkeypatch.setattr(nexsnap, "REPO", tmp_path)

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="main\n", stderr="")

    monkeypatch.setattr(nexsnap.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="checked-out branch changed"):
        nexsnap.git_push("engineering/fix")


def test_current_branch_refuses_detached_head(monkeypatch, tmp_path):
    monkeypatch.setattr(nexsnap, "REPO", tmp_path)

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="\n", stderr="")

    monkeypatch.setattr(nexsnap.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="detached HEAD"):
        nexsnap.current_branch()


def test_write_state_extracts_runtime_once(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(nexsnap, "SNAP_DIR", tmp_path)
    monkeypatch.setattr(nexsnap.ex, "extract_runtime_state",
                        lambda: calls.append("runtime") or {"fountain_24h_by_branch": {"x": 2}})
    monkeypatch.setattr(nexsnap.ex, "extract_port_status", lambda: {"rows": []})

    path = nexsnap.write_state_json(1_700_000_000)

    assert calls == ["runtime"]
    import json
    state = json.loads(path.read_text())
    assert state["fountain_by_branch_24h"] == {"x": 2}
