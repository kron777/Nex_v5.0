import json
import subprocess
from pathlib import Path

import pytest

from rdo.model import CLASSIFICATIONS
from rdo_adapters.objective_intake import (
    ObjectiveInputError, ObjectiveInputStore, RAW_OBJECTIVE_SCHEMA_VERSION,
    submit_approved_seed_proposal, submit_objective, validate_raw_objective,
)
from rdo_adapters.seed_proposals import SeedProposalError, SeedProposalStore


def _raw(revision=1, supersedes=None):
    return {
        "schema_version": RAW_OBJECTIVE_SCHEMA_VERSION,
        "objective_id": "raw-idea-001",
        "raw_revision": revision,
        "supersedes_raw_sha256": supersedes,
        "original_text": "Build a safe, reproducible deployment workflow.",
        "intent": "Make deployments repeatable and recoverable.",
        "owner": "engineering",
        "source": {"kind": "external_llm", "reference": "provider:external"},
        "scope": {
            "in_scope": ["deployment pipeline"],
            "affected_paths": ["src/app.py"],
        },
        "constraints": ["preserve existing deployment contract"],
        "exclusions": ["no production deployment"],
        "assumptions": ["a staging environment exists"],
        "acceptance_criteria": [
            "deployments are reproducible",
            "rollback is recoverable",
        ],
        "max_depth": 2,
    }


def _alternative(alt_id="systems_first", title="Deployment pipeline"):
    return {
        "id": alt_id,
        "label": title,
        "interpretation": "Build the workflow around repeatability and recovery evidence.",
        "seed_obligations": [{
            "key": "deployment_pipeline",
            "title": "Implement a reproducible deployment pipeline",
            "kind": "implementation",
            "classification": CLASSIFICATIONS[0],
            "rationale": "The raw idea requires a repeatable deployment process.",
            "impact": "Deployment changes can be reviewed and repeated.",
            "evidence_needs": ["test:deployment-reproducibility"],
            "assumptions": ["staging is available"],
            "confidence": "inferred",
        }, {
            "key": "rollback_path",
            "title": "Define and verify a rollback path",
            "kind": "verification",
            "classification": CLASSIFICATIONS[0],
            "rationale": "The raw idea explicitly requires recovery.",
            "impact": "Failed deployments can be reversed safely.",
            "evidence_needs": ["test:rollback-recovery"],
            "assumptions": [],
            "confidence": "inferred",
        }],
        "relationships": [{
            "src": "rollback_path",
            "dst": "deployment_pipeline",
            "kind": "depends_on",
            "authority": "bounded",
            "reversible": None,
            "note": "Rollback verification depends on the deployment workflow.",
        }],
        "reconciliation_signatures": {},
        "assumptions": ["deployment credentials are provisioned outside RDO"],
        "evidence_needs": ["evidence:staging-run", "evidence:rollback-drill"],
        "acceptance_coverage": [
            {"criterion": "deployments are reproducible",
             "obligation_keys": ["deployment_pipeline"]},
            {"criterion": "rollback is recoverable",
             "obligation_keys": ["rollback_path"]},
        ],
        "open_questions": ["Which deployment platform will host the workflow?"],
        "disconfirming_cases": ["A reproducible run cannot be repeated from the same inputs."],
        "provenance": ["provider:external", "source:raw-idea-001"],
    }


def _submit(store, raw=None, alternatives=None, supersedes=None):
    return store.submit(
        raw or _raw(), alternatives or [_alternative()],
        "external_llm", "provider:external", "source:raw-idea-001",
        supersedes_proposal_id=supersedes,
    )


def test_raw_objective_accepts_unseeded_idea_and_rejects_seed_graph_fields():
    raw = validate_raw_objective(_raw())
    assert raw["schema_version"] == RAW_OBJECTIVE_SCHEMA_VERSION
    assert raw["objective_id"] == "raw-idea-001"
    assert "seed_obligations" not in raw
    invalid = _raw()
    invalid["seed_obligations"] = []
    with pytest.raises(ObjectiveInputError, match="unsupported fields"):
        validate_raw_objective(invalid)


def test_seed_proposal_remains_inert_until_explicit_review_selects_an_alternative(tmp_path):
    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    created = _submit(store)
    proposal_id = created["proposal_id"]
    assert store.list_proposals()[0]["status"] == "candidate"
    with pytest.raises(SeedProposalError, match="not explicitly approved"):
        store.approved_objective(proposal_id)

    store.review(
        proposal_id, "changes_requested", "reviewer", "review:seed-001",
        "Clarify the hosting boundary.", ["review:scope-question"],
    )
    with pytest.raises(SeedProposalError, match="not explicitly approved"):
        store.approved_objective(proposal_id)

    store.review(
        proposal_id, "approved", "reviewer", "review:seed-002",
        "Both acceptance criteria have explicit seed coverage.",
        ["review:coverage", "review:disconfirming-case"],
        selected_alternative_id="systems_first",
    )
    approved = store.approved_objective(proposal_id)
    assert approved["objective"]["schema_version"] == "rdo.objective.v1"
    assert len(approved["objective"]["seed_obligations"]) == 2
    assert approved["reference"]["selected_alternative_id"] == "systems_first"
    assert store.verify_reference(approved["reference"])["reference"] == approved["reference"]


def test_seed_proposal_requires_complete_acceptance_coverage_and_known_seed_keys(tmp_path):
    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    alt = _alternative()
    alt["acceptance_coverage"] = alt["acceptance_coverage"][:1]
    with pytest.raises(SeedProposalError, match="map every acceptance criterion"):
        _submit(store, alternatives=[alt])

    alt = _alternative()
    alt["acceptance_coverage"][0]["obligation_keys"] = ["missing_seed"]
    with pytest.raises(SeedProposalError, match="unknown seed keys"):
        _submit(store, alternatives=[alt])


def test_external_llm_seed_obligations_must_remain_inferred(tmp_path):
    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    alt = _alternative()
    alt["seed_obligations"][0]["confidence"] = "stated"
    with pytest.raises(ObjectiveInputError, match="must remain inferred"):
        _submit(store, alternatives=[alt])


def test_approval_requires_explicit_selection_and_traceable_review_evidence(tmp_path):
    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    proposal_id = _submit(store)["proposal_id"]
    with pytest.raises(SeedProposalError, match="explicitly select"):
        store.review(
            proposal_id, "approved", "reviewer", "review:approval",
            "Approve.", ["review:evidence"],
        )
    with pytest.raises(ObjectiveInputError, match="at least one item"):
        store.review(
            proposal_id, "changes_requested", "reviewer", "review:changes",
            "Need evidence.", [], 
        )


def test_superseding_a_candidate_invalidates_it_and_allows_a_revised_approval(tmp_path):
    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    first = _submit(store)
    store.review(
        first["proposal_id"], "changes_requested", "reviewer", "review:first",
        "Clarify the rollback evidence.", ["review:first-evidence"],
    )
    revised_alt = _alternative("recovery_first", "Recovery-first decomposition")
    revised_alt["interpretation"] = "Prioritise rollback proof before deployment automation."
    second = _submit(store, alternatives=[revised_alt], supersedes=first["proposal_id"])
    with pytest.raises(SeedProposalError, match="superseded"):
        store.approved_objective(first["proposal_id"])

    store.review(
        second["proposal_id"], "approved", "reviewer", "review:second",
        "The revised alternative has better failure recovery coverage.",
        ["review:revised-coverage"],
        selected_alternative_id="recovery_first",
    )
    approved = store.approved_objective(second["proposal_id"])
    assert approved["reference"]["selected_alternative_id"] == "recovery_first"
    assert store.list_proposals()[0]["status"] == "superseded"


def test_approved_seed_proposal_cannot_be_superseded_in_place(tmp_path):
    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    first = _submit(store)
    store.review(
        first["proposal_id"], "approved", "reviewer", "review:first",
        "Approve the first decomposition.", ["review:first-evidence"],
        selected_alternative_id="systems_first",
    )
    with pytest.raises(SeedProposalError, match="new raw revision"):
        _submit(store, alternatives=[_alternative("revised", "Revised")],
                supersedes=first["proposal_id"])


def test_raw_objective_revision_requires_exact_predecessor_digest(tmp_path):
    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    first = _submit(store)
    raw2 = _raw(revision=2, supersedes="0" * 64)
    with pytest.raises(SeedProposalError, match="preceding raw objective digest"):
        _submit(store, raw=raw2)


def test_valid_raw_objective_revision_cites_previous_raw_digest(tmp_path):
    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    first = _submit(store)
    raw2 = _raw(revision=2, supersedes=first["proposal"]["raw_objective_sha256"])
    raw2["assumptions"].append("a staging approval is required")
    second = _submit(store, raw=raw2)
    assert second["proposal"]["raw_objective"]["raw_revision"] == 2


def test_seed_proposal_ledger_detects_tampering(tmp_path):
    path = tmp_path / "seed_proposals.jsonl"
    store = SeedProposalStore(str(path))
    _submit(store)
    lines = path.read_text(encoding="utf-8").splitlines()
    event = json.loads(lines[0])
    event["record"]["raw_objective"]["intent"] = "tampered intent"
    lines[0] = json.dumps(event)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(SeedProposalError, match="digest mismatch"):
        store.events()


def test_identical_seed_proposal_submission_is_idempotent(tmp_path):
    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    first = _submit(store)
    second = _submit(store)
    assert first["proposal_id"] == second["proposal_id"]
    assert second["replayed"] is True
    assert len(store.events()) == 1



def _clean_repo(path: Path) -> Path:
    path.mkdir()
    (path / "src").mkdir()
    (path / "src" / "app.py").write_text("def deploy():\\n    return 'staging'\\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "RDO test"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "rdo-test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", "fixture snapshot"], check=True)
    return path


def _approved_proposal(workdir: Path) -> str:
    store = SeedProposalStore(str(workdir / "seed_proposals.jsonl"))
    proposal = _submit(store)
    store.review(
        proposal["proposal_id"], "approved", "reviewer", "review:seed-intake",
        "The selected graph covers both acceptance criteria.",
        ["review:coverage", "review:negative-case"],
        selected_alternative_id="systems_first",
    )
    return proposal["proposal_id"]


def test_seed_intake_runs_only_after_approval_and_preserves_cycle_lineage(tmp_path):
    workdir = tmp_path / "work"
    workdir.mkdir()
    repo = _clean_repo(tmp_path / "repo")
    proposal_id = _approved_proposal(workdir)

    result = submit_approved_seed_proposal(proposal_id, repo_dir=str(repo), workdir=str(workdir))
    cycle = result["cycle"]
    assert result["status"] == "created"
    assert cycle["objective_input"]["seed_proposal"]["proposal_id"] == proposal_id
    assert cycle["objective_input"]["seed_proposal"]["selected_alternative_id"] == "systems_first"
    history = ObjectiveInputStore(str(workdir / "objectives")).history("raw-idea-001")
    assert len(history) == 1
    assert history[0]["record"]["source"]["kind"] == "external_llm"

    # Repeating an approved intake reuses the same immutable revision and cycle.
    repeated = submit_approved_seed_proposal(proposal_id, repo_dir=str(repo), workdir=str(workdir))
    assert repeated["cycle"]["id"] == cycle["id"]
    assert len(ObjectiveInputStore(str(workdir / "objectives")).history("raw-idea-001")) == 1


def test_external_llm_objective_cannot_bypass_seed_proposal_review(tmp_path):
    raw = _raw()
    alternative = _alternative()
    objective = {
        "schema_version": "rdo.objective.v1",
        "objective_id": raw["objective_id"],
        "revision": 1,
        "supersedes_sha256": None,
        "original_text": raw["original_text"],
        "intent": raw["intent"],
        "owner": raw["owner"],
        "source": raw["source"],
        "scope": raw["scope"],
        "constraints": raw["constraints"],
        "exclusions": raw["exclusions"],
        "assumptions": raw["assumptions"] + alternative["assumptions"],
        "acceptance_criteria": raw["acceptance_criteria"],
        "seed_obligations": alternative["seed_obligations"],
        "relationships": alternative["relationships"],
        "reconciliation_signatures": alternative["reconciliation_signatures"],
        "max_depth": raw["max_depth"],
    }
    with pytest.raises(ObjectiveInputError, match="explicitly approved seed proposal"):
        submit_objective(objective, repo_dir=str(tmp_path), workdir=str(tmp_path / "work"))
