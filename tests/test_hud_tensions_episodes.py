"""HUD read-only visibility for held_tensions and episodes (2026-11-08).

Pure GET, no write path, no admin gate needed (matches every other GET
endpoint -- the before_request mutation gate only checks mutating methods).
Uses a real Flask test_client against a disposable DB, same pattern as the
gui/server.py connection-leak fix smoke test.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests._bootstrap import *  # noqa: F401, F403


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_hud_te_")
    os.environ["NEX5_DATA_DIR"] = tmp
    os.environ["NEX5_ADMIN_HASH_FILE"] = str(Path(tmp) / "admin.argon2")
    from substrate.init_db import init_all
    init_all()
    from substrate import Reader, Writer, db_paths
    paths = db_paths()
    writers = {n: Writer(p, name=n) for n, p in paths.items()}
    readers = {n: Reader(p) for n, p in paths.items()}
    return writers, readers, tmp


def _cleanup(writers, tmp):
    for w in writers.values():
        try:
            w.close()
        except Exception:
            pass
    shutil.rmtree(tmp, ignore_errors=True)
    os.environ.pop("NEX5_DATA_DIR", None)
    os.environ.pop("NEX5_ADMIN_HASH_FILE", None)


def _seed_belief(writers, content):
    now = int(time.time())
    return writers["beliefs"].write(
        "INSERT INTO beliefs (content, tier, confidence, created_at, source, locked, paused) "
        "VALUES (?, 5, 0.65, ?, 'test', 0, 0)", (content, now),
    )


class TestHudEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.writers, cls.readers, cls.tmp = _make_env()
        from voice.llm import VoiceClient
        from gui.server import AppState, create_app
        cls.state = AppState(
            writers=cls.writers, readers=cls.readers,
            voice=VoiceClient(request_fn=lambda u, p: {"choices": [{"message": {"content": "ok"}}]}),
        )
        cls.app = create_app(cls.state)
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.state.close()
        _cleanup(cls.writers, cls.tmp)

    def tearDown(self):
        # setUpClass shares one DB across every test in this class -- clear
        # the two tables these tests write to so each test starts clean.
        self.writers["dynamic"].write("DELETE FROM held_tensions")
        self.writers["dynamic"].write("DELETE FROM episodes")

    def test_tensions_endpoint_empty_by_default(self):
        r = self.client.get("/api/harmonizer/tensions")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["tensions"], [])
        self.assertEqual(data["open_count"], 0)

    def test_episodes_endpoint_empty_by_default(self):
        r = self.client.get("/api/episodic/episodes")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["episodes"], [])

    def test_tensions_endpoint_shows_data_with_belief_content(self):
        a_id = _seed_belief(self.writers, "Markets trend upward over decades")
        b_id = _seed_belief(self.writers, "Markets do not trend upward over decades")
        self.writers["dynamic"].write(
            "INSERT INTO held_tensions (belief_id_a, belief_id_b, created_at) "
            "VALUES (?, ?, ?)", (a_id, b_id, time.time()),
        )
        r = self.client.get("/api/harmonizer/tensions")
        data = r.get_json()
        self.assertEqual(len(data["tensions"]), 1)
        self.assertEqual(data["open_count"], 1)
        t = data["tensions"][0]
        self.assertIsNone(t["resolved_at"])
        self.assertEqual(t["belief_a_content"], "Markets trend upward over decades")
        self.assertEqual(t["belief_b_content"], "Markets do not trend upward over decades")

    def test_tensions_endpoint_open_count_excludes_resolved(self):
        a_id = _seed_belief(self.writers, "p")
        b_id = _seed_belief(self.writers, "q")
        self.writers["dynamic"].write(
            "INSERT INTO held_tensions (belief_id_a, belief_id_b, created_at, resolved_at, resolved_reason) "
            "VALUES (?, ?, ?, ?, 'stale_retention')", (a_id, b_id, time.time() - 1000, time.time()),
        )
        r = self.client.get("/api/harmonizer/tensions")
        data = r.get_json()
        self.assertEqual(len(data["tensions"]), 1)
        self.assertEqual(data["open_count"], 0)

    def test_episodes_endpoint_shows_data(self):
        self.writers["dynamic"].write(
            "INSERT INTO episodes (created_at, source_kind, source_id, what, salience, "
            "affect_bound_at, affect_synthesis, recorded_at) "
            "VALUES (?, 'ghost_flag', 1, 'something happened', 0.9, ?, 'I am curious', ?)",
            (time.time(), time.time(), time.time()),
        )
        r = self.client.get("/api/episodic/episodes")
        data = r.get_json()
        self.assertEqual(len(data["episodes"]), 1)
        self.assertEqual(data["episodes"][0]["what"], "something happened")
        self.assertEqual(data["episodes"][0]["affect_synthesis"], "I am curious")

    def test_endpoints_require_no_admin_session(self):
        """Pure read -- must work with no admin login at all (unlike POST
        mutations, which 403 without one)."""
        r1 = self.client.get("/api/harmonizer/tensions")
        r2 = self.client.get("/api/episodic/episodes")
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)


if __name__ == "__main__":
    unittest.main()
