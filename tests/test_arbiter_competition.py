"""Arbiter-competition instrument (NEX5_GW_LOG + check_arbiter_competition).

The logger is observational: default OFF => no file written, arbitrate() byte-identical.
The instrument reads the JSONL and reports override rate / depth / winner distribution.
No fire-path behaviour change (the log is a lock-free append, never the one-pen). ANALOGUE.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from tests._bootstrap import *  # noqa: F401, F403


class TestArbiterLogger(unittest.TestCase):

    def setUp(self):
        import theory_x.stage_tom.global_workspace as gw
        self.gw = gw
        self._orig_path_fn = gw._decisions_path
        self._tmp = tempfile.mkdtemp()
        self._jsonl = os.path.join(self._tmp, "arbiter_decisions.jsonl")
        gw._decisions_path = lambda: self._jsonl
        self._db = os.path.join(self._tmp, "dynamic.db")   # empty => no surprise/momentum
        os.environ.pop("NEX5_GW_LOG", None)

    def tearDown(self):
        self.gw._decisions_path = self._orig_path_fn
        os.environ.pop("NEX5_GW_LOG", None)

    def _status(self):
        return {"branches": [{"branch_id": "emerging_tech", "focus_num": 0.9}]}

    def test_off_writes_nothing_and_is_byte_identical(self):
        line_off = self.gw.arbitrate(self._status(), dynamic_db=self._db)
        self.assertFalse(os.path.exists(self._jsonl))     # OFF => no file at all
        os.environ["NEX5_GW_LOG"] = "1"
        line_on = self.gw.arbitrate(self._status(), dynamic_db=self._db)
        self.assertEqual(line_on, line_off)               # decision unchanged by logging
        self.assertTrue(os.path.exists(self._jsonl))
        with open(self._jsonl) as f:
            rows = [json.loads(x) for x in f if x.strip()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["winner_kind"], "bonsai")
        self.assertEqual(rows[0]["n_candidates"], 1)
        self.assertEqual(rows[0]["kinds_present"], ["bonsai"])

    def test_winner_index_is_first_max(self):
        os.environ["NEX5_GW_LOG"] = "1"
        # two equal-salience maxima: the FIRST wins, matching arbitrate_candidates()
        self.gw._maybe_log_decision([(0.5, "a"), (0.9, "b"), (0.9, "c")],
                                    ["surprise", "momentum", "bonsai"])
        with open(self._jsonl) as f:
            rec = json.loads(f.readline())
        self.assertEqual(rec["winner_kind"], "momentum")
        self.assertEqual(rec["winner_salience"], 0.9)
        self.assertEqual(rec["kinds_present"], ["bonsai", "momentum", "surprise"])

    def test_empty_candidates_is_noop(self):
        os.environ["NEX5_GW_LOG"] = "1"
        self.gw._maybe_log_decision([], [])
        self.assertFalse(os.path.exists(self._jsonl))


class TestArbiterMeasure(unittest.TestCase):

    def _write(self, rows):
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        with os.fdopen(fd, "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        return path

    def test_entropy(self):
        from tools.check_arbiter_competition import _entropy
        self.assertAlmostEqual(_entropy({"a": 1, "b": 1, "c": 1, "d": 1}), 2.0)
        self.assertEqual(_entropy({"a": 9}), 0.0)

    def test_aggregation(self):
        from tools.check_arbiter_competition import measure, _verdict
        rows = ([{"ts": 1.0, "n_candidates": 1, "kinds_present": ["bonsai"],
                  "winner_kind": "bonsai", "winner_salience": 0.45}] * 30
                + [{"ts": 1.0, "n_candidates": 2, "kinds_present": ["bonsai", "momentum"],
                    "winner_kind": "momentum", "winner_salience": 0.55}] * 10)
        path = self._write(rows)
        try:
            m = measure(path, window=5000)
        finally:
            os.unlink(path)
        self.assertEqual(m["n"], 40)
        self.assertEqual(m["winner_distribution"]["bonsai"], 0.75)
        self.assertEqual(m["winner_distribution"]["momentum"], 0.25)
        self.assertEqual(m["non_bonsai_win_share"], 0.25)
        self.assertEqual(m["override_given_bonsai_present"], 0.25)   # bonsai lost 10/40 present
        self.assertEqual(m["bonsai_present_share"], 1.0)
        self.assertEqual(m["mean_candidates"], 1.25)
        self.assertEqual(m["kinds_present_rate"]["momentum"], 0.25)
        self.assertTrue(_verdict(m).startswith("ACTIVE"))

    def test_rubber_stamp_verdict(self):
        from tools.check_arbiter_competition import measure, _verdict
        rows = [{"ts": 1.0, "n_candidates": 1, "kinds_present": ["bonsai"],
                 "winner_kind": "bonsai", "winner_salience": 0.45}] * 50
        path = self._write(rows)
        try:
            m = measure(path, window=5000)
        finally:
            os.unlink(path)
        self.assertEqual(m["override_given_bonsai_present"], 0.0)
        self.assertTrue(_verdict(m).startswith("RUBBER-STAMP"))

    def test_insufficient(self):
        from tools.check_arbiter_competition import measure
        path = self._write([{"ts": 1.0, "n_candidates": 1,
                             "kinds_present": ["bonsai"], "winner_kind": "bonsai",
                             "winner_salience": 0.45}] * 5)
        try:
            m = measure(path)
        finally:
            os.unlink(path)
        self.assertIn("error", m)


if __name__ == "__main__":
    unittest.main()
