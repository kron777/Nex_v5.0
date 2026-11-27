"""The recursion-attribution sidecar must never write dynamic.db."""
from __future__ import annotations

from substrate import connect, Reader
from theory_x.stage_tom import recursion_attribution


def test_sample_does_not_create_or_write_recursion_table(tmp_path, monkeypatch):
    db_path = tmp_path / "dynamic.db"
    cx = connect(db_path)
    cx.close()
    monkeypatch.setattr(recursion_attribution, "_db", lambda name: str(db_path))

    assert recursion_attribution.sample() is None
    assert Reader(db_path).read(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='recursion_attrib'"
    ) == []


def test_sample_and_verdict_read_runtime_owned_rows_only(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "dynamic.db"
    cx = connect(db_path)
    cx.execute(
        "CREATE TABLE recursion_attrib ("
        "ts REAL PRIMARY KEY, nudge_active INTEGER, branch TEXT, "
        "branch_prev TEXT, moved INTEGER)"
    )
    cx.executemany(
        "INSERT INTO recursion_attrib VALUES (?, ?, ?, ?, ?)",
        [
            (1.0, 1, "branch-b", "branch-a", 1),
            (2.0, 0, "branch-b", "branch-b", 0),
        ],
    )
    cx.commit()
    cx.close()
    monkeypatch.setattr(recursion_attribution, "_db", lambda name: str(db_path))

    latest = recursion_attribution.sample()
    assert latest == {
        "ts": 2.0,
        "nudge_active": 0,
        "branch": "branch-b",
        "branch_prev": "branch-b",
        "moved": 0,
    }
    result = recursion_attribution.verdict()
    assert result["samples"] == 2
    assert result["active"] == 1
    assert result["inactive"] == 1
    assert "attribution verdict" in capsys.readouterr().out
    assert Reader(db_path).count("recursion_attrib") == 2
