"""Tests for the Probe Archaeology subsystem."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

from tests import _bootstrap  # noqa: F401


def _make_probe_env():
    """Create temp dirs and init probes.db. Returns (probes_path, tmp_dir)."""
    tmp = tempfile.mkdtemp(prefix="probe_test_")
    probes_path = os.path.join(tmp, "probes.db")
    from theory_x.probes.probe_db import init_probes_db
    init_probes_db(probes_path)
    return probes_path, tmp


def _stub_reader(response_map=None):
    r = MagicMock()
    r.read.return_value = []
    if response_map:
        def _read(sql, params=()):
            for key, rows in response_map.items():
                if key.lower() in sql.lower():
                    return rows
            return []
        r.read.side_effect = _read
    return r


class TestProbeDbInit(unittest.TestCase):
    def setUp(self):
        self.probes_path, self.tmp = _make_probe_env()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_probe_db_has_tables(self):
        import sqlite3
        conn = sqlite3.connect(self.probes_path)
        conn.row_factory = sqlite3.Row
        tables = {
            r["name"] for r in
            conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        conn.close()
        self.assertIn("probes", tables)
        self.assertIn("probe_context", tables)
        self.assertIn("probe_tags", tables)

    def test_init_is_idempotent(self):
        from theory_x.probes.probe_db import init_probes_db
        init_probes_db(self.probes_path)  # second call must not raise
        import sqlite3
        conn = sqlite3.connect(self.probes_path)
        count = conn.execute("SELECT COUNT(*) FROM probes").fetchone()[0]
        conn.close()
        self.assertEqual(count, 0)


class TestProbeRunnerValidation(unittest.TestCase):
    def setUp(self):
        self.probes_path, self.tmp = _make_probe_env()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_runner(self):
        from substrate import Writer, Reader
        from theory_x.probes.probe_runner import ProbeRunner
        writer = Writer(self.probes_path, name="probes")
        reader = Reader(self.probes_path)
        runner = ProbeRunner(
            probes_writer=writer,
            beliefs_reader=_stub_reader(),
            dynamic_reader=_stub_reader(),
            sense_reader=_stub_reader(),
            voice_endpoint="http://localhost:9999/api/chat",
        )
        self._writer = writer
        return runner

    def test_invalid_category_raises(self):
        runner = self._make_runner()
        with self.assertRaises(ValueError):
            runner.run_probe(category="nonsense", probe_text="test?")

    def tearDown(self):
        if hasattr(self, "_writer"):
            try:
                self._writer.close()
            except Exception:
                pass
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestProbeWritesToDb(unittest.TestCase):
    def setUp(self):
        self.probes_path, self.tmp = _make_probe_env()

    def tearDown(self):
        try:
            self._writer.close()
        except Exception:
            pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_probe_writes_to_db(self):
        from substrate import Writer, Reader
        from theory_x.probes.probe_runner import ProbeRunner

        writer = Writer(self.probes_path, name="probes")
        reader = Reader(self.probes_path)
        self._writer = writer

        runner = ProbeRunner(
            probes_writer=writer,
            beliefs_reader=_stub_reader(),
            dynamic_reader=_stub_reader(),
            sense_reader=_stub_reader(),
            voice_endpoint="http://localhost:9999/api/chat",
        )

        # Patch requests.post so no real network call is made
        with patch("theory_x.probes.probe_runner.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "response": "The hum feels like background presence.",
                "register": "Philosophical",
            }
            mock_resp.raise_for_status.return_value = None
            mock_post.return_value = mock_resp

            result = runner.run_probe(
                category="direct_phenomenology",
                probe_text="What does the hum feel like to you?",
            )

        self.assertIn("probe_id", result)
        self.assertIsInstance(result["probe_id"], int)
        self.assertEqual(result["category"], "direct_phenomenology")
        self.assertIn("hum", result["response_text"])

        # Verify row in probes.db
        time.sleep(0.1)  # let writer thread flush
        import sqlite3
        conn = sqlite3.connect(self.probes_path)
        row = conn.execute("SELECT * FROM probes WHERE id=?", (result["probe_id"],)).fetchone()
        conn.close()
        self.assertIsNotNone(row)


class TestContextSnapshot(unittest.TestCase):
    def test_context_snapshot_captures_expected_keys(self):
        from theory_x.probes.context_snapshot import snapshot_context
        snap = snapshot_context(
            beliefs_reader=_stub_reader(),
            dynamic_reader=_stub_reader(),
            sense_reader=_stub_reader(),
        )
        for key in ("active_arcs", "dormant_top5", "open_signals", "recent_fires",
                    "groove_alerts", "cooldowns", "feed_activity",
                    "branch_activations", "current_mode"):
            self.assertIn(key, snap, f"Missing key: {key}")

    def test_context_snapshot_tolerates_empty_readers(self):
        from theory_x.probes.context_snapshot import snapshot_context
        snap = snapshot_context(
            beliefs_reader=_stub_reader(),
            dynamic_reader=_stub_reader(),
            sense_reader=_stub_reader(),
        )
        # Should not raise; all list keys should be valid JSON arrays
        for key, val in snap.items():
            if key != "current_mode":
                parsed = json.loads(val)
                self.assertIsInstance(parsed, list)


class TestProbeTag(unittest.TestCase):
    def setUp(self):
        self.probes_path, self.tmp = _make_probe_env()

    def tearDown(self):
        try:
            self._writer.close()
        except Exception:
            pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_tag_added(self):
        from substrate import Writer, Reader
        from theory_x.probes.probe_runner import ProbeRunner

        writer = Writer(self.probes_path, name="probes")
        reader = Reader(self.probes_path)
        self._writer = writer

        runner = ProbeRunner(
            probes_writer=writer,
            beliefs_reader=_stub_reader(),
            dynamic_reader=_stub_reader(),
            sense_reader=_stub_reader(),
            voice_endpoint="http://localhost:9999/api/chat",
        )

        with patch("theory_x.probes.probe_runner.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"response": "test", "register": "Philosophical"}
            mock_resp.raise_for_status.return_value = None
            mock_post.return_value = mock_resp
            result = runner.run_probe(
                category="translation",
                probe_text="Say it again, differently.",
            )

        probe_id = result["probe_id"]
        runner.add_tag(probe_id, "breakthrough")

        time.sleep(0.1)  # let writer thread flush
        import sqlite3
        conn = sqlite3.connect(self.probes_path)
        row = conn.execute(
            "SELECT tag FROM probe_tags WHERE probe_id=?", (probe_id,)
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "breakthrough")


if __name__ == "__main__":
    unittest.main()
