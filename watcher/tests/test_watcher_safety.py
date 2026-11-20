"""Passive-mode safety proofs: the Watcher cannot modify NEX or its databases."""
import hashlib
import json
import os
import sqlite3

import pytest

from watcher.collector import collect_cloud
from watcher.safety import PassiveViolation, guard_sql, read_only_connect, read_only_query


def _make_db(path):
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE beliefs(id INTEGER PRIMARY KEY, confidence REAL)")
    c.executemany("INSERT INTO beliefs(confidence) VALUES (?)", [(0.5,), (0.7,)])
    c.commit()
    c.close()


def _sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def test_read_only_connect_refuses_every_write(tmp_path):
    db = tmp_path / "beliefs.db"
    _make_db(str(db))
    before = _sha(str(db))
    con = read_only_connect(str(db))
    for sql in ("INSERT INTO beliefs(confidence) VALUES (0.9)",
                "UPDATE beliefs SET confidence=1.0",
                "DELETE FROM beliefs",
                "DROP TABLE beliefs"):
        with pytest.raises(sqlite3.Error):
            con.execute(sql)
    con.close()
    assert _sha(str(db)) == before, "db was modified under passive mode"


def test_guard_sql_rejects_mutating():
    for sql in ("insert into x values(1)", "UPDATE t SET a=1", "DELETE FROM t",
                "DROP TABLE t", "REPLACE INTO t VALUES(1)"):
        with pytest.raises(PassiveViolation):
            guard_sql(sql)
    # read-only passes
    assert guard_sql("SELECT * FROM t") == "SELECT * FROM t"


def test_read_only_query_reads(tmp_path):
    db = tmp_path / "b.db"
    _make_db(str(db))
    rows = read_only_query(str(db), "SELECT COUNT(*) AS n FROM beliefs")
    assert rows[0]["n"] == 2


def _fixture_repo(tmp_path):
    (tmp_path / "mind_map").mkdir()
    (tmp_path / "mind_map" / "MIND_MAP.yaml").write_text(
        "nodes:\n  - id: p7_valence\n    layer: ring\n    evidence: inferred\n    last_verified: 2026-11-01\n")
    (tmp_path / "sentience_dag.json").write_text(
        json.dumps({"nodes": {"L1": {"layer": 1, "status": "built", "prereqs": []}}}))
    obs = tmp_path / "observation_reports"
    obs.mkdir()
    (obs / "r77.md").write_text("# r77")
    (obs / "r79_PREREGISTRATION.md").write_text("# prereg")
    return tmp_path


def test_collect_cloud_writes_nothing_to_the_repo(tmp_path):
    repo = _fixture_repo(tmp_path)
    # snapshot every file hash before
    before = {p: _sha(p) for p in _all_files(str(repo))}
    records = collect_cloud(str(repo))
    after = {p: _sha(p) for p in _all_files(str(repo))}
    assert before == after, "collect_cloud modified files"
    # and it produced real cloud evidence
    assert records and all(r.origin in ("cloud", "host") for r in records)
    assert any(r.subject == "experiment_registry" for r in records)


def _all_files(root):
    out = []
    for d, _, fs in os.walk(root):
        for f in fs:
            out.append(os.path.join(d, f))
    return sorted(out)
