"""Phase 0 host-evidence request coverage.

These tests inspect the generated collection specification only. They do not
execute host commands, access a live NEX checkout, or read runtime databases.
"""
import ast
import hashlib
import json
import os
import pathlib
import re
import stat
import subprocess

from watcher.host import host_requests, host_results_template, ingest_host_results


def _requests():
    return {request.id: request for request in host_requests()}


def _commands(request_id):
    return "\n".join(_requests()[request_id].read_only_commands)


def _artifact_helper_namespace():
    command_text = _commands("runtime_artifact_hashes")
    blocks = re.findall(r"<<'PY'\n(.*?)\nPY(?:\n|$)", command_text, re.DOTALL)
    assert len(blocks) == 1
    tree = ast.parse(blocks[0])
    helper_nodes = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in {"stamp", "fingerprint", "walk", "choose_artifact_roots", "scan_artifact_roots"}
    ]
    assert {node.name for node in helper_nodes} == {"stamp", "fingerprint", "walk", "choose_artifact_roots", "scan_artifact_roots"}
    namespace = {
        "hashlib": hashlib, "os": os, "pathlib": pathlib, "re": re, "stat": stat,
    }
    module = ast.Module(body=helper_nodes, type_ignores=[])
    exec(compile(module, "embedded_host_fingerprint_helpers", "exec"), namespace)
    return namespace


def _artifact_fingerprint_function():
    return _artifact_helper_namespace()["fingerprint"]


def _artifact_walk_function():
    return _artifact_helper_namespace()["walk"]

def test_phase0_host_request_covers_host_and_candidate_model_fingerprint():
    request = _requests()["phase0_environment"]
    commands = "\n".join(request.read_only_commands)

    for required in (
        "cat /etc/os-release",
        "lscpu",
        "/proc/meminfo",
        "lspci",
        "/sys/module/$module/version",
        "mem_info_vram_",
        "/sys/fs/cgroup/memory.max",
        "candidate_python_version=",
        "candidate_sqlite_version=",
        "NEX5_VOICE_URL",
        "NEX5_VOICE_MODEL",
        "voice_endpoint_origin=",
        "configured_model_api_digest=",
        "ollama_list_model_entry=",
        "modelfile_backing_blob=",
        "ollama_ps_status=",
    ):
        assert required in commands

    assert "No inference" in request.collects
    assert "throughput benchmark" in request.collects
    assert "ollama run" not in commands
    assert "UNKNOWN_NO_UNIQUE_PROCESS_CANDIDATE" in commands
    assert "NOT_SAFE_TO_QUERY" in commands


def test_checkout_and_process_requests_are_redacted_and_fail_closed():
    checkout = _commands("checkouts_drift")
    runtime = _commands("runtime_identity")
    combined = checkout + "\n" + runtime

    assert "/home/rr/Desktop/Desktop/nex5" in checkout
    assert "/home/rr/Desktop/NEX_AUDIT/Nex_v5.0-main" in checkout
    assert "remote get-url origin" in checkout
    assert "origin_identity=" in checkout
    assert "origin_sanitized=" not in checkout
    assert "origin_main_cached_sha=" in checkout
    assert "rev-list --left-right --count" in checkout
    assert "process_checkout_candidate_pid=" in checkout
    assert "git --no-optional-locks" in checkout
    assert "git --no-optional-locks" in runtime or "status --porcelain" not in runtime
    assert "git fetch" not in combined

    assert "VIRTUAL_ENV" in runtime
    assert "PYTHONHOME" in runtime
    assert "NEX5_DATA_DIR" in runtime
    assert "NEX5_VOICE_ENDPOINT_ORIGIN" in runtime
    assert "process_candidates=NONE_AFTER_FILTER" in runtime
    assert "NEX5_VOICE_MODEL" in runtime
    assert "systemctl --user show-environment" in runtime
    assert "user_manager=AVAILABLE" in runtime
    assert "user_manager=UNAVAILABLE" in runtime
    assert "user_unit_list=UNAVAILABLE" in runtime
    assert "matching_user_services=NONE" in runtime
    assert "set -o pipefail" in runtime
    assert "--property=MainPID" in runtime
    assert "Do not read service unit contents" in _requests()["runtime_identity"].collects

    assert "pgrep -af" not in combined
    assert "/proc/$pid/cmdline" not in combined
    assert "remote -v" not in combined
    assert "grep '^NEX5_'" not in combined
    assert "<verified-" not in combined
    assert "<NEX_RUNTIME_ROOTS>" not in combined


def test_artifact_fingerprint_is_derived_no_follow_and_failure_safe():
    request = _requests()["runtime_artifact_hashes"]
    commands = "\n".join(request.read_only_commands)

    assert "NEX5_DATA_DIR" in commands
    assert "runtime_process_candidate_count=" in commands
    assert "UNKNOWN_NO_UNIQUE_PROCESS_CANDIDATE" in commands
    assert "UNVERIFIED_CANDIDATE" in commands
    assert "O_NOFOLLOW" in commands
    assert "hashlib.sha256()" in commands
    assert "os.fstat(fd)" in commands
    assert "os.stat(path, follow_symlinks=False)" in commands
    assert "CHANGED_DURING_HASH" in commands
    assert "HASH_FAILED:" in commands
    assert "st_mtime_ns" in commands
    assert "st_ctime_ns" in commands
    assert "state_snapshot.json.tmp" in commands
    assert "state_snapshot.json.consumed" in commands
    assert '(".db", ".sqlite", ".sqlite3")' in commands
    assert '("", "-wal", "-shm", "-journal")' in commands
    assert '(".json", ".snapshot", ".snap", ".bak")' in commands
    assert "followlinks=False" in commands
    assert "path.is_symlink()" in commands
    assert "NEX5_SNAPSHOT_DIR" not in commands
    assert "find <NEX_RUNTIME_ROOTS>" not in commands
    assert "sha256sum --" not in commands
    assert "sha256sum -- \"$file\" | awk" not in commands
    assert "SELECT COUNT(*)" not in commands
    assert "No SQL" in request.collects
    assert "file copies" in request.collects


def test_embedded_fingerprint_accepts_only_stable_sha256(tmp_path):
    fingerprint = _artifact_fingerprint_function()
    path = tmp_path / "beliefs.db"
    payload = b"isolated fingerprint fixture, not a NEX database"
    path.write_bytes(payload)

    status, detail = fingerprint(path)

    assert status == "YES"
    assert hashlib.sha256(payload).hexdigest() in detail
    for metadata in ("device=", "inode=", "size=", "mtime_ns=", "ctime_ns="):
        assert metadata in detail


def test_embedded_fingerprint_never_accepts_hash_failure(tmp_path, monkeypatch):
    fingerprint = _artifact_fingerprint_function()
    path = tmp_path / "beliefs.db"
    path.write_bytes(b"isolated hash failure fixture")

    def fail_hash():
        raise PermissionError("simulated hash failure")

    monkeypatch.setattr(hashlib, "sha256", fail_hash)
    status, detail = fingerprint(path)

    assert status == "NO"
    assert detail == "HASH_FAILED:PermissionError"


def test_embedded_fingerprint_rejects_file_changed_during_read(tmp_path, monkeypatch):
    fingerprint = _artifact_fingerprint_function()
    path = tmp_path / "sense.db"
    path.write_bytes(b"isolated mutation fixture with enough bytes to read")
    original_read = os.read
    touched = False

    def read_then_mutate(fd, size):
        nonlocal touched
        data = original_read(fd, size)
        if data and not touched:
            touched = True
            before = os.stat(path)
            os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
        return data

    monkeypatch.setattr(os, "read", read_then_mutate)
    status, detail = fingerprint(path)

    assert touched is True
    assert status == "NO"
    assert detail == "CHANGED_DURING_HASH"


def test_artifact_roots_fallback_to_named_checkouts_and_execute_scan(tmp_path, capsys):
    commands = _commands("runtime_artifact_hashes")
    assert re.search(r"^scan_artifact_roots\\(targets\\)$", commands, re.MULTILINE)
    helpers = _artifact_helper_namespace()
    choose = helpers["choose_artifact_roots"]
    scan = helpers["scan_artifact_roots"]

    checkouts = []
    for name in ("runtime_checkout", "audit_checkout"):
        checkout = tmp_path / name
        (checkout / "substrate").mkdir(parents=True)
        (checkout / "run.py").write_text("# fixture marker", encoding="utf-8")
        (checkout / "substrate" / "paths.py").write_text("# fixture marker", encoding="utf-8")
        (checkout / "data").mkdir()
        (checkout / "snapshots").mkdir()
        (checkout / "data" / "beliefs.db").write_bytes((name + " database").encode())
        (checkout / "snapshots" / (name + ".json")).write_text('{"fixture": true}', encoding="utf-8")
        checkouts.append(checkout)

    # No live process: only the two explicit historical checkout defaults are considered.
    targets = choose([], checkouts)
    assert [item[0] for item in targets] == [
        "known_checkout_1_data",
        "known_checkout_2_data",
    ]
    assert all(item[2] == "known_checkout_default_candidate_active_root_unknown" for item in targets)
    assert all(item[3] is None for item in targets)

    scan(targets)
    output = capsys.readouterr().out
    assert "runtime_process_identity=UNKNOWN; no unique process candidate" in output
    assert "known_checkout_1_data_artifact stable=YES" in output
    assert "known_checkout_1_data_snapshot_archive_artifact stable=YES" in output
    assert "known_checkout_2_data_artifact stable=YES" in output
    assert "known_checkout_2_data_snapshot_archive_artifact stable=YES" in output

    # A unique process candidate remains the only authority for a custom data root.
    custom_data = tmp_path / "custom_runtime_data"
    custom_data.mkdir()
    (custom_data / "sense.db").write_bytes(b"configured data directory")
    candidate = ("4321", checkouts[0], str(custom_data))
    selected = choose([candidate], checkouts)
    assert len(selected) == 1
    assert selected[0][0] == "data"
    assert selected[0][1] == custom_data
    assert selected[0][2] == "process_NEX5_DATA_DIR_candidate_active_root_unverified"
    assert selected[0][3] == "4321"


def test_artifact_walk_reports_empty_and_incomplete_inventory(tmp_path, monkeypatch, capsys):
    walk = _artifact_walk_function()
    root = tmp_path / "data"
    root.mkdir()
    payload = root / "beliefs.db"
    payload.write_bytes(b"isolated inventory fixture")

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "hidden.db").write_bytes(b"must not be traversed through a symlink")
    (root / "linked.db").symlink_to(outside / "hidden.db")
    (root / "linked_dir").symlink_to(outside, target_is_directory=True)

    walk(root, "data")
    output = capsys.readouterr().out
    assert "data_artifact_match_count=1" in output
    assert "data_artifact_stable_count=1" in output
    assert "data_artifact_unstable_count=0" in output
    assert "data_symlink_directories_skipped=1" in output
    assert "data_symlink_files_skipped=1" in output
    assert "data_walk_status=COMPLETE_WITH_SKIPS" in output

    empty = tmp_path / "empty"
    empty.mkdir()
    walk(empty, "data")
    output = capsys.readouterr().out
    assert "data_artifact_match_count=0" in output
    assert "data_walk_status=COMPLETE_EMPTY" in output

    def failing_walk(directory, followlinks=False, onerror=None):
        error_path = str(pathlib.Path(directory) / "restricted")
        onerror(PermissionError(13, "permission denied", error_path))
        return iter(())

    monkeypatch.setattr(os, "walk", failing_walk)
    walk(root, "data")
    output = capsys.readouterr().out
    assert "data_walk_error=YES" in output
    assert "PermissionError" in output
    assert "data_walk_error_count=1" in output
    assert "data_walk_status=INCOMPLETE" in output


def test_generated_host_commands_have_valid_shell_and_python_syntax():
    for request in host_requests():
        command_text = "\n".join(request.read_only_commands)
        shell = subprocess.run(
            ["bash", "-n"],
            input=command_text,
            text=True,
            capture_output=True,
            check=False,
        )
        assert shell.returncode == 0, f"{request.id}: {shell.stderr}"

        python_blocks = re.findall(r"<<'PY'\n(.*?)\nPY(?:\n|$)", command_text, re.DOTALL)
        for block in python_blocks:
            ast.parse(block, filename=f"{request.id}:host-heredoc")


def test_host_requests_remain_unknown_until_host_results_arrive():
    expected = {
        "checkouts_drift",
        "runtime_identity",
        "phase0_environment",
        "runtime_artifact_hashes",
    }
    template = host_results_template()

    assert expected.issubset(template)
    assert "live_db_metadata" not in template
    assert template["phase0_environment"]["data"] is None
    assert template["phase0_environment"]["evidence_class"] is None
    assert template["phase0_environment"]["source_ref"] is None

    records = {record.subject: record for record in ingest_host_results({})}
    for request_id in expected:
        record = records[f"host:{request_id}"]
        assert record.origin == "host"
        assert record.evidence_class == "unknown"
        assert record.modifier == "unverified"
        assert record.data is None


def test_nonempty_host_data_without_explicit_provenance_is_not_measured():
    records = ingest_host_results({
        "phase0_environment": {"data": {"python": "3.12"}}
    })
    record = next(item for item in records if item.subject == "host:phase0_environment")

    assert record.data == {"python": "3.12"}
    assert record.evidence_class == "unknown"
    assert record.modifier == "unverified"
    assert record.source_ref == "host result (missing or invalid provenance)"


def test_measured_host_data_requires_an_explicit_source_reference():
    records = ingest_host_results({
        "phase0_environment": {
            "data": {"python": "3.12"},
            "evidence_class": "measured",
            "source_ref": "host command transcript: phase0 run 1",
        }
    })
    record = next(item for item in records if item.subject == "host:phase0_environment")

    assert record.evidence_class == "measured"
    assert record.modifier is None
    assert record.source_ref == "host command transcript: phase0 run 1"


def test_host_results_loader_drops_unanswered_placeholders(tmp_path):
    template = host_results_template()
    path = tmp_path / "host_results.json"
    template["phase0_environment"]["data"] = {"python": "3.12"}
    template["phase0_environment"]["evidence_class"] = "measured"
    template["phase0_environment"]["source_ref"] = "isolated host fixture"
    path.write_text(json.dumps(template), encoding="utf-8")

    from watcher.host import load_host_results

    results = load_host_results(str(path))
    assert set(results) == {"phase0_environment"}
    assert results["phase0_environment"]["data"] == {"python": "3.12"}
    assert results["phase0_environment"]["evidence_class"] == "measured"
    assert "_commands" not in results["phase0_environment"]
