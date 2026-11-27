"""One-pen persistence tests for IdentityLoop."""
from __future__ import annotations

import time
from datetime import datetime

from nex_config import local_tz
from substrate import Reader, Writer, connect
from theory_x.life import identity_loop


def _dbs(tmp_path):
    dynamic_path = tmp_path / "dynamic.db"
    beliefs_path = tmp_path / "beliefs.db"
    conversations_path = tmp_path / "conversations.db"

    cx = connect(dynamic_path)
    cx.execute("CREATE TABLE current_focus (id INTEGER PRIMARY KEY, problem_id INTEGER)")
    cx.execute("INSERT INTO current_focus VALUES (1, 7)")
    cx.execute(
        "CREATE TABLE surprise_events (triggered_at REAL, big_surprise INTEGER, "
        "actual_content TEXT, surprise_score REAL)"
    )
    cx.execute(
        "INSERT INTO surprise_events VALUES (?, 1, 'A meaningful surprise', 0.9)",
        (time.time() - 30,),
    )
    cx.execute("CREATE TABLE fountain_events (ts REAL, thought TEXT, tag TEXT)")
    cx.execute(
        "INSERT INTO fountain_events VALUES (?, 'A recent thought', 'coin')",
        (time.time() - 20,),
    )
    cx.execute(
        "CREATE TABLE moltbook_posts (ts REAL, status TEXT)"
    )
    cx.execute(
        "INSERT INTO moltbook_posts VALUES (?, 'posted')",
        (time.time() - 10,),
    )
    cx.commit()
    cx.close()

    cx = connect(beliefs_path)
    cx.execute(
        "CREATE TABLE beliefs (id INTEGER PRIMARY KEY, content TEXT, tier INTEGER, confidence REAL, "
        "source TEXT, created_at REAL, affinity REAL, branch_id TEXT, tags TEXT)"
    )
    cx.execute(
        "INSERT INTO beliefs VALUES "
        "(1, 'A held belief', 6, 0.9, 'precipitated_from_sense', ?, 0.8, 'cognition', '[\\"identity\\"]')",
        (time.time() - 60,),
    )
    cx.commit()
    cx.close()

    cx = connect(conversations_path)
    cx.execute("CREATE TABLE open_problems (id INTEGER PRIMARY KEY, title TEXT, state TEXT)")
    cx.execute("INSERT INTO open_problems VALUES (7, 'Understand continuity', 'open')")
    cx.commit()
    cx.close()
    return dynamic_path, beliefs_path, conversations_path


def test_identity_gather_metrics_uses_injected_readers(tmp_path, monkeypatch):
    dynamic_path, beliefs_path, conversations_path = _dbs(tmp_path)
    monkeypatch.setenv("NEX_TAG_FEEDBACK_ON", "1")
    result = identity_loop._gather_metrics(
        time.time(),
        beliefs_reader=Reader(beliefs_path),
        dynamic_reader=Reader(dynamic_path),
        conversations_reader=Reader(conversations_path),
    )
    assert result["new_beliefs_6h"] == 1
    assert result["top_affinity"] == "A held belief"
    assert result["reads_6h"] == 1
    assert result["focus_title"] == "Understand continuity"
    assert result["last_surprise"] == "A meaningful surprise"
    assert result["fountain_fires_6h"] == 1
    assert result["moltbook_6h"] == 1
    assert result["tags_coin_6h"] == 1


def test_identity_tick_uses_injected_writers(tmp_path, monkeypatch):
    dynamic_path, beliefs_path, conversations_path = _dbs(tmp_path)
    d_reader = Reader(dynamic_path)
    b_reader = Reader(beliefs_path)
    c_reader = Reader(conversations_path)
    d_writer = Writer(dynamic_path, name="identity-test-dynamic")
    b_writer = Writer(beliefs_path, name="identity-test-beliefs")
    identity_loop._ensure_identity_log(d_reader, d_writer)
    hour = datetime.fromtimestamp(time.time(), local_tz()).hour
    monkeypatch.setattr(identity_loop, "COMPOSE_HOURS", {hour})
    monkeypatch.setattr(identity_loop, "_gather_metrics", lambda *args, **kwargs: {"new_beliefs_6h": 2})
    try:
        result = identity_loop.identity_tick(
            dynamic_reader=d_reader, dynamic_writer=d_writer,
            beliefs_reader=b_reader, beliefs_writer=b_writer,
            conversations_reader=c_reader,
        )
        assert result["composed"] is True
        saved = d_reader.read_one(
            "SELECT statement, ablation_arm FROM identity_log ORDER BY composed_at DESC LIMIT 1"
        )
        assert saved is not None
        assert saved["statement"].startswith("I am the attending")
        belief = b_reader.read_one(
            "SELECT source, tier, confidence, tags FROM beliefs WHERE source=?",
            ("identity_loop",),
        )
        assert belief is not None
        assert belief["tier"] == 6
        assert belief["confidence"] == 0.90
        assert belief["tags"] == '["identity"]'
    finally:
        d_writer.close()
        b_writer.close()
