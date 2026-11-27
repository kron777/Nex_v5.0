"""One-pen persistence tests for the recursive self-model loops."""
from __future__ import annotations

import time

from substrate import Reader, Writer, connect
from theory_x.life import pattern_loop, witness_loop


def _dynamic_db(path):
    cx = connect(path)
    cx.execute(
        "CREATE TABLE identity_log ("
        "id INTEGER PRIMARY KEY, statement TEXT, composed_at REAL)"
    )
    cx.executemany(
        "INSERT INTO identity_log (statement, composed_at) VALUES (?, ?)",
        [("I value curiosity and patience.", time.time()-100),
         ("I notice patterns in difficult problems.", time.time()-50)],
    )
    cx.execute(
        "CREATE TABLE pattern_log ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, composed_at REAL NOT NULL, "
        "date_local TEXT NOT NULL, hour_local INTEGER NOT NULL, "
        "statement TEXT NOT NULL, UNIQUE(date_local, hour_local))"
    )
    cx.execute(
        "INSERT INTO pattern_log (composed_at, date_local, hour_local, statement) "
        "VALUES (?, '2026-11-26', 3, 'I repeatedly return to curiosity.')",
        (time.time()-20,),
    )
    cx.commit()
    cx.close()


def _beliefs_db(path):
    cx = connect(path)
    cx.execute(
        "CREATE TABLE beliefs ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL UNIQUE, "
        "tier INTEGER NOT NULL, confidence REAL NOT NULL, created_at INTEGER NOT NULL, "
        "source TEXT NOT NULL, branch_id TEXT, tags TEXT)"
    )
    cx.commit()
    cx.close()


def test_pattern_tick_uses_injected_writers(tmp_path, monkeypatch):
    dynamic_path = tmp_path / "dynamic.db"
    beliefs_path = tmp_path / "beliefs.db"
    _dynamic_db(dynamic_path)
    _beliefs_db(beliefs_path)
    d_reader = Reader(dynamic_path)
    d_writer = Writer(dynamic_path, name="pattern-test-dynamic")
    b_writer = Writer(beliefs_path, name="pattern-test-beliefs")
    monkeypatch.setattr(
        pattern_loop, "_compose_pattern",
        lambda voice, statements: "I repeatedly emphasize curiosity and patience.",
    )
    try:
        result = pattern_loop.pattern_tick(
            object(), force=True, dynamic_reader=d_reader,
            dynamic_writer=d_writer, beliefs_writer=b_writer,
        )
        assert result["composed"] is True
        assert d_reader.read_one(
            "SELECT statement FROM pattern_log ORDER BY composed_at DESC LIMIT 1"
        )["statement"] == "I repeatedly emphasize curiosity and patience."
        b_reader = Reader(beliefs_path)
        saved = b_reader.read_one(
            "SELECT source, tier, confidence, tags FROM beliefs WHERE source=?",
            ("pattern_loop",),
        )
        assert saved is not None
        assert saved["tier"] == 6
        assert saved["confidence"] == 0.85
        assert saved["tags"] == '["self_pattern"]'
    finally:
        d_writer.close()
        b_writer.close()


def test_witness_tick_uses_injected_writers(tmp_path, monkeypatch):
    dynamic_path = tmp_path / "dynamic.db"
    beliefs_path = tmp_path / "beliefs.db"
    _dynamic_db(dynamic_path)
    _beliefs_db(beliefs_path)
    d_reader = Reader(dynamic_path)
    d_writer = Writer(dynamic_path, name="witness-test-dynamic")
    b_writer = Writer(beliefs_path, name="witness-test-beliefs")
    monkeypatch.setattr(
        witness_loop, "_compose_witness",
        lambda voice, patterns: "I may overlook the assumptions behind my observations.",
    )
    try:
        result = witness_loop.witness_tick(
            object(), force=True, dynamic_reader=d_reader,
            dynamic_writer=d_writer, beliefs_writer=b_writer,
        )
        assert result["composed"] is True
        assert d_reader.read_one(
            "SELECT statement FROM witness_log ORDER BY composed_at DESC LIMIT 1"
        )["statement"] == "I may overlook the assumptions behind my observations."
        b_reader = Reader(beliefs_path)
        saved = b_reader.read_one(
            "SELECT source, tier, confidence, tags FROM beliefs WHERE source=?",
            ("witness_loop",),
        )
        assert saved is not None
        assert saved["tier"] == 6
        assert saved["confidence"] == 0.85
        assert saved["tags"] == '["blind_spot"]'
    finally:
        d_writer.close()
        b_writer.close()
