"""Regression tests for Fountain momentum's one-pen persistence path."""
from __future__ import annotations

import time

from substrate import Reader, Writer, connect
from theory_x.stage_tom.momentum import (
    capture_momentum,
    read_momentum,
    stamp_resolution,
)


def _handles(path):
    cx = connect(path)
    cx.execute(
        "CREATE TABLE surprise_events ("
        "id INTEGER PRIMARY KEY, triggered_at REAL, "
        "surprise_score REAL, actual_content TEXT)"
    )
    cx.execute(
        "INSERT INTO surprise_events (triggered_at, surprise_score, actual_content) "
        "VALUES (?, 0.8, 'An unexpected observation')",
        (time.time() - 10,),
    )
    cx.commit()
    cx.close()
    return Reader(path), Writer(path, name="momentum-test")


def test_capture_and_resolution_use_injected_reader_writer(tmp_path, monkeypatch):
    db_path = tmp_path / "dynamic.db"
    reader, writer = _handles(db_path)
    monkeypatch.setenv("NEX5_CARRYOVER", "1")
    thought = (
        "A sufficiently long thought about neural continuity and persistent memory."
    )
    try:
        assert capture_momentum(
            thought, "cognition", dynamic_reader=reader, dynamic_writer=writer
        )
        assert capture_momentum(
            thought, "cognition", dynamic_reader=reader, dynamic_writer=writer
        )
        row = reader.read_one(
            "SELECT branch, thought_fragment, surprise_score, surprise_note, "
            "carry_count, resolved FROM momentum WHERE id=1"
        )
        assert row is not None
        assert row["branch"] == "cognition"
        assert row["carry_count"] == 2
        assert row["surprise_score"] == 0.8
        assert row["surprise_note"] == "An unexpected observation"

        assert stamp_resolution(
            True, dynamic_reader=reader, dynamic_writer=writer
        )
        row = reader.read_one(
            "SELECT resolved FROM momentum WHERE id=1"
        )
        assert row["resolved"] == 1

        rendered = read_momentum(dynamic_reader=reader)
        assert rendered is not None
        assert "settled into a belief" in rendered
    finally:
        writer.close()


def test_read_momentum_does_not_create_missing_table(tmp_path):
    db_path = tmp_path / "empty-dynamic.db"
    cx = connect(db_path)
    cx.close()
    reader = Reader(db_path)
    assert read_momentum(dynamic_reader=reader) is None
    tables = reader.read(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='momentum'"
    )
    assert tables == []


def test_legacy_schema_migrates_once_without_expected_error_events(tmp_path, monkeypatch):
    import substrate.writer as writer_module

    db_path = tmp_path / "legacy-dynamic.db"
    cx = connect(db_path)
    cx.execute(
        "CREATE TABLE momentum ("
        "id INTEGER PRIMARY KEY CHECK (id = 1), updated_at REAL NOT NULL, "
        "branch TEXT, thought_fragment TEXT, surprise_score REAL DEFAULT 0.0, "
        "surprise_note TEXT)"
    )
    cx.execute(
        "INSERT INTO momentum (id, updated_at, branch, thought_fragment) "
        "VALUES (1, ?, 'cognition', 'neural continuity and persistent memory')",
        (time.time(),),
    )
    cx.execute(
        "CREATE TABLE surprise_events (id INTEGER PRIMARY KEY, triggered_at REAL, "
        "surprise_score REAL, actual_content TEXT)"
    )
    cx.commit()
    cx.close()

    reader = Reader(db_path)
    writer = Writer(db_path, name="momentum-legacy-test")
    reported_errors = []
    monkeypatch.setattr(
        writer_module.error_channel,
        "record",
        lambda *args, **kwargs: reported_errors.append((args, kwargs)),
    )
    thought = "Neural continuity and persistent memory remain important."
    try:
        assert capture_momentum(
            thought, "cognition", dynamic_reader=reader, dynamic_writer=writer
        )
        assert capture_momentum(
            thought, "cognition", dynamic_reader=reader, dynamic_writer=writer
        )

        columns = {
            row["name"] for row in reader.read("PRAGMA table_info(momentum)")
        }
        assert {"carry_count", "resolved"} <= columns
        row = reader.read_one(
            "SELECT carry_count, resolved FROM momentum WHERE id=1"
        )
        assert row["carry_count"] == 3
        assert row["resolved"] is None
        assert reported_errors == []
    finally:
        writer.close()
