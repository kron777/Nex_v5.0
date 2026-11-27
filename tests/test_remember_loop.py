"""Regression tests for RememberLoop's one-pen belief access."""
from __future__ import annotations

import time

from substrate import Reader, Writer, connect
from theory_x.life import remember_loop


def _make_beliefs_db(path):
    cx = connect(path)
    cx.execute(
        "CREATE TABLE beliefs ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "content TEXT NOT NULL UNIQUE, tier INTEGER NOT NULL, "
        "confidence REAL NOT NULL, created_at INTEGER NOT NULL, "
        "source TEXT NOT NULL, branch_id TEXT, tags TEXT)"
    )
    now = int(time.time())
    cx.executemany(
        "INSERT INTO beliefs "
        "(content, tier, confidence, created_at, source, branch_id, tags) "
        "VALUES (?, 6, 0.7, ?, 'manual', 'test', '[]')",
        [
            ("An older belief for temporal recall", now - 8 * 86400),
            ("A recent belief for temporal recall", now - 60),
        ],
    )
    cx.commit()
    cx.close()


def test_remember_tick_reads_and_writes_through_injected_handles(tmp_path, monkeypatch):
    db_path = tmp_path / "beliefs.db"
    _make_beliefs_db(db_path)
    reader = Reader(db_path)
    writer = Writer(db_path, name="remember-loop-test")
    monkeypatch.setattr(
        remember_loop, "_compose_link",
        lambda voice, old, recent: "A temporal connection between two thoughts.",
    )
    try:
        result = remember_loop.remember_tick(
            object(), beliefs_reader=reader, beliefs_writer=writer
        )
        assert result["linked"] is True
        assert result["old_id"] != result["recent_id"]
        saved = reader.read_one(
            "SELECT tier, confidence, source, branch_id FROM beliefs "
            "WHERE content=?",
            ("A temporal connection between two thoughts.",),
        )
        assert saved is not None
        assert saved["tier"] == 6
        assert saved["confidence"] == 0.70
        assert saved["source"] == "remember_loop"
        assert saved["branch_id"] == "test"
    finally:
        writer.close()


def test_remember_tick_preserves_daily_cap(tmp_path, monkeypatch):
    db_path = tmp_path / "beliefs.db"
    _make_beliefs_db(db_path)
    cx = connect(db_path)
    now = int(time.time())
    cx.executemany(
        "INSERT INTO beliefs "
        "(content, tier, confidence, created_at, source, branch_id, tags) "
        "VALUES (?, 6, 0.7, ?, 'remember_loop', 'test', '[]')",
        [(f"daily item {i}", now - i) for i in range(remember_loop.DAILY_CAP)],
    )
    cx.commit()
    cx.close()
    reader = Reader(db_path)
    writer = Writer(db_path, name="remember-loop-cap-test")
    monkeypatch.setattr(
        remember_loop, "_compose_link",
        lambda *args: (_ for _ in ()).throw(AssertionError("must not compose at cap")),
    )
    try:
        assert remember_loop.remember_tick(
            object(), beliefs_reader=reader, beliefs_writer=writer
        ) == {"skipped": "daily_cap"}
    finally:
        writer.close()


def test_remember_tick_preserves_duplicate_content_handling(tmp_path, monkeypatch):
    db_path = tmp_path / "beliefs.db"
    _make_beliefs_db(db_path)
    cx = connect(db_path)
    cx.execute(
        "INSERT INTO beliefs "
        "(content, tier, confidence, created_at, source, branch_id, tags) "
        "VALUES ('Existing temporal link', 6, 0.7, ?, 'manual', 'test', '[]')",
        (int(time.time()),),
    )
    cx.commit()
    cx.close()
    reader = Reader(db_path)
    writer = Writer(db_path, name="remember-loop-duplicate-test")
    monkeypatch.setattr(
        remember_loop, "_compose_link",
        lambda voice, old, recent: "Existing temporal link",
    )
    try:
        assert remember_loop.remember_tick(
            object(), beliefs_reader=reader, beliefs_writer=writer
        ) == {"skipped": "duplicate_content"}
    finally:
        writer.close()
