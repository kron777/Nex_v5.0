"""Novel expansion-rule proposals remain inert, versioned and reviewable."""
import json

import pytest

from rdo.extrapolator import EXPANSION_RULES, expand
from rdo.model import MISSING, Obligation
from rdo_adapters.rule_proposals import RuleProposalError, RuleProposalStore


def _request():
    source = Obligation(
        "deployment.specialized",
        "specialized deployment mechanism",
        "specialized_deployment",
        rationale="A deployment-specific mechanism may be required.",
        evidence_needs=["Identify deployment environment and constraints."],
    )
    _, _, frontier = expand(
        [source], reconcile_fn=lambda _ob: MISSING, max_depth=4
    )
    return frontier[0]["rule_proposal_request"]


def _candidate():
    return {
        "proposal_rationale": "A specialised deployment rule may need staged preparation and rollback evidence.",
        "decomposition_steps": [
            {
                "child_kind": "preflight_validation",
                "classification": "necessary",
                "rationale": "Validate the target and prerequisites before deployment.",
                "shared_target": None,
            },
            {
                "child_kind": "rollback_plan",
                "classification": "necessary",
                "rationale": "A bounded rollback path is required for reversible delivery.",
                "shared_target": None,
            },
        ],
        "alternative_interpretations": [
            "Treat deployment as a lifecycle pattern rather than a specialised engineering kind."
        ],
        "applicability": "Only deployment work with an identified target environment.",
        "preconditions": ["The target environment is explicitly identified."],
        "constraints": ["No live deployment authority is implied."],
        "exceptions": ["Documentation-only deployment planning may not require rollback execution."],
        "anti_requirements": ["Do not introduce a second deployment controller."],
        "assumptions": ["A rollback plan can be reviewed without executing it."],
        "evidence_references": ["review:deployment-pattern-analysis"],
        "disconfirming_cases": ["A static documentation-only task may not need staged deployment."],
        "positive_tests": ["A deployment seed expands into preflight and rollback obligations."],
        "negative_tests": ["A documentation-only seed does not activate a live deployment action."],
    }


def _submit(store):
    return store.submit(
        _request(), _candidate(),
        proposer_kind="external_llm",
        proposer_reference="provider-neutral proposal fixture",
        source_reference="fixture:novel-kind-frontier",
    )


def test_novel_rule_proposal_is_persisted_as_inert_candidate(tmp_path):
    store = RuleProposalStore(str(tmp_path / "rule_proposals.jsonl"))
    item = _submit(store)

    assert item["status"] == "candidate"
    proposal = item["proposal"]
    assert proposal["target_kind"] == "specialized_deployment"
    assert proposal["source_request_sha256"]
    assert proposal["catalogue_digest"] == _request()["catalogue_digest"]
    assert proposal["alternative_interpretations"]
    assert proposal["disconfirming_cases"]
    assert proposal["positive_tests"] and proposal["negative_tests"]
    assert proposal["proposer_kind"] == "external_llm"
    assert proposal["supersedes_proposal_id"] is None

    reopened = RuleProposalStore(str(tmp_path / "rule_proposals.jsonl"))
    assert reopened.get(proposal["proposal_id"]) == item
    assert len(reopened.events()) == 1


def test_approved_for_catalogue_does_not_activate_or_change_expansion_rules(tmp_path):
    before = {key: list(value) for key, value in EXPANSION_RULES.items()}
    store = RuleProposalStore(str(tmp_path / "rule_proposals.jsonl"))
    candidate = _submit(store)
    reviewed = store.review(
        candidate["proposal"]["proposal_id"],
        "approved_for_catalogue",
        reviewer="independent reviewer",
        source_reference="review:rule-catalogue",
        rationale="The decomposition is sufficiently bounded for a separate source review.",
        evidence_references=["review:positive-case", "review:negative-case"],
    )

    assert reviewed["status"] == "approved_for_catalogue"
    assert EXPANSION_RULES == before
    assert not hasattr(store, "activate")

    source = Obligation("still.novel", "still novel", "still_novel_kind")
    _, _, frontier = expand(
        [source], reconcile_fn=lambda _ob: MISSING, max_depth=4
    )
    assert len(frontier) == 1
    assert frontier[0]["frontier_type"] == "novel_kind_requires_rule_proposal"


def test_request_from_changed_rule_catalogue_is_rejected_as_stale(tmp_path, monkeypatch):
    import rdo.extrapolator as extrapolator

    request = _request()
    existing = list(extrapolator.EXPANSION_RULES["persistence"])
    monkeypatch.setitem(
        extrapolator.EXPANSION_RULES,
        "persistence",
        existing + [("audit_marker", "necessary", "catalogue changed", None)],
    )
    store = RuleProposalStore(str(tmp_path / "rule_proposals.jsonl"))
    with pytest.raises(RuleProposalError, match="different catalogue"):
        store.submit(
            request, _candidate(),
            proposer_kind="human",
            proposer_reference="reviewer",
            source_reference="fixture:stale-request",
        )


def test_candidate_requires_positive_and_negative_tests_and_disconfirmations_field(tmp_path):
    candidate = _candidate()
    candidate["negative_tests"] = []
    store = RuleProposalStore(str(tmp_path / "rule_proposals.jsonl"))
    with pytest.raises(RuleProposalError, match="negative_tests must not be empty"):
        store.submit(
            _request(), candidate,
            proposer_kind="human",
            proposer_reference="engineer",
            source_reference="fixture:missing-negative-test",
        )


def test_candidate_rejects_executable_or_unknown_fields(tmp_path):
    candidate = _candidate()
    candidate["python_callable"] = "os.system"
    store = RuleProposalStore(str(tmp_path / "rule_proposals.jsonl"))
    with pytest.raises(RuleProposalError, match="exactly the documented"):
        store.submit(
            _request(), candidate,
            proposer_kind="external_llm",
            proposer_reference="model",
            source_reference="fixture:code-field",
        )


def test_exact_submission_replay_is_idempotent(tmp_path):
    store = RuleProposalStore(str(tmp_path / "rule_proposals.jsonl"))
    first = _submit(store)
    replay = _submit(store)
    assert replay == first
    assert len(store.events()) == 1


def test_review_is_append_only_and_cannot_be_replaced(tmp_path):
    store = RuleProposalStore(str(tmp_path / "rule_proposals.jsonl"))
    candidate = _submit(store)
    pid = candidate["proposal"]["proposal_id"]
    store.review(
        pid, "changes_requested", reviewer="reviewer",
        source_reference="review:1", rationale="Clarify the applicability boundary.",
        evidence_references=["review:scope-question"],
    )
    with pytest.raises(RuleProposalError, match="already has a review decision"):
        store.review(
            pid, "approved_for_catalogue", reviewer="reviewer",
            source_reference="review:2", rationale="Now approved.",
            evidence_references=["review:approval"],
        )
    assert store.get(pid)["status"] == "changes_requested"
    assert [event["event_kind"] for event in store.events()] == [
        "proposal_submitted", "review_decision"
    ]


def test_revised_candidate_links_to_changes_requested_predecessor(tmp_path):
    store = RuleProposalStore(str(tmp_path / "rule_proposals.jsonl"))
    first = _submit(store)
    prior_id = first["proposal"]["proposal_id"]
    store.review(
        prior_id, "changes_requested", reviewer="reviewer",
        source_reference="review:1", rationale="Add a clearer negative case.",
        evidence_references=["review:negative-case-gap"],
    )
    revised = store.submit(
        _request(), _candidate(),
        proposer_kind="human",
        proposer_reference="engineer",
        source_reference="fixture:revision-2",
        supersedes_proposal_id=prior_id,
    )
    assert revised["status"] == "candidate"
    assert revised["proposal"]["supersedes_proposal_id"] == prior_id
    assert revised["proposal"]["proposal_id"] != prior_id


def test_tampered_proposal_ledger_fails_closed(tmp_path):
    path = tmp_path / "rule_proposals.jsonl"
    store = RuleProposalStore(str(path))
    _submit(store)
    events = path.read_text(encoding="utf-8").splitlines()
    event = json.loads(events[0])
    event["record"]["proposal_rationale"] = "tampered"
    events[0] = json.dumps(event, sort_keys=True)
    path.write_text("\n".join(events) + "\n", encoding="utf-8")

    with pytest.raises(RuleProposalError, match="digest mismatch"):
        store.proposals()


def test_dangling_symlink_is_not_treated_as_an_empty_rule_ledger(tmp_path):
    target = tmp_path / "missing-target.jsonl"
    ledger = tmp_path / "rule_proposals.jsonl"
    ledger.symlink_to(target)
    store = RuleProposalStore(str(ledger))

    with pytest.raises(RuleProposalError, match="must not be a symlink"):
        store.events()
    with pytest.raises(RuleProposalError, match="must not be a symlink"):
        store.proposals()


def test_proposal_request_schema_and_catalogue_fingerprint_are_required(tmp_path):
    request = _request()
    request["schema_version"] = 1
    store = RuleProposalStore(str(tmp_path / "rule_proposals.jsonl"))
    with pytest.raises(RuleProposalError, match="schema"):
        store.submit(
            request, _candidate(),
            proposer_kind="human",
            proposer_reference="engineer",
            source_reference="fixture:old-schema",
        )
