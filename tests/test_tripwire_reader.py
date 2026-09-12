"""Tests for tools/check_tripwires._driver_context — the maxDF* attractor-vs-
register discriminator (R73: burst ratio + branch entropy).

This is a READING aid, not wired into the alarm (the maxDF* recalibration was
STOPPED — see session report: with the attractors decayed, burst+entropy no
longer separate them from register on live data, so shipping a refit would
defang). These tests document that the discriminator DOES separate a synthetic
single-story collapse (bursty + branch-concentrated) from standing register
(flat + branch-spread) on controlled data — the property a future refit needs,
provable only against a live attractor.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest

from tests import _bootstrap  # noqa: F401

import tools.check_tripwires as ct  # noqa: E402


class TestDriverContext(unittest.TestCase):

    def setUp(self):
        # fresh isolated DB per test (never the live soak DBs)
        self.tmp = tempfile.mkdtemp(prefix="nex5_tripwire_")
        os.environ["NEX5_DATA_DIR"] = self.tmp
        from substrate.init_db import init_all
        init_all()
        from substrate import Writer, db_paths
        self.w = Writer(db_paths()["beliefs"], name="beliefs")
        self._orig = ct._BELIEFS
        ct._BELIEFS = str(db_paths()["beliefs"])  # point the tool at our DB

    def tearDown(self):
        ct._BELIEFS = self._orig
        try:
            self.w.close()
        except Exception:
            pass
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.pop("NEX5_DATA_DIR", None)

    def _add(self, content, branch, day_offset):
        # created_at spread across days; >=5 docs/day so days count
        ts = time.time() - day_offset * 86400
        self.w.write(
            "INSERT INTO beliefs (content, tier, confidence, created_at, source, branch_id, locked) "
            "VALUES (?, 6, 0.6, ?, 'fountain_insight', ?, 0)",
            (content, ts, branch),
        )
        time.sleep(0.004)

    def _seed_baseline(self):
        # 6 docs/day for 6 days across many branches, no target token
        branches = ["ai_research", "crypto", "markets", "history", "language", "psychology"]
        for d in range(6):
            for i in range(6):
                self._add(f"a filler observation number {d}{i} about assorted matters",
                          branches[i % len(branches)], d)

    def test_collapse_token_is_bursty_and_concentrated(self):
        self._seed_baseline()
        # a single-story collapse: 'zebrastory' simmers low on days 1-5 then
        # SPIKES on day 0, all in ONE branch -> high burst + low branch entropy
        for d in range(1, 6):
            self._add(f"zebrastory a passing mention number {d}", "crypto", d)
        for i in range(8):
            self._add(f"zebrastory zebrastory dominates the corpus today take {i}", "crypto", 0)
        ctx = ct._driver_context("zebrastory", window_days=30)
        self.assertIsNotNone(ctx["burst"])
        self.assertGreaterEqual(ctx["burst"], 3.0)          # spiked vs its own baseline
        self.assertLess(ctx["branch_entropy"], 0.55)         # one branch

    def test_register_token_is_flat_and_spread(self):
        # 'systemsy' appears steadily every day across all branches
        branches = ["ai_research", "crypto", "markets", "history", "language", "psychology"]
        for d in range(6):
            for i in range(6):
                self._add(f"systemsy reflection {d}{i} on the nature of things",
                          branches[i % len(branches)], d)
        ctx = ct._driver_context("systemsy", window_days=30)
        self.assertIsNotNone(ctx["burst"])
        self.assertLess(ctx["burst"], 3.0)                   # steady, no spike
        self.assertGreater(ctx["branch_entropy"], 0.9)       # all branches

    def test_absent_token_returns_none(self):
        self._seed_baseline()
        ctx = ct._driver_context("neverappears", window_days=30)
        self.assertIsNone(ctx["burst"])


if __name__ == "__main__":
    unittest.main()
