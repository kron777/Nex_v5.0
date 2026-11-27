"""One-pen persistence tests for the Moltbook listener."""
from __future__ import annotations

import time

from substrate import Reader, Writer, connect
from theory_x.stage7_moltbook.listener import DMListenLoop


class _Client:
    dry_run = True

    def dm_check(self):
        return {"has_activity": True, "unread_messages": True}

    def dm_list_conversations(self):
        return [{
            "conversation_id": "conv-1",
            "with_agent": {"name": "Friend", "isClaimed": True, "karma": 500, "description": ""},
        }]

    def dm_read(self, conv_id):
        return {"messages": [{
            "id": "msg-1", "created_at": time.time(),
            "from": {"id": "friend-id", "name": "Friend"},
            "message": "A thoughtful question about attention.",
        }]}

    def dm_approve(self, conv_id):
        return True


def _dbs(tmp_path):
    dynamic_path = tmp_path / "dynamic.db"
    sense_path = tmp_path / "sense.db"
    cx = connect(dynamic_path)
    cx.execute(
        "CREATE TABLE moltbook_dms (conversation_id TEXT PRIMARY KEY, with_agent TEXT, "
        "last_msg_id TEXT, last_seen_ts REAL, approved INTEGER)"
    )
    cx.execute(
        "CREATE TABLE moltbook_pending_replies (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "conversation_id TEXT, message_id TEXT, content TEXT, from_agent TEXT, "
        "needs_human INTEGER, status TEXT, created_at REAL)"
    )
    cx.commit()
    cx.close()
    cx = connect(sense_path)
    cx.execute(
        "CREATE TABLE sense_events (id INTEGER PRIMARY KEY AUTOINCREMENT, stream TEXT, "
        "payload TEXT, provenance TEXT, timestamp INTEGER)"
    )
    cx.commit()
    cx.close()
    return dynamic_path, sense_path


def test_listener_routes_incoming_dm_to_shared_writers(tmp_path):
    dynamic_path, sense_path = _dbs(tmp_path)
    d_reader = Reader(dynamic_path)
    d_writer = Writer(dynamic_path, name="listener-test-dynamic")
    s_writer = Writer(sense_path, name="listener-test-sense")
    listener = DMListenLoop(
        _Client(), dynamic_path, sense_path,
        dynamic_reader=d_reader, dynamic_writer=d_writer, sense_writer=s_writer,
    )
    listener._self_agent_id = "self-id"
    listener._self_agent_name = "NEX"
    try:
        listener.tick()
        dm = d_reader.read_one(
            "SELECT with_agent, last_msg_id, approved FROM moltbook_dms WHERE conversation_id=?",
            ("conv-1",),
        )
        assert dm["with_agent"] == "Friend"
        assert dm["last_msg_id"] == "msg-1"
        assert dm["approved"] == 1
        pending = d_reader.read_one(
            "SELECT content, from_agent, status FROM moltbook_pending_replies"
        )
        assert pending["content"] == "A thoughtful question about attention."
        assert pending["from_agent"] == "Friend"
        assert pending["status"] == "new"
        sense = Reader(sense_path).read_one(
            "SELECT stream, provenance, payload FROM sense_events"
        )
        assert sense["stream"] == "moltbook_dm"
        assert sense["provenance"] == "moltbook:conv:conv-1"
        assert "msg-1" in sense["payload"]
    finally:
        d_writer.close()
        s_writer.close()
