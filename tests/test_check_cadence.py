"""The cadence harness computes a downtime-robust fire rate."""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest

from tests._bootstrap import *  # noqa: F401, F403


class TestCadenceHarness(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nex5_cad_")
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
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _fire(self, ts):
        self.dw.write(
            "INSERT INTO fountain_events (ts, thought, readiness) VALUES (?, ?, ?)",
            (float(ts), "a thought", 0.5),
        )

    def test_median_and_active_rate(self):
        base = 1_000_000.0
        for k in range(5):                 # fires 600s (10 min) apart
            self._fire(base + k * 600)
        self.dw.close()
        from tools.check_cadence import measure
        m = measure(days=None)
        self.assertEqual(m["n_fires"], 5)
        self.assertAlmostEqual(m["median_inter_arrival_min"], 10.0, places=2)
        self.assertAlmostEqual(m["active_fires_per_day"], 144.0, places=1)  # 86400/600

    def test_pause_excluded_from_median(self):
        base = 2_000_000.0
        # four 600s gaps, then one 2-day pause, then four more 600s gaps
        ts = [base + k * 600 for k in range(5)]
        ts += [ts[-1] + 2 * 86400 + k * 600 for k in range(1, 5)]
        for t in ts:
            self._fire(t)
        self.dw.close()
        from tools.check_cadence import measure
        m = measure(days=None)
        # the 2-day pause must not drag the median off 10 min
        self.assertAlmostEqual(m["median_inter_arrival_min"], 10.0, places=2)
        self.assertEqual(m["likely_pauses"], 1)

    def test_verdict_band(self):
        from tools.check_cadence import _verdict
        base = {"active_fires_per_day": 100.0, "median_inter_arrival_min": 14.4}
        ok_in, _ = _verdict({"active_fires_per_day": 110.0,
                             "median_inter_arrival_min": 13.0}, base, band=0.20)
        ok_out, _ = _verdict({"active_fires_per_day": 150.0,
                              "median_inter_arrival_min": 9.6}, base, band=0.20)
        self.assertTrue(ok_in)
        self.assertFalse(ok_out)


if __name__ == "__main__":
    unittest.main()
