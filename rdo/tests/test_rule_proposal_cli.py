"""CLI coverage for the inert novel expansion-rule proposal lifecycle."""
import json

from rdo import __main__ as cli
from rdo.extrapolator import EXPANSION_RULES, expand
from rdo.model import MISSING, Obligation


def test_rule_proposal_cli_routes_submit_review_and_history(tmp_path, monkeypatch, capsys):
    calls = []
    proposal_id = "ruleprop_" + "a" * 24

    class FakeStore:
        def __init__(self, path):
            calls.append(("path", path))

        def submit(self, request, candidate, **kwargs):
            calls.append(("submit", request, candidate, kwargs))
            return {"proposal": {"proposal_id": proposal_id}, "status": "candidate"}

        def review(self, pid, decision, **kwargs):
            calls.append(("review", pid, decision, kwargs))
            return {"proposal": {"proposal_id": pid}, "status": decision}

        def proposals(self):
            return [{"proposal": {"proposal_id": proposal_id}, "status": "approved_for_catalogue"}]

        def events(self):
            return [
                {"proposal_id": proposal_id, "event_kind": "proposal_submitted"},
                {"proposal_id": proposal_id, "event_kind": "review_decision"},
                {"proposal_id": "ruleprop_" + "b" * 24, "event_kind": "proposal_submitted"},
            ]

    monkeypatch.setattr(cli, "RuleProposalStore", FakeStore)
    payload = {
        "request": {"target_kind": "specialized_deployment"},
        "candidate": {"proposal_rationale": "candidate only"},
        "proposer_kind": "external_llm",
        "proposer_reference": "provider/model",
        "source_reference": "source:1",
    }
    input_path = tmp_path / "rule-proposal.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")
    out = str(tmp_path / "cycles")

    assert cli.main(["rule-propose", "--input", str(input_path), "--dir", out]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "candidate"
    submit = next(call for call in calls if call[0] == "submit")
    assert submit[1] == payload["request"]
    assert submit[2] == payload["candidate"]
    assert submit[3]["proposer_kind"] == "external_llm"

    assert cli.main([
        "rule-review", "--proposal-id", proposal_id,
        "--decision", "approved_for_catalogue", "--reviewer", "reviewer",
        "--source-reference", "review:1", "--rationale", "Candidate suitable for separate source review",
        "--evidence-reference", "positive:test", "--evidence-reference", "negative:test",
        "--dir", out,
    ]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "approved_for_catalogue"
    review = next(call for call in calls if call[0] == "review")
    assert review[1:3] == (proposal_id, "approved_for_catalogue")
    assert review[3]["evidence_references"] == ["positive:test", "negative:test"]

    assert cli.main(["rule-history", "--proposal-id", proposal_id, "--dir", out]) == 0
    history = json.loads(capsys.readouterr().out)
    assert history["proposal_count"] == 1
    assert len(history["events"]) == 2


def test_rule_propose_rejects_unknown_input_fields_before_store_access(tmp_path, monkeypatch, capsys):
    class ForbiddenStore:
        def __init__(self, path):
            raise AssertionError("invalid input must not open the proposal store")

    monkeypatch.setattr(cli, "RuleProposalStore", ForbiddenStore)
    path = tmp_path / "rule-proposal.json"
    path.write_text(json.dumps({"unexpected": True}), encoding="utf-8")
    assert cli.main(["rule-propose", "--input", str(path), "--dir", str(tmp_path)]) == 2
    assert "exactly the documented fields" in capsys.readouterr().err


def test_rule_propose_rejects_duplicate_json_keys_before_store_access(tmp_path, monkeypatch, capsys):
    class ForbiddenStore:
        def __init__(self, path):
            raise AssertionError("duplicate-key input must not open the proposal store")

    monkeypatch.setattr(cli, "RuleProposalStore", ForbiddenStore)
    path = tmp_path / "duplicate-rule-proposal.json"
    path.write_text('{"request": {}, "request": {}, "candidate": {}}', encoding="utf-8")
    assert cli.main(["rule-propose", "--input", str(path), "--dir", str(tmp_path)]) == 2
    assert "duplicate JSON property: request" in capsys.readouterr().err


def test_rule_proposal_cli_real_store_keeps_approval_inert(tmp_path, capsys):
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
    request = frontier[0]["rule_proposal_request"]
    candidate = {
        "proposal_rationale": "A staged deployment candidate requires preflight and rollback planning.",
        "decomposition_steps": [
            {"child_kind": "preflight_validation", "classification": "necessary",
             "rationale": "Validate target prerequisites.", "shared_target": None},
            {"child_kind": "rollback_plan", "classification": "necessary",
             "rationale": "Preserve a bounded recovery path.", "shared_target": None},
        ],
        "alternative_interpretations": ["Use an existing lifecycle rule with narrower scope."],
        "applicability": "Deployment work with an identified target environment.",
        "preconditions": ["The target environment is identified."],
        "constraints": ["No live deployment authority is implied."],
        "exceptions": ["Documentation-only work may not require an executable rollback."],
        "anti_requirements": ["Do not introduce a second deployment controller."],
        "assumptions": ["A rollback plan can be reviewed without execution."],
        "evidence_references": ["review:deployment-pattern"],
        "disconfirming_cases": ["Static documentation-only work may not need staged deployment."],
        "positive_tests": ["A deployment candidate includes preflight and rollback obligations."],
        "negative_tests": ["A documentation-only candidate does not authorize deployment."],
    }
    payload = {
        "request": request,
        "candidate": candidate,
        "proposer_kind": "external_llm",
        "proposer_reference": "fixture:provider",
        "source_reference": "fixture:frontier",
    }
    input_path = tmp_path / "rule-proposal.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")
    before = {key: list(value) for key, value in EXPANSION_RULES.items()}
    out = str(tmp_path / "cycles")

    assert cli.main(["rule-propose", "--input", str(input_path), "--dir", out]) == 0
    submitted = json.loads(capsys.readouterr().out)
    proposal_id = submitted["proposal"]["proposal_id"]
    assert submitted["status"] == "candidate"

    assert cli.main([
        "rule-review", "--proposal-id", proposal_id,
        "--decision", "approved_for_catalogue", "--reviewer", "reviewer",
        "--source-reference", "review:1", "--rationale", "Eligible for separate source review",
        "--evidence-reference", "evidence:positive", "--evidence-reference", "evidence:negative",
        "--dir", out,
    ]) == 0
    reviewed = json.loads(capsys.readouterr().out)
    assert reviewed["status"] == "approved_for_catalogue"
    assert EXPANSION_RULES == before

    assert cli.main(["rule-history", "--proposal-id", proposal_id, "--dir", out]) == 0
    history = json.loads(capsys.readouterr().out)
    assert history["proposal_count"] == 1
    assert [event["event_kind"] for event in history["events"]] == [
        "proposal_submitted", "review_decision"
    ]
