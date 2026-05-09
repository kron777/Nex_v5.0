"""Tests for theory_x.conversation_memory — ConversationMemory SentienceNode."""
from __future__ import annotations

import sqlite3
import tempfile
import time
import unittest

from tests._bootstrap import *  # noqa: F401, F403


def _make_db(messages=None):
    """Create a temp DB with conversations.db schema. Returns path."""
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    path = f.name
    f.close()
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE messages ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "session_id TEXT NOT NULL, "
        "role TEXT NOT NULL, "
        "content TEXT NOT NULL, "
        "register TEXT, "
        "timestamp REAL NOT NULL, "
        "tool_used TEXT"
        ")"
    )
    if messages:
        con.executemany(
            "INSERT INTO messages "
            "(session_id, role, content, register, timestamp) "
            "VALUES (?, ?, ?, ?, ?)",
            messages,
        )
    con.commit()
    con.close()
    return path


def _cm(n_turns=8, messages=None):
    from theory_x.conversation_memory import ConversationMemory
    path = _make_db(messages)
    return ConversationMemory(db_path=path, n_turns=n_turns)


class TestSentienceNodeProtocol(unittest.TestCase):

    def test_implements_sentience_node_protocol(self):
        from theory_x import SentienceNode
        from theory_x.conversation_memory import ConversationMemory
        instance = ConversationMemory(db_path=_make_db())
        self.assertIsInstance(instance, SentienceNode)

    def test_has_name_attribute(self):
        from theory_x.conversation_memory import ConversationMemory
        self.assertEqual(ConversationMemory.name, "conversation_memory")
        self.assertEqual(ConversationMemory(db_path=_make_db()).name, "conversation_memory")

    def test_tick_returns_dict_with_name(self):
        cm = _cm()
        result = cm.tick()
        self.assertIsInstance(result, dict)
        self.assertIn("name", result)
        self.assertEqual(result["name"], "conversation_memory")

    def test_tick_accepts_context_with_session_id(self):
        cm = _cm()
        result = cm.tick(context={"session_id": "abc123"})
        self.assertIsInstance(result, dict)
        self.assertIn("turns", result)

    def test_decay_is_noop(self):
        t = time.time()
        cm = _cm(messages=[("s1", "user", "hello", None, t - 30)])
        before = cm.state(session_id="s1")
        cm.decay(time.time())
        after = cm.state(session_id="s1")
        self.assertEqual(before["count"], after["count"])

    def test_state_returns_expected_fields(self):
        cm = _cm()
        s = cm.state(session_id="sess1")
        self.assertIn("name", s)
        self.assertIn("session_id", s)
        self.assertIn("turns", s)
        self.assertIn("count", s)


class TestConversationMemoryCore(unittest.TestCase):

    def _populated(self, n_turns=8):
        t = time.time()
        msgs = [
            ("sess1", "user", "what are you?",        "Conversational", t - 60),
            ("sess1", "nex",  "I am the attending...", "Philosophical",  t - 55),
            ("sess1", "user", "tell me more",          "Conversational", t - 30),
            ("sess1", "nex",  "The attending continues...", "Philosophical", t - 25),
            ("sess2", "user", "other session",         "Conversational", t - 10),
        ]
        return _cm(n_turns=n_turns, messages=msgs)

    def test_state_none_returns_empty(self):
        cm = _cm()
        s = cm.state(session_id=None)
        self.assertEqual(s["turns"], [])
        self.assertEqual(s["count"], 0)

    def test_empty_session_returns_empty(self):
        cm = _cm()
        s = cm.state(session_id="nonexistent")
        self.assertEqual(s["turns"], [])
        self.assertEqual(s["count"], 0)

    def test_chronological_order_oldest_first(self):
        cm = self._populated()
        turns = cm.state(session_id="sess1")["turns"]
        self.assertGreater(len(turns), 1)
        for i in range(len(turns) - 1):
            self.assertLessEqual(turns[i]["timestamp"], turns[i + 1]["timestamp"])

    def test_session_isolation(self):
        cm = self._populated()
        turns = cm.state(session_id="sess1")["turns"]
        contents = [t["content"] for t in turns]
        self.assertNotIn("other session", contents)

    def test_n_turns_limit_respected(self):
        t = time.time()
        msgs = [("s", "user", f"msg{i}", None, t - (20 - i)) for i in range(20)]
        cm = _cm(n_turns=4, messages=msgs)
        s = cm.state(session_id="s")
        self.assertLessEqual(s["count"], 4)

    def test_turns_contain_role_and_content(self):
        cm = self._populated()
        turns = cm.state(session_id="sess1")["turns"]
        for t in turns:
            self.assertIn("role", t)
            self.assertIn("content", t)
            self.assertIn(t["role"], ("user", "nex"))

    def test_count_matches_turns_length(self):
        cm = self._populated()
        s = cm.state(session_id="sess1")
        self.assertEqual(s["count"], len(s["turns"]))


if __name__ == "__main__":
    unittest.main()
