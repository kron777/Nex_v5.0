"""nex_db_reaper — age-based pruning of observability logs (M4).

Exercises reap_table against a temp DB: rows older than the cutoff go, newer
rows stay, and the batched delete loop terminates. Points the reaper's DATA
dir at a temp location so nothing touches live data.
"""
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

import nex_db_reaper as reaper


class TestReaperObservabilityLogs(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig_data = reaper.DATA
        reaper.DATA = self._tmp.name
        self.db = Path(self._tmp.name) / "conversations.db"
        con = sqlite3.connect(str(self.db))
        con.execute(
            "CREATE TABLE drive_emergence_log "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, tick_at REAL NOT NULL)"
        )
        con.execute(
            "CREATE TABLE substrate_coherence "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL)"
        )
        self.now = int(time.time())
        old = self.now - 40 * 86400   # older than the 30d default
        recent = self.now - 1 * 86400
        con.executemany("INSERT INTO drive_emergence_log (tick_at) VALUES (?)",
                        [(old,)] * 5 + [(recent,)] * 3)
        # substrate_coherence uses a 90d window, so 40d is still "recent" here.
        con.executemany("INSERT INTO substrate_coherence (ts) VALUES (?)",
                        [(self.now - 120 * 86400,)] * 4 + [(recent,)] * 2)
        con.commit()
        con.close()

    def tearDown(self):
        reaper.DATA = self._orig_data
        self._tmp.cleanup()

    def _count(self, table):
        con = sqlite3.connect(str(self.db))
        try:
            return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        finally:
            con.close()

    def test_prunes_old_keeps_recent(self):
        cutoff = self.now - 30 * 86400
        deleted = reaper.reap_table(
            "conversations.db", "drive_emergence_log", "tick_at", cutoff
        )
        self.assertEqual(deleted, 5)
        self.assertEqual(self._count("drive_emergence_log"), 3)

    def test_generous_window_keeps_40d_rows(self):
        cutoff = self.now - 90 * 86400
        deleted = reaper.reap_table(
            "conversations.db", "substrate_coherence", "ts", cutoff
        )
        self.assertEqual(deleted, 4)              # only the 120d rows
        self.assertEqual(self._count("substrate_coherence"), 2)

    def test_targets_include_the_two_logs(self):
        tables = {(t[0], t[1]) for t in reaper.TARGETS}
        self.assertIn(("conversations.db", "drive_emergence_log"), tables)
        self.assertIn(("conversations.db", "substrate_coherence"), tables)


if __name__ == "__main__":
    unittest.main()
