"""Tests for the alobha (non-attachment) lever in the curiosity pick (NEX5_ALOBHA)."""
from __future__ import annotations

import os
import random
import shutil
import tempfile
import unittest

from tests import _bootstrap  # noqa: F401


class TestAlobha(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nex5_alobha_")
        os.environ["NEX5_DATA_DIR"] = self.tmp
        from substrate.init_db import init_all
        init_all()
        from theory_x.stage6_fountain import generator as g
        self.g = g
        self._orig_ctx = g._alobha_context
        self.items = ["quantum battery storage breakthrough announced in lab",
                      "central bank holds interest rates steady this quarter",
                      "volcanic eruption grounds flights across northern europe"]

    def tearDown(self):
        self.g._alobha_context = self._orig_ctx
        os.environ.pop("NEX5_ALOBHA", None)
        os.environ.pop("NEX5_DATA_DIR", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _pick(self, seed):
        random.seed(seed)
        return self.g._curiosity_pick(list(self.items))

    def test_penalty_math(self):
        g = self.g
        union = g._dedup_tokens(self.items[0])
        full = g._alobha_penalty(self.items[0], (union, g._ALOBHA_R_MED), 2.0)
        self.assertAlmostEqual(full, 2.0)                          # r = r_med, full containment
        self.assertAlmostEqual(g._alobha_penalty(self.items[0], (union, 2 * g._ALOBHA_R_MED), 2.0), 4.0)
        self.assertEqual(g._alobha_penalty(self.items[1], (union, g._ALOBHA_R_MED), 2.0), 0.0)
        self.assertEqual(g._alobha_penalty(self.items[0], (union, 0.0), 2.0), 0.0)
        self.assertEqual(g._alobha_penalty(self.items[0], (set(), 0.5), 2.0), 0.0)

    def test_flag_off_and_zero_penalty_identical(self):
        off = [self._pick(s) for s in range(40)]
        os.environ["NEX5_ALOBHA"] = "1"
        self.g._alobha_context = lambda: (set(), 0.5)              # nothing held -> no penalty
        self.assertEqual([self._pick(s) for s in range(40)], off)

    def test_gripped_candidate_loses(self):
        os.environ["NEX5_ALOBHA"] = "1"
        held = self.items[0]
        self.g._alobha_context = lambda: (self.g._dedup_tokens(held), 10 * self.g._ALOBHA_R_MED)
        picks = [self._pick(s) for s in range(40)]
        self.assertNotIn(held, picks)                               # strongly gripped -> never chosen
        self.assertTrue(set(picks) <= set(self.items[1:]))


if __name__ == "__main__":
    unittest.main()
