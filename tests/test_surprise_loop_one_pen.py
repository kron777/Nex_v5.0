"""One-pen persistence tests for SurpriseLoop."""
from __future__ import annotations

import time

from substrate import Reader, Writer, connect
from theory_x.life import surprise_loop


def test_surprise_tick_uses_injected_writers(tmp_path):
    dynamic_path = tmp_path / "dynamic.db"
    beliefs_path = tmp_path / "beliefs.db"
    cx = connect(dynamic_path)
    cx.execute(
        "CREATE TABLE surprise_events ("
        "id INTEGER PRIMARY KEY, triggered_at REAL, surprise_flag INTEGER, "
        "actual_content TEXT, predicted_content TEXT, prediction_type TEXT, "
        "surprise_score REAL, big_surprise INTEGER)"
    )
    triggered_at = time.time()
    cx.execute(
        "INSERT INTO surprise_events VALUES (1, ?, 1, ?, ?, ?, ?, ?)",
        (triggered_at, "A new unexpected event", "An expected event",
         "external_input", 0.9, 1),
    )
    cx.commit()
    cx.close()
    cx = connect(beliefs_path)
    cx.execute(
        "CREATE TABLE beliefs ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL UNIQUE, "
        "tier INTEGER NOT NULL, confidence REAL NOT NULL, created_at INTEGER NOT NULL, "
        "source TEXT NOT NULL, branch_id TEXT, tags TEXT)"
    )
    cx.commit()
    cx.close()

    d_reader = Reader(dynamic_path)
    d_writer = Writer(dynamic_path, name="surprise-test-dynamic")
    b_writer = Writer(beliefs_path, name="surprise-test-beliefs")
    try:
        result = surprise_loop.surprise_tick(
            dynamic_reader=d_reader, dynamic_writer=d_writer,
            beliefs_writer=b_writer,
        )
        assert result == {"promoted": 1}
        belief = Reader(beliefs_path).read_one(
            "SELECT tier, confidence, source, branch_id, tags FROM beliefs"
        )
        assert belief is not None
        assert belief["tier"] == 6
        assert belief["confidence"] == 0.75
        assert belief["source"] == "surprise"
        assert belief["branch_id"] == "cognition"
        assert "big_surprise" in belief["tags"]
        marker = d_reader.read_one(
            "SELECT value FROM daemon_kv WHERE key=?",
            (surprise_loop.LAST_PROMOTED_TS_KEY,),
        )
        assert float(marker["value"]) == triggered_at
    finally:
        d_writer.close()
        b_writer.close()
