"""Round 11, item 1 — downtime as an experienced event.

Criterion (Beam): after a restart, a durable WITNESSED belief records the gap, and
the identity anchor's neighbourhood retrieval returns it. Pass = 1/1 per restart.

Pure fixture test: temp data dir + in-memory beliefs DB, no boot path.
"""
import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

from theory_x.memory import downtime as D


class _FakeWriter:
    def __init__(self, cx):
        self._cx = cx

    def write(self, sql, params=()):
        self._cx.execute(sql, params)
        self._cx.commit()


def _beliefs_db():
    cx = sqlite3.connect(":memory:")
    cx.row_factory = sqlite3.Row
    cx.execute(
        "CREATE TABLE beliefs (id INTEGER PRIMARY KEY, content TEXT, tier INTEGER, "
        "confidence REAL, created_at INTEGER, source TEXT, branch_id TEXT, locked INTEGER)"
    )
    return cx


class TestDowntimeRecord(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name
        self.snap = str(Path(self.dir) / "state_snapshot.json")
        self.cx = _beliefs_db()
        self.w = _FakeWriter(self.cx)

    def tearDown(self):
        self._tmp.cleanup()

    def _rows(self):
        return self.cx.execute(
            "SELECT content, source, tier FROM beliefs WHERE source=? ORDER BY id",
            (D.SOURCE,),
        ).fetchall()

    def test_clean_shutdown_writes_witnessed_record(self):
        t_off = time.time() - 3600  # offline an hour ago
        D.mark_clean_shutdown(self.dir, ts=t_off)
        res = D.record_boot(self.w, self.dir, self.snap, now=t_off + 3600)
        self.assertTrue(res["recorded"])
        self.assertEqual(res["reason"], "clean_standby")
        self.assertEqual(res["boot_count"], 1)
        self.assertAlmostEqual(res["duration_s"], 3600, delta=1)
        rows = self._rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source"], "self_downtime")
        self.assertEqual(rows[0]["tier"], 6)
        self.assertIn("offline", rows[0]["content"].lower())
        # marker consumed -> a second boot with no fresh marker is "unclean"
        self.assertIsNone(D._read_marker(self.dir))

    def test_unclean_falls_back_to_snapshot_mtime(self):
        # no marker; a snapshot file whose mtime is the last-alive heartbeat
        Path(self.snap).write_text("{}")
        past = time.time() - 1800
        os.utime(self.snap, (past, past))
        res = D.record_boot(self.w, self.dir, self.snap, now=past + 1800)
        self.assertTrue(res["recorded"])
        self.assertEqual(res["reason"], "unclean")
        self.assertAlmostEqual(res["offline_from"], past, delta=1)

    def test_blip_not_recorded(self):
        t = time.time()
        D.mark_clean_shutdown(self.dir, ts=t)
        res = D.record_boot(self.w, self.dir, self.snap, now=t + 2)  # 2s < 5s floor
        self.assertFalse(res["recorded"])
        self.assertEqual(res["reason"], "blip")
        self.assertEqual(len(self._rows()), 0)

    def test_first_boot_no_signal_not_recorded(self):
        res = D.record_boot(self.w, self.dir, self.snap, now=time.time())
        self.assertFalse(res["recorded"])
        self.assertEqual(res["reason"], "first_boot")

    def test_boot_count_increments(self):
        t = time.time()
        D.mark_clean_shutdown(self.dir, ts=t - 100)
        r1 = D.record_boot(self.w, self.dir, self.snap, now=t)
        D.mark_clean_shutdown(self.dir, ts=t + 100)
        r2 = D.record_boot(self.w, self.dir, self.snap, now=t + 200)
        self.assertEqual((r1["boot_count"], r2["boot_count"]), (1, 2))

    def test_source_maps_to_witnessed(self):
        from theory_x.life import affinity_loop as A
        self.assertAlmostEqual(A.PROVENANCE_BASE[D.SOURCE], A._WITNESSED, places=6)

    def test_anchor_neighbourhood_query_returns_record(self):
        # mirrors generator.py's downtime block retrieval
        D.mark_clean_shutdown(self.dir, ts=time.time() - 600)
        D.record_boot(self.w, self.dir, self.snap, now=time.time())
        got = self.cx.execute(
            "SELECT content FROM beliefs WHERE source='self_downtime' "
            "ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        self.assertIsNotNone(got)
        self.assertIn("boot #", got["content"])


if __name__ == "__main__":
    unittest.main()
