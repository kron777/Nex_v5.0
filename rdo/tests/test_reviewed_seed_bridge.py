"""Reviewed seed selection prepares objective.v1 without persistence or execution."""
import hashlib
import json

import pytest

from rdo_adapters.objective_intake import ObjectiveInputStore
from rdo_adapters.reviewed_seed_bridge import (
    ReviewedSeedBridgeError,
    prepare_reviewed_selection,
)
from rdo_adapters.seed_proposals import SeedProposalError, SeedProposalStore


def _digest(value):
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def _raw(revision=1, supersedes=None):
    return {
        "schema_version": "rdo.raw_objective.v1",
        "objective_id": "bridge-objective",
        "revision": revision,
        "supersedes_sha256": supersedes,
        "original_text": "Preserve this exact request wording.",
        "intent": "Prepare a reviewed development network without executing it.",
        "owner": "founder",
        "source": {"kind": "human", "reference": "founder:request-1"},
        "scope": {
            "in_scope": ["reviewed objective intake"],
            "affected_paths": ["rdo_adapters/seed_proposals.py"],
        },
        "constraints": ["raw constraint"],
        "exclusions": ["raw exclusion"],
        "assumptions": ["raw assumption"],
        "acceptance_criteria": ["Every selected seed has traceable provenance."],
        "reconciliation_signatures": {
            "raw.context": [{
                "pattern": "raw context signature",
                "path": "rdo/README.md",
                "label": "raw-only signature",
            }]
        },
        "max_depth": 3,
    }


def _seed(key):
    return {
        "key": key,
        "title": f"Obligation {key}",
        "kind": "capability",
        "classification": "necessary",
        "rationale": "The selected objective interpretation requires this obligation.",
        "impact": "Omitting it would leave the candidate network incomplete.",
        "evidence_needs": ["Inspect the relevant source and test evidence."],
        "assumptions": [],
        "confidence": "inferred",
    }


def _edge(src, dst, kind):
    return {
        "src": src,
        "dst": dst,
        "kind": kind,
        "authority": "none",
        "reversible": True,
        "note": "Candidate relationship only.",
    }


def _alternative(alt_id, prefix, edges=None, count=2):
    seeds = [_seed(f"{prefix}.{i}") for i in range(count)]
    return {
        "alternative_id": alt_id,
        "interpretation": f"{alt_id} is a distinct {prefix} interpretation.",
        "seed_obligations": seeds,
        "relationships": edges or [],
        "reconciliation_signatures": {
            seeds[0]["key"]: [{
                "pattern": "selected seed signature",
                "path": "rdo/README.md",
                "label": "selected-only signature",
            }]
        },
        "assumptions": ["candidate assumption"],
        "constraints": ["candidate constraint"],
        "exclusions": ["candidate exclusion"],
        "acceptance_criterion_coverage": [{
            "criterion_index": 0,
            "obligation_keys": [seeds[0]["key"]],
            "rationale": "The first selected seed supports the criterion.",
        }],
        "open_questions": ["Does repository evidence support this decomposition?"],
        "disconfirming_cases": ["A simpler decomposition may be sufficient."],
        "evidence_needs": ["Reconcile every selected obligation against current source."],
    }


def _approved_store(tmp_path, raw=None, selected="alternative-a", alt_a=None):
    store = SeedProposalStore(str(tmp_path / "seed-proposals.jsonl"))
    raw = raw or _raw()
    alt_a = alt_a or _alternative("alternative-a", "alpha")
    alt_b = _alternative("alternative-b", "beta")
    submitted = store.submit(
        raw, [alt_a, alt_b],
        proposer_kind="external_llm",
        proposer_reference="provider-neutral proposal",
        source_reference="proposal-source:1",
    )
    proposal_id = submitted["proposal"]["proposal_id"]
    store.review(
        proposal_id, "approved",
        reviewer="founder",
        source_reference="review:1",
        rationale="Selected after comparing the competing interpretations.",
        evidence_references=["review-evidence:1"],
        selected_alternative_id=selected,
    )
    return store, proposal_id


def test_unreviewed_candidate_cannot_cross_the_bridge(tmp_path):
    store = SeedProposalStore(str(tmp_path / "seed-proposals.jsonl"))
    submitted = store.submit(
        _raw(),
        [_alternative("alternative-a", "alpha"),
         _alternative("alternative-b", "beta")],
        proposer_kind="external_llm",
        proposer_reference="provider-neutral proposal",
        source_reference="proposal-source:1",
    )
    intake = ObjectiveInputStore(str(tmp_path / "objectives"))
    with pytest.raises(SeedProposalError, match="explicit approval"):
        prepare_reviewed_selection(
            store, submitted["proposal"]["proposal_id"], intake
        )
    assert intake.history("bridge-objective") == []


def test_approved_selection_maps_to_valid_objective_and_preserves_both_lineages(tmp_path):
    edges = [
        _edge("alpha.0", "alpha.1", "depends_on"),
        _edge("alpha.1", "alpha.0", "depends_on"),
    ]
    store, proposal_id = _approved_store(
        tmp_path,
        alt_a=_alternative("alternative-a", "alpha", edges=edges),
    )
    intake = ObjectiveInputStore(str(tmp_path / "objectives"))
    result = prepare_reviewed_selection(store, proposal_id, intake)

    objective = result["objective"]
    lineage = result["lineage"]
    assert result["status"] == "prepared_for_intake_review"
    assert result["persisted"] is False
    assert result["planning_started"] is False
    assert result["stage7_handoff_created"] is False
    assert objective["schema_version"] == "rdo.objective.v1"
    assert objective["original_text"] == _raw()["original_text"]
    assert objective["intent"] == _raw()["intent"]
    assert objective["source"] == _raw()["source"]
    assert objective["constraints"] == ["raw constraint", "candidate constraint"]
    assert objective["assumptions"] == ["raw assumption", "candidate assumption"]
    assert all(seed["confidence"] == "inferred" for seed in objective["seed_obligations"])
    assert "raw.context" not in objective["reconciliation_signatures"]
    assert "alpha.0" in objective["reconciliation_signatures"]
    assert lineage["raw_objective_sha256"] != lineage["objective_input_sha256"]
    assert lineage["proposal_id"] == proposal_id
    assert lineage["selected_alternative_id"] == "alternative-a"
    assert lineage["approval"]["sequence"] == 2
    assert lineage["approval"]["event_sha256"]
    assert lineage["acceptance_criterion_coverage"]
    assert result["graph_analysis"]["status"] == "complete"
    assert result["graph_analysis"]["classified_cycles"][0]["classification"] == "prerequisite_cycle"
    system = result["graph_analysis"]["system_assessments"]
    assert any(item["subject"] == "feedback_cycles" and item["verdict"] == "underdeveloped"
               for item in system)
    assert intake.history("bridge-objective") == []


def test_influence_cycle_is_reported_as_feedback_not_a_build_order_defect(tmp_path):
    edges = [
        _edge("alpha.0", "alpha.1", "depends_on"),
        _edge("alpha.1", "alpha.0", "influences"),
    ]
    store, proposal_id = _approved_store(
        tmp_path,
        alt_a=_alternative("alternative-a", "alpha", edges=edges),
    )
    intake = ObjectiveInputStore(str(tmp_path / "objectives"))
    result = prepare_reviewed_selection(store, proposal_id, intake)
    assert result["graph_analysis"]["classified_cycles"][0]["classification"] == "feedback_loop"
    feedback = next(
        item for item in result["graph_analysis"]["system_assessments"]
        if item["subject"] == "feedback_cycles"
    )
    assert feedback["verdict"] == "unknown"


def test_large_cyclic_component_is_left_unknown_without_enumeration(tmp_path):
    count = 8
    keys = [f"large.{i}" for i in range(count)]
    seeds = [_seed(key) for key in keys]
    edges = [
        _edge(keys[i], keys[(i + 1) % count], "depends_on")
        for i in range(count)
    ]
    large = {
        "alternative_id": "alternative-a",
        "interpretation": "A larger cyclic interpretation.",
        "seed_obligations": seeds,
        "relationships": edges,
        "reconciliation_signatures": {},
        "assumptions": [],
        "constraints": [],
        "exclusions": [],
        "acceptance_criterion_coverage": [{
            "criterion_index": 0,
            "obligation_keys": [keys[0]],
            "rationale": "The first obligation supports the criterion.",
        }],
        "open_questions": ["Can the large cycle be decomposed?"],
        "disconfirming_cases": ["The apparent cycle may be an incomplete dependency model."],
        "evidence_needs": ["Inspect every edge."],
    }
    store, proposal_id = _approved_store(tmp_path, alt_a=large)
    result = prepare_reviewed_selection(
        store, proposal_id, ObjectiveInputStore(str(tmp_path / "objectives"))
    )
    graph = result["graph_analysis"]
    assert graph["status"] == "bounded_unknown"
    assert graph["scc_components"][0]["size"] == 8
    assert graph["scc_components"][0]["enumeration"] == "skipped_unknown"
    assert graph["classified_cycles"] == []
    assert graph["system_assessments"] == []


def test_intake_revision_chain_uses_intake_digest_not_raw_digest(tmp_path):
    store, proposal_id = _approved_store(tmp_path)
    intake = ObjectiveInputStore(str(tmp_path / "objectives"))
    first = prepare_reviewed_selection(store, proposal_id, intake)
    stored_first = intake.append(first["objective"])
    assert stored_first["sha256"] == first["objective_input_sha256"]

    raw_one_digest = _digest(_raw())
    raw_two = _raw(revision=2, supersedes=raw_one_digest)
    raw_two["constraints"] = ["raw constraint", "new raw constraint"]
    submitted = store.submit(
        raw_two,
        [_alternative("alternative-a", "alpha"),
         _alternative("alternative-b", "beta")],
        proposer_kind="external_llm",
        proposer_reference="provider-neutral proposal revision 2",
        source_reference="proposal-source:2",
    )
    second_id = submitted["proposal"]["proposal_id"]
    store.review(
        second_id, "approved",
        reviewer="founder",
        source_reference="review:2",
        rationale="Approved the revised raw objective interpretation.",
        evidence_references=["review-evidence:2"],
        selected_alternative_id="alternative-a",
    )
    second = prepare_reviewed_selection(store, second_id, intake)
    assert second["objective"]["revision"] == 2
    assert second["objective"]["supersedes_sha256"] == stored_first["sha256"]
    assert second["objective"]["supersedes_sha256"] != raw_two["supersedes_sha256"]
    assert second["lineage"]["raw_objective_supersedes_sha256"] == raw_one_digest
    assert second["lineage"]["objective_supersedes_sha256"] == stored_first["sha256"]


def test_existing_intake_chain_rejects_changed_immutable_intent(tmp_path):
    store, proposal_id = _approved_store(tmp_path)
    intake = ObjectiveInputStore(str(tmp_path / "objectives"))
    first = prepare_reviewed_selection(store, proposal_id, intake)
    intake.append(first["objective"])

    raw_changed = _raw(revision=2, supersedes=first["lineage"]["raw_objective_sha256"])
    raw_changed["intent"] = "A different intent must not reuse this objective ID."
    changed_store = SeedProposalStore(str(tmp_path / "changed-seed-proposals.jsonl"))
    submitted = changed_store.submit(
        raw_changed,
        [_alternative("alternative-a", "alpha"),
         _alternative("alternative-b", "beta")],
        proposer_kind="external_llm",
        proposer_reference="provider-neutral proposal",
        source_reference="proposal-source:changed",
    )
    proposal_id_changed = submitted["proposal"]["proposal_id"]
    changed_store.review(
        proposal_id_changed, "approved",
        reviewer="founder",
        source_reference="review:changed",
        rationale="Test immutable intent guard.",
        evidence_references=["review-evidence:changed"],
        selected_alternative_id="alternative-a",
    )
    with pytest.raises(ReviewedSeedBridgeError, match="original_text/intent"):
        prepare_reviewed_selection(changed_store, proposal_id_changed, intake)
