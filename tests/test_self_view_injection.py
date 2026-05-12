"""Self-view context injection tests — Phase 39.

Verifies that SelfMindView.current_summary() and
SocialPresence.current_summary() are injected into the LLM prompt on
every chat turn. Six tests per Phase 39 spec.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_svi_")
    os.environ["NEX5_DATA_DIR"] = tmp
    os.environ["NEX5_ADMIN_HASH_FILE"] = str(Path(tmp) / "admin.argon2")
    from substrate.init_db import init_all
    init_all()
    from substrate import Reader, Writer, db_paths
    paths = db_paths()
    writers = {n: Writer(p, name=n) for n, p in paths.items()}
    readers = {n: Reader(p) for n, p in paths.items()}
    return writers, readers, tmp


def _cleanup(state, writers, tmp):
    state.close()
    for w in writers.values():
        try:
            w.close()
        except Exception:
            pass
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    os.environ.pop("NEX5_DATA_DIR", None)
    os.environ.pop("NEX5_ADMIN_HASH_FILE", None)


def _make_app(writers, readers, smv=None, sp=None):
    """Build a Flask test client with optional self-view nodes."""
    from gui.server import AppState, create_app
    from voice.llm import VoiceClient

    captured = []

    def _capture(url, payload):
        captured.append(payload)
        return {"choices": [{"message": {"content": "ok"}}]}

    state = AppState(
        writers=writers,
        readers=readers,
        voice=VoiceClient(request_fn=_capture),
        self_mind_view=smv,
        social_presence=sp,
    )
    app = create_app(state)
    client = app.test_client()
    return state, client, captured


def _seed_beliefs(writers, n=5):
    """Seed enough beliefs to clear the gap gate."""
    import time
    now = int(time.time())
    for i in range(n):
        writers["beliefs"].write(
            "INSERT INTO beliefs (content, tier, confidence, source, created_at, tags) "
            "VALUES (?, 7, 0.9, 'spectrum', ?, '[]')",
            (f"Awareness is primary and self-illuminating aspect {i}.", now - i),
        )
    import time as _t; _t.sleep(0.05)


# ── 1. SMV summary appears in the LLM user-message when self_mind_view is set ─

class TestSMVInjected(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        _seed_beliefs(self.writers)
        smv = MagicMock()
        smv.current_summary.return_value = "Holding 999 beliefs, no open problems."
        self.state, self.client, self.captured = _make_app(
            self.writers, self.readers, smv=smv
        )

    def tearDown(self):
        _cleanup(self.state, self.writers, self.tmp)

    def test_smv_summary_in_prompt(self):
        self.client.post("/api/chat", json={"prompt": "hello world"})
        self.assertTrue(self.captured, "no LLM call recorded")
        user_content = self.captured[-1]["messages"][-1]["content"]
        self.assertIn("Holding 999 beliefs", user_content)

    def test_smv_label_in_prompt(self):
        self.client.post("/api/chat", json={"prompt": "hello"})
        user_content = self.captured[-1]["messages"][-1]["content"]
        self.assertIn("Current cognitive state:", user_content)


# ── 2. SP summary appears in the LLM user-message when social_presence is set ─

class TestSPInjected(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        _seed_beliefs(self.writers)
        sp = MagicMock()
        sp.current_summary.return_value = "Currently engaged in 2 active conversations."
        self.state, self.client, self.captured = _make_app(
            self.writers, self.readers, sp=sp
        )

    def tearDown(self):
        _cleanup(self.state, self.writers, self.tmp)

    def test_sp_summary_in_prompt(self):
        self.client.post("/api/chat", json={"prompt": "hello"})
        user_content = self.captured[-1]["messages"][-1]["content"]
        self.assertIn("Currently engaged in 2 active conversations", user_content)

    def test_sp_label_in_prompt(self):
        self.client.post("/api/chat", json={"prompt": "hello"})
        user_content = self.captured[-1]["messages"][-1]["content"]
        self.assertIn("Current social posture:", user_content)


# ── 3. Both summaries injected together ───────────────────────────────────────

class TestBothInjected(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        _seed_beliefs(self.writers)
        smv = MagicMock()
        smv.current_summary.return_value = "SMV_MARKER"
        sp = MagicMock()
        sp.current_summary.return_value = "SP_MARKER"
        self.state, self.client, self.captured = _make_app(
            self.writers, self.readers, smv=smv, sp=sp
        )

    def tearDown(self):
        _cleanup(self.state, self.writers, self.tmp)

    def test_both_markers_present(self):
        self.client.post("/api/chat", json={"prompt": "hi"})
        user_content = self.captured[-1]["messages"][-1]["content"]
        self.assertIn("SMV_MARKER", user_content)
        self.assertIn("SP_MARKER", user_content)


# ── 4. Exception in current_summary() does not break chat ─────────────────────

class TestInjectionFaultTolerance(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        _seed_beliefs(self.writers)
        smv = MagicMock()
        smv.current_summary.side_effect = RuntimeError("db gone")
        sp = MagicMock()
        sp.current_summary.side_effect = RuntimeError("connection lost")
        self.state, self.client, self.captured = _make_app(
            self.writers, self.readers, smv=smv, sp=sp
        )

    def tearDown(self):
        _cleanup(self.state, self.writers, self.tmp)

    def test_chat_succeeds_despite_injection_errors(self):
        r = self.client.post("/api/chat", json={"prompt": "hi"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["text"], "ok")


# ── 5. Injection is always-on (non-introspective query) ──────────────────────

class TestInjectionAlwaysOn(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        _seed_beliefs(self.writers)
        smv = MagicMock()
        smv.current_summary.return_value = "ALWAYS_MARKER"
        self.state, self.client, self.captured = _make_app(
            self.writers, self.readers, smv=smv
        )

    def tearDown(self):
        _cleanup(self.state, self.writers, self.tmp)

    def test_non_introspective_query_still_gets_injection(self):
        # is_probe=True bypasses the gap gate so the LLM is always called.
        self.client.post(
            "/api/chat", json={"prompt": "what is the capital of France", "is_probe": True}
        )
        self.assertTrue(self.captured, "no LLM call recorded")
        user_content = self.captured[-1]["messages"][-1]["content"]
        self.assertIn("ALWAYS_MARKER", user_content)


# ── 6. Neither node present — chat proceeds without injection ─────────────────

class TestNoNodesNoInjection(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        _seed_beliefs(self.writers)
        self.state, self.client, self.captured = _make_app(
            self.writers, self.readers
        )

    def tearDown(self):
        _cleanup(self.state, self.writers, self.tmp)

    def test_chat_ok_without_nodes(self):
        r = self.client.post("/api/chat", json={"prompt": "hi"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["text"], "ok")


if __name__ == "__main__":
    unittest.main()
