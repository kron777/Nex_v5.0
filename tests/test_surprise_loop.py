"""Regression tests for surprise promotion ordering and retry semantics."""

import sqlite3

import pytest


def _prepare_databases(tmp_path, monkeypatch, initial_ts=100.0, initial_id=None):
    from theory_x.life import surprise_loop as loop

    dynamic_path = tmp_path / "dynamic.db"
    beliefs_path = tmp_path / "beliefs.db"
    with sqlite3.connect(dynamic_path) as db:
        db.execute(
            "CREATE TABLE surprise_events ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, triggered_at REAL NOT NULL, "
            "prediction_id INTEGER NOT NULL, prediction_type TEXT NOT NULL, "
            "surprise_score REAL NOT NULL, surprise_flag INTEGER NOT NULL, "
            "big_surprise INTEGER NOT NULL DEFAULT 0, predicted_content TEXT, "
            "actual_content TEXT, tags TEXT NOT NULL DEFAULT '[]')"
        )
        db.execute(
            "CREATE TABLE daemon_kv (key TEXT PRIMARY KEY, value TEXT, updated_at REAL)"
        )
        db.execute(
            "INSERT INTO daemon_kv (key, value, updated_at) VALUES (?, ?, 0)",
            (loop.LAST_PROMOTED_TS_KEY, str(initial_ts)),
        )
        if initial_id is not None:
            db.execute(
                "INSERT INTO daemon_kv (key, value, updated_at) VALUES (?, ?, 0)",
                (loop.LAST_PROMOTED_ID_KEY, str(initial_id)),
            )
    with sqlite3.connect(beliefs_path) as db:
        db.execute(
            "CREATE TABLE beliefs (content TEXT UNIQUE, tier INTEGER, confidence REAL, "
            "created_at INTEGER, source TEXT, branch_id TEXT, tags TEXT)"
        )

    def _connect(path, timeout=15):
        return sqlite3.connect(str(path), timeout=timeout)

    monkeypatch.setattr(loop, "connect", _connect)
    monkeypatch.setattr(loop, "DYNAMIC_DB", dynamic_path)
    monkeypatch.setattr(loop, "BELIEFS_DB", beliefs_path)
    return loop, dynamic_path, beliefs_path


def _insert_event(db_path, timestamp, index):
    with sqlite3.connect(db_path) as db:
        db.execute(
            "INSERT INTO surprise_events "
            "(triggered_at, prediction_id, prediction_type, surprise_score, "
            "surprise_flag, big_surprise, predicted_content, actual_content) "
            "VALUES (?, ?, 'external_input', 0.9, 1, 0, ?, ?)",
            (timestamp, index, f"prediction-{index}", f"actual-{index}"),
        )


def test_equal_timestamp_events_continue_across_batches(tmp_path, monkeypatch):
    loop, dynamic_path, beliefs_path = _prepare_databases(tmp_path, monkeypatch)
    for i in range(25):
        _insert_event(dynamic_path, 200.0, i)

    assert loop.surprise_tick() == {"promoted": 20}
    assert loop.surprise_tick() == {"promoted": 5}

    with sqlite3.connect(beliefs_path) as db:
        assert db.execute("SELECT COUNT(*) FROM beliefs").fetchone()[0] == 25


def test_failed_event_is_retried_without_advancing_cursor(tmp_path, monkeypatch):
    loop, dynamic_path, beliefs_path = _prepare_databases(tmp_path, monkeypatch)
    _insert_event(dynamic_path, 200.0, 1)
    _insert_event(dynamic_path, 201.0, 2)

    original = loop._surprise_to_belief
    failed = {"once": False}

    def fail_once(row):
        if not failed["once"]:
            failed["once"] = True
            raise RuntimeError("transient conversion failure")
        return original(row)

    monkeypatch.setattr(loop, "_surprise_to_belief", fail_once)
    assert loop.surprise_tick() == {"promoted": 0}

    with sqlite3.connect(dynamic_path) as db:
        cursor = dict(db.execute("SELECT key, value FROM daemon_kv"))
        assert loop.LAST_PROMOTED_TS_KEY not in cursor
        assert loop.LAST_PROMOTED_ID_KEY not in cursor

    monkeypatch.setattr(loop, "_surprise_to_belief", original)
    assert loop.surprise_tick() == {"promoted": 2}
    with sqlite3.connect(beliefs_path) as db:
        assert db.execute("SELECT COUNT(*) FROM beliefs").fetchone()[0] == 2


def test_legacy_timestamp_cursor_replays_same_timestamp_safely(tmp_path, monkeypatch):
    loop, dynamic_path, beliefs_path = _prepare_databases(tmp_path, monkeypatch, initial_ts=200.0)
    _insert_event(dynamic_path, 200.0, 1)
    _insert_event(dynamic_path, 200.0, 2)
    _insert_event(dynamic_path, 201.0, 3)

    assert loop.surprise_tick() == {"promoted": 3}
    with sqlite3.connect(beliefs_path) as db:
        assert db.execute("SELECT COUNT(*) FROM beliefs").fetchone()[0] == 3


def test_non_big_surprise_has_one_surprise_tag():
    from theory_x.life.surprise_loop import _surprise_tags
    assert _surprise_tags(False) == ["surprise"]


def test_big_surprise_has_both_distinct_tags():
    from theory_x.life.surprise_loop import _surprise_tags
    tags = _surprise_tags(True)
    assert tags == ["surprise", "big_surprise"]
    assert len(tags) == len(set(tags))
