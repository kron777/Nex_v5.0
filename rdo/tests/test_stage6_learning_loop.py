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
                        prediction_accuracy, record_actual, reopening_candidates)
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


def test_planning_review_is_not_counted_as_execution():
    reviewed = _cycle("rev", 2, actual={"reviewer": "jon", "review_kind": "planning_review",
                                        "missed": ["m"], "unnecessary": [], "reuse_wrong": []})
    loop = learning_loop([reviewed])
    assert loop["provenance_split"]["reviewer_attributed"] == 1
    # a native_planning review contributes no genuinely-comparable executed cycle
    assert loop["comparability"]["largest_genuinely_comparable_group"] == 0


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
