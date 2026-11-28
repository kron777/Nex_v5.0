"""Governed lifecycle for novel Extrapolator rule proposals."""
import json

import pytest

from rdo.extrapolator import expand
from rdo.model import MISSING, Obligation, Pattern
from rdo.memory import PatternMemory
from rdo.rule_proposals import RuleProposalStore


def _proposal(target="specialized_deployment"):
    return {
        "target_kind": target,
        "source_obligation": {
            "key": "deployment.specialized",
            "title": "specialized deployment mechanism",
            "kind": target,
            "rationale": "The objective requires a deployment-specific mechanism.",
            "evidence_needs": ["Identify the target deployment environment."],
        },
        "alternatives": [
            {
                "id": "environment_first",
                "description": "Establish environment constraints before deployment packaging.",
                "steps": [
                    {
                        "child_kind": "environment_check",
                        "classification": "necessary",
                        "rationale": "Deployment needs a verified target environment.",
                        "shared_target": None,
                    },
                    {
                        "child_kind": "rollback_plan",
                        "classification": "necessary",
                        "rationale": "A deployment needs a recoverable rollback path.",
                        "shared_target": None,
                    },
                ],
            },
            {
                "id": "package_first",
                "description": "Package the release before environment validation.",
                "steps": [
                    {
                        "child_kind": "release_package",
                        "classification": "necessary",
                        "rationale": "The release must be packaged.",
                        "shared_target": None,
                    }
                ],
            },
        ],
        "assumptions": ["The deployment target is supplied by the objective owner."],
        "applicability": ["Only deployment objectives with an identified target environment."],
        "preconditions": ["A target environment has been named."],
        "exceptions": ["Do not apply to documentation-only releases."],
        "anti_requirements": ["Do not deploy as a side effect of planning."],
        "evidence_needs": ["A source-backed target environment description."],
        "disconfirming_cases": ["A deployment objective with no controllable target environment."],
        "provenance": ["frontier:cycle-001:deployment.specialized"],
        "positive_tests": ["tests/test_deployment_rule.py::test_environment_first"],
        "negative_tests": ["tests/test_deployment_rule.py::test_docs_only_not_decomposed"],
    }


def _approve(store, proposal_id, decision="approved", alternative="environment_first"):
    return store.review(
        proposal_id, decision, "reviewer attribution", "review:rule-design-001",
        ["review:rule-contract-001"], selected_alternative=alternative,
        positive_test_evidence=["tests/test_deployment_rule.py::test_environment_first"],
        negative_test_evidence=["tests/test_deployment_rule.py::test_docs_only_not_decomposed"],
    )


def test_novel_kind_request_is_candidate_only_until_explicit_review(tmp_path):
    store = RuleProposalStore(str(tmp_path / "rule_proposals.jsonl"))
    seed = Obligation(
        "deployment.specialized", "specialized deployment", "specialized_deployment",
        rationale="A deployment-specific mechanism is required.",
        evidence_needs=["Identify the target environment."],
    )

    obligations, relationships, frontier = expand(
        [seed], reconcile_fn=lambda _ob: MISSING, max_depth=4
    )
    assert set(obligations) == {seed.key}
    assert relationships == []
    assert frontier[0]["frontier_type"] == "novel_kind_requires_rule_proposal"
    assert store.approved_catalogue() is None


def test_proposal_preserves_alternatives_and_does_not_activate_by_repetition(tmp_path):
    store = RuleProposalStore(str(tmp_path / "rule_proposals.jsonl"))
    created = store.propose(_proposal())
    proposal_id = created["data"]["proposal_id"]

    assert created["event_kind"] == "proposal_created"
    assert len(created["data"]["proposal"]["alternatives"]) == 2
    assert created["data"]["proposal"]["disconfirming_cases"]
    assert store.approved_catalogue() is None
    assert len(store.events()) == 1

    # Repeated learning observations remain PatternMemory evidence, not rule activation.
    memory = PatternMemory(str(tmp_path / "patterns.jsonl"))
    memory.add(Pattern("deployment", "deployment patterns recur", "cycle:1"))
    memory.add(Pattern("deployment", "deployment patterns recur", "cycle:2"))
    memory.add(Pattern("deployment", "deployment patterns recur", "cycle:3"))
    assert memory.patterns()[0].observed_count == 3
    assert store.approved_catalogue() is None


def test_approval_activates_only_selected_alternative_in_versioned_catalogue(tmp_path):
    store = RuleProposalStore(str(tmp_path / "rule_proposals.jsonl"))
    created = store.propose(_proposal())
    proposal_id = created["data"]["proposal_id"]

    with pytest.raises(ValueError, match="every declared positive test"):
        store.review(
            proposal_id, "approved", "reviewer", "review:1", ["review:evidence"],
            selected_alternative="environment_first",
            positive_test_evidence=["tests/other.py::test_unrelated"],
            negative_test_evidence=["tests/test_deployment_rule.py::test_docs_only_not_decomposed"],
        )

    approved = _approve(store, proposal_id)
    catalogue = store.approved_catalogue()

    assert approved["data"]["decision"] == "approved"
    assert approved["data"]["catalogue_version"] == 1
    assert catalogue.version == 1
    assert len(catalogue.sha256) == 64
    assert set(catalogue.rules) == {"specialized_deployment"}
    assert [step[0] for step in catalogue.rules["specialized_deployment"]] == [
        "environment_check", "rollback_plan"
    ]
    assert catalogue.provenance["specialized_deployment"]["alternative_id"] == "environment_first"
    assert catalogue.provenance["specialized_deployment"]["disconfirming_cases"] == [
        "A deployment objective with no controllable target environment."
    ]


def test_only_approved_catalogue_changes_recursive_expansion(tmp_path):
    store = RuleProposalStore(str(tmp_path / "rule_proposals.jsonl"))
    created = store.propose(_proposal())
    proposal_id = created["data"]["proposal_id"]
    seed = Obligation(
        "deployment.specialized", "specialized deployment", "specialized_deployment",
        rationale="A deployment-specific mechanism is required.",
    )

    before, _, before_frontier = expand(
        [seed], reconcile_fn=lambda _ob: MISSING, max_depth=2
    )
    assert set(before) == {seed.key}
    assert before_frontier[0]["frontier_type"] == "novel_kind_requires_rule_proposal"

    _approve(store, proposal_id)
    after, relationships, frontier = expand(
        [seed], reconcile_fn=lambda _ob: MISSING, max_depth=2,
        approved_catalogue=store.approved_catalogue(),
    )
    assert set(after) == {
        "deployment.specialized",
        "deployment.specialized.environment_check",
        "deployment.specialized.rollback_plan",
    }
    assert {(edge.src, edge.dst) for edge in relationships} == {
        ("deployment.specialized", "deployment.specialized.environment_check"),
        ("deployment.specialized", "deployment.specialized.rollback_plan"),
    }
    assert any("no expansion rule for kind 'environment_check'" in item["reason"]
               for item in frontier)


def test_rejected_or_changes_requested_proposals_never_enter_catalogue(tmp_path):
    store = RuleProposalStore(str(tmp_path / "rule_proposals.jsonl"))
    created = store.propose(_proposal())
    proposal_id = created["data"]["proposal_id"]

    store.review(proposal_id, "changes_requested", "reviewer", "review:changes",
                 ["review:missing-negative-case"], note="Add another disconfirming case.")
    assert store.approved_catalogue() is None
    store.review(proposal_id, "rejected", "reviewer", "review:reject",
                 ["review:scope-conflict"], note="This rule is too domain-specific.")
    assert store.approved_catalogue() is None
    with pytest.raises(ValueError, match="terminal"):
        _approve(store, proposal_id)


def test_approval_requires_existing_proposal_and_known_alternative(tmp_path):
    store = RuleProposalStore(str(tmp_path / "rule_proposals.jsonl"))
    with pytest.raises(ValueError, match="does not exist"):
        _approve(store, "rp_does_not_exist")

    created = store.propose(_proposal())
    with pytest.raises(ValueError, match="not part of this proposal"):
        _approve(store, created["data"]["proposal_id"], alternative="unknown")


def test_builtin_and_terminal_kinds_cannot_be_overridden(tmp_path):
    store = RuleProposalStore(str(tmp_path / "rule_proposals.jsonl"))
    with pytest.raises(ValueError, match="built-in"):
        store.propose(_proposal("persistence"))
    with pytest.raises(ValueError, match="built-in"):
        store.propose(_proposal("schema"))


def test_approved_rule_kind_cannot_be_approved_twice(tmp_path):
    store = RuleProposalStore(str(tmp_path / "rule_proposals.jsonl"))
    first = store.propose(_proposal())
    _approve(store, first["data"]["proposal_id"])
    second_payload = _proposal()
    second_payload["source_obligation"]["key"] = "deployment.specialized.second"
    second_payload["provenance"] = ["frontier:cycle-002:deployment.specialized"]
    second = store.propose(second_payload)

    with pytest.raises(ValueError, match="already has an approved rule"):
        _approve(store, second["data"]["proposal_id"])


def test_event_ledger_is_hash_chained_and_tampering_is_detected(tmp_path):
    path = tmp_path / "rule_proposals.jsonl"
    store = RuleProposalStore(str(path))
    created = store.propose(_proposal())
    _approve(store, created["data"]["proposal_id"])

    events = store.events()
    assert len(events) == 2
    assert events[0]["previous_event_sha256"] is None
    assert events[1]["previous_event_sha256"] == events[0]["event_sha256"]
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2

    lines = path.read_text(encoding="utf-8").splitlines()
    event = json.loads(lines[0])
    event["data"]["proposal"]["assumptions"] = ["tampered"]
    lines[0] = json.dumps(event)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="digest mismatch"):
        store.events()


def test_untrusted_catalogue_objects_and_conflicting_rules_fail_closed():
    from rdo.rule_proposals import ApprovedRuleCatalogue

    seed = Obligation("x", "novel", "new_kind")
    with pytest.raises(ValueError, match="must come from"):
        expand([seed], approved_catalogue={"new_kind": []})
    forged = ApprovedRuleCatalogue(
        version=1, sha256="not-a-digest",
        rules={"new_kind": [("child", "necessary", "reason", None)]},
        provenance={},
    )
    with pytest.raises(ValueError, match="invalid version or digest"):
        expand([seed], approved_catalogue=forged)



def test_cycle_persists_the_exact_approved_catalogue_used_for_expansion(tmp_path):
    from rdo.memory import CycleStore
    from rdo.orchestrator import run_cycle

    store = RuleProposalStore(str(tmp_path / "rule_proposals.jsonl"))
    created = store.propose(_proposal())
    _approve(store, created["data"]["proposal_id"])
    catalogue = store.approved_catalogue()
    seed = Obligation(
        "deployment.specialized", "specialized deployment", "specialized_deployment",
        rationale="A deployment-specific mechanism is required.",
    )

    cycle, _ = run_cycle(
        "approved-rule-cycle", "specialized deployment", [], [seed], {},
        repo_dir=str(tmp_path), active_experiments=[], authorised_gates=set(),
        approved_catalogue=catalogue,
    )
    assert cycle.rule_catalogue["version"] == catalogue.version
    assert cycle.rule_catalogue["sha256"] == catalogue.sha256
    assert "specialized_deployment" in cycle.rule_catalogue["rules"]

    cycles = CycleStore(str(tmp_path / "cycles"))
    cycles.save(cycle)
    resumed = cycles.load(cycle.id)
    assert resumed.rule_catalogue == cycle.rule_catalogue



def test_changes_requested_proposal_can_be_approved_with_next_catalogue_version(tmp_path):
    store = RuleProposalStore(str(tmp_path / "rule_proposals.jsonl"))
    created = store.propose(_proposal())
    proposal_id = created["data"]["proposal_id"]
    store.review(
        proposal_id, "changes_requested", "reviewer", "review:changes",
        ["review:clarify-exception"], note="Clarify the applicability boundary.",
    )
    approved = _approve(store, proposal_id)
    assert approved["data"]["catalogue_version"] == 1
    assert store.approved_catalogue().version == 1


def test_mutated_approved_catalogue_is_rejected_by_digest_validation(tmp_path):
    store = RuleProposalStore(str(tmp_path / "rule_proposals.jsonl"))
    created = store.propose(_proposal())
    _approve(store, created["data"]["proposal_id"])
    catalogue = store.approved_catalogue()
    catalogue.rules["specialized_deployment"][0] = (
        "malicious_child", "necessary", "unreviewed step", None
    )
    seed = Obligation("deployment.specialized", "specialized deployment",
                      "specialized_deployment")
    with pytest.raises(ValueError, match="digest mismatch"):
        expand([seed], approved_catalogue=catalogue)
