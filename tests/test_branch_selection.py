"""Tests for _weighted_branch_pick (attention fix — gate-check finding).

The gate-check showed branch crediting was winner-take-top: cold branches
(history/language/psychology) sit at focus_num 0.19-0.47 (lifted off zero by the
starvation bonus) but got 0% of fires because selection took the single top
focus_num branch. This weights the pick by focus_num so a lifted cold branch can
occasionally win, while hot branches still usually win.

Env knob NEX5_BRANCH_TEMP: unset/<=0 -> exact top-pick (old behaviour); >0 ->
softmax(focus_num/temp) roulette. Fail-safe: any error -> top_pick.
"""
from __future__ import annotations

import os
import unittest

from tests import _bootstrap  # noqa: F401

from theory_x.stage6_fountain.generator import _weighted_branch_pick

_FLAG = "NEX5_BRANCH_TEMP"

# focus_num spread mirroring the live gate-check snapshot
_BRANCHES = [
    {"branch_id": "ai_research", "focus_num": 0.95},
    {"branch_id": "emerging_tech", "focus_num": 0.84},
    {"branch_id": "markets", "focus_num": 0.66},
    {"branch_id": "psychology", "focus_num": 0.47},
    {"branch_id": "language", "focus_num": 0.22},
    {"branch_id": "history", "focus_num": 0.19},
    {"branch_id": "systems", "focus_num": 0.003},
]


class TestWeightedBranchPick(unittest.TestCase):

    def setUp(self):
        self._prev = os.environ.get(_FLAG)

    def tearDown(self):
        if self._prev is None:
            os.environ.pop(_FLAG, None)
        else:
            os.environ[_FLAG] = self._prev

    # ---- default OFF: exact top-pick preserved ----
    def test_unset_returns_top_pick(self):
        os.environ.pop(_FLAG, None)
        self.assertEqual(_weighted_branch_pick(_BRANCHES, "ai_research"), "ai_research")

    def test_zero_temp_returns_top_pick(self):
        os.environ[_FLAG] = "0"
        self.assertEqual(_weighted_branch_pick(_BRANCHES, "ai_research"), "ai_research")

    def test_negative_temp_returns_top_pick(self):
        os.environ[_FLAG] = "-1"
        self.assertEqual(_weighted_branch_pick(_BRANCHES, "ai_research"), "ai_research")

    def test_unparseable_temp_returns_top_pick(self):
        os.environ[_FLAG] = "banana"
        self.assertEqual(_weighted_branch_pick(_BRANCHES, "ai_research"), "ai_research")

    # ---- weighting on: hot usually wins, cold occasionally surfaces ----
    def test_conservative_temp_hot_dominates_but_cold_surfaces(self):
        os.environ[_FLAG] = "0.35"
        import collections
        import random
        random.seed(1234)
        counts = collections.Counter(
            _weighted_branch_pick(_BRANCHES, "ai_research") for _ in range(4000)
        )
        top2 = counts["ai_research"] + counts["emerging_tech"]
        cold3 = counts["psychology"] + counts["language"] + counts["history"]
        # hot branches still win the majority...
        self.assertGreater(top2, 2000)
        # ...but the cold-3 now get a real, non-zero share (the whole point)
        self.assertGreater(cold3, 0)
        self.assertGreater(counts["psychology"], 0)

    def test_high_temp_more_uniform_than_low_temp(self):
        import collections
        import random

        def cold_share(temp, n=4000, seed=7):
            os.environ[_FLAG] = str(temp)
            random.seed(seed)
            c = collections.Counter(
                _weighted_branch_pick(_BRANCHES, "ai_research") for _ in range(n)
            )
            return (c["history"] + c["language"] + c["psychology"]) / n

        # a hotter temperature lifts the cold-branch share
        self.assertGreater(cold_share(1.0), cold_share(0.2))

    # ---- fail-safe ----
    def test_empty_branches_returns_top_pick(self):
        os.environ[_FLAG] = "0.35"
        self.assertEqual(_weighted_branch_pick([], "ai_research"), "ai_research")

    def test_branches_without_ids_return_top_pick(self):
        os.environ[_FLAG] = "0.35"
        self.assertEqual(
            _weighted_branch_pick([{"focus_num": 0.5}, {"focus_num": 0.1}], "ai_research"),
            "ai_research",
        )

    def test_only_one_branch_returns_it(self):
        os.environ[_FLAG] = "0.35"
        self.assertEqual(
            _weighted_branch_pick([{"branch_id": "solo", "focus_num": 0.4}], "solo"),
            "solo",
        )


if __name__ == "__main__":
    unittest.main()
