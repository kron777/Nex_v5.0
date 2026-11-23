"""Phase 0 host-evidence request coverage.

These tests inspect the generated collection specification only. They do not
execute host commands, access a live NEX checkout, or read runtime databases.
"""
from watcher.host import host_requests, host_results_template, ingest_host_results


def test_phase0_host_request_covers_machine_and_model_fingerprint():
    requests = {request.id: request for request in host_requests()}
    request = requests["phase0_environment"]

    commands = "\n".join(request.read_only_commands)
    for required in (
        "cat /etc/os-release",
        "lscpu",
        "free -b",
        "python3 --version",
        "sqlite3.sqlite_version",
        "ollama --version",
        "ollama list",
        "ollama show qwen2.5:3b --modelfile",
        "ollama ps",
        "lspci",
        "mem_info_vram_total",
    ):
        assert required in commands

    assert "throughput is deliberately not measured" in request.collects
    assert "ollama run" not in commands


def test_phase0_runtime_artifact_request_hashes_without_copying_content():
    requests = {request.id: request for request in host_requests()}
    request = requests["runtime_artifact_hashes"]

    commands = "\n".join(request.read_only_commands)
    assert "find <NEX_RUNTIME_ROOTS>" in commands
    assert "sha256sum" in commands
    assert "do not copy files" in commands
    assert "never copy or dump private contents" in request.collects


def test_phase0_host_requests_remain_unknown_until_host_results_arrive():
    expected = {"phase0_environment", "runtime_artifact_hashes"}
    template = host_results_template()
    assert expected.issubset(template)

    records = {record.subject: record for record in ingest_host_results({})}
    for request_id in expected:
        record = records[f"host:{request_id}"]
        assert record.origin == "host"
        assert record.evidence_class == "unknown"
        assert record.modifier == "unverified"
        assert record.data is None
