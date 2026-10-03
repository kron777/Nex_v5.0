"""Tests for the self-maintenance SHADOW regulator (Phase A, log-only).

The load-bearing property: a tick writes one row to self_maintain_shadow and
changes NOTHING in beliefs.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import time
import unittest

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_selfmaint_")
    os.environ["NEX5_DATA_DIR"] = tmp
    from substrate.init_db import init_all
    init_all()
    from substrate import Reader, Writer, db_paths
    p = db_paths()
    w = {k: Writer(p[k], name=k) for k in ("beliefs", "dynamic", "sense")}
    r = {k: Reader(p[k]) for k in ("beliefs", "dynamic", "sense")}
    return tmp, w, r


def _cleanup(tmp, writers):
    for w in writers.values():
        try:
            w.close()
        except Exception:
            pass
    shutil.rmtree(tmp, ignore_errors=True)
    os.environ.pop("NEX5_DATA_DIR", None)


def _beliefs_hash(reader) -> str:
    rows = reader.read("SELECT * FROM beliefs ORDER BY id")
    return hashlib.sha256(json.dumps([tuple(r) for r in rows], default=str).encode()).hexdigest()


class TestCounts(unittest.TestCase):
    def test_would_pause_count(self):
        from theory_x.stage_self_maintain.shadow import CAP, would_pause_count, would_unpause_count
        self.assertEqual(would_pause_count(100, None), 0)
        self.assertEqual(would_pause_count(100, 100.0), 0)
        self.assertEqual(would_pause_count(100, 150.0), 0)          # below setpoint: no pause
        self.assertEqual(would_pause_count(150, 100.0), 5)          # 0.1 * 50
        self.assertEqual(would_pause_count(10_000, 100.0), CAP)     # capped
        self.assertEqual(would_unpause_count(100, 150.0), 5)
        self.assertEqual(would_unpause_count(150, 100.0), 0)


class TestTick(unittest.TestCase):
    def setUp(self):
        self.tmp, self.w, self.r = _make_env()
        from theory_x.stage_self_maintain.shadow import SelfMaintainShadow
        self.now = time.time()
        old = int(self.now - 72 * 3600)
        bw = self.w["beliefs"]
        ins = ("INSERT INTO beliefs (content, tier, confidence, created_at, source, branch_id, locked, paused) "
               "VALUES (?,?,?,?,?,?,?,?)")
        self.eligible = [bw.write(ins, (f"eligible {i}", 6, 0.001 * (i + 1), old, "fountain_insight", "systems", 0, 0))
                         for i in range(3)]
        self.excluded = [
            bw.write(ins, ("locked", 6, 0.0, old, "fountain_insight", "systems", 1, 0)),
            bw.write(ins, ("paused", 6, 0.0, old, "fountain_insight", "systems", 0, 1)),
            bw.write(ins, ("protected", 6, 0.0, old, "keystone_seed", "systems", 0, 0)),
            bw.write(ins, ("too young", 6, 0.0, int(self.now), "fountain_insight", "systems", 0, 0)),
            bw.write(ins, ("tier five", 5, 0.0, old, "fountain_insight", "systems", 0, 0)),
        ]
        bw.write("INSERT INTO dormant_beliefs (belief_id, last_active_at, dormancy_score, flagged_at) "
                 "VALUES (?,?,?,?)", (self.eligible[0], old, 0.9, self.now))
        self.shadow = SelfMaintainShadow(self.w["dynamic"], self.r["beliefs"], self.r["dynamic"], self.r["sense"])

    def tearDown(self):
        _cleanup(self.tmp, self.w)

    def _active(self):
        return self.r["beliefs"].read_one(
            "SELECT COUNT(*) AS n FROM beliefs WHERE tier <= 6 AND paused = 0")["n"]

    def test_tick_logs_and_changes_no_belief(self):
        before = _beliefs_hash(self.r["beliefs"])
        a = self._active()
        self.shadow._setpoint = lambda now: (float(a - 30), "test")   # deviation 30 -> n = 3
        rec = self.shadow.tick(now=self.now)
        self.assertEqual(_beliefs_hash(self.r["beliefs"]), before)   # nothing paused, nothing written
        self.assertEqual(rec["n_would_pause"], 3)
        ids = json.loads(rec["candidate_ids"])
        self.assertEqual(sorted(ids), sorted(self.eligible))
        for bad in self.excluded:
            self.assertNotIn(bad, ids)
        self.assertEqual(rec["n_in_dormant"], 1)
        self.assertEqual(rec["n_in_dormant_pending"], 1)
        rows = self.r["dynamic"].read("SELECT * FROM self_maintain_shadow")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["n_would_pause"], 3)

    def test_below_setpoint_selects_nothing(self):
        before = _beliefs_hash(self.r["beliefs"])
        a = self._active()
        self.shadow._setpoint = lambda now: (float(a + 100), "test")
        rec = self.shadow.tick(now=self.now)
        self.assertEqual(rec["n_would_pause"], 0)
        self.assertEqual(rec["n_would_unpause"], 10)
        self.assertEqual(json.loads(rec["candidate_ids"]), [])
        self.assertEqual(_beliefs_hash(self.r["beliefs"]), before)

    def test_first_tick_on_fresh_db(self):
        # Regression: _setpoint reads self_maintain_shadow, so the first tick on a DB
        # without the table must create it first, not fail.
        rec = self.shadow.tick(now=self.now)
        self.assertEqual(rec["setpoint_source"], "insufficient")
        self.assertEqual(rec["n_would_pause"], 0)
        self.assertEqual(len(self.r["dynamic"].read("SELECT id FROM self_maintain_shadow")), 1)

    def test_setpoint_from_interoception_then_insufficient(self):
        from theory_x.stage_self_maintain.shadow import _TABLE
        sw = self.w["sense"]
        self.w["dynamic"].write(_TABLE, ())
        self.assertEqual(self.shadow._setpoint(self.now), (None, "insufficient"))
        base = int(self.now) - 30 * 3600
        for h in range(30):
            payload = json.dumps({"tier_counts": {"3": 100 + h, "6": 900, "7": 5000}})
            sw.write("INSERT INTO sense_events (stream, payload, timestamp) VALUES (?,?,?)",
                     ("internal.interoception", payload, base + h * 3600))
        s, src = self.shadow._setpoint(self.now)
        self.assertEqual(src, "interoception")
        paused_le6 = self.r["beliefs"].read_one(
            "SELECT COUNT(*) AS n FROM beliefs WHERE tier <= 6 AND paused = 1")["n"]
        self.assertAlmostEqual(s, 1014.5 - paused_le6)      # median of 1000..1029 minus paused

    def test_setpoint_switches_to_own_log(self):
        a = self._active()
        self.shadow._setpoint_orig = self.shadow._setpoint
        for h in range(24):
            self.shadow._setpoint = lambda now: (float(a), "test")
            self.shadow.tick(now=self.now - (24 - h) * 3600)
        del self.shadow._setpoint                              # restore the real method
        s, src = self.shadow._setpoint(self.now)
        self.assertEqual(src, "own_log")
        self.assertEqual(s, float(a))


if __name__ == "__main__":
    unittest.main()
