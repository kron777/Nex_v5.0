"""Phase 0 host-evidence request coverage.

These tests inspect the generated collection specification only. They do not
execute host commands, access a live NEX checkout, or read runtime databases.
"""
from watcher.host import host_requests, host_results_template, ingest_host_results


def _requests():
    return {request.id: request for request in host_requests()}


def _commands(request_id):
    return "\n".join(_requests()[request_id].read_only_commands)


def test_phase0_host_request_covers_machine_and_model_fingerprint():
    request = _requests()["phase0_environment"]
    commands = "\n".join(request.read_only_commands)

    for required in (
        "cat /etc/os-release",
        "lscpu",
        "/proc/meminfo",
        "lspci",
        "mem_info_vram_total",
        "<verified-NEX-python> --version",
        "<verified-NEX-python> -c 'import sqlite3;",
        "ollama --version",
        "ollama list",
        "/api/tags",
        "modelfile_backing_blob=",
        "ollama ps",
    ):
        assert required in commands

    assert "No inference" in request.collects
    assert "throughput benchmark" in request.collects
    assert "ollama run" not in commands
    assert "qwen2.5:3b_api_digest=" in commands
    assert "Modelfile FROM blob" in commands


def test_checkout_and_process_requests_do_not_expose_credentials_or_raw_argv():
    checkout = _commands("checkouts_drift")
    runtime = _commands("runtime_identity")
    combined = checkout + "\n" + runtime

    assert "/home/rr/Desktop/Desktop/nex5" in checkout
    assert "/home/rr/Desktop/NEX_AUDIT/Nex_v5.0-main" in checkout
    assert "remote get-url origin" in checkout
    assert "urllib.parse.urlsplit" in checkout
    assert "origin_main_cached_sha=" in checkout
    assert "rev-list --left-right --count" in checkout
    assert "git fetch" not in combined

    # The collector must summarize worktree state without printing filenames,
    # and must not dump process arguments or a complete environment.
    assert "status --porcelain=v1" in checkout
    assert "dirty_entries=" in checkout
    assert "pgrep -af" not in combined
    assert "/proc/$pid/cmdline" not in combined
    assert "remote -v" not in combined
    assert "grep '^NEX5_'" not in combined
    assert "VIRTUAL_ENV" in runtime
    assert "PYTHONHOME" in runtime
    assert "NEX5_DATA_DIR" in runtime
    assert "NEX5_* dump" in runtime
    assert "systemctl --user list-units" in runtime
    assert "Do not infer STANDBY" in runtime


def test_phase0_runtime_artifact_request_uses_verified_roots_and_stability_check():
    request = _requests()["runtime_artifact_hashes"]
    commands = "\n".join(request.read_only_commands)

    assert "verified NEX process" in request.collects
    assert "do not guess or scan home" in request.collects
    assert "NEX5_DATA_DIR" in commands
    assert "NEX5_SNAPSHOT_DIR" in commands
    assert "verified checkout" in commands
    assert "find <NEX_RUNTIME_ROOTS>" not in commands

    for suffix in (
        "*.db-wal",
        "*.db-shm",
        "*.db-journal",
        "*.sqlite-wal",
        "*.sqlite-shm",
        "*.sqlite3-wal",
        "*.sqlite3-shm",
        "state_snapshot.json",
        "*.snapshot",
        "*.snap",
    ):
        assert suffix in commands

    assert "stat -c '%d:%i:%s:%y:%z'" in commands
    assert 'before="$' not in commands  # before/after are captured as separate stat calls
    assert 'after=$(stat' in commands
    assert 'if [ "$before" = "$after" ]' in commands
    assert "stable=NO sha256=DISCARD" in commands
    assert "sha256sum" in commands
    assert "SELECT COUNT(*)" not in commands
    assert "row counts" in request.collects
    assert "do not copy" in request.collects


def test_phase0_host_requests_remain_unknown_until_host_results_arrive():
    expected = {
        "checkouts_drift",
        "runtime_identity",
        "phase0_environment",
        "runtime_artifact_hashes",
    }
    template = host_results_template()

    assert expected.issubset(template)
    assert "live_db_metadata" not in template

    records = {record.subject: record for record in ingest_host_results({})}
    for request_id in expected:
        record = records[f"host:{request_id}"]
        assert record.origin == "host"
        assert record.evidence_class == "unknown"
        assert record.modifier == "unverified"
        assert record.data is None


def test_host_results_loader_drops_unanswered_placeholders(tmp_path):
    import json
    from watcher.host import load_host_results

    template = host_results_template()
    path = tmp_path / "host_results.json"
    template["phase0_environment"]["data"] = {"python": "3.x"}
    template["phase0_environment"]["source_ref"] = "host test fixture"
    path.write_text(json.dumps(template), encoding="utf-8")

    results = load_host_results(str(path))
    assert set(results) == {"phase0_environment"}
    assert results["phase0_environment"]["data"] == {"python": "3.x"}
    assert "_commands" not in results["phase0_environment"]
