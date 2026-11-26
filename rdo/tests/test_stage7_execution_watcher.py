"""Stage 7 (RDO v1.3 §16) — execution integration verified through the Watcher.

Covers the vertical slice and req-10 cases: traceability, persistence + fresh-process resumption,
conflicting evidence, missing evidence, rollback/reopen, the three SEPARATE evidence dimensions, and
that a success is never inferred from a claim / passing test alone. Isolated temp-dir fixtures only;
no live NEX, no commits.
"""
import json
import subprocess
import sys

from rdo import execution as ex
from rdo.memory import learning_provenance, learning_loop
from rdo.model import CycleRecord, NATIVE_PLANNING

_GUARD_OK = "def guard(x):\n    return x > 0\n"
_TEST_OK = "from guard import guard\n\ndef test_g():\n    assert guard(1) and not guard(-1)\n"
_TEST_FAIL = "from guard import guard\n\ndef test_g():\n    assert guard(-1)\n"   # asserts the wrong thing
_REQ = {"guard": {"source_signature": r"def guard", "source_path": "guard.py", "test_file": "test_guard.py"}}


def _verify_slice(tmp_path, files, req=_REQ, claim=True):
    repo = tmp_path / f"repo_{len(list(tmp_path.iterdir()))}"
    repo.mkdir()
    for name, content in files.items():
        (repo / name).write_text(content, encoding="utf-8")
    wp = {"key": "wp:guard", "obligation_keys": list(req)}
    rec = ex.create_execution_record("exec:guard", "cyc7", "add a guard", wp, req)
    ex.record_claim(rec, completion_claim=claim, changed_artifacts=list(files), tests=[], failures=[])
    approved = [r["test_file"] for r in req.values() if r.get("test_file")]
    return ex.verify(rec, str(repo), str(repo / "ledger.jsonl"),
                     approved_test_files=approved)


# ----------------------------- the verified vertical slice -----------------------------

def test_verified_when_source_and_test_independently_confirm(tmp_path):
    rec = _verify_slice(tmp_path, {"guard.py": _GUARD_OK, "test_guard.py": _TEST_OK})
    assert rec["verdict"] == "verified"
    d = rec["verification"]["dimensions"]["guard"]
    # three SEPARATE evidence dimensions
    assert d["source_implemented"]["evidence_class"] == "static"
    assert d["test_verified"]["status"] == "passed"
    assert d["runtime_observed"]["origin"] == "host" and d["runtime_observed"]["evidence_class"] == "unknown"
    assert d["ledger_state"] == "TEST_PASSED"


def test_traceability_objective_to_obligations(tmp_path):
    rec = _verify_slice(tmp_path, {"guard.py": _GUARD_OK, "test_guard.py": _TEST_OK})
    assert rec["objective"] == "add a guard" and rec["work_package"] == "wp:guard"
    assert rec["obligation_keys"] == ["guard"] and rec["cycle_id"] == "cyc7"


# ------------------- req 6: a claim / passing test alone is NOT success -------------------

def test_claim_without_source_evidence_is_not_accepted(tmp_path):
    # the agent CLAIMS complete, and an unrelated test passes, but the required source is absent
    rec = _verify_slice(tmp_path, {"guard.py": "def other(): pass\n", "test_guard.py":
                                   "def test_ok():\n    assert True\n"}, claim=True)
    assert rec["claim"]["completion_claim"] is True
    assert rec["verdict"] == "claim_unverified"      # independent evidence, not the claim, decides


def test_missing_all_evidence_is_claim_unverified(tmp_path):
    rec = _verify_slice(tmp_path, {}, claim=True)     # nothing created at all
    assert rec["verdict"] == "claim_unverified"


# ----------------------------- conflicting / failing evidence -----------------------------

def test_failing_test_overrides_a_completion_claim(tmp_path):
    rec = _verify_slice(tmp_path, {"guard.py": _GUARD_OK, "test_guard.py": _TEST_FAIL}, claim=True)
    assert rec["verdict"] == "failed"                # source present but the test fails -> failed
    assert rec["verification"]["dimensions"]["guard"]["test_verified"]["status"] == "failed"


def test_source_without_test_is_partial(tmp_path):
    req = {"guard": {"source_signature": r"def guard", "source_path": "guard.py"}}  # no test_file
    rec = _verify_slice(tmp_path, {"guard.py": _GUARD_OK}, req=req)
    assert rec["verdict"] == "partial"


# ----------------------------- runtime stays host-only UNKNOWN -----------------------------

def test_runtime_dimension_is_never_verified_from_cloud(tmp_path):
    rec = _verify_slice(tmp_path, {"guard.py": _GUARD_OK, "test_guard.py": _TEST_OK})
    rt = rec["verification"]["dimensions"]["guard"]["runtime_observed"]
    assert rt["origin"] == "host" and rt["evidence_class"] == "unknown" and rt["data"] is None


# ----------------------------- persistence + fresh-process resume -----------------------------

def test_record_and_ledger_persist_and_resume(tmp_path):
    rec = _verify_slice(tmp_path, {"guard.py": _GUARD_OK, "test_guard.py": _TEST_OK})
    path = ex.save_record(rec, str(tmp_path / "rec.json"))
    # append-only ledger survived on disk
    ledger_path = rec["verification"]["ledger_path"]
    entries = [l for l in open(ledger_path, encoding="utf-8").read().splitlines() if l.strip()]
    assert len(entries) >= 3 and all("to_state" in json.loads(e) for e in entries)
    # fresh process re-reads the durable record
    code = (f"import json; from rdo.execution import load_record; r=load_record({path!r}); "
            "print(json.dumps({'verdict': r['verdict'], 'ob': r['obligation_keys']}))")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["verdict"] == "verified" and out["ob"] == ["guard"]


# ----------------------------- rollback / reopen + learning feedback -----------------------------

def test_failed_verification_reopens_and_feeds_learning_with_provenance(tmp_path):
    rec = _verify_slice(tmp_path, {"guard.py": "def other(): pass\n"}, claim=True)  # unverified
    actual = ex.feedback_to_learning(rec)
    assert actual["review_kind"] == "watcher_verified_execution"
    assert "guard" in actual["reopened"]                      # unverified obligation is reopened
    # the independently-verified outcome is a DISTINCT provenance in the Stage-6 loop
    c = CycleRecord(id="c", objective="o", kind=NATIVE_PLANNING, predicted={"net_new_count": 1})
    c.actual = actual
    assert learning_provenance(c) == "independent_watcher_verified"
    loop = learning_loop([c])
    assert loop["provenance_split"]["reviewer_attributed"] == 0
    assert loop["provenance_split"]["controlled_fixture_review"] == 0
    assert loop["provenance_split"]["independent_watcher_verified"] == 1  # watcher evidence is independent
    assert loop["per_cycle"][0]["provenance"] == "independent_watcher_verified"


def test_rollback_is_isolated_nothing_live_touched(tmp_path):
    # the whole slice runs in a throwaway temp dir; verification touches no path outside it
    rec = _verify_slice(tmp_path, {"guard.py": _GUARD_OK, "test_guard.py": _TEST_OK})
    assert str(tmp_path) in rec["verification"]["ledger_path"]
    # execution.py performs no DB write and no live-state mutation
    src = open(ex.__file__, encoding="utf-8").read()
    assert "import sqlite3" not in src and "mode=rw" not in src


# -------------------------- explicit test-execution authorization --------------------------

def test_declared_test_is_not_run_without_allowlist(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "guard.py").write_text(_GUARD_OK, encoding="utf-8")
    marker = repo / "executed.txt"
    (repo / "test_guard.py").write_text(
        "from pathlib import Path\n"
        "Path('executed.txt').write_text('ran')\n"
        "def test_g():\n    assert True\n",
        encoding="utf-8",
    )
    rec = ex.create_execution_record(
        "exec:no_approval", "cyc7", "add a guard",
        {"key": "wp:guard", "obligation_keys": ["guard"]}, _REQ
    )
    rec = ex.verify(rec, str(repo), str(repo / "ledger.jsonl"))
    d = rec["verification"]["dimensions"]["guard"]
    assert rec["verdict"] == "partial"
    assert d["test_verified"]["status"] == "not_authorized"
    assert d["test_verified"]["execution_authorized"] is False
    assert d["ledger_state"] == "SOURCE_CONFIRMED"
    assert not marker.exists(), "a declared test path must not execute without explicit approval"


def test_allowlisted_test_path_cannot_escape_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "guard.py").write_text(_GUARD_OK, encoding="utf-8")
    marker = repo / "escaped.txt"
    outside = tmp_path / "test_outside.py"
    outside.write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('ran')\n"
        "def test_g():\n    assert True\n",
        encoding="utf-8",
    )
    req = {"guard": {"source_signature": r"def guard", "source_path": "guard.py",
                     "test_file": "../test_outside.py"}}
    rec = ex.create_execution_record(
        "exec:path_escape", "cyc7", "add a guard",
        {"key": "wp:guard", "obligation_keys": ["guard"]}, req
    )
    rec = ex.verify(rec, str(repo), str(repo / "ledger.jsonl"),
                    approved_test_files=["../test_outside.py"])
    d = rec["verification"]["dimensions"]["guard"]
    assert rec["verdict"] == "partial"
    assert d["test_verified"]["status"] == "not_authorized"
    assert d["test_verified"]["execution_authorized"] is False
    assert not marker.exists(), "path traversal must not execute a test outside repo_dir"
