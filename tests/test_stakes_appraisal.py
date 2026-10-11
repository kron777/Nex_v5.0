"""L4_stakes: bounded self-referent cost + its wiring into readiness.

Default OFF (NEX5_STAKES unset) -> readiness is unchanged. ON -> a bounded,
clamped cost is subtracted when grooming RISES (r79 Path A: the cost is sourced
from the live groove detector's template_repetition rate, not the inert drift
ratio). The ratio instrument (appraise) is retained and still tested, but is not
wired into readiness. ANALOGUE.
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
    """The drift-RATIO instrument (retained, not wired — inert on live)."""

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


class TestAppraiseGroove(unittest.TestCase):
    """The Path-A (r79) grooming-ONSET cost — the one readiness actually uses."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nex5_grv_")
        os.environ["NEX5_DATA_DIR"] = self.tmp
        from substrate.init_db import init_all
        init_all()
        from substrate import Writer, db_paths
        self.bw = Writer(str(db_paths()["beliefs"]), name="beliefs")
        self.db = str(db_paths()["beliefs"])
        import theory_x.stage_tom.stakes_appraisal as sa
        sa._groove_cache.update(val=None, at=0.0)   # no cross-test cache leak

    def tearDown(self):
        try:
            self.bw.close()
        except Exception:
            pass
        os.environ.pop("NEX5_DATA_DIR", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _alert(self, ts, atype="template_repetition", sev=1.0):
        self.bw.write(
            "INSERT INTO groove_alerts (detected_at, alert_type, severity, window_size) "
            "VALUES (?, ?, ?, ?)", (float(ts), atype, sev, 10))

    def test_at_or_below_onset_zero_cost(self):
        from theory_x.stage_tom.stakes_appraisal import appraise_groove, _GROOVE_ONSET
        now = time.time()
        for _ in range(int(_GROOVE_ONSET)):      # rate == onset -> no brake at rest
            self._alert(now - 100)
        self.bw.close()
        a = appraise_groove(beliefs_db=self.db, now=now)
        self.assertEqual(a["cost"], 0.0)
        self.assertFalse(a["stakes_active"])

    def test_burst_saturates_at_clamp(self):
        from theory_x.stage_tom.stakes_appraisal import appraise_groove, _COST_CLAMP, _GROOVE_SAT
        now = time.time()
        for k in range(int(_GROOVE_SAT) + 2):    # rate > saturation -> bounded max
            self._alert(now - 60 * k - 1)
        self.bw.close()
        a = appraise_groove(beliefs_db=self.db, now=now)
        self.assertTrue(a["stakes_active"])
        self.assertEqual(a["cost"], _COST_CLAMP)

    def test_mid_range_is_bounded_positive(self):
        from theory_x.stage_tom.stakes_appraisal import appraise_groove, _COST_CLAMP
        now = time.time()
        for k in range(4):                        # onset < 4/hr < saturation
            self._alert(now - 60 * k - 1)
        self.bw.close()
        a = appraise_groove(beliefs_db=self.db, now=now)
        self.assertGreater(a["cost"], 0.0)
        self.assertLess(a["cost"], _COST_CLAMP)

    def test_window_and_type_filtered(self):
        from theory_x.stage_tom.stakes_appraisal import appraise_groove
        now = time.time()
        for k in range(8):
            self._alert(now - 7200 - k)           # older than the 1h window -> excluded
        self._alert(now - 100, atype="ngram_repetition")  # wrong type -> excluded
        self.bw.close()
        a = appraise_groove(beliefs_db=self.db, now=now)
        self.assertEqual(a["n"], 0)
        self.assertEqual(a["cost"], 0.0)

    def test_empty_fail_safe_zero(self):
        from theory_x.stage_tom.stakes_appraisal import appraise_groove
        self.bw.close()
        a = appraise_groove(beliefs_db=self.db)
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
        self.bw = Writer(str(db_paths()["beliefs"]), name="beliefs")
        self.br = Reader(str(db_paths()["beliefs"]))
        now = time.time()
        for k in range(8):                       # a grooming BURST (>= saturation)
            self.bw.write("INSERT INTO groove_alerts (detected_at, alert_type, severity, window_size) "
                          "VALUES (?, ?, ?, ?)", (now - 60 * k - 1, "template_repetition", 1.0, 10))
        import theory_x.stage_tom.stakes_appraisal as sa
        self._sa = sa
        sa._groove_cache.update(val=None, at=0.0)

    def tearDown(self):
        try:
            self.bw.close()
        except Exception:
            pass
        os.environ.pop("NEX5_DATA_DIR", None)
        os.environ.pop("NEX5_STAKES", None)
        self._sa._groove_cache.update(val=None, at=0.0)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _score(self):
        from theory_x.stage6_fountain.readiness import ReadinessEvaluator
        ds = MagicMock()
        ds.status.return_value = {"branches": [], "consolidation_active": False}
        return ReadinessEvaluator().score(ds, self.br, last_fire_ts=0.0)

    def test_stakes_off_no_penalty_on_subtracts(self):
        os.environ.pop("NEX5_STAKES", None)
        self._sa._groove_cache.update(val=None, at=0.0)
        off = self._score()
        os.environ["NEX5_STAKES"] = "1"
        self._sa._groove_cache.update(val=None, at=0.0)
        on = self._score()
        self.assertLess(on, off)                 # the grooming-burst cost was subtracted
        self.assertAlmostEqual(off - on, 0.2, places=3)  # == _COST_CLAMP for a full burst


if __name__ == "__main__":
    unittest.main()
