import json

import pytest

from rdo.model import CLASSIFICATIONS
from rdo_adapters.objective_intake import (
    ObjectiveInputError, RAW_OBJECTIVE_SCHEMA_VERSION, validate_raw_objective,
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
            "rationale": "Rollback verification depends on the deployment workflow.",
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


def test_superseding_a_seed_proposal_invalidates_its_prior_approval(tmp_path):
    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    first = _submit(store)
    store.review(
        first["proposal_id"], "approved", "reviewer", "review:first",
        "Approve the first decomposition.", ["review:first-evidence"],
        selected_alternative_id="systems_first",
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


def test_raw_objective_revision_requires_exact_predecessor_digest(tmp_path):
    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    first = _submit(store)
    raw2 = _raw(revision=2, supersedes="0" * 64)
    with pytest.raises(SeedProposalError, match="preceding raw objective digest"):
        _submit(store, raw=raw2)


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
