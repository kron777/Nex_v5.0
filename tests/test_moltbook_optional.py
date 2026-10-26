"""moltbook is optional: its tables exist only once the integration is set up.

On her fresh store (moltbook unwired, no credentials) the HUD's poll queried
moltbook_posts every few seconds and failed -- a 500, an error_channel record
and a NEX5_SCHEMA_TRIPWIRE hit per poll. The same missing table also aborted
daily_life's state snapshot before it read her focus and fire count. Every test
here runs with the tripwire ON and requires it to stay silent.
"""
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from tests import _bootstrap  # noqa: F401

from substrate import connect, table_exists

_MOLTBOOK_DDL = (
    "CREATE TABLE moltbook_posts (id INTEGER PRIMARY KEY, ts REAL, submolt TEXT, "
    "status TEXT, post_id TEXT, thought_id INTEGER)",
    "CREATE TABLE moltbook_pending_replies (id INTEGER PRIMARY KEY, created_at REAL, "
    "from_agent TEXT, content TEXT, status TEXT)",
)


def _mock_req(url, payload):
    return {"choices": [{"message": {"content": "mocked"}}]}


class _Store(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(os.environ, {
            "NEX5_DATA_DIR": self._tmp.name,
            "NEX5_ADMIN_HASH_FILE": str(Path(self._tmp.name) / "admin.argon2"),
            "NEX5_SCHEMA_TRIPWIRE": "1",
        })
        self._env.start()
        from substrate.init_db import init_all
        init_all()
        from substrate.paths import db_paths
        self.dyn = str(db_paths()["dynamic"])

    def tearDown(self):
        self._env.stop()
        self._tmp.cleanup()

    def _install_moltbook(self):
        c = connect(self.dyn)
        for ddl in _MOLTBOOK_DDL:
            c.execute(ddl)
        c.execute("INSERT INTO moltbook_posts VALUES (1, ?, 'nex', 'posted', 'p1', NULL)",
                  (time.time(),))
        c.execute("INSERT INTO moltbook_pending_replies VALUES (1, ?, 'agent_b', 'hi', 'new')",
                  (time.time(),))
        c.commit(); c.close()


class TestTableExists(_Store):

    def test_connection_and_reader(self):
        from substrate import Reader
        c = connect(self.dyn)
        try:
            self.assertTrue(table_exists(c, "fountain_events"))
            self.assertFalse(table_exists(c, "moltbook_posts"))
        finally:
            c.close()
        self.assertFalse(table_exists(Reader(self.dyn), "moltbook_posts"))


class TestHudMoltbookPoll(_Store):

    def _client(self):
        from gui.server import AppState, create_app
        from substrate import Reader, Writer, db_paths
        from voice.llm import VoiceClient
        paths = db_paths()
        self.state = AppState(
            writers={n: Writer(p, name=n) for n, p in paths.items()},
            readers={n: Reader(p) for n, p in paths.items()},
            voice=VoiceClient(request_fn=_mock_req))
        self.addCleanup(self.state.close)
        return create_app(self.state).test_client()

    def test_no_moltbook_schema_is_silent_200(self):
        client = self._client()
        with self.assertNoLogs("substrate.schema_tripwire", "ERROR"):
            for _ in range(3):                       # the HUD polls repeatedly
                r = client.get("/api/moltbook/chats")
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r.get_json(), {"events": []})

    def test_unchanged_when_moltbook_is_installed(self):
        self._install_moltbook()
        client = self._client()
        r = client.get("/api/moltbook/chats")
        self.assertEqual(r.status_code, 200)
        kinds = sorted(e["kind"] for e in r.get_json()["events"])
        self.assertEqual(kinds, ["dm_in", "post"])


class TestLifeLoopsWithoutMoltbook(_Store):

    def test_daily_snapshot_still_reads_focus_and_fires(self):
        from theory_x.life import daily_life as dl
        c = connect(self.dyn)
        c.execute("INSERT INTO current_focus (id, problem_id, picked_at) VALUES (1, 7, ?)",
                  (time.time(),))
        c.execute("INSERT INTO fountain_events (ts, thought, readiness) VALUES (?, 'a', 0.8)",
                  (time.time(),))
        c.commit(); c.close()
        with self.assertNoLogs("substrate.schema_tripwire", "ERROR"):
            snap = dl._state_snapshot()
        self.assertEqual(snap["moltbook_posts_24h"], 0)
        self.assertEqual(snap["focus_problem_id"], 7)     # was skipped before
        self.assertEqual(snap["fountain_fires_24h"], 1)   # morning said "?" before

    def test_identity_metrics_count_zero_posts(self):
        from theory_x.life import identity_loop as il
        with self.assertNoLogs("substrate.schema_tripwire", "ERROR"):
            m = il._gather_metrics(time.time())
        self.assertEqual(m["moltbook_6h"], 0)


if __name__ == "__main__":
    unittest.main()
