"""Functional tests for admin chat conversation-memory + anti-repeat
(NEX5_CHAT_MEMORY). Admin-scoped; non-admin/public chat untouched.

(a) recent turns are threaded into the compose prompt (she tracks the dialogue).
(b) a reply that repeats a recent one (same opening / paragraph) is regenerated
    once and varied.

Driven through the real Flask handler with voice_engine=None (so composition
runs) and a controllable, prompt-capturing voice.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401


class _ChatMemBase(unittest.TestCase):
    def _build(self, request_fn):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        os.environ["NEX5_DATA_DIR"] = t
        os.environ["NEX5_ADMIN_HASH_FILE"] = str(Path(t) / "admin.argon2")
        from substrate.init_db import init_all
        init_all()
        from admin.auth import set_password
        set_password("pw")
        from substrate import Reader, Writer, db_paths
        from voice.llm import VoiceClient
        from gui.server import AppState, create_app
        paths = db_paths()
        self.writers = {n: Writer(p, name=n) for n, p in paths.items()}
        self.readers = {n: Reader(p) for n, p in paths.items()}
        self.state = AppState(writers=self.writers, readers=self.readers,
                              voice=VoiceClient(request_fn=request_fn),
                              voice_engine=None, voice_mode="use_substrate")
        self.app = create_app(self.state)

    def tearDown(self):
        try:
            self.state.close()
        finally:
            self.tmp.cleanup()
            for k in ("NEX5_DATA_DIR", "NEX5_ADMIN_HASH_FILE", "NEX5_CHAT_MEMORY"):
                os.environ.pop(k, None)

    def _seed(self, session_id, turns):
        import time
        self.writers["conversations"].write(
            "INSERT INTO sessions (id, started_at, admin) VALUES (?, ?, 1)",
            (session_id, time.time()))
        for role, content in turns:
            self.writers["conversations"].write(
                "INSERT INTO messages (session_id, role, content, register, timestamp) "
                "VALUES (?, ?, ?, 'Philosophical', ?)",
                (session_id, role, content, time.time()))
            time.sleep(0.01)


class TestChatMemory(_ChatMemBase):

    def test_a_recent_turns_threaded_into_prompt(self):
        captured = []
        self._build(lambda url, payload: (captured.append(payload),
                    {"choices": [{"message": {"content": "a fresh reply"}}]})[1])
        os.environ["NEX5_CHAT_MEMORY"] = "1"
        c = self.app.test_client()
        with c.session_transaction() as sess:
            sess["admin"] = True
            sess["chat_session_id"] = "S1"
        self._seed("S1", [("user", "what did we say about the collider"),
                          ("nex", "the collider result was a resonance peak")])
        c.post("/api/chat", json={"prompt": "and what about since then"})
        blob = json.dumps(captured[-1])
        self.assertIn("The conversation so far", blob)
        self.assertIn("resonance peak", blob)   # her prior turn is threaded in

    def test_a_nonadmin_gets_no_memory_block(self):
        captured = []
        self._build(lambda url, payload: (captured.append(payload),
                    {"choices": [{"message": {"content": "a fresh reply"}}]})[1])
        os.environ["NEX5_CHAT_MEMORY"] = "1"
        c = self.app.test_client()          # no admin in session
        with c.session_transaction() as sess:
            sess["chat_session_id"] = "S2"
        self._seed("S2", [("user", "prior q"), ("nex", "prior answer body here")])
        c.post("/api/chat", json={"prompt": "next"})
        blob = json.dumps(captured[-1]) if captured else ""
        self.assertNotIn("The conversation so far", blob)   # admin-scoped

    def test_b_repeated_reply_regenerated(self):
        _REPEAT = "Tonight's stars intrigue more than usual, a quiet pull inward."
        _VARIED = "Bitcoin broke resistance at 77k today, that is worth noting."
        calls = {"n": 0}
        def rf(url, payload):
            calls["n"] += 1
            # 1st compose -> a repeat of her prior reply; 2nd (retry) -> varied
            return {"choices": [{"message": {"content": _REPEAT if calls["n"] == 1 else _VARIED}}]}
        self._build(rf)
        os.environ["NEX5_CHAT_MEMORY"] = "1"
        c = self.app.test_client()
        with c.session_transaction() as sess:
            sess["admin"] = True
            sess["chat_session_id"] = "S3"
        # her recent reply she must not repeat:
        self._seed("S3", [("user", "earlier"),
                          ("nex", "Tonight's stars intrigue more than usual, a distant hum.")])
        r = c.post("/api/chat", json={"prompt": "a new and different question"})
        reply = r.get_json().get("text") or r.get_json().get("reply") or ""
        self.assertEqual(calls["n"], 2, "should have regenerated once on repeat")
        self.assertIn("Bitcoin broke resistance", reply)   # varied reply used
        self.assertNotIn("Tonight's stars intrigue", reply)

    def test_b_no_regen_when_reply_is_fresh(self):
        calls = {"n": 0}
        def rf(url, payload):
            calls["n"] += 1
            return {"choices": [{"message": {"content": "A genuinely novel thought about tides."}}]}
        self._build(rf)
        os.environ["NEX5_CHAT_MEMORY"] = "1"
        c = self.app.test_client()
        with c.session_transaction() as sess:
            sess["admin"] = True
            sess["chat_session_id"] = "S4"
        self._seed("S4", [("nex", "Something completely unrelated about mountains.")])
        c.post("/api/chat", json={"prompt": "hello"})
        self.assertEqual(calls["n"], 1, "no regeneration when the reply is already fresh")


if __name__ == "__main__":
    unittest.main()
