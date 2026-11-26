"""Adversarial tests for independent, non-executing Watcher handoff verification."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from watcher.handoff_verify import (
    HandoffVerificationError,
    REQUEST_SCHEMA,
    verify_handoff_request,
)


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha(value):
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, check=True, timeout=15,
    )
    return result.stdout.strip()


def _repo(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "docs").mkdir()
    (repo / "docs" / "REQUIREMENTS.md").write_text("# Base requirements\n", encoding="utf-8")
    (repo / "README.md").write_text("# Fixture\n", encoding="utf-8")
    (repo / ".gitignore").write_text("rdo/.cycles/\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    _git(repo, "config", "user.name", "Watcher handoff test")
    _git(repo, "config", "user.email", "watcher-handoff@example.invalid")
    _git(repo, "add", ".gitignore", "README.md", "docs/REQUIREMENTS.md")
    _git(repo, "commit", "-q", "-m", "planning baseline")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "rdo" / ".cycles" / "handoffs").mkdir(parents=True)
    return repo, base


def _manifest(repo: Path, base: str, allowed=None):
    allowed = allowed or ["docs/REQUIREMENTS.md"]
    handoff_id = "handoff_" + ("a" * 24)
    resolved = {}
    for path in allowed:
        candidate = os.path.realpath(repo / path)
        resolved[path] = os.path.relpath(candidate, repo).replace(os.sep, "/")
    manifest = {
        "schema_version": "rdo.handoff.v1",
        "handoff_id": handoff_id,
        "created_at": "2026-11-26T00:00:00Z",
        "cycle": {"repository_revision": base},
        "scope": {"allowed_paths": allowed, "resolved_paths": resolved},
        "authority": {
            "handoff_status": "pending_human_review",
            "execution_authority": "none",
            "tests_execution_authorized": False,
            "runtime_operations_authorized": False,
        },
        "evidence_dimensions": {
            "test_verified": "not_authorized",
            "runtime_observed": "unknown_host_only",
            "human_acceptance": "not_recorded",
        },
    }
    manifest["manifest_sha256"] = _sha(manifest)
    path = repo / "rdo" / ".cycles" / "handoffs" / f"{handoff_id}.json"
    path.write_text(_canonical(manifest) + "\n", encoding="utf-8")
    return manifest, path


def _events(repo: Path, manifest: dict, *, approved=True):
    actions = ["edit_documentation_within_scope"] if approved else []
    event = {
        "schema_version": "rdo.handoff_event.v1",
        "sequence": 1,
        "handoff_id": manifest["handoff_id"],
        "manifest_sha256": manifest["manifest_sha256"],
        "previous_event_sha256": None,
        "recorded_at": "2026-11-26T00:01:00Z",
        "reviewer_identity_status": "caller_attributed_not_authenticated",
        "event_kind": "scope_review",
        "decision": "approved" if approved else "rejected",
        "reviewer": "fixture-reviewer",
        "source_reference": "fixture-approval-reference",
        "permitted_actions": actions,
        "note": "Test fixture only",
        "execution_authorized": False,
    }
    event["event_sha256"] = _sha(event)
    path = repo / "rdo" / ".cycles" / "handoffs" / f"{manifest['handoff_id']}.events.jsonl"
    path.write_text(_canonical(event) + "\n", encoding="utf-8")
    return path


def _request(repo: Path, manifest_path: Path, events_path: Path):
    return {
        "schema_version": REQUEST_SCHEMA,
        "repo_root": str(repo),
        "manifest_path": manifest_path.relative_to(repo).as_posix(),
        "events_path": events_path.relative_to(repo).as_posix(),
        "ledger_path": "rdo/.cycles/watcher_handoff_verification_ledger.jsonl",
    }


def test_watcher_process_confirms_source_file_only(tmp_path):
    repo, base = _repo(tmp_path)
    manifest, manifest_path = _manifest(repo, base)
    events_path = _events(repo, manifest)
    changed = repo / "docs" / "REQUIREMENTS.md"
    changed.write_text("# Updated requirements\nA scoped proposal is present.\n", encoding="utf-8")

    report = verify_handoff_request_path = verify_handoff_request_for_test(
        tmp_path, repo, manifest_path, events_path
    )
    assert report["verification_process"] == "independent_watcher_cli_process"
    assert report["scope"]["scope_compliant"] is True
    assert report["scope"]["changed_paths"] == ["docs/REQUIREMENTS.md"]
    assert report["evidence_dimensions"]["source_implemented"] == "source_confirmed"
    assert report["evidence_dimensions"]["test_verified"] == "not_authorized"
    assert report["evidence_dimensions"]["runtime_observed"] == "unknown_host_only"
    assert report["human_acceptance"]["status"] == "not_recorded"
    assert report["source_evidence"][0]["data"]["path"] == "docs/REQUIREMENTS.md"
    assert (repo / "rdo" / ".cycles" / "watcher_handoff_verification_ledger.jsonl").exists()


def verify_handoff_request_for_test(tmp_path, repo, manifest_path, events_path):
    request = _request(repo, manifest_path, events_path)
    request_path = tmp_path / "watcher-request.json"
    request_path.write_text(_canonical(request), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "watcher", "verify-handoff", "--request", str(request_path)],
        cwd=str(repo), capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr + "\n" + result.stdout
    return json.loads(result.stdout)


def test_watcher_refuses_a_scope_approved_event_with_invalid_event_hash(tmp_path):
    repo, base = _repo(tmp_path)
    manifest, manifest_path = _manifest(repo, base)
    events_path = _events(repo, manifest)
    event = json.loads(events_path.read_text(encoding="utf-8"))
    event["decision"] = "rejected"
    events_path.write_text(_canonical(event) + "\n", encoding="utf-8")
    request = _request(repo, manifest_path, events_path)
    request_path = tmp_path / "request.json"
    request_path.write_text(_canonical(request), encoding="utf-8")
    with pytest.raises(HandoffVerificationError, match="digest mismatch"):
        verify_handoff_request_for_test_direct(request_path)


def verify_handoff_request_for_test_direct(request_path):
    from watcher.handoff_verify import verify_handoff_request
    return verify_handoff_request(str(request_path))


def test_watcher_refuses_missing_or_nonapproved_scope_review(tmp_path):
    repo, base = _repo(tmp_path)
    manifest, manifest_path = _manifest(repo, base)
    events_path = _events(repo, manifest, approved=False)
    request_path = tmp_path / "request.json"
    request_path.write_text(_canonical(_request(repo, manifest_path, events_path)), encoding="utf-8")
    with pytest.raises(HandoffVerificationError, match="not approved"):
        verify_handoff_request_for_test_direct(request_path)


def test_watcher_flags_changes_outside_exact_file_allowlist(tmp_path):
    repo, base = _repo(tmp_path)
    manifest, manifest_path = _manifest(repo, base)
    events_path = _events(repo, manifest)
    (repo / "README.md").write_text("# Changed out of scope\n", encoding="utf-8")
    request_path = tmp_path / "request.json"
    request_path.write_text(_canonical(_request(repo, manifest_path, events_path)), encoding="utf-8")
    from watcher.handoff_verify import verify_handoff_request
    report = verify_handoff_request(str(request_path))
    assert report["exit_status"] == "scope_violation"
    assert report["scope"]["out_of_scope_paths"] == ["README.md"]
    assert report["evidence_dimensions"]["test_verified"] == "not_authorized"


def test_watcher_rejects_a_symlink_escape_in_allowed_path(tmp_path):
    repo, base = _repo(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("outside\n", encoding="utf-8")
    (repo / "docs" / "escape.md").symlink_to(outside)
    manifest, manifest_path = _manifest(repo, base, ["docs/escape.md"])
    # Simulate a forged/stale resolution map to exercise the Watcher's independent
    # realpath check rather than relying on the RDO creator to reject the link.
    manifest["scope"]["resolved_paths"]["docs/escape.md"] = "docs/escape.md"
    manifest["manifest_sha256"] = _sha({k:v for k,v in manifest.items() if k != "manifest_sha256"})
    manifest_path.write_text(_canonical(manifest) + "\\n", encoding="utf-8")
    events_path = _events(repo, manifest)
    request_path = tmp_path / "request.json"
    request_path.write_text(_canonical(_request(repo, manifest_path, events_path)), encoding="utf-8")
    from watcher.handoff_verify import verify_handoff_request
    report = verify_handoff_request(str(request_path))
    assert report["scope"]["scope_compliant"] is False
    assert report["scope"]["path_resolution_errors"]


def test_watcher_requires_planning_commit_to_be_an_ancestor(tmp_path):
    repo, base = _repo(tmp_path)
    other, other_base = _repo(tmp_path / "other")
    manifest, manifest_path = _manifest(repo, other_base)
    events_path = _events(repo, manifest)
    request_path = tmp_path / "request.json"
    request_path.write_text(_canonical(_request(repo, manifest_path, events_path)), encoding="utf-8")
    from watcher.handoff_verify import verify_handoff_request
    with pytest.raises(HandoffVerificationError, match="not an ancestor"):
        verify_handoff_request(str(request_path))


def test_watcher_refuses_duplicate_json_keys_in_request(tmp_path):
    request = tmp_path / "request.json"
    request.write_text('{"schema_version":"watcher.handoff_verify_request.v1","schema_version":"x"}',
                       encoding="utf-8")
    from watcher.handoff_verify import verify_handoff_request
    with pytest.raises(HandoffVerificationError, match="duplicate JSON property"):
        verify_handoff_request(str(request))
