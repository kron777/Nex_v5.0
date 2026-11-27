"""One-pen persistence tests for the Moltbook responder."""
from __future__ import annotations

from substrate import Reader, Writer, connect
from theory_x.stage7_moltbook.responder import DMResponder


class _UnusedClient:
    dry_run = True


def test_responder_uses_shared_dynamic_writer_and_readers(tmp_path):
    dynamic_path = tmp_path / "dynamic.db"
    beliefs_path = tmp_path / "beliefs.db"

    cx = connect(dynamic_path)
    cx.execute(
        "CREATE TABLE moltbook_pending_replies ("
        "id INTEGER PRIMARY KEY, conversation_id TEXT, message_id TEXT, content TEXT, "
        "from_agent TEXT, needs_human INTEGER, status TEXT, created_at REAL)"
    )
    cx.execute(
        "INSERT INTO moltbook_pending_replies VALUES "
        "(1, 'conv-1', 'msg-1', 'hello', 'agent-a', 1, 'new', 1.0)"
    )
    cx.commit()
    cx.close()

    cx = connect(beliefs_path)
    cx.execute(
        "CREATE TABLE beliefs (id INTEGER PRIMARY KEY, content TEXT, source TEXT, created_at REAL)"
    )
    cx.execute(
        "INSERT INTO beliefs VALUES (1, 'attention and memory are connected', 'spectrum', 1.0)"
    )
    cx.commit()
    cx.close()

    d_reader = Reader(dynamic_path)
    d_writer = Writer(dynamic_path, name="moltbook-responder-test")
    b_reader = Reader(beliefs_path)
    responder = DMResponder(
        _UnusedClient(), dynamic_path, beliefs_path,
        dynamic_reader=d_reader, dynamic_writer=d_writer, beliefs_reader=b_reader,
    )
    try:
        responder.tick()
        row = d_reader.read_one(
            "SELECT status FROM moltbook_pending_replies WHERE id=1"
        )
        assert row["status"] == "awaiting_human"
        assert responder._related_beliefs("attention and memory", k=2)
    finally:
        d_writer.close()
