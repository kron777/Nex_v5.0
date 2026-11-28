"""Raw-objective seed proposals remain competing, bound and inert until reviewed."""
import json

import pytest

from rdo_adapters.seed_proposals import SeedProposalError, SeedProposalStore


def _raw(revision=1, supersedes=None):
    return {
        "schema_version": "rdo.raw_objective.v1",
        "objective_id": "objective-alpha",
        "revision": revision,
        "supersedes_sha256": supersedes,
        "original_text": "Build a safe objective intake and review pathway.",
        "intent": "Create a traceable first-level development network.",
        "owner": "founder",
        "source": {"kind": "external_llm", "reference": "source:raw-idea-1"},
        "scope": {"in_scope": ["RDO intake and proposal review"], "affected_paths": ["rdo_adapters/seed_proposals.py"]},
        "constraints": ["No unreviewed planning cycle."],
        "exclusions": ["No runtime or deployment changes."],
        "assumptions": ["The objective can be represented by more than one seed graph."],
        "acceptance_criteria": [
            "A reviewer can compare competing seed interpretations.",
            "The selected seed graph retains evidence needs and provenance.",
        ],
        "reconciliation_signatures": {},
        "max_depth": 4,
    }


def _alternative(alt_id, prefix):
    return {
        "alternative_id": alt_id,
        "interpretation": f"{alt_id} treats the objective through a {prefix} decomposition.",
        "seed_obligations": [
            {
                "key": f"{prefix}.intake",
                "title": "Preserve raw objective input",
                "kind": "persistence",
                "classification": "necessary",
                "rationale": "The source request must remain recoverable.",
                "impact": "Without this, later decisions cannot be traced to the original request.",
                "evidence_needs": ["Inspect the immutable objective revision ledger."],
                "assumptions": ["The input can be stored as a canonical record."],
                "confidence": "inferred",
            },
            {
                "key": f"{prefix}.review",
                "title": "Review candidate interpretation",
                "kind": "human_review",
                "classification": "necessary",
                "rationale": "Competing interpretations require explicit selection.",
                "impact": "Without review, an inferred graph could be mistaken for the user's intent.",
                "evidence_needs": ["Verify the approval event binds the selected alternative."],
                "assumptions": [],
                "confidence": "inferred",
            },
        ],
        "relationships": [
            {
                "src": f"{prefix}.intake",
                "dst": f"{prefix}.review",
                "kind": "depends_on",
                "authority": "none",
                "reversible": True,
                "note": "Review follows preservation of the source objective.",
            }
        ],
        "reconciliation_signatures": {},
        "assumptions": ["The proposal remains advisory until approved."],
        "constraints": ["No executable code is accepted in the candidate payload."],
        "exclusions": ["No planning cycle is run during proposal creation."],
        "acceptance_criterion_coverage": [
            {
                "criterion_index": 0,
                "obligation_keys": [f"{prefix}.review"],
                "rationale": "The review obligation supports comparing alternatives.",
            },
            {
                "criterion_index": 1,
                "obligation_keys": [f"{prefix}.intake"],
                "rationale": "The intake obligation preserves lineage and evidence needs.",
            },
        ],
        "open_questions": ["Which interpretation best preserves the objective's intent?"],
        "disconfirming_cases": ["A simpler objective may not need a separate review subsystem."],
        "evidence_needs": ["Compare the candidate against existing objective intake and handoff code."],
    }


def _submit(store, raw=None):
    return store.submit(
        raw or _raw(),
        [_alternative("alternative-a", "alpha"), _alternative("alternative-b", "beta")],
        proposer_kind="external_llm",
        proposer_reference="provider-neutral model proposal",
        source_reference="source:proposal-1",
    )


def test_proposal_binds_multiple_seed_graphs_to_exact_raw_objective(tmp_path):
    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    item = _submit(store)
    proposal = item["proposal"]
    assert item["status"] == "candidate"
    assert len(proposal["alternatives"]) == 2
    assert proposal["raw_objective_sha256"]
    assert proposal["raw_objective"]["original_text"] == _raw()["original_text"]
    assert proposal["alternatives"][0]["acceptance_criterion_coverage"]
    assert proposal["alternatives"][0]["disconfirming_cases"]
    assert len(store.events()) == 1
    assert store.proposals() == [item]
    assert SeedProposalStore(str(tmp_path / "seed_proposals.jsonl")).get(
        proposal["proposal_id"]
    ) == item


def test_external_llm_seed_confidence_must_remain_inferred(tmp_path):
    alternatives = [_alternative("alternative-a", "alpha"),
                    _alternative("alternative-b", "beta")]
    alternatives[0]["seed_obligations"][0]["confidence"] = "stated"
    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    with pytest.raises(SeedProposalError, match="must remain inferred"):
        store.submit(_raw(), alternatives, proposer_kind="external_llm",
                     proposer_reference="model", source_reference="source:1")


def test_approval_must_select_exactly_one_existing_alternative(tmp_path):
    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    item = _submit(store)
    pid = item["proposal"]["proposal_id"]
    with pytest.raises(SeedProposalError, match="select one existing alternative"):
        store.review(pid, "approved", reviewer="founder", source_reference="review:1",
                     rationale="Choose a graph.", evidence_references=["review:evidence"])
    approved = store.review(
        pid, "approved", reviewer="founder", source_reference="review:2",
        rationale="The first graph is better supported.",
        evidence_references=["review:comparison"], selected_alternative_id="alternative-a",
    )
    selected = store.approved_selection(pid)
    assert approved["status"] == "approved"
    assert selected["selected_alternative_id"] == "alternative-a"
    assert selected["raw_objective_sha256"] == item["proposal"]["raw_objective_sha256"]
    assert selected["alternative"]["seed_obligations"][0]["key"] == "alpha.intake"


def test_unreviewed_or_rejected_proposal_cannot_yield_approved_selection(tmp_path):
    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    item = _submit(store)
    with pytest.raises(SeedProposalError, match="no explicit approval"):
        store.approved_selection(item["proposal"]["proposal_id"])
    store.review(item["proposal"]["proposal_id"], "rejected", reviewer="founder",
                 source_reference="review:reject", rationale="Insufficient evidence.",
                 evidence_references=["review:gap"])
    with pytest.raises(SeedProposalError, match="no explicit approval"):
        store.approved_selection(item["proposal"]["proposal_id"])


def test_review_cannot_be_replaced_and_revision_must_supersede_reviewed_predecessor(tmp_path):
    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    first = _submit(store)
    pid = first["proposal"]["proposal_id"]
    store.review(pid, "changes_requested", reviewer="founder",
                 source_reference="review:1", rationale="Clarify graph alternatives.",
                 evidence_references=["review:missing-contrast"])
    with pytest.raises(SeedProposalError, match="already has a review decision"):
        store.review(pid, "approved", reviewer="founder", source_reference="review:2",
                     rationale="Approve.", evidence_references=["review:approval"],
                     selected_alternative_id="alternative-a")
    revised = store.submit(
        _raw(), [_alternative("alternative-c", "gamma"),
                 _alternative("alternative-d", "delta")],
        proposer_kind="human", proposer_reference="engineer",
        source_reference="source:revision-2", supersedes_proposal_id=pid,
    )
    assert revised["proposal"]["supersedes_proposal_id"] == pid
    assert revised["status"] == "candidate"


def test_raw_objective_revision_hash_chain_is_enforced(tmp_path):
    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    _submit(store)
    raw2 = _raw(revision=2, supersedes="0" * 64)
    with pytest.raises(SeedProposalError, match="revision chain"):
        _submit(store, raw2)
    assert len(store.events()) == 1


def test_candidate_rejects_unknown_executable_fields_and_unbound_relationships(tmp_path):
    alternatives = [_alternative("alternative-a", "alpha"),
                    _alternative("alternative-b", "beta")]
    alternatives[0]["python_callable"] = "os.system"
    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    with pytest.raises(SeedProposalError, match="exactly the documented"):
        store.submit(_raw(), alternatives, proposer_kind="human",
                     proposer_reference="engineer", source_reference="source:bad")

    alternatives = [_alternative("alternative-a", "alpha"),
                    _alternative("alternative-b", "beta")]
    alternatives[0]["relationships"][0]["dst"] = "not-a-seed"
    with pytest.raises(SeedProposalError, match="connect declared seed keys"):
        store.submit(_raw(), alternatives, proposer_kind="human",
                     proposer_reference="engineer", source_reference="source:bad-edge")


def test_exact_submission_replay_is_idempotent(tmp_path):
    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    first = _submit(store)
    assert _submit(store) == first
    assert len(store.events()) == 1


def test_tampered_ledger_is_rejected(tmp_path):
    path = tmp_path / "seed_proposals.jsonl"
    store = SeedProposalStore(str(path))
    _submit(store)
    event = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    event["record"]["alternatives"][0]["interpretation"] = "tampered"
    path.write_text(json.dumps(event) + "\n", encoding="utf-8")
    with pytest.raises(SeedProposalError, match="digest mismatch"):
        store.events()


def test_seed_proposal_rejects_symlink_ledger(tmp_path):
    target = tmp_path / "target.jsonl"
    target.write_text("", encoding="utf-8")
    path = tmp_path / "seed_proposals.jsonl"
    path.symlink_to(target)
    with pytest.raises(SeedProposalError, match="must not be a symlink"):
        SeedProposalStore(str(path)).events()


def test_seed_proposal_rejects_dangling_symlink_ledger(tmp_path):
    path = tmp_path / "seed_proposals.jsonl"
    path.symlink_to(tmp_path / "missing-target.jsonl")
    with pytest.raises(SeedProposalError, match="must not be a symlink"):
        SeedProposalStore(str(path)).events()


def test_every_acceptance_criterion_has_an_explicit_coverage_record(tmp_path):
    alternatives = [_alternative("alternative-a", "alpha"),
                    _alternative("alternative-b", "beta")]
    alternatives[0]["acceptance_criterion_coverage"].pop()
    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    with pytest.raises(SeedProposalError, match="acceptance_criterion_coverage"):
        store.submit(_raw(), alternatives, proposer_kind="external_llm",
                     proposer_reference="model", source_reference="source:coverage-gap")


def test_acceptance_criterion_coverage_must_name_at_least_one_seed_obligation(tmp_path):
    alternatives = [_alternative("alternative-a", "alpha"),
                    _alternative("alternative-b", "beta")]
    alternatives[0]["acceptance_criterion_coverage"][0]["obligation_keys"] = []
    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    with pytest.raises(SeedProposalError, match="coverage.obligation_keys must not be empty"):
        store.submit(_raw(), alternatives, proposer_kind="external_llm",
                     proposer_reference="model", source_reference="source:empty-coverage")


def test_duplicate_seed_graphs_are_not_misrepresented_as_competing_alternatives(tmp_path):
    first = _alternative("alternative-a", "alpha")
    second = dict(first)
    second["alternative_id"] = "alternative-b"
    second["interpretation"] = "A different explanation but the exact same seed graph."
    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    with pytest.raises(SeedProposalError, match="distinct seed graphs"):
        store.submit(_raw(), [first, second], proposer_kind="external_llm",
                     proposer_reference="model", source_reference="source:duplicate-graph")


def test_human_authored_seed_proposal_can_mark_stated_confidence(tmp_path):
    raw = _raw()
    alternatives = [_alternative("alternative-a", "alpha"),
                    _alternative("alternative-b", "beta")]
    for alternative in alternatives:
        for seed in alternative["seed_obligations"]:
            seed["confidence"] = "stated"
    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    item = store.submit(raw, alternatives, proposer_kind="human",
                        proposer_reference="founder", source_reference="source:human-analysis")
    assert item["proposal"]["alternatives"][0]["seed_obligations"][0]["confidence"] == "stated"


def test_raw_objective_revision_two_must_link_to_previous_exact_digest(tmp_path):
    from rdo_adapters.seed_proposals import _digest, validate_raw_objective

    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    first = validate_raw_objective(_raw())
    _submit(store, first)
    second_raw = _raw(revision=2, supersedes=_digest(first))
    second_raw["constraints"] = ["A later revision adds an explicit constraint."]
    second = store.submit(
        second_raw, [_alternative("alternative-c", "gamma"),
                     _alternative("alternative-d", "delta")],
        proposer_kind="external_llm", proposer_reference="model",
        source_reference="source:raw-revision-2",
    )
    assert second["proposal"]["raw_objective"]["revision"] == 2


def test_ledger_append_refuses_to_exceed_byte_limit(tmp_path, monkeypatch):
    import rdo_adapters.seed_proposals as seed_module

    path = tmp_path / "seed_proposals.jsonl"
    monkeypatch.setattr(seed_module, "MAX_LEDGER_BYTES", 32)
    store = SeedProposalStore(str(path))
    with pytest.raises(SeedProposalError, match="byte limit"):
        _submit(store)
    assert path.read_text(encoding="utf-8") == ""


def test_invalid_raw_revision_is_rejected_before_it_can_poison_the_ledger(tmp_path):
    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    _submit(store)
    before = store.events()
    invalid = _raw(revision=2, supersedes="0" * 64)
    with pytest.raises(SeedProposalError, match="revision chain"):
        store.submit(
            invalid, [_alternative("alternative-c", "gamma"),
                      _alternative("alternative-d", "delta")],
            proposer_kind="external_llm", proposer_reference="model",
            source_reference="source:invalid-revision",
        )
    assert store.events() == before


def test_raw_objective_original_text_and_intent_cannot_be_rewritten(tmp_path):
    from rdo_adapters.seed_proposals import _digest, validate_raw_objective

    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    first = validate_raw_objective(_raw())
    _submit(store, first)
    changed = _raw(revision=2, supersedes=_digest(first))
    changed["original_text"] = "A different raw objective."
    with pytest.raises(SeedProposalError, match="original_text and intent are immutable"):
        store.submit(
            changed, [_alternative("alternative-c", "gamma"),
                      _alternative("alternative-d", "delta")],
            proposer_kind="external_llm", proposer_reference="model",
            source_reference="source:changed-raw-objective",
        )
    assert len(store.events()) == 1


def test_history_derives_seed_proposals_and_events_from_one_ledger_snapshot(tmp_path, monkeypatch):
    store = SeedProposalStore(str(tmp_path / "seed_proposals.jsonl"))
    submitted = _submit(store)
    proposal_id = submitted["proposal"]["proposal_id"]
    store.review(
        proposal_id,
        "changes_requested",
        reviewer="reviewer",
        source_reference="review:history-snapshot",
        rationale="Clarify one evidence gap before approval.",
        evidence_references=["review:evidence-gap"],
    )

    original_read = store._read_events
    read_count = 0

    def counted_read():
        nonlocal read_count
        read_count += 1
        return original_read()

    monkeypatch.setattr(store, "_read_events", counted_read)
    history = store.history(proposal_id)

    assert read_count == 1
    assert history["proposal_count"] == 1
    assert history["proposals"][0]["status"] == "changes_requested"
    assert [event["event_kind"] for event in history["events"]] == [
        "proposal_submitted", "review_decision"
    ]
