"""Generic RDO objective-intake contract, revisions and persistence tests."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from rdo.model import AcceptanceVerificationRecord, ContextRequirement, NECESSARY, ANTI_REQUIREMENT, CONDITIONAL
from rdo_adapters.objective_intake import (
    ObjectiveInputError,
    ObjectiveInputStore,
    compare_revisions,
    objective_history,
    resume_objective,
    submit_objective,
    validate_objective,
)


def payload(objective_id="demo_objective") -> dict:
    return {
        "schema_version": "rdo.objective.v1",
        "objective_id": objective_id,
        "revision": 1,
        "supersedes_sha256": None,
        "original_text": "  Build a bounded route capability. Preserve this wording exactly.\n",
        "intent": "Expose one read-only route without changing NEX runtime behaviour.",
        "owner": "founder",
        "source": {"kind": "human", "reference": "founder-provided objective"},
        "scope": {
            "in_scope": ["RDO planning and repository reconciliation"],
            "affected_paths": ["module.py", "rdo"],
        },
        "constraints": ["Advisory only", "No runtime or live database changes"],
        "exclusions": ["No deployment", "No autonomous execution"],
        "assumptions": ["The repository snapshot is the current Git HEAD"],
        "acceptance_criteria": [
            "A traceable obligation graph is persisted.",
            "Every work package traces to the original request.",
        ],
        "seed_obligations": [
            {
                "key": "api",
                "title": "Expose the route",
                "kind": "api",
                "classification": "necessary",
                "rationale": "A route is required to expose the requested capability.",
                "impact": "Without it, the capability cannot be consumed.",
                "evidence_needs": ["Route source anchor", "Route response contract"],
                "assumptions": ["The route remains read-only"],
                "confidence": "stated",
            },
            {
                "key": "store",
                "title": "Persist route configuration",
                "kind": "persistence",
                "classification": "conditional",
                "rationale": "Configuration may need persistence after repository inspection.",
                "impact": "Without persistence, the configuration may not survive restart.",
                "evidence_needs": ["Existing storage mechanism or documented reason not to persist"],
                "assumptions": [],
                "confidence": "inferred",
            },
        ],
        "relationships": [
            {
                "src": "api",
                "dst": "store",
                "kind": "depends_on",
                "authority": "none",
                "reversible": None,
                "note": "The route may consume persisted configuration.",
            }
        ],
        "reconciliation_signatures": {
            "api": [
                {
                    "pattern": "def current_route",
                    "path": "module.py",
                    "label": "current route source anchor",
                }
            ]
        },
        "max_depth": 3,
    }


def make_clean_repo(path: Path) -> Path:
    path.mkdir()
    (path / "module.py").write_text(
        "def current_route():\n    return {'status': 'existing'}\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "RDO test"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "rdo-test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(path), "add", "module.py"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", "fixture snapshot"], check=True)
    return path


def test_published_example_matches_python_contract():
    from rdo_adapters.objective_intake import load_objective_file

    example = Path(__file__).resolve().parents[1] / "examples" / "objective.v1.example.json"
    checked = load_objective_file(str(example))
    assert checked["schema_version"] == "rdo.objective.v1"
    assert checked["objective_id"] == "read_only_route_example"


def test_validation_preserves_original_text_and_all_scope_fields():
    raw = payload()
    checked = validate_objective(raw)
    assert checked["original_text"] == raw["original_text"]
    assert checked["intent"] == raw["intent"]
    assert checked["scope"] == raw["scope"]
    assert checked["constraints"] == raw["constraints"]
    assert checked["exclusions"] == raw["exclusions"]
    assert checked["acceptance_criteria"] == raw["acceptance_criteria"]


def test_input_is_strict_and_does_not_accept_reconciliation_or_authority_claims():
    raw = payload()
    raw["approved"] = True
    with pytest.raises(ObjectiveInputError, match="unsupported fields"):
        validate_objective(raw)

    raw = payload()
    raw["seed_obligations"][0]["recon_status"] = "reuse_existing"
    with pytest.raises(ObjectiveInputError, match="unsupported fields"):
        validate_objective(raw)


def test_external_llm_proposals_must_remain_inferred():
    raw = payload()
    raw["source"] = {"kind": "external_llm", "reference": "independent-model-output"}
    raw["seed_obligations"][0]["confidence"] = "inferred"
    assert validate_objective(raw)["seed_obligations"][0]["confidence"] == "inferred"

    raw["seed_obligations"][0]["confidence"] = "stated"
    with pytest.raises(ObjectiveInputError, match="must remain inferred"):
        validate_objective(raw)

    raw["seed_obligations"][0]["confidence"] = "measured"
    with pytest.raises(ObjectiveInputError, match="measured is reserved"):
        validate_objective(raw)


def test_measured_confidence_cannot_be_injected_for_human_seed():
    raw = payload()
    raw["seed_obligations"][0]["confidence"] = "measured"
    with pytest.raises(ObjectiveInputError, match="measured is reserved"):
        validate_objective(raw)


def test_paths_relationships_and_signature_keys_are_bounded():
    raw = payload()
    raw["scope"]["affected_paths"] = ["../outside.py"]
    with pytest.raises(ObjectiveInputError, match="repository-relative"):
        validate_objective(raw)

    raw = payload()
    raw["relationships"][0]["dst"] = "not_a_seed"
    with pytest.raises(ObjectiveInputError, match="declared seed"):
        validate_objective(raw)

    raw = payload()
    raw["reconciliation_signatures"]["not_a_seed"] = [
        {"pattern": "def x", "path": "module.py", "label": "x"}
    ]
    with pytest.raises(ObjectiveInputError, match="unsupported fields"):
        validate_objective(raw)


def test_revision_store_is_append_only_hash_chained_and_idempotent(tmp_path):
    store = ObjectiveInputStore(str(tmp_path / "objectives"))
    first = payload()
    saved1 = store.append(first)
    replay = store.append(first)
    assert replay["sha256"] == saved1["sha256"]
    assert replay["replayed"] is True
    assert len(store.history(first["objective_id"])) == 1

    second = payload()
    second["revision"] = 2
    second["supersedes_sha256"] = saved1["sha256"]
    second["constraints"] = second["constraints"] + ["Clarification: keep the route read-only."]
    saved2 = store.append(second)
    assert saved2["sha256"] != saved1["sha256"]
    history = store.history(first["objective_id"])
    assert [x["record"]["revision"] for x in history] == [1, 2]
    assert history[0]["record"]["original_text"] == history[1]["record"]["original_text"]

    diff = compare_revisions(history[0]["record"], history[1]["record"])
    assert sorted(diff["changed_fields"]) == ["constraints"]

    wrong_parent = dict(second, revision=3, supersedes_sha256="0" * 64)
    with pytest.raises(ObjectiveInputError, match="immediately previous"):
        store.append(wrong_parent)

    rewritten_intent = dict(second, revision=3, supersedes_sha256=saved2["sha256"],
                            original_text="A different objective")
    with pytest.raises(ObjectiveInputError, match="immutable"):
        store.append(rewritten_intent)

    changed_same_revision = dict(second, constraints=["rewritten"], supersedes_sha256=saved1["sha256"])
    with pytest.raises(ObjectiveInputError, match="already exists"):
        store.append(changed_same_revision)


def test_revisions_must_be_sequential_and_revision_one_has_no_parent(tmp_path):
    store = ObjectiveInputStore(str(tmp_path / "objectives"))
    raw = payload()
    raw["revision"] = 2
    raw["supersedes_sha256"] = "a" * 64
    with pytest.raises(ObjectiveInputError, match="expected revision 1"):
        store.append(raw)

    raw = payload()
    raw["supersedes_sha256"] = "a" * 64
    with pytest.raises(ObjectiveInputError, match="revision 1"):
        validate_objective(raw)


def test_duplicate_json_properties_are_rejected(tmp_path):
    from rdo_adapters.objective_intake import load_objective_file

    path = tmp_path / "duplicate.json"
    path.write_text('{"schema_version":"rdo.objective.v1","schema_version":"other"}', encoding="utf-8")
    with pytest.raises(ObjectiveInputError, match="duplicate JSON property"):
        load_objective_file(str(path))


def test_submit_runs_existing_pipeline_and_persists_intake_provenance(tmp_path, monkeypatch):
    repo = make_clean_repo(tmp_path / "repo")
    workdir = tmp_path / "cycles"

    import rdo.orchestrator as orchestrator
    monkeypatch.setattr(orchestrator, "_active_experiments", lambda _repo: [])

    raw = payload()
    result = submit_objective(raw, repo_dir=str(repo), workdir=str(workdir))
    assert result["status"] == "created"
    assert result["revision"] == 1
    assert result["repository_revision"]
    assert result["summary"]["counts"]["discovered"] >= len(raw["seed_obligations"])

    cycle = result["cycle"]
    assert cycle["objective"] == raw["original_text"]
    assert cycle["objective_input"]["objective_id"] == raw["objective_id"]
    assert cycle["objective_context"] == {
        "intent": raw["intent"],
        "owner": raw["owner"],
        "source": raw["source"],
        "scope": raw["scope"],
        "assumptions": raw["assumptions"],
        "constraints": raw["constraints"],
        "exclusions": raw["exclusions"],
        "acceptance_criteria": raw["acceptance_criteria"],
    }
    assert cycle["assumptions"] == raw["assumptions"]
    assert cycle["context_assessment"]["status"] == "unmapped"
    assert cycle["context_assessment"]["review_required"] is True
    context_items = cycle["context_assessment"]["items"]
    assert all(item["status"] == "unmapped" and item["evidence"] == []
               and item["mapped_obligation_keys"] == [] and item["review_required"] is True
               for item in context_items)
    assert len(context_items) == 10
    assert all(item["item_id"].startswith("ctx:") for item in context_items)
    assert all(item["source_ref"].startswith(
        f"objective_input:{result['input_sha256']}:"
    ) for item in context_items)
    classifications = {item["kind"]: item["classification"] for item in context_items}
    assert classifications["intent"] == NECESSARY
    assert classifications["scope"] == NECESSARY
    assert classifications["affected_path"] == NECESSARY
    assert classifications["assumption"] == CONDITIONAL
    assert classifications["constraint"] == NECESSARY
    assert classifications["exclusion"] == ANTI_REQUIREMENT
    assert classifications["acceptance_criterion"] == NECESSARY
    acceptance_records = cycle["context_assessment"]["acceptance_verification"]
    assert len(acceptance_records) == len(raw["acceptance_criteria"])
    assert [item["criterion"] for item in acceptance_records] == raw["acceptance_criteria"]
    assert all(item["status"] == "unknown" and item["review_required"] is True
               and item["mapped_obligation_keys"] == [] and item["evidence_refs"] == []
               for item in acceptance_records)
    assert cycle["context_assessment"]["unmapped_count"] == len(context_items)
    assert cycle["context_assessment"]["acceptance_criteria_count"] == len(acceptance_records)
    assert cycle["work_packages"]
    # Context uncertainty blocks execution readiness but must not be
    # misrepresented as a Stage-1 package blocker or erase genuine blockers.
    assert all(package["eligibility"] in ("eligible", "blocked")
               for package in cycle["work_packages"])
    assert all(not any("objective context" in blocker.lower()
                       for blocker in package["blockers"])
               for package in cycle["work_packages"])
    assert cycle["context_assessment"]["execution_readiness"] == "blocked"
    assert cycle["context_assessment"]["handoff_readiness"] == "reviewable"
    assert all(
        any("No autonomous execution" in item
            for item in package["anti_requirements"])
        for package in cycle["work_packages"]
    )
    assert cycle["objective_input"]["revision"] == 1
    assert cycle["objective_input"]["sha256"] == result["input_sha256"]
    by_key = {item["key"]: item for item in cycle["obligations"]}
    assert by_key["api"]["impact"] == raw["seed_obligations"][0]["impact"]
    assert by_key["api"]["evidence_needs"] == raw["seed_obligations"][0]["evidence_needs"]
    assert "intake:human:founder-provided objective" in by_key["api"]["provenance"]
    assert all(item["evidence_needs"] and item["impact"] for item in cycle["obligations"])
    assert all(item["confidence"] == "inferred" for item in cycle["obligations"] if item["depth"] > 0)
    assert any(
        edge["src"] == "api" and edge["dst"] == "store" and edge["kind"] == "depends_on"
        for edge in cycle["relationships"]
    )

    replay = submit_objective(raw, repo_dir=str(repo), workdir=str(workdir))
    assert replay["status"] == "reused_existing_cycle"
    assert replay["cycle"]["id"] == cycle["id"]

    resumed = resume_objective(str(workdir), raw["objective_id"], 1)
    assert resumed["objective"]["original_text"] == raw["original_text"]
    assert len(resumed["cycles"]) == 1
    assert resumed["cycles"][0]["objective_input"]["sha256"] == result["input_sha256"]
    assert resumed["cycles"][0]["objective_context"] == cycle["objective_context"]
    assert resumed["cycles"][0]["context_assessment"] == cycle["context_assessment"]


def test_context_requirement_requires_evidence_before_mapping():
    base = dict(
        item_id="ctx:constraint:0",
        kind="constraint",
        text="Do not alter live databases",
        source_field="constraints",
        source_index=0,
        source_ref="objective_input:sha:constraints[0]",
        classification=NECESSARY,
    )
    with pytest.raises(ValueError, match="mapped context requirements need mapped obligation keys"):
        ContextRequirement(
            **base, status="mapped", evidence=["review:constraint-1"],
            review_required=False,
        )
    mapped = ContextRequirement(
        **base, status="mapped", mapped_obligation_keys=["db.read_only"],
        evidence=["review:constraint-1"], review_required=False,
    )
    assert mapped.status == "mapped"
    assert mapped.mapped_obligation_keys == ["db.read_only"]


def test_context_requirement_classification_is_typed():
    with pytest.raises(ValueError, match="must use classification"):
        ContextRequirement(
            item_id="ctx:exclusion:0",
            kind="exclusion",
            text="No deployment",
            source_field="exclusions",
            source_index=0,
            source_ref="objective_input:sha:exclusions[0]",
            classification=NECESSARY,
        )


def test_acceptance_verification_cannot_claim_pass_without_evidence():
    base = dict(
        criterion_id="ctx:acceptance:0",
        source_ref="objective_input:sha:acceptance_criteria[0]",
        criterion="The report is reproducible",
        status="passed",
        mapped_obligation_keys=["report.reproducibility"],
        verification_method="pytest -q tests/test_report.py",
        verifier="CI",
        confidence="measured",
        verified_at="2026-11-28T10:00:00Z",
    )
    with pytest.raises(ValueError, match="needs traceable evidence"):
        AcceptanceVerificationRecord(**base)
    with pytest.raises(ValueError, match="timezone offset"):
        AcceptanceVerificationRecord(
            **{**base, "evidence_refs": ["ci:run-1"], "verified_at": "2026-11-28T10:00:00"}
        )
    verified = AcceptanceVerificationRecord(
        **{**base, "evidence_refs": ["ci:run-1"]}
    )
    assert verified.status == "passed"
    assert verified.review_required is False


def test_unknown_acceptance_verification_cannot_carry_completion_claim():
    with pytest.raises(ValueError, match="cannot carry a completion claim"):
        AcceptanceVerificationRecord(
            criterion_id="ctx:acceptance:0",
            source_ref="objective_input:sha:acceptance_criteria[0]",
            criterion="The report is reproducible",
            evidence_refs=["ci:run-1"],
        )


def test_acceptance_verification_pending_and_failed_states_have_distinct_proof_requirements():
    common = dict(
        criterion_id="ctx:acceptance:pending",
        source_ref="objective_input:sha:acceptance_criteria[0]",
        criterion="The capability behaves as specified",
        mapped_obligation_keys=["capability.behaviour"],
        verification_method="pytest -q tests/test_capability.py",
    )
    pending = AcceptanceVerificationRecord(**common, status="pending")
    assert pending.review_required is True
    with pytest.raises(ValueError, match="needs traceable evidence"):
        AcceptanceVerificationRecord(
            **common, status="failed", verifier="CI",
            confidence="measured", verified_at="2026-11-28T10:00:00Z",
        )
    failed = AcceptanceVerificationRecord(
        **common, status="failed", evidence_refs=["ci:run-42"],
        verifier="CI", confidence="measured",
        verified_at="2026-11-28T10:00:00Z",
    )
    assert failed.status == "failed"
    assert failed.review_required is False


def test_context_requirement_rejects_invalid_source_index_and_status():
    base = dict(
        item_id="ctx:constraint:0",
        kind="constraint",
        text="Do not modify live data",
        source_field="constraints",
        source_index=0,
        source_ref="objective_input:sha:constraints[0]",
        classification=NECESSARY,
    )
    with pytest.raises(ValueError, match="source_index"):
        ContextRequirement(**{**base, "source_index": -1})
    with pytest.raises(ValueError, match="status"):
        ContextRequirement(**{**base, "status": "verified"})


def test_context_requirement_rejects_duplicate_mapping_references():
    base = dict(
        item_id="ctx:constraint:0",
        kind="constraint",
        text="Do not modify live data",
        source_field="constraints",
        source_index=0,
        source_ref="objective_input:sha:constraints[0]",
        classification=NECESSARY,
        status="mapped",
        mapped_obligation_keys=["db.read_only", "db.read_only"],
        evidence=["review:constraint-1"],
        review_required=False,
    )
    # Repeated references add no traceability and can hide duplicate mapping work.
    with pytest.raises(ValueError, match="unique"):
        ContextRequirement(**base)


def test_intake_smoke_on_real_rdo_repository(tmp_path):
    """A real, read-only RDO documentation/tooling objective against this checkout."""
    repo = Path(__file__).resolve().parents[2]
    raw = payload("rdo_intake_contract_smoke")
    raw["original_text"] = (
        "Produce a reviewable, read-only plan to verify the RDO objective intake "
        "contract and its evidence/provenance boundaries."
    )
    raw["intent"] = "Check the current intake contract and test coverage without editing NEX."
    raw["scope"] = {"in_scope": ["RDO intake schema", "RDO validator and tests"],
                    "affected_paths": ["rdo_adapters/objective_intake.py", "rdo/tests/test_intake.py"]}
    raw["seed_obligations"] = [{
        "key": "intake_contract_guard",
        "title": "Verify the objective intake contract",
        "kind": "invariant",
        "classification": "necessary",
        "rationale": "A versioned input contract must reject claims outside its evidence authority.",
        "impact": "Without a guard, proposal data could be confused with verified evidence or approval.",
        "evidence_needs": ["JSON Schema and validator contract", "Adversarial regression tests"],
        "assumptions": [],
        "confidence": "stated",
    }]
    raw["relationships"] = []
    raw["reconciliation_signatures"] = {
        "intake_contract_guard": [{
            "pattern": "def validate_objective",
            "path": "rdo_adapters/objective_intake.py",
            "label": "intake validator source anchor",
        }]
    }
    result = submit_objective(raw, repo_dir=str(repo), workdir=str(tmp_path / "real-cycles"))
    cycle = result["cycle"]
    assert result["repository_revision"]
    assert cycle["objective"] == raw["original_text"]
    assert any(o["key"] == "intake_contract_guard" for o in cycle["obligations"])
    assert cycle["signature_matches"] == ["intake_contract_guard"]
    # A source anchor is not semantic satisfaction; this stays review work.
    assert "intake_contract_guard" not in cycle["reused"]
    assert cycle["objective_input"]["objective_id"] == raw["objective_id"]


def test_dirty_repository_refuses_to_claim_a_snapshot(tmp_path, monkeypatch):
    repo = make_clean_repo(tmp_path / "repo")
    workdir = tmp_path / "cycles"
    import rdo.orchestrator as orchestrator
    monkeypatch.setattr(orchestrator, "_active_experiments", lambda _repo: [])
    (repo / "module.py").write_text("# uncommitted change\n", encoding="utf-8")
    with pytest.raises(ObjectiveInputError, match="not clean"):
        submit_objective(payload(), repo_dir=str(repo), workdir=str(workdir))
    # The input revision is preserved and can be retried after the snapshot is committed.
    assert len(ObjectiveInputStore(str(workdir / "objectives")).history("demo_objective")) == 1


def test_history_and_resume_cli_work_in_a_fresh_python_process(tmp_path, monkeypatch):
    repo = make_clean_repo(tmp_path / "repo")
    workdir = tmp_path / "cycles"
    import rdo.orchestrator as orchestrator
    monkeypatch.setattr(orchestrator, "_active_experiments", lambda _repo: [])
    raw = payload("cli_objective")
    submit_objective(raw, repo_dir=str(repo), workdir=str(workdir))

    # The child process re-opens the append-only input ledger and CycleStore from disk.
    project_root = Path(__file__).resolve().parents[2]
    resumed = subprocess.run(
        [sys.executable, "-m", "rdo", "resume", "--objective-id", "cli_objective",
         "--revision", "1", "--out", str(workdir)],
        cwd=str(project_root), capture_output=True, text=True, timeout=30,
    )
    assert resumed.returncode == 0, resumed.stderr
    restored = json.loads(resumed.stdout)
    assert restored["objective"]["original_text"] == raw["original_text"]
    assert restored["cycles"][0]["objective_input"]["revision"] == 1

    history = subprocess.run(
        [sys.executable, "-m", "rdo", "history", "--objective-id", "cli_objective",
         "--out", str(workdir)],
        cwd=str(project_root), capture_output=True, text=True, timeout=30,
    )
    assert history.returncode == 0, history.stderr
    parsed = json.loads(history.stdout)
    assert parsed["revisions"][0]["revision"] == 1


def test_stage7_real_objective_example_is_valid():
    project_root = Path(__file__).resolve().parents[2]
    objective_path = project_root / "rdo" / "objectives" / "stage7_real_objective.json"
    raw = json.loads(objective_path.read_text(encoding="utf-8"))
    record = validate_objective(raw)
    assert record["objective_id"] == "stage7-real-objective-record"
    assert record["scope"]["affected_paths"] == ["rdo/STAGE7_HANDOFF.md"]
    assert record["seed_obligations"][0]["key"] == "record-stage7-real-objective-run"
