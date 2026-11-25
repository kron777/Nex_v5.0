"""Regression tests for the corpus snapshot git safety boundary."""
import subprocess
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
    assert calls[1][0:4] == ["git", "-C", str(tmp_path), "add"]
    assert calls[1][-2:] == ["CORPUS.md", "snapshot.json"]
    assert calls[2][0:4] == ["git", "-C", str(tmp_path), "commit"]
    assert "--only" in calls[2]
    assert calls[2][-2:] == ["CORPUS.md", "snapshot.json"]
    assert not any("push" in command for command in calls)


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

def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_git_commit_leaves_unrelated_pre_staged_changes_outside_snapshot_commit(
    monkeypatch, tmp_path
):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "feature/nexsnap")
    _git(repo, "config", "user.name", "NEXsnap test")
    _git(repo, "config", "user.email", "nexsnap-test@example.invalid")

    (repo / "unrelated.txt").write_text("baseline\\n", encoding="utf-8")
    _git(repo, "add", "unrelated.txt")
    _git(repo, "commit", "-m", "fixture baseline")

    # User work is already staged before NEXsnap runs.
    (repo / "unrelated.txt").write_text("user work, keep staged\\n", encoding="utf-8")
    _git(repo, "add", "unrelated.txt")

    corpus = repo / "CORPUS.md"
    snapshot = repo / "snapshots" / "state.json"
    snapshot.parent.mkdir()
    corpus.write_text("# generated corpus\\n", encoding="utf-8")
    snapshot.write_text('{"fixture": true}\\n', encoding="utf-8")

    monkeypatch.setattr(nexsnap, "REPO", repo)
    committed_branch = nexsnap.git_commit(corpus, snapshot)

    assert committed_branch == "feature/nexsnap"
    committed_files = set(_git(repo, "show", "--format=", "--name-only", "HEAD").splitlines())
    assert committed_files == {"CORPUS.md", "snapshots/state.json"}
    assert _git(repo, "diff", "--cached", "--name-only") == "unrelated.txt"
    assert _git(repo, "diff", "--name-only") == ""


def test_git_commit_refuses_artifact_outside_repository(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(nexsnap, "REPO", repo)

    with pytest.raises(RuntimeError, match="outside repository"):
        nexsnap._repo_relative_path(tmp_path / "outside.json")

def test_main_shares_one_runtime_capture_between_corpus_and_state(monkeypatch, tmp_path):
    runtime = {"drives": {"coherence": 0.7}, "fountain_24h_by_branch": {"x": 3}}
    port_data = {"rows": [{"status": "DONE"}]}
    runtime_extractions = []
    port_extractions = []
    received = {}

    def extract_runtime():
        runtime_extractions.append(runtime)
        return runtime

    def extract_port():
        port_extractions.append(port_data)
        return port_data

    def assemble(snap_ts, runtime=None, port_data=None):
        received["corpus_runtime"] = runtime
        received["corpus_port"] = port_data
        return "# fixture corpus\\n"

    def write_state(snap_ts, runtime=None, port_data=None):
        received["state_runtime"] = runtime
        received["state_port"] = port_data
        return tmp_path / "state.json"

    monkeypatch.setattr(nexsnap.ex, "extract_runtime_state", extract_runtime)
    monkeypatch.setattr(nexsnap.ex, "extract_port_status", extract_port)
    monkeypatch.setattr(nexsnap, "assemble_corpus", assemble)
    monkeypatch.setattr(nexsnap, "write_state_json", write_state)
    monkeypatch.setattr(nexsnap, "CORPUS_PATH", tmp_path / "CORPUS.md")
    monkeypatch.setattr(nexsnap.time, "time", lambda: 1_700_000_000)

    nexsnap.main([])

    assert len(runtime_extractions) == 1
    assert len(port_extractions) == 1
    assert received["corpus_runtime"] is runtime
    assert received["state_runtime"] is runtime
    assert received["corpus_port"] is port_data
    assert received["state_port"] is port_data
