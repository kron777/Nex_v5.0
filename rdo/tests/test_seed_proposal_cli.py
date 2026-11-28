"""CLI coverage for the candidate-only seed proposal lifecycle."""
import json
import os

from rdo import __main__ as cli


def test_seed_proposal_cli_routes_submit_review_history_and_selection(tmp_path, monkeypatch, capsys):
    calls = []
    proposal_id = "seedprop_" + "a" * 24
    approved = {"proposal_id": proposal_id, "selected_alternative_id": "alt-a"}

    class FakeStore:
        def __init__(self, path):
            calls.append(("path", path))

        def submit(self, raw, alternatives, **kwargs):
            calls.append(("submit", raw, alternatives, kwargs))
            return {"proposal": {"proposal_id": proposal_id}, "status": "candidate"}

        def review(self, pid, decision, **kwargs):
            calls.append(("review", pid, decision, kwargs))
            return {"proposal": {"proposal_id": pid}, "status": decision}

        def history(self, requested_id=None):
            assert requested_id in (None, proposal_id)
            return {
                "proposal_count": 1,
                "proposals": [
                    {"proposal": {"proposal_id": proposal_id}, "status": "approved"}
                ],
                "events": [
                    {"proposal_id": proposal_id, "event_kind": "proposal_submitted"},
                    {"proposal_id": proposal_id, "event_kind": "review_decision"},
                ],
            }

        def approved_selection(self, pid):
            calls.append(("selection", pid))
            return approved

    monkeypatch.setattr(cli, "SeedProposalStore", FakeStore)
    payload = {
        "raw_objective": {"objective_id": "demo"},
        "alternatives": [{"alternative_id": "alt-a"}, {"alternative_id": "alt-b"}],
        "proposer_kind": "external_llm",
        "proposer_reference": "provider/model",
        "source_reference": "source:1",
    }
    input_path = tmp_path / "proposal.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")
    out = str(tmp_path / "cycles")

    assert cli.main(["seed-propose", "--input", str(input_path), "--dir", out]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "candidate"
    submit_call = next(item for item in calls if item[0] == "submit")
    assert submit_call[1] == payload["raw_objective"]
    assert submit_call[2] == payload["alternatives"]
    assert submit_call[3]["proposer_kind"] == "external_llm"

    assert cli.main([
        "seed-review", "--proposal-id", proposal_id, "--decision", "approved",
        "--selected-alternative-id", "alt-a", "--reviewer", "founder",
        "--source-reference", "review:1", "--rationale", "Evidence reviewed",
        "--evidence-reference", "evidence:one", "--dir", out,
    ]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "approved"
    review_call = next(item for item in calls if item[0] == "review")
    assert review_call[1:3] == (proposal_id, "approved")
    assert review_call[3]["selected_alternative_id"] == "alt-a"
    assert review_call[3]["evidence_references"] == ["evidence:one"]

    assert cli.main(["seed-history", "--proposal-id", proposal_id, "--dir", out]) == 0
    history = json.loads(capsys.readouterr().out)
    assert history["proposal_count"] == 1
    assert len(history["events"]) == 2

    assert cli.main(["seed-selection", "--proposal-id", proposal_id, "--dir", out]) == 0
    assert json.loads(capsys.readouterr().out) == approved
    assert ("selection", proposal_id) in calls


def test_seed_propose_rejects_unknown_input_fields_before_store_access(tmp_path, monkeypatch, capsys):
    class ForbiddenStore:
        def __init__(self, path):
            raise AssertionError("invalid input must not open the proposal store")

    monkeypatch.setattr(cli, "SeedProposalStore", ForbiddenStore)
    path = tmp_path / "proposal.json"
    path.write_text(json.dumps({"unexpected": True}), encoding="utf-8")
    assert cli.main(["seed-propose", "--input", str(path), "--dir", str(tmp_path)]) == 2
    assert "exactly the documented fields" in capsys.readouterr().err


def test_seed_propose_rejects_duplicate_json_keys_before_store_access(tmp_path, monkeypatch, capsys):
    class ForbiddenStore:
        def __init__(self, path):
            raise AssertionError("duplicate-key input must not open the proposal store")

    monkeypatch.setattr(cli, "SeedProposalStore", ForbiddenStore)
    inputs = [
        (
            "duplicate-top-level.json",
            '{"raw_objective": {}, "raw_objective": {}, "alternatives": [], '
            '"proposer_kind": "external_llm", "proposer_reference": "provider/model", '
            '"source_reference": "source:1"}',
            "raw_objective",
        ),
        (
            "duplicate-nested.json",
            '{"raw_objective": {"objective_id": "first", "objective_id": "second"}, '
            '"alternatives": [], "proposer_kind": "external_llm", '
            '"proposer_reference": "provider/model", "source_reference": "source:1"}',
            "objective_id",
        ),
    ]
    for filename, content, duplicate_key in inputs:
        path = tmp_path / filename
        path.write_text(content, encoding="utf-8")
        assert cli.main([
            "seed-propose", "--input", str(path), "--dir", str(tmp_path)
        ]) == 2
        assert f"duplicate JSON property: {duplicate_key}" in capsys.readouterr().err



def test_seed_prepare_and_intake_cli_keep_read_only_and_persisted_paths_separate(tmp_path, monkeypatch, capsys):
    calls = []
    proposal_id = "seedprop_" + "c" * 24

    class FakeProposalStore:
        def __init__(self, path):
            calls.append(("proposal_store", path))

    class FakeObjectiveStore:
        def __init__(self, path):
            self.directory = path
            calls.append(("objective_store", path))

    monkeypatch.setattr(cli, "SeedProposalStore", FakeProposalStore)
    monkeypatch.setattr(cli, "ObjectiveInputStore", FakeObjectiveStore)
    monkeypatch.setattr(
        cli, "prepare_reviewed_selection",
        lambda proposal, pid, objective: (
            calls.append(("prepare", pid, objective.directory))
            or {"status": "prepared_for_intake_review", "persisted": False}
        ),
    )
    monkeypatch.setattr(
        cli, "submit_reviewed_selection",
        lambda proposal, pid, objective, repo_dir, workdir: (
            calls.append(("intake", pid, objective.directory, repo_dir, workdir))
            or {"status": "created", "proposal_id": pid}
        ),
    )
    out = str(tmp_path / "cycles")
    assert cli.main(["seed-prepare", "--proposal-id", proposal_id, "--dir", out]) == 0
    prepared = json.loads(capsys.readouterr().out)
    assert prepared["persisted"] is False
    assert any(call[0] == "prepare" for call in calls)

    assert cli.main([
        "seed-intake", "--proposal-id", proposal_id, "--repo", str(tmp_path),
        "--dir", out,
    ]) == 0
    intake = json.loads(capsys.readouterr().out)
    assert intake["status"] == "created"
    intake_call = next(call for call in calls if call[0] == "intake")
    assert intake_call[1:] == (
        proposal_id, os.path.join(out, "objectives"), str(tmp_path), out
    )
