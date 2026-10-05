"""NEX5_PROBLEM_SELF_GATE — an N_branch signal opens a problem only if the
entity reaches >=2 branches WITHOUT her own self-sources (hot_observer quotes
of her fires; the grounded_scorecard self-belief). Repair 2026-10-05
(research log voice_collapse_2026-10-05). Flag off: unchanged.
"""
from __future__ import annotations

import json
import os
import time
import unittest

from tests import _bootstrap  # noqa: F401
from tests.test_fountain import _cleanup, _make_env

ENT = "Ethereum Layer"


class TestProblemSelfGate(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self._prev = os.environ.get("NEX5_PROBLEM_SELF_GATE")

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("NEX5_PROBLEM_SELF_GATE", None)
        else:
            os.environ["NEX5_PROBLEM_SELF_GATE"] = self._prev
        _cleanup(self.writers, self.tmp)

    def _belief(self, content, branch, source, t):
        self.writers["beliefs"].write(
            "INSERT INTO beliefs (content, tier, confidence, created_at, branch_id, source, locked) "
            "VALUES (?, 7, 0.7, ?, ?, ?, 0)", (content, int(t), branch, source))

    def _signal(self, branches, t):
        from theory_x.signals import signal_to_problem as S
        import sqlite3
        cx = sqlite3.connect(str(S.BELIEFS_DB))
        S._ensure_actioned_column(cx)
        cx.execute("INSERT INTO signals (detected_at, detector_name, signal_type, payload, confidence) "
                   "VALUES (?, 'co_occurrence', ?, ?, 0.7)",
                   (t, f"{len(branches)}_branch",
                    json.dumps({"entity": ENT, "branches": branches, "window_seconds": 1800, "contexts": []})))
        cx.commit(); cx.close()

    def _opened(self):
        from theory_x.signals import signal_to_problem as S
        S.signal_to_problem_tick()
        time.sleep(0.05)
        return [r["title"] for r in self.readers["conversations"].read("SELECT title FROM open_problems")]

    def _self_only_setup(self):
        now = time.time()
        self._belief(f"{ENT} network shuts down after fees fall", "crypto", "precipitated_from_sense", now - 100)
        self._belief(f"I notice this fire engaged the world directly (branch: markets): '{ENT} ...'",
                     "markets", "hot_observer", now - 50)
        time.sleep(0.05)
        self._signal(["crypto", "markets"], now)

    def test_flag_off_self_supported_signal_opens(self):
        os.environ.pop("NEX5_PROBLEM_SELF_GATE", None)
        self._self_only_setup()
        self.assertTrue(any(ENT in t for t in self._opened()))

    def test_flag_on_hot_observer_branch_does_not_count(self):
        os.environ["NEX5_PROBLEM_SELF_GATE"] = "1"
        self._self_only_setup()
        self.assertFalse(any(ENT in t for t in self._opened()))

    def test_flag_on_scorecard_branch_does_not_count(self):
        os.environ["NEX5_PROBLEM_SELF_GATE"] = "1"
        now = time.time()
        self._belief(f"{ENT} network shuts down after fees fall", "crypto", "precipitated_from_sense", now - 100)
        self._belief(f"My hourly market direction calls on {ENT} are worse than chance",
                     "systems", "grounded_scorecard:market_direction_v1", now - 50)
        time.sleep(0.05)
        self._signal(["crypto", "systems"], now)
        self.assertFalse(any(ENT in t for t in self._opened()))

    def test_flag_on_two_external_branches_opens(self):
        os.environ["NEX5_PROBLEM_SELF_GATE"] = "1"
        now = time.time()
        self._belief(f"{ENT} network shuts down after fees fall", "crypto", "precipitated_from_sense", now - 100)
        self._belief(f"Analysts debate what {ENT} closure means for rollups", "emerging_tech",
                     "precipitated_from_sense", now - 60)
        time.sleep(0.05)
        self._signal(["crypto", "emerging_tech"], now)
        self.assertTrue(any(ENT in t for t in self._opened()))


if __name__ == "__main__":
    unittest.main()
