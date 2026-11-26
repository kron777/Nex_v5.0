"""Stage-7 handoff manifest, approval and acceptance boundary tests."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from rdo_adapters.handoff import (
    HandoffError,
    create_handoff,
    handoff_history,
    load_handoff,
    record_human_acceptance,
    record_scope_review,
)
from rdo_adapters.objective_intake import submit_objective
from rdo.memory import CycleStore


def _clean_repo(path: Path) -> Path:
    path.mkdir()
    (path / "README.md").write_text("# Fixture repository\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "RDO handoff test"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "rdo-handoff@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(path), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", "fixture snapshot"], check=True)
    return path


def _objective(affected_path: str = "docs/REQUIREMENTS.md") -> dict:
    return {
        "schema_version": "rdo.objective.v1",
        "objective_id": "handoff_fixture",
        "revision": 1,
        "supersedes_sha256": None,
        "original_text": "Prepare a narrowly scoped documentation change and return a reviewable proposal.",
        "intent": "Create a bounded documentation proposal; do not execute code or alter NEX.",
        "owner": "test-caller-attribution",
        "source": {"kind": "human", "reference": "fixture-only"},
        "scope": {
            "in_scope": ["One documentation page"],
            "affected_paths": [affected_path],
        },
        "constraints": ["Keep the patch within the exact path allowlist"],
        "exclusions": ["No runtime code", "No database changes", "No tests or arbitrary commands"],
        "assumptions": ["The current clean repository SHA is the intended baseline"],
        "acceptance_criteria": [
            "A proposed documentation diff exists at the allowed path.",
            "The proposal maps every change to the original objective.",
        ],
        "seed_obligations": [{
            "key": "doc_change",
            "title": "Prepare the documentation change",
            "kind": "documentation",
            "classification": "necessary",
            "rationale": "The objective explicitly requests a documentation proposal.",
            "impact": "Without this work the requested document is not produced.",
            "evidence_needs": ["The changed document path", "A diff suitable for human review"],
            "assumptions": [],
            "confidence": "stated",
        }],
        "relationships": [],
        "reconciliation_signatures": {},
        "max_depth": 0,
    }


def _create_cycle(tmp_path, monkeypatch, affected_path: str = "docs/REQUIREMENTS.md"):
    repo = _clean_repo(tmp_path / "repo")
    workdir = str(tmp_path / "cycles")
    import rdo.orchestrator as orchestrator
    monkeypatch.setattr(orchestrator, "_active_experiments", lambda _repo: [])
    result = submit_objective(_objective(affected_path), repo_dir=str(repo), workdir=workdir)
    cycle = result["cycle"]
    assert cycle["objective_input"]["objective_id"] == "handoff_fixture"
    assert cycle["work_packages"]
    package = cycle["work_packages"][0]
    assert package["eligibility"] == "eligible"
    return repo, workdir, result, package


def test_real_intake_cycle_creates_immutable_handoff_manifest(tmp_path, monkeypatch):
    repo, workdir, result, package = _create_cycle(tmp_path, monkeypatch)
    manifest = create_handoff(
        workdir, str(repo), "handoff_fixture", 1, result["cycle"]["id"], package["key"]
    )
    assert manifest["schema_version"] == "rdo.handoff.v1"
    assert manifest["authority"]["handoff_status"] == "pending_human_review"
    assert manifest["authority"]["execution_authority"] == "none"
    assert manifest["authority"]["tests_execution_authorized"] is False
    assert manifest["scope"]["allowed_paths"] == ["docs/REQUIREMENTS.md"]
    assert manifest["scope"]["resolved_paths"] == {"docs/REQUIREMENTS.md": "docs/REQUIREMENTS.md"}
    assert manifest["objective"]["original_text"] == _objective()["original_text"]
    assert manifest["cycle"]["repository_revision"] == result["repository_revision"]
    assert manifest["manifest_sha256"]
    assert manifest["evidence_dimensions"] == {
        "source_implemented": "not_collected",
        "test_verified": "not_authorized",
        "runtime_observed": "unknown_host_only",
        "human_acceptance": "not_recorded",
    }


def test_handoff_create_is_idempotent_and_detects_tampering(tmp_path, monkeypatch):
    repo, workdir, result, package = _create_cycle(tmp_path, monkeypatch)
    args = (workdir, str(repo), "handoff_fixture", 1, result["cycle"]["id"], package["key"])
    first = create_handoff(*args)
    replay = create_handoff(*args)
    assert replay == first

    path = Path(workdir) / "handoffs" / f"{first['handoff_id']}.json"
    tampered = json.loads(path.read_text(encoding="utf-8"))
    tampered["scope"]["allowed_paths"] = ["outside.py"]
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(HandoffError, match="digest mismatch"):
        load_handoff(workdir, first["handoff_id"])


def test_handoff_refuses_a_repository_that_moved_since_planning(tmp_path, monkeypatch):
    repo, workdir, result, package = _create_cycle(tmp_path, monkeypatch)
    (repo / "README.md").write_text("# Changed after the RDO cycle\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "moved snapshot"], check=True)
    with pytest.raises(HandoffError, match="differs from the cycle snapshot"):
        create_handoff(
            workdir, str(repo), "handoff_fixture", 1, result["cycle"]["id"], package["key"]
        )


def test_blocked_work_package_cannot_receive_scope_approval(tmp_path, monkeypatch):
    repo, workdir, result, package = _create_cycle(tmp_path, monkeypatch)
    store = CycleStore(workdir)
    cycle = store.load(result["cycle"]["id"])
    cycle.work_packages[0]["eligibility"] = "blocked"
    cycle.work_packages[0]["blockers"] = ["A required dependency is unresolved"]
    store.save(cycle)

    manifest = create_handoff(
        workdir, str(repo), "handoff_fixture", 1, result["cycle"]["id"], package["key"]
    )
    assert manifest["authority"]["handoff_status"] == "blocked"
    with pytest.raises(HandoffError, match="blocked handoffs"):
        record_scope_review(
            workdir, manifest["handoff_id"], "approved", "human",
            "chat approval reference", ["prepare_scoped_patch"],
        )


def test_scope_review_is_digest_bound_attributed_and_non_executing(tmp_path, monkeypatch):
    repo, workdir, result, package = _create_cycle(tmp_path, monkeypatch)
    manifest = create_handoff(
        workdir, str(repo), "handoff_fixture", 1, result["cycle"]["id"], package["key"]
    )
    event = record_scope_review(
        workdir, manifest["handoff_id"], "approved", "founder-attribution",
        "external approval reference", ["prepare_scoped_patch", "edit_documentation_within_scope"],
        note="Approve preparation of a proposed patch only.",
    )
    assert event["manifest_sha256"] == manifest["manifest_sha256"]
    assert event["reviewer_identity_status"] == "caller_attributed_not_authenticated"
    assert event["execution_authorized"] is False
    assert "run_tests" not in event["permitted_actions"]


@pytest.mark.parametrize("action", ["run_tests", "execute_code", "deploy", "write_live_database"])
def test_scope_review_rejects_execution_and_operational_authority(tmp_path, monkeypatch, action):
    repo, workdir, result, package = _create_cycle(tmp_path, monkeypatch)
    manifest = create_handoff(
        workdir, str(repo), "handoff_fixture", 1, result["cycle"]["id"], package["key"]
    )
    with pytest.raises(HandoffError, match="exceed this handoff"):
        record_scope_review(
            workdir, manifest["handoff_id"], "approved", "reviewer",
            "approval-reference", ["prepare_scoped_patch", action],
        )


def test_rejections_and_change_requests_cannot_carry_permitted_actions(tmp_path, monkeypatch):
    repo, workdir, result, package = _create_cycle(tmp_path, monkeypatch)
    manifest = create_handoff(
        workdir, str(repo), "handoff_fixture", 1, result["cycle"]["id"], package["key"]
    )
    with pytest.raises(HandoffError, match="cannot carry permitted actions"):
        record_scope_review(
            workdir, manifest["handoff_id"], "changes_requested", "reviewer",
            "review-reference", ["prepare_scoped_patch"],
        )
    event = record_scope_review(
        workdir, manifest["handoff_id"], "changes_requested", "reviewer",
        "review-reference", [],
    )
    assert event["decision"] == "changes_requested"


def test_human_acceptance_is_separate_and_does_not_rewrite_evidence_dimensions(tmp_path, monkeypatch):
    repo, workdir, result, package = _create_cycle(tmp_path, monkeypatch)
    manifest = create_handoff(
        workdir, str(repo), "handoff_fixture", 1, result["cycle"]["id"], package["key"]
    )
    with pytest.raises(HandoffError, match="requires a recorded approved scope review"):
        record_human_acceptance(
            workdir, manifest["handoff_id"], "accepted", "reviewer",
            "acceptance-reference", "delivery-reference",
            {"source_implemented": [], "test_verified": [], "runtime_observed": []},
        )

    record_scope_review(
        workdir, manifest["handoff_id"], "approved", "reviewer",
        "approval-reference", ["prepare_scoped_patch"],
    )
    acceptance = record_human_acceptance(
        workdir, manifest["handoff_id"], "accepted", "reviewer",
        "acceptance-reference", "delivery-reference",
        {
            "source_implemented": ["diff://commit/abc123"],
            "test_verified": [],
            "runtime_observed": [],
        },
        note="Human review of the proposed document.",
    )
    history = handoff_history(workdir, manifest["handoff_id"])
    assert acceptance["event_kind"] == "human_acceptance"
    assert acceptance["decision"] == "accepted"
    assert acceptance["acceptance_authority"].startswith("human_judgement_only")
    assert history["latest_scope_review"]["event_kind"] == "scope_review"
    assert history["latest_human_acceptance"]["event_kind"] == "human_acceptance"
    assert history["manifest"]["evidence_dimensions"]["test_verified"] == "not_authorized"
    assert history["manifest"]["evidence_dimensions"]["runtime_observed"] == "unknown_host_only"
    assert history["manifest"]["evidence_dimensions"]["human_acceptance"] == "not_recorded"


def test_handoff_decision_ledger_is_hash_chained_and_tamper_evident(tmp_path, monkeypatch):
    repo, workdir, result, package = _create_cycle(tmp_path, monkeypatch)
    manifest = create_handoff(
        workdir, str(repo), "handoff_fixture", 1, result["cycle"]["id"], package["key"]
    )
    record_scope_review(
        workdir, manifest["handoff_id"], "rejected", "reviewer", "source-ref", [],
    )
    path = Path(workdir) / "handoffs" / f"{manifest['handoff_id']}.events.jsonl"
    event = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    event["decision"] = "approved"
    path.write_text(json.dumps(event) + "\n", encoding="utf-8")
    with pytest.raises(HandoffError, match="digest mismatch"):
        handoff_history(workdir, manifest["handoff_id"])


def test_handoff_history_survives_new_process(tmp_path, monkeypatch):
    repo, workdir, result, package = _create_cycle(tmp_path, monkeypatch)
    manifest = create_handoff(
        workdir, str(repo), "handoff_fixture", 1, result["cycle"]["id"], package["key"]
    )
    record_scope_review(
        workdir, manifest["handoff_id"], "approved", "reviewer",
        "approval-reference", ["prepare_scoped_patch"],
    )
    project_root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [os.sys.executable, "-m", "rdo", "handoff-history",
         "--handoff-id", manifest["handoff_id"], "--out", workdir],
        cwd=str(project_root), capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    restored = json.loads(proc.stdout)
    assert restored["manifest"]["manifest_sha256"] == manifest["manifest_sha256"]
    assert restored["latest_scope_review"]["decision"] == "approved"

def test_human_acceptance_requires_evidence_and_current_scope_approval(tmp_path, monkeypatch):
    repo, workdir, result, package = _create_cycle(tmp_path, monkeypatch)
    manifest = create_handoff(
        workdir, str(repo), "handoff_fixture", 1, result["cycle"]["id"], package["key"]
    )
    record_scope_review(
        workdir, manifest["handoff_id"], "approved", "reviewer",
        "approval-reference", ["prepare_scoped_patch"],
    )
    empty_evidence = {
        "source_implemented": [],
        "test_verified": [],
        "runtime_observed": [],
    }
    with pytest.raises(HandoffError, match="at least one evidence reference"):
        record_human_acceptance(
            workdir, manifest["handoff_id"], "accepted", "reviewer",
            "acceptance-reference", "delivery-reference", empty_evidence,
        )

    record_scope_review(
        workdir, manifest["handoff_id"], "changes_requested", "reviewer",
        "superseding-review-reference", [],
    )
    with pytest.raises(HandoffError, match="currently approved scope review"):
        record_human_acceptance(
            workdir, manifest["handoff_id"], "accepted", "reviewer",
            "acceptance-reference", "delivery-reference",
            {
                "source_implemented": ["diff://change"],
                "test_verified": [],
                "runtime_observed": [],
            },
        )


def test_handoff_requires_exact_native_cycle_and_objective_revision(tmp_path, monkeypatch):
    repo, workdir, result, package = _create_cycle(tmp_path, monkeypatch)
    with pytest.raises(HandoffError, match="does not belong"):
        create_handoff(
            workdir, str(repo), "handoff_fixture", 2, result["cycle"]["id"], package["key"]
        )
    cycle = CycleStore(workdir).load(result["cycle"]["id"])
    cycle.kind = "imported_retrospective"
    CycleStore(workdir).save(cycle)
    with pytest.raises(HandoffError, match="native planning cycle"):
        create_handoff(
            workdir, str(repo), "handoff_fixture", 1, result["cycle"]["id"], package["key"]
        )

def test_handoff_refuses_a_symlink_that_resolves_outside_repository(tmp_path, monkeypatch):
    outside = tmp_path / "outside.md"
    outside.write_text("outside target\n", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# Fixture repository\n", encoding="utf-8")
    os.symlink(outside, repo / "escape.md")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "RDO handoff test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "rdo-handoff@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "README.md", "escape.md"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "fixture with external symlink"], check=True)
    workdir = str(tmp_path / "cycles")
    import rdo.orchestrator as orchestrator
    monkeypatch.setattr(orchestrator, "_active_experiments", lambda _repo: [])
    result = submit_objective(_objective("escape.md"), repo_dir=str(repo), workdir=workdir)
    package = result["cycle"]["work_packages"][0]
    with pytest.raises(HandoffError, match="outside the repository"):
        create_handoff(
            workdir, str(repo), "handoff_fixture", 1, result["cycle"]["id"], package["key"]
        )


def test_handoff_records_internal_symlink_resolution(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# Fixture repository\n", encoding="utf-8")
    os.symlink("README.md", repo / "readme-alias.md")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "RDO handoff test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "rdo-handoff@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "README.md", "readme-alias.md"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "fixture with internal symlink"], check=True)
    workdir = str(tmp_path / "cycles")
    import rdo.orchestrator as orchestrator
    monkeypatch.setattr(orchestrator, "_active_experiments", lambda _repo: [])
    result = submit_objective(_objective("readme-alias.md"), repo_dir=str(repo), workdir=workdir)
    package = result["cycle"]["work_packages"][0]
    manifest = create_handoff(
        workdir, str(repo), "handoff_fixture", 1, result["cycle"]["id"], package["key"]
    )
    assert manifest["scope"]["allowed_paths"] == ["readme-alias.md"]
    assert manifest["scope"]["resolved_paths"] == {"readme-alias.md": "README.md"}

def test_handoff_rejects_directory_as_an_allowed_path(tmp_path, monkeypatch):
    repo = _clean_repo(tmp_path / "repo")
    (repo / "docs").mkdir()
    (repo / "docs" / "guide.md").write_text("# Guide\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "docs/guide.md"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "add docs directory"], check=True)
    workdir = str(tmp_path / "cycles")
    import rdo.orchestrator as orchestrator
    monkeypatch.setattr(orchestrator, "_active_experiments", lambda _repo: [])
    result = submit_objective(_objective("docs"), repo_dir=str(repo), workdir=workdir)
    package = result["cycle"]["work_packages"][0]
    with pytest.raises(HandoffError, match="exact file, not a directory"):
        create_handoff(
            workdir, str(repo), "handoff_fixture", 1, result["cycle"]["id"], package["key"]
        )

