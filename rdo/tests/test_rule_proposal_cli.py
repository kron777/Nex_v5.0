"""CLI coverage for the inert novel expansion-rule proposal lifecycle."""
import json

from rdo import __main__ as cli


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
