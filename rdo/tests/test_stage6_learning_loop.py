"""Stage 6 (RDO v1.3 §16) — learning loop.

Calibration over development evidence: predicted-vs-actual obligations and reuse, missed /
unnecessary / inappropriate-reuse tracking, reviewed-vs-automated provenance, reopening on new
evidence, explicit UNKNOWNs for incomplete/contradictory data, and anti-gaming (over-generation
never raises accuracy). Uses controlled fixtures plus the real RDO stage evidence.
"""
import json
import subprocess
import sys

from rdo.memory import (CycleStore, learning_loop, learning_provenance,
                        prediction_accuracy, record_actual, reopening_candidates,
                        transfer_observations)
from rdo.model import CycleRecord, EXECUTED_VERIFIED, NATIVE_PLANNING


def _cycle(cid, predicted_net_new, *, actual=None, kind=NATIVE_PLANNING, missing=None,
           obligations=None, frontier=None):
    c = CycleRecord(id=cid, objective=cid, kind=kind,
                    predicted={"net_new_count": predicted_net_new, "effort": predicted_net_new},
                    missing=list(missing or []), obligations=obligations or [],
                    frontier=frontier or [])
    if actual is not None:
        record_actual(c, actual)
    return c


# ----------------------------- prediction accuracy / anti-gaming -----------------------------

def test_over_generation_never_raises_accuracy():
    tight = _cycle("tight", 2, actual={"missed": [], "unnecessary": [], "reuse_wrong": [], "effort_actual": 2})
    inflated = _cycle("inflated", 10,
                      actual={"missed": [], "unnecessary": [f"x{i}" for i in range(8)], "reuse_wrong": [], "effort_actual": 10})
    a_tight = prediction_accuracy(tight)["accuracy"]
    a_inflated = prediction_accuracy(inflated)["accuracy"]
    assert a_tight == 1.0 and a_inflated < a_tight     # proposing unnecessary work LOWERS accuracy


def test_missed_obligations_lower_accuracy():
    c = _cycle("miss", 2, actual={"missed": ["m1"], "unnecessary": [], "reuse_wrong": [], "effort_actual": 2})
    acc = prediction_accuracy(c)
    assert acc["missed"] == 1 and acc["accuracy"] == round(2 / 3, 3)


def test_predicted_vs_actual_reuse_and_effort_tracked():
    c = _cycle("reuse", 2, actual={"missed": [], "unnecessary": [], "reuse_wrong": ["r1"],
                                   "effort_actual": 4})
    acc = prediction_accuracy(c)
    assert acc["inappropriate_reuse"] == 1 and acc["effort_error"] == 2.0   # 4 actual - 2 predicted


# --------------------------------- UNKNOWN / contradictory ----------------------------------

def test_no_actual_is_unknown_not_fabricated():
    c = _cycle("pending", 3)                            # no actual
    assert prediction_accuracy(c) is None
    loop = learning_loop([c])
    assert loop["per_cycle"][0]["outcome_status"] == "UNKNOWN (pending)"
    assert loop["mean_prediction_accuracy"] is None     # cannot average what is unknown


def test_contradictory_evidence_is_flagged():
    # the same obligation reported BOTH missed and unnecessary -> contradictory, surfaced not silenced
    c = _cycle("contra", 1, actual={"missed": ["z"], "unnecessary": ["z"], "reuse_wrong": [], "effort_actual": 1})
    loop = learning_loop([c])
    assert loop["per_cycle"][0]["contradictory_evidence"] == ["z"]


# ----------------------------- reviewed vs automated provenance -----------------------------

def test_reviewed_vs_automated_vs_executed_provenance():
    reviewed = _cycle("rev", 2, actual={"reviewer": "jon", "review_kind": "planning_review",
                                        "missed": [], "unnecessary": []})
    executed = _cycle("exe", 2, kind=EXECUTED_VERIFIED, actual={"missed": [], "unnecessary": []})
    selfass = _cycle("self", 2, actual={"missed": [], "unnecessary": []})
    pending = _cycle("pend", 2)
    fixture = _cycle("fixture", 2, actual={"reviewer": "fixture label",
                                           "review_kind": "controlled_fixture_review",
                                           "missed": [], "unnecessary": [], "reuse_wrong": []})
    assert learning_provenance(reviewed) == "reviewer_attributed:planning_review"
    assert learning_provenance(fixture) == "controlled_fixture_review"
    assert learning_provenance(executed) == "executed_verified_outcome"
    assert learning_provenance(selfass) == "automated_self_assessment"
    assert learning_provenance(pending) == "unknown_no_outcome"


def test_controlled_fixture_does_not_influence_accuracy_aggregate():
    reviewed = _cycle("reviewed", 2, actual={
        "reviewer": "reviewer-id", "review_kind": "planning_review",
        "missed": ["m1"], "unnecessary": [], "reuse_wrong": [],
    })
    fixture = _cycle("fixture", 10, actual={
        "reviewer": "fixture label", "review_kind": "controlled_fixture_review",
        "missed": [], "unnecessary": [f"x{i}" for i in range(8)], "reuse_wrong": [],
    })
    loop = learning_loop([reviewed, fixture])
    assert loop["provenance_split"]["reviewer_attributed"] == 1
    assert loop["provenance_split"]["controlled_fixture_review"] == 1
    assert loop["controlled_fixtures_excluded"] == 1
    assert loop["mean_prediction_accuracy"] == prediction_accuracy(reviewed)["accuracy"]


def test_planning_review_is_not_counted_as_execution():
    reviewed = _cycle("rev", 2, actual={"reviewer": "jon", "review_kind": "planning_review",
                                        "missed": ["m"], "unnecessary": [], "reuse_wrong": []})
    loop = learning_loop([reviewed])
    assert loop["provenance_split"]["reviewer_attributed"] == 1
    # a native_planning review contributes no genuinely-comparable executed cycle
    assert loop["comparability"]["largest_genuinely_comparable_group"] == 0


def test_transfer_match_requires_complete_empty_discrepancy_evidence():
    matched = _cycle("matched", 1, kind=EXECUTED_VERIFIED, actual={
        "effort_actual": 1, "missed": [], "unnecessary": [], "reuse_wrong": [],
    })
    unnecessary = _cycle("unnecessary", 1, kind=EXECUTED_VERIFIED, actual={
        "effort_actual": 1, "missed": [], "unnecessary": ["extra"], "reuse_wrong": [],
    })
    incomplete = _cycle("incomplete", 1, kind=EXECUTED_VERIFIED, actual={
        "effort_actual": 1, "missed": [],
    })
    result = transfer_observations([matched, unnecessary, incomplete])
    by_id = {row["cycle"]: row for row in result["executed_cycles"]}
    assert by_id["matched"]["prediction_matched"] is True
    assert by_id["unnecessary"]["prediction_matched"] is False
    assert by_id["incomplete"]["prediction_matched"] is None
    assert result["unknown_cycles"] == ["incomplete"]


# ------------------------------------- reopening --------------------------------------------

def test_reopening_only_on_concrete_contradicting_evidence():
    c = _cycle("reopen", 1,
               obligations=[{"key": "A", "recon_status": "reuse_existing"},
                            {"key": "C", "recon_status": "signature_matched"},
                            {"key": "B", "recon_status": "unknown"}],
               frontier=[{"key": "D", "reason": "max_depth 1 reached"}])
    out = {e["key"]: e for e in reopening_candidates(c, [
        {"key": "A", "now": "missing", "observation": "reviewed mechanism A deleted"},
        {"key": "C", "now": "missing", "observation": "previous source anchor no longer found"},
        {"key": "D", "blocker_cleared": True, "observation": "budget raised"},
        {"key": "B", "now": "unknown", "observation": ""},
    ])}
    assert out["A"]["reopen"] is True
    assert out["C"]["reopen"] is True and "semantic review remains open" in out["C"]["reason"]
    assert out["D"]["reopen"] is True
    assert out["B"]["reopen"] is False and "UNKNOWN" in out["B"]["reason"]


# ----------------------------- real evidence + persistence + resume --------------------------

def test_real_stage_evidence_loop_persists_and_resumes(tmp_path):
    from rdo.report import run_stage6_learning_loop
    d = str(tmp_path / "s6")
    res = run_stage6_learning_loop(repo_dir=".", workdir=d)
    assert res["cycles_ingested"] >= 5
    assert res["provenance_split"]["controlled_fixture_review"] >= 1  # explicitly not human review
    assert res["provenance_split"]["reviewer_attributed"] == 0
    assert res["unknown_outcomes"] >= 1                          # planning-only cycles are UNKNOWN
    # reopening demonstrated: source-match->missing reopens its review path, UNKNOWN does not
    reopen = {r["key"]: r["reopen"] for r in res["reopening"]}
    assert reopen.get("belief_staleness_input") is True
    assert reopen.get("belief_decay_policy") is False
    # durable + reproducible in a fresh process
    code = (f"import json; d=json.load(open({(d + '/learning_loop.json')!r})); "
            "print(json.dumps({'mean':d['mean_prediction_accuracy'],"
            "'split':d['provenance_split']}))")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["mean"] == res["mean_prediction_accuracy"]
    assert out["split"] == res["provenance_split"]



def test_regression_outcome_becomes_scoped_candidate_for_later_cycles(tmp_path):
    from rdo.memory import PatternMemory, compare, derive_lessons
    from rdo.orchestrator import run_cycle
    from rdo.model import Obligation

    outcome = _cycle("regression", 2, actual={
        "missed": [], "unnecessary": [], "reuse_wrong": [],
        "regressions": ["ci:run-123 regression in belief-decay path"],
    })
    lessons = derive_lessons(outcome, compare(outcome))
    regression = next(item for item in lessons if item.key == "regression_risk:regression")
    assert regression.applicability == outcome.objective
    assert "one regression" in regression.exceptions[0]

    memory = PatternMemory(str(tmp_path / "patterns.jsonl"))
    memory.add(regression)
    assert regression.confidence == 0.3 and regression.observed_count == 1
    assert [item.key for item in memory.applicable("regression")] == ["regression_risk:regression"]
    assert memory.applicable("another regression objective") == []
    reopened = PatternMemory(str(tmp_path / "patterns.jsonl"))
    assert [item.key for item in reopened.applicable("regression")] == ["regression_risk:regression"]
    assert reopened.applicable("another regression objective") == []

    next_cycle, _ = run_cycle(
        "next-regression-review", "regression", [],
        [Obligation("seed", "bounded seed", "test")], signatures={},
        repo_dir=str(tmp_path), active_experiments=[], memory=memory, max_depth=0,
    )
    assert any("applied_patterns=['regression_risk:regression']" in item
               for item in next_cycle.uncertainties)


def test_malformed_regression_outcome_does_not_create_learning_pattern():
    from rdo.memory import compare, derive_lessons
    cycle = _cycle("malformed-regression", 1, actual={
        "missed": [], "unnecessary": [], "reuse_wrong": [], "regressions": [" "],
    })
    assert all(not item.key.startswith("regression_risk:")
               for item in derive_lessons(cycle, compare(cycle)))


def test_regression_lessons_from_different_objectives_do_not_collapse_scope():
    from rdo.memory import compare, derive_lessons
    first = _cycle("regression-a", 1, actual={
        "missed": [], "unnecessary": [], "reuse_wrong": [], "regressions": ["ci:a"],
    })
    second = _cycle("regression-b", 1, actual={
        "missed": [], "unnecessary": [], "reuse_wrong": [], "regressions": ["ci:b"],
    })
    a = next(item for item in derive_lessons(first, compare(first))
             if item.key.startswith("regression_risk:"))
    b = next(item for item in derive_lessons(second, compare(second))
             if item.key.startswith("regression_risk:"))
    assert a.key != b.key
    assert a.applicability == first.objective
    assert b.applicability == second.objective


def test_regression_without_objective_scope_does_not_create_global_pattern():
    from rdo.memory import compare, derive_lessons
    cycle = _cycle("unscoped-regression", 1, actual={
        "missed": [], "unnecessary": [], "reuse_wrong": [], "regressions": ["ci:regression"],
    })
    cycle.objective = " "
    assert all(not item.key.startswith("regression_risk:")
               for item in derive_lessons(cycle, compare(cycle)))


def test_exact_scope_patterns_do_not_use_legacy_token_overlap(tmp_path):
    from rdo.memory import PatternMemory
    from rdo.model import Pattern
    memory = PatternMemory(str(tmp_path / "patterns.jsonl"))
    memory.add(Pattern(key="exact", statement="scoped", provenance="cycle:1",
        applicability="belief decay", exact_scope=True))
    assert [p.key for p in memory.applicable("belief decay")] == ["exact"]
    assert [p.key for p in memory.applicable("  belief decay  ")] == ["exact"]
    assert memory.applicable("belief retrieval") == []
    assert memory.applicable("other belief decay") == []


def test_pattern_exact_scope_requires_boolean_value():
    import pytest
    from rdo.model import Pattern
    with pytest.raises(ValueError, match="exact_scope must be a boolean"):
        Pattern(key="bad", statement="bad", provenance="cycle:1", exact_scope="true")


def test_exact_scope_pattern_requires_nonblank_applicability():
    import pytest
    from rdo.model import Pattern
    with pytest.raises(ValueError, match="non-blank applicability"):
        Pattern(key="unscoped", statement="bad", provenance="cycle:1", exact_scope=True)


def test_exact_scope_matching_normalizes_internal_whitespace_and_case(tmp_path):
    from rdo.memory import PatternMemory
    from rdo.model import Pattern
    memory = PatternMemory(str(tmp_path / "patterns.jsonl"))
    memory.add(Pattern(key="exact", statement="scoped", provenance="cycle:1",
        applicability="Belief   Decay", exact_scope=True))
    assert [p.key for p in memory.applicable(" belief decay ")] == ["exact"]


def test_exact_scope_pattern_key_collision_fails_closed(tmp_path):
    import pytest
    from rdo.memory import PatternMemory
    from rdo.model import Pattern
    memory = PatternMemory(str(tmp_path / "patterns.jsonl"))
    memory.add(Pattern(key="regression_risk:shared", statement="first",
        provenance="cycle:1", applicability="belief decay", exact_scope=True))
    with pytest.raises(ValueError, match="conflicting exact scopes"):
        memory.add(Pattern(key="regression_risk:shared", statement="other",
            provenance="cycle:2", applicability="belief retrieval", exact_scope=True))
    assert [p.key for p in memory.applicable("belief decay")] == ["regression_risk:shared"]
    assert memory.applicable("belief retrieval") == []


def test_exact_scope_pattern_cannot_collide_with_legacy_fuzzy_pattern(tmp_path):
    import pytest
    from rdo.memory import PatternMemory
    from rdo.model import Pattern
    memory = PatternMemory(str(tmp_path / "patterns.jsonl"))
    memory.add(Pattern(key="regression_risk:shared", statement="legacy",
        provenance="cycle:1", applicability="belief", exact_scope=False))
    with pytest.raises(ValueError, match="conflicting scope modes"):
        memory.add(Pattern(key="regression_risk:shared", statement="exact",
            provenance="cycle:2", applicability="belief decay", exact_scope=True))


def test_persisted_exact_scope_key_collision_fails_closed(tmp_path):
    import json
    import pytest
    from rdo.memory import PatternMemory
    from rdo.model import Pattern
    path = tmp_path / "patterns.jsonl"
    first = Pattern(key="same", statement="first", provenance="cycle:1",
        applicability="belief decay", exact_scope=True)
    second = Pattern(key="same", statement="second", provenance="cycle:2",
        applicability="belief retrieval", exact_scope=True)
    path.write_text(json.dumps(first.to_dict()) + "\n" + json.dumps(second.to_dict()) + "\n")
    with pytest.raises(ValueError, match="persisted pattern key collision"):
        PatternMemory(str(path))


def test_pattern_memory_add_revalidates_mutated_exact_scope_metadata(tmp_path):
    import pytest
    from rdo.memory import PatternMemory
    from rdo.model import Pattern
    memory = PatternMemory(str(tmp_path / "patterns.jsonl"))
    pattern = Pattern(key="mutated", statement="scoped", provenance="cycle:1",
        applicability="belief decay", exact_scope=True)
    pattern.applicability = " "
    with pytest.raises(ValueError, match="non-blank applicability"):
        memory.add(pattern)
