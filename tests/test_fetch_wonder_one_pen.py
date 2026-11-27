"""One-pen persistence tests for FetchLoop and WonderLoop."""
from __future__ import annotations

import json
import time

from substrate import Reader, Writer, connect
from theory_x.life import fetch_loop, wonder_loop


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


def _sense_db(path):
    cx = connect(path)
    cx.execute(
        "CREATE TABLE sense_events ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, stream TEXT, payload TEXT, timestamp REAL)"
    )
    cx.execute(
        "INSERT INTO sense_events (stream, payload, timestamp) VALUES (?, ?, ?)",
        ("feed.rss", json.dumps({"url": "https://example.test/story", "title": "Example Story"}), time.time()),
    )
    cx.commit()
    cx.close()


def test_fetch_tick_uses_injected_handles(tmp_path, monkeypatch):
    beliefs_path = tmp_path / "beliefs.db"
    sense_path = tmp_path / "sense.db"
    _beliefs_db(beliefs_path)
    _sense_db(sense_path)
    reader = Reader(beliefs_path)
    writer = Writer(beliefs_path, name="fetch-loop-test")
    sense_reader = Reader(sense_path)
    monkeypatch.setattr(fetch_loop, "_fetch_body", lambda url: "x" * 160)
    monkeypatch.setattr(
        fetch_loop, "_compose_response",
        lambda voice, url, title, body: "I want to understand this reported pattern.",
    )
    try:
        result = fetch_loop.fetch_tick(
            object(), beliefs_reader=reader, beliefs_writer=writer,
            sense_reader=sense_reader,
        )
        assert result["fetched"] is True
        row = reader.read_one(
            "SELECT tier, confidence, source, branch_id FROM beliefs WHERE source=?",
            (fetch_loop.SOURCE,),
        )
        assert row is not None
        assert row["tier"] == 6
        assert row["confidence"] == 0.65
        assert row["source"] == "fetch_loop"
        assert row["branch_id"] == "computing"
    finally:
        writer.close()


def test_wonder_tick_uses_injected_handles(tmp_path, monkeypatch):
    beliefs_path = tmp_path / "beliefs.db"
    sense_path = tmp_path / "sense.db"
    _beliefs_db(beliefs_path)
    _sense_db(sense_path)
    reader = Reader(beliefs_path)
    writer = Writer(beliefs_path, name="wonder-loop-test")
    sense_reader = Reader(sense_path)
    monkeypatch.setattr(wonder_loop, "_pick_entity", lambda sense: "Quantum")
    monkeypatch.setattr(
        wonder_loop, "_context_for", lambda entity, sense: "Quantum computing research"
    )
    monkeypatch.setattr(
        wonder_loop, "_compose_question",
        lambda voice, entity, context: "Why does quantum computing change this field?",
    )
    try:
        result = wonder_loop.wonder_tick(
            object(), beliefs_reader=reader, beliefs_writer=writer,
            sense_reader=sense_reader,
        )
        assert result["wondered"] is True
        row = reader.read_one(
            "SELECT tier, confidence, source, branch_id FROM beliefs WHERE source=?",
            (wonder_loop.SOURCE,),
        )
        assert row is not None
        assert row["tier"] == 6
        assert row["confidence"] == 0.60
        assert row["source"] == "wonder_loop"
        assert row["branch_id"] == "cognition"
    finally:
        writer.close()
