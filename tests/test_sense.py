"""Phase 2 smoke tests — sense stream.

Covers:
- Adapter base: submit() routes through Writer, not direct sqlite3
- Scheduler: starts paused (external), internal sensors always enabled
- start_all() / stop_all() / enable / disable
- Mock poll() events land in sense.db with correct columns
- GUI endpoints: /api/sense/status, /api/sense/start, /api/sense/stop,
  /api/sense/toggle/<id>, /api/sense/recent
- No live network calls — all external adapters use a mock request_fn
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

# ---- helpers ---------------------------------------------------------------

def _noop_fetch(url, params=None):
    return ""


def _rss_fetch(url, params=None):
    return """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Mock Feed</title>
    <item>
      <title>Test Entry</title>
      <link>https://example.com/test</link>
      <description>A test item</description>
      <pubDate>Wed, 23 Apr 2026 00:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>"""


def _make_env():
    """Create a temp DB env, init substrate, return (writers, readers, tmpdir)."""
    tmp = tempfile.mkdtemp(prefix="nex5_sense_")
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
        w.close()
    import shutil
    shutil.rmtree(tmp)
    os.environ.pop("NEX5_DATA_DIR", None)
    os.environ.pop("NEX5_ADMIN_HASH_FILE", None)


# ---- Adapter base class tests ----------------------------------------------

class TestAdapterBase(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_submit_writes_to_sense_db_via_writer(self):
        from theory_x.stage1_sense.feeds.reuters import Reuters
        adapter = Reuters(self.writers["sense"], request_fn=_rss_fetch)

        events = adapter.poll()
        self.assertGreater(len(events), 0)

        count = adapter.submit(events)
        self.assertGreater(count, 0)

        rows = self.readers["sense"].read("SELECT * FROM sense_events")
        self.assertEqual(len(rows), count)
        self.assertEqual(rows[0]["stream"], "news.reuters")

    def test_submit_stores_correct_columns(self):
        from theory_x.stage1_sense.base import SenseEvent
        from theory_x.stage1_sense.feeds.bbc_news import BBCNews

        adapter = BBCNews(self.writers["sense"], request_fn=_rss_fetch)
        ev = SenseEvent(
            stream="news.bbc",
            payload=json.dumps({"title": "test", "link": "https://test.com"}),
            provenance="https://feeds.bbci.co.uk/news/rss.xml",
            timestamp=1000000,
        )
        adapter.submit([ev])

        row = self.readers["sense"].read_one(
            "SELECT * FROM sense_events WHERE stream = 'news.bbc'"
        )
        self.assertIsNotNone(row)
        self.assertEqual(row["provenance"], "https://feeds.bbci.co.uk/news/rss.xml")
        self.assertEqual(row["timestamp"], 1000000)
        payload = json.loads(row["payload"])
        self.assertEqual(payload["title"], "test")

    def test_no_direct_sqlite3_outside_substrate(self):
        """Enforced structurally: only substrate/ may call sqlite3.connect."""
        import subprocess
        result = subprocess.run(
            [
                "grep", "-r", "sqlite3.connect",
                "/home/rr/Desktop/nex5",
                "--include=*.py",
                "--exclude-dir=.venv",
                "--exclude-dir=substrate",
                "--exclude-dir=tests",
                "--exclude-dir=strikes",
                "--exclude-dir=__pycache__",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.stdout.strip(), "",
            f"Direct sqlite3.connect found outside substrate/:\n{result.stdout}",
        )


# ---- Scheduler tests -------------------------------------------------------

class TestScheduler(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        if hasattr(self, "scheduler"):
            self.scheduler.shutdown()
        _cleanup(self.writers, self.tmp)

    def _build(self, adapters):
        from theory_x.stage1_sense.scheduler import SenseScheduler
        self.scheduler = SenseScheduler(adapters)
        return self.scheduler

    def test_starts_paused_for_external(self):
        from theory_x.stage1_sense.feeds.reuters import Reuters
        adapter = Reuters(self.writers["sense"], request_fn=_noop_fetch)
        sched = self._build([adapter])
        status = sched.status()
        self.assertFalse(status["global_running"])
        self.assertFalse(status["adapters"]["reuters"]["enabled"])

    def test_internal_sensors_always_enabled(self):
        from theory_x.stage1_sense.internal.temporal import Temporal
        adapter = Temporal(self.writers["sense"])
        sched = self._build([adapter])
        status = sched.status()
        self.assertTrue(status["adapters"]["temporal"]["enabled"])
        self.assertTrue(status["adapters"]["temporal"]["is_internal"])

    def test_start_all_enables_external(self):
        from theory_x.stage1_sense.feeds.reuters import Reuters
        from theory_x.stage1_sense.feeds.bbc_news import BBCNews
        adapters = [
            Reuters(self.writers["sense"], request_fn=_noop_fetch),
            BBCNews(self.writers["sense"],  request_fn=_noop_fetch),
        ]
        sched = self._build(adapters)
        sched.start_all()
        status = sched.status()
        self.assertTrue(status["global_running"])
        self.assertTrue(status["adapters"]["reuters"]["enabled"])
        self.assertTrue(status["adapters"]["bbc_news"]["enabled"])

    def test_stop_all_pauses_external(self):
        from theory_x.stage1_sense.feeds.reuters import Reuters
        adapter = Reuters(self.writers["sense"], request_fn=_noop_fetch)
        sched = self._build([adapter])
        sched.start_all()
        sched.stop_all()
        self.assertFalse(sched.status()["global_running"])

    def test_internal_unaffected_by_stop_all(self):
        from theory_x.stage1_sense.internal.temporal import Temporal
        adapter = Temporal(self.writers["sense"])
        sched = self._build([adapter])
        sched.start_all()
        sched.stop_all()
        self.assertTrue(sched.status()["adapters"]["temporal"]["enabled"])

    def test_per_adapter_disable_cannot_disable_internal(self):
        from theory_x.stage1_sense.internal.temporal import Temporal
        adapter = Temporal(self.writers["sense"])
        sched = self._build([adapter])
        with self.assertRaises(ValueError):
            sched.disable("temporal")

    def test_mock_poll_events_land_in_sense_db(self):
        from theory_x.stage1_sense.base import SenseEvent

        poll_called = threading.Event()

        class MockAdapter:
            id = "mock_feed"
            stream = "test.mock"
            poll_interval_seconds = 9999
            provenance = "mock://test"
            is_internal = False

            def __init__(self, writer):
                self._writer = writer
                self.enabled = False

            def poll(self):
                poll_called.set()
                return [SenseEvent(
                    stream=self.stream,
                    payload=json.dumps({"msg": "hello"}),
                    provenance=self.provenance,
                    timestamp=int(time.time()),
                )]

            def submit(self, events):
                from theory_x.stage1_sense.base import Adapter
                count = 0
                for ev in events:
                    self._writer.write(
                        "INSERT INTO sense_events "
                        "(stream, payload, provenance, timestamp) VALUES (?,?,?,?)",
                        (ev.stream, ev.payload, ev.provenance, ev.timestamp),
                    )
                    count += 1
                return count

        adapter = MockAdapter(self.writers["sense"])
        from theory_x.stage1_sense.scheduler import SenseScheduler, _AdapterThread
        import threading as _th
        global_run = _th.Event()
        t = _AdapterThread(adapter, global_run)
        t.enable()
        global_run.set()

        # Give the thread up to 2s to fire once.
        fired = poll_called.wait(timeout=2.0)
        self.assertTrue(fired, "mock adapter poll() was never called")

        time.sleep(0.1)  # let submit complete
        n = self.readers["sense"].count("sense_events")
        self.assertGreater(n, 0, "no events landed in sense.db")

        t.stop()


# ---- GUI sense endpoints ---------------------------------------------------

class TestSenseGUIEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.writers, cls.readers, cls.tmp = _make_env()

        from admin.auth import set_password
        set_password("sense-test-pw")

        from voice.llm import VoiceClient
        from theory_x.stage1_sense import build_scheduler
        from gui.server import AppState, create_app

        sched = build_scheduler(cls.writers, cls.readers)
        cls.scheduler = sched

        cls.state = AppState(
            writers=cls.writers,
            readers=cls.readers,
            voice=VoiceClient(request_fn=lambda u, p: {"choices": [{"message": {"content": "ok"}}]}),
            scheduler=sched,
        )
        cls.app = create_app(cls.state)
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.state.close()
        _cleanup(cls.writers, cls.tmp)

    def test_sense_status(self):
        r = self.client.get("/api/sense/status")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn("global_running", data)
        self.assertIn("adapters", data)
        self.assertEqual(len(data["adapters"]), 31)

    def test_sense_start(self):
        r = self.client.post("/api/sense/start")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["global_running"])

    def test_sense_stop(self):
        self.client.post("/api/sense/start")
        r = self.client.post("/api/sense/stop")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.get_json()["global_running"])

    def test_sense_toggle_external(self):
        # reuters starts enabled after start_all, then toggle disables it
        self.client.post("/api/sense/start")
        r = self.client.post("/api/sense/toggle/reuters")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        # toggled: enabled was True after start_all, now False
        self.assertFalse(data["enabled"])

        # toggle again -> enabled
        r2 = self.client.post("/api/sense/toggle/reuters")
        self.assertTrue(r2.get_json()["enabled"])

    def test_sense_toggle_internal_forbidden(self):
        r = self.client.post("/api/sense/toggle/temporal")
        self.assertEqual(r.status_code, 400)

    def test_sense_recent(self):
        r = self.client.get("/api/sense/recent?limit=10")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn("events", data)

    def test_no_scheduler_returns_503(self):
        from voice.llm import VoiceClient
        from gui.server import AppState, create_app
        state_no_sched = AppState(
            writers=self.writers,
            readers=self.readers,
            voice=VoiceClient(request_fn=lambda u, p: {"choices": [{"message": {"content": "ok"}}]}),
            scheduler=None,
        )
        app = create_app(state_no_sched)
        c = app.test_client()
        r = c.get("/api/sense/status")
        self.assertEqual(r.status_code, 503)


if __name__ == "__main__":
    unittest.main()
