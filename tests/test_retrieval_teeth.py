"""L4_teeth retrieval shift (NEX5_RETRIEVAL_TEETH): _fixation_teeth diverts the
credit+carry branch on fixation so a DIFFERENT branch seeds subsequent fires.

This is the MECHANICAL teeth (retrieval weight shift on fixation), distinct from the
frame-only r81 demotion. Default OFF at the call site -> no divert. ANALOGUE.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
import unittest

from tests._bootstrap import *  # noqa: F401, F403


class TestFixationTeeth(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nex5_rteeth_")
        self.db = os.path.join(self.tmp, "dynamic.db")
        self.sorted_b = [
            {"branch_id": "alpha", "focus_num": 0.9},
            {"branch_id": "beta", "focus_num": 0.5},
        ]

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _record(self, branch):
        con = sqlite3.connect(self.db)
        con.execute("CREATE TABLE IF NOT EXISTS recursion_attrib "
                    "(ts REAL PRIMARY KEY, nudge_active INTEGER, branch TEXT, "
                    "branch_prev TEXT, moved INTEGER)")
        con.execute("INSERT INTO recursion_attrib VALUES (?,?,?,?,?)",
                    (__import__("time").time(), 0, branch, "", 0))
        con.commit()
        con.close()

    def test_fixation_diverts_to_next_branch(self):
        from theory_x.stage6_fountain.generator import _fixation_teeth
        self._record("alpha")                         # previous fire seeded alpha
        out = _fixation_teeth(self.sorted_b, "alpha", dynamic_db=self.db)
        self.assertEqual(out, "beta")                 # fixation -> divert to the next real branch

    def test_no_fixation_leaves_pick(self):
        from theory_x.stage6_fountain.generator import _fixation_teeth
        self._record("alpha")                         # previous = alpha
        out = _fixation_teeth(self.sorted_b, "beta", dynamic_db=self.db)
        self.assertEqual(out, "beta")                 # pick != prev -> untouched

    def test_no_history_is_fail_safe(self):
        from theory_x.stage6_fountain.generator import _fixation_teeth
        # no recursion_attrib table at all -> fail-safe returns the pick
        out = _fixation_teeth(self.sorted_b, "alpha", dynamic_db=self.db)
        self.assertEqual(out, "alpha")

    def test_no_alternative_leaves_pick(self):
        from theory_x.stage6_fountain.generator import _fixation_teeth
        self._record("alpha")
        only = [{"branch_id": "alpha", "focus_num": 0.9}]   # nothing to divert to
        out = _fixation_teeth(only, "alpha", dynamic_db=self.db)
        self.assertEqual(out, "alpha")

    def test_zero_focus_alternative_is_skipped(self):
        from theory_x.stage6_fountain.generator import _fixation_teeth
        self._record("alpha")
        branches = [{"branch_id": "alpha", "focus_num": 0.9},
                    {"branch_id": "beta", "focus_num": 0.0}]  # beta has no focus
        out = _fixation_teeth(branches, "alpha", dynamic_db=self.db)
        self.assertEqual(out, "alpha")                # no positive-focus alternative


if __name__ == "__main__":
    unittest.main()
