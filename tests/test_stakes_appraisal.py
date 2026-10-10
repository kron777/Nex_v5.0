"""L4_stakes: bounded self-referent cost + its wiring into readiness.

Default OFF (NEX5_STAKES unset) -> readiness is unchanged. ON -> a bounded,
clamped cost is subtracted when recent fires drift into template. ANALOGUE.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from unittest.mock import MagicMock

from tests._bootstrap import *  # noqa: F401, F403

# A thought that matches stakes_monitor's template patterns (>=15 words).
_TEMPLATE = ("I notice the transient nature of all things as each passing moment "
             "reminds me the world keeps turning onward and onward still today")
# A grounded, non-template thought (>=15 words).
_CONCRETE = ("Bitcoin dropped three percent today after the exchange posted its "
             "outage notice and several traders began repositioning their books quickly")


class TestAppraise(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nex5_stk_")
        os.environ["NEX5_DATA_DIR"] = self.tmp
        from substrate.init_db import init_all
        init_all()
        from substrate import Writer, db_paths
        self.dw = Writer(str(db_paths()["dynamic"]), name="dynamic")

    def tearDown(self):
        try:
            self.dw.close()
        except Exception:
            pass
        os.environ.pop("NEX5_DATA_DIR", None)
        os.environ.pop("NEX5_STAKES", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _fire(self, thought, ts):
        self.dw.write(
            "INSERT INTO fountain_events (ts, thought, readiness) VALUES (?, ?, ?)",
            (float(ts), thought, 0.5))

    def test_drift_produces_bounded_cost(self):
        from theory_x.stage_tom.stakes_appraisal import appraise, _COST_CLAMP
        now = time.time()
        for k in range(8):
            self._fire(_TEMPLATE, now - (8 - k) * 60)
        self.dw.close()
        a = appraise()
        self.assertTrue(a["stakes_active"])
        self.assertGreater(a["cost"], 0.0)
        self.assertLessEqual(a["cost"], _COST_CLAMP)   # welfare bound

    def test_world_contact_has_zero_cost(self):
        from theory_x.stage_tom.stakes_appraisal import appraise
        now = time.time()
        for k in range(8):
            self._fire(_CONCRETE + f" item {k}", now - (8 - k) * 60)
        self.dw.close()
        a = appraise()
        self.assertFalse(a["stakes_active"])
        self.assertEqual(a["cost"], 0.0)

    def test_empty_is_fail_safe_zero(self):
        from theory_x.stage_tom.stakes_appraisal import appraise
        a = appraise()  # no fires
        self.assertEqual(a["cost"], 0.0)
        self.assertFalse(a["stakes_active"])


class TestReadinessPenalty(unittest.TestCase):

    def test_bounded_nonpositive(self):
        from theory_x.stage_tom.stakes_appraisal import readiness_penalty, _COST_CLAMP
        self.assertEqual(readiness_penalty(0.0), 0.0)
        self.assertEqual(readiness_penalty(-5.0), 0.0)           # cost can't be negative
        self.assertAlmostEqual(readiness_penalty(0.1), -0.1)
        self.assertEqual(readiness_penalty(10.0), -_COST_CLAMP)  # clamped


class TestReadinessWiring(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nex5_stkr_")
        os.environ["NEX5_DATA_DIR"] = self.tmp
        from substrate.init_db import init_all
        init_all()
        from substrate import Writer, Reader, db_paths
        self.dw = Writer(str(db_paths()["dynamic"]), name="dynamic")
        self.br = Reader(str(db_paths()["beliefs"]))
        now = time.time()
        for k in range(8):                       # drift the fire stream
            self.dw.write("INSERT INTO fountain_events (ts, thought, readiness) "
                          "VALUES (?, ?, ?)", (now - (8 - k) * 60, _TEMPLATE, 0.5))
        self.dw.close()

    def tearDown(self):
        os.environ.pop("NEX5_DATA_DIR", None)
        os.environ.pop("NEX5_STAKES", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _score(self):
        from theory_x.stage6_fountain.readiness import ReadinessEvaluator
        ds = MagicMock()
        ds.status.return_value = {"branches": [], "consolidation_active": False}
        return ReadinessEvaluator().score(ds, self.br, last_fire_ts=0.0)

    def test_stakes_off_no_penalty_on_subtracts(self):
        os.environ.pop("NEX5_STAKES", None)
        off = self._score()
        os.environ["NEX5_STAKES"] = "1"
        on = self._score()
        self.assertLess(on, off)                 # the drift cost was subtracted
        self.assertAlmostEqual(off - on, 0.2, places=3)  # == _COST_CLAMP for full drift


if __name__ == "__main__":
    unittest.main()
