"""Functional test for HYBRID admin+operator chat routing.

Admin+flag: RAG still runs, but a hit is fed into the composition prompt as
grounding and the reply is COMPOSED from it (grounding AND operator stance) —
not returned verbatim. Non-admin: RAG hit returned verbatim, unchanged.

Drives the real Flask handler with a fake voice_engine (returns a hit) and a
prompt-capturing voice, so we can assert both what grounds the compose prompt
and what the reply actually is.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

_RAG_HIT = "RAGHIT_DISTINCTIVE_BELIEF about the collider resonance."
_COMPOSED = "COMPOSED_OPERATOR_COLOURED_REPLY"

_DOC = """# INTAKE
## 1 · Who you are
  › Call me Jon. I am the architect.
## 5 · How you want her to be with you
  › Casual, easy.
"""


class _FakeVE:
    name = "voice_engine"
    def query_reply(self, query=None, session_id=None, turn_n=0):
        return {"content": _RAG_HIT, "score": 1.0, "source": "belief", "belief_id": 1}


class TestOperatorHybrid(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        tmp = cls._tmp.name
        os.environ["NEX5_DATA_DIR"] = tmp
        os.environ["NEX5_ADMIN_HASH_FILE"] = str(Path(tmp) / "admin.argon2")
        cls._docf = Path(tmp) / "op.md"
        cls._docf.write_text(_DOC)
        os.environ["NEX5_OPERATOR_DOC"] = str(cls._docf)

        from substrate.init_db import init_all
        init_all()
        from admin.auth import set_password
        set_password("pw")
        from substrate import Reader, Writer, db_paths
        from voice.llm import VoiceClient
        from gui.server import AppState, create_app

        cls.captured = []
        def _cap(url, payload):
            cls.captured.append(payload)
            return {"choices": [{"message": {"content": _COMPOSED}}]}

        paths = db_paths()
        cls.writers = {n: Writer(p, name=n) for n, p in paths.items()}
        cls.readers = {n: Reader(p) for n, p in paths.items()}
        cls.state = AppState(
            writers=cls.writers, readers=cls.readers,
            voice=VoiceClient(request_fn=_cap),
            voice_engine=_FakeVE(), voice_mode="use_substrate",
        )
        cls.app = create_app(cls.state)

    @classmethod
    def tearDownClass(cls):
        cls.state.close()
        cls._tmp.cleanup()
        for k in ("NEX5_DATA_DIR", "NEX5_ADMIN_HASH_FILE", "NEX5_OPERATOR_DOC",
                  "NEX5_OPERATOR_MODEL"):
            os.environ.pop(k, None)

    def _payload_str(self):
        import json
        return json.dumps(self.captured[-1]) if self.captured else ""

    def test_admin_flag_hybrid_grounds_and_composes(self):
        os.environ["NEX5_OPERATOR_MODEL"] = "1"
        self.captured.clear()
        c = self.app.test_client()
        r = c.post("/api/admin/login", json={"password": "pw"})
        self.assertTrue(r.get_json().get("authenticated"))
        r = c.post("/api/chat", json={"prompt": "tell me about the collider"})
        reply = r.get_json().get("reply") or r.get_json().get("text") or ""
        # composed, NOT the RAG hit verbatim
        self.assertIn(_COMPOSED, reply)
        self.assertNotEqual(reply.strip(), _RAG_HIT)
        # the compose prompt was GROUNDED in the RAG hit AND carried the operator block
        payload = self._payload_str()
        self.assertIn("RAGHIT_DISTINCTIVE_BELIEF", payload, "RAG hit not fed into compose (no grounding)")
        self.assertIn("held read of your architect", payload, "operator block missing from admin compose")

    def test_nonadmin_gets_rag_verbatim_unchanged(self):
        os.environ["NEX5_OPERATOR_MODEL"] = "1"
        self.captured.clear()
        c = self.app.test_client()   # fresh session, no admin login
        r = c.post("/api/chat", json={"prompt": "tell me about the collider"})
        reply = r.get_json().get("reply") or r.get_json().get("text") or ""
        # non-admin: RAG hit returned verbatim; composition (voice) never called
        self.assertIn("RAGHIT_DISTINCTIVE_BELIEF", reply)
        self.assertEqual(self.captured, [], "voice.speak should not run for non-admin RAG hit")

    def test_flag_off_admin_gets_rag_verbatim(self):
        os.environ.pop("NEX5_OPERATOR_MODEL", None)
        self.captured.clear()
        c = self.app.test_client()
        c.post("/api/admin/login", json={"password": "pw"})
        r = c.post("/api/chat", json={"prompt": "tell me about the collider"})
        reply = r.get_json().get("reply") or r.get_json().get("text") or ""
        self.assertIn("RAGHIT_DISTINCTIVE_BELIEF", reply)   # verbatim, flag off
        self.assertEqual(self.captured, [])


if __name__ == "__main__":
    unittest.main()
