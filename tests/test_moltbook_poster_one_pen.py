"""One-pen persistence tests for the Moltbook poster."""
from __future__ import annotations

import time

from substrate import Reader, Writer, connect
from theory_x.stage7_moltbook.poster import PostLoop


class _Client:
    dry_run = True

    def create_post(self, submolt, title, content):
        return {"id": "post-1"}


def _dbs(tmp_path):
    dynamic_path = tmp_path / "dynamic.db"
    beliefs_path = tmp_path / "beliefs.db"
    cx = connect(dynamic_path)
    cx.execute("CREATE TABLE daemon_kv (key TEXT PRIMARY KEY, value TEXT, updated_at REAL)")
    cx.execute(
        "CREATE TABLE moltbook_post_queue (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "thought_id INTEGER UNIQUE, content TEXT, queued_at REAL, status TEXT, "
        "word_count INTEGER, droplet TEXT)"
    )
    cx.execute(
        "CREATE TABLE moltbook_posts (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id TEXT, "
        "thought_id INTEGER, ts REAL, submolt TEXT, status TEXT, error TEXT)"
    )
    cx.commit()
    cx.close()
    cx = connect(beliefs_path)
    cx.execute(
        "CREATE TABLE beliefs (id INTEGER PRIMARY KEY, content TEXT, created_at REAL, source TEXT)"
    )
    cx.execute(
        "INSERT INTO beliefs VALUES (1, 'An older thought that initializes the cursor', ?, 'fountain_insight')",
        (time.time()-100,),
    )
    cx.commit()
    cx.close()
    return dynamic_path, beliefs_path


def test_poster_enqueue_uses_shared_writer_and_reader(tmp_path):
    dynamic_path, beliefs_path = _dbs(tmp_path)
    d_reader = Reader(dynamic_path)
    d_writer = Writer(dynamic_path, name="poster-test-dynamic")
    b_reader = Reader(beliefs_path)
    poster = PostLoop(
        _Client(), dynamic_path,
        dynamic_reader=d_reader, dynamic_writer=d_writer, beliefs_reader=b_reader,
    )
    try:
        poster.enqueue_tick()  # initialize HWM; no backfill
        marker = d_reader.read_one(
            "SELECT value FROM daemon_kv WHERE key=?",
            ("moltbook_last_belief_id",),
        )
        assert marker["value"] == "1"
        cx = connect(beliefs_path)
        cx.execute(
            "INSERT INTO beliefs VALUES (2, 'A fresh reflection about patience and attention', ?, 'fountain_insight')",
            (time.time(),),
        )
        cx.commit()
        cx.close()
        poster.enqueue_tick()
        queued = d_reader.read_one(
            "SELECT thought_id, status FROM moltbook_post_queue"
        )
        assert queued["thought_id"] == 2
        assert queued["status"] == "pending"
        marker = d_reader.read_one(
            "SELECT value FROM daemon_kv WHERE key=?",
            ("moltbook_last_belief_id",),
        )
        assert marker["value"] == "2"
    finally:
        d_writer.close()


def test_poster_post_tick_uses_shared_writer(tmp_path, monkeypatch):
    dynamic_path, beliefs_path = _dbs(tmp_path)
    cx = connect(dynamic_path)
    cx.execute(
        "INSERT INTO moltbook_post_queue "
        "(thought_id, content, queued_at, status, word_count, droplet) "
        "VALUES (2, 'A thought about patience and attention.', ?, 'pending', 6, NULL)",
        (time.time(),),
    )
    cx.commit()
    cx.close()
    d_reader = Reader(dynamic_path)
    d_writer = Writer(dynamic_path, name="poster-post-test")
    b_reader = Reader(beliefs_path)
    poster = PostLoop(
        _Client(), dynamic_path,
        dynamic_reader=d_reader, dynamic_writer=d_writer, beliefs_reader=b_reader,
    )
    monkeypatch.setattr(poster, "_refresh_submolts", lambda force: None)
    try:
        poster.post_tick()
        post = d_reader.read_one("SELECT post_id, status FROM moltbook_posts")
        assert post["post_id"] == "post-1"
        assert post["status"] == "posted"
        queue = d_reader.read_one("SELECT status FROM moltbook_post_queue WHERE thought_id=2")
        assert queue["status"] == "posted"
    finally:
        d_writer.close()
