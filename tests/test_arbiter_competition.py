"""Arbiter-competition instrument (NEX5_GW_LOG + check_arbiter_competition).

Logger: default OFF => no file, arbitrate() byte-identical; logs the full candidate VECTOR
[{kind, salience}] so the three channels can be computed offline. Instrument: R_correct
(tripwire, ~0), R_design (readout, expected large), and the earns-its-keep primary
(P(bonsai | momentum absent) + focus_num region). No fire-path change. ANALOGUE.
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
        self._db = os.path.join(self._tmp, "dynamic.db")
        os.environ.pop("NEX5_GW_LOG", None)

    def tearDown(self):
        self.gw._decisions_path = self._orig_path_fn
        os.environ.pop("NEX5_GW_LOG", None)

    def _status(self):
        return {"branches": [{"branch_id": "emerging_tech", "focus_num": 0.9}]}

    def test_off_writes_nothing_and_is_byte_identical(self):
        line_off = self.gw.arbitrate(self._status(), dynamic_db=self._db)
        self.assertFalse(os.path.exists(self._jsonl))
        os.environ["NEX5_GW_LOG"] = "1"
        line_on = self.gw.arbitrate(self._status(), dynamic_db=self._db)
        self.assertEqual(line_on, line_off)
        with open(self._jsonl) as f:
            rows = [json.loads(x) for x in f if x.strip()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["winner_kind"], "bonsai")
        self.assertEqual(rows[0]["candidates"], [{"kind": "bonsai", "salience": 0.45}])

    def test_winner_index_is_first_max_and_vector_logged(self):
        os.environ["NEX5_GW_LOG"] = "1"
        self.gw._maybe_log_decision([(0.5, "a"), (0.9, "b"), (0.9, "c")],
                                    ["surprise", "momentum", "bonsai"])
        with open(self._jsonl) as f:
            rec = json.loads(f.readline())
        self.assertEqual(rec["winner_kind"], "momentum")
        self.assertEqual(len(rec["candidates"]), 3)
        self.assertEqual(rec["candidates"][0], {"kind": "surprise", "salience": 0.5})

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

    def _row(self, winner, *cands):
        return {"ts": 1.0, "winner_kind": winner,
                "candidates": [{"kind": k, "salience": s} for k, s in cands]}

    def test_entropy(self):
        from tools.check_arbiter_competition import _entropy
        self.assertAlmostEqual(_entropy({"a": 1, "b": 1, "c": 1, "d": 1}), 2.0)
        self.assertEqual(_entropy({"a": 9}), 0.0)

    def test_nominal_and_effective(self):
        from tools.check_arbiter_competition import _nominal_predicted, _effective_argmax
        self.assertEqual(_nominal_predicted(["momentum", "surprise"]), "surprise")  # weight 1.0
        self.assertEqual(_nominal_predicted(["bonsai", "drive"]), "bonsai")         # 0.50 > 0.45
        self.assertIsNone(_nominal_predicted([]))
        self.assertEqual(_effective_argmax(
            [{"kind": "surprise", "salience": 0.40}, {"kind": "momentum", "salience": 0.55}]),
            "momentum")

    def test_three_channels_weak_surprise(self):
        # weak surprise (0.40) enters but loses to flat momentum (0.55): R_correct 0, R_design large
        from tools.check_arbiter_competition import measure, _verdict
        weak = self._row("momentum", ("surprise", 0.40), ("momentum", 0.55))
        strong = self._row("surprise", ("surprise", 0.80), ("momentum", 0.55))
        path = self._write([weak] * 30 + [strong] * 10)
        try:
            m = measure(path, window=5000)
        finally:
            os.unlink(path)
        self.assertEqual(m["R_correct"], 0.0)                      # winner == max-salience always
        self.assertEqual(m["R_design"], 0.75)                      # 30/40 depart the nominal ladder
        self.assertEqual(m["surprise"]["entry_rate"], 1.0)
        self.assertEqual(m["surprise"]["dead_band_share_of_entries"], 0.75)  # 30 below drive 0.45
        self.assertEqual(m["earns_keep"]["momentum_absent_share"], 0.0)
        self.assertEqual(m["earns_keep"]["data_driven_region_share"], 0.0)
        self.assertTrue(_verdict(m).startswith("NEAR-DETERMINISTIC"))

    def test_data_driven_region(self):
        # momentum absent; focus_num decides bonsai-vs-drive
        from tools.check_arbiter_competition import measure, _verdict
        hi = self._row("bonsai", ("bonsai", 0.50), ("drive", 0.45))   # focus_num 1.0 -> >0.9, wins
        lo = self._row("drive", ("bonsai", 0.20), ("drive", 0.45))    # focus_num 0.4 -> <0.5, loses
        path = self._write([hi] * 20 + [lo] * 20)
        try:
            m = measure(path, window=5000)
        finally:
            os.unlink(path)
        self.assertEqual(m["R_correct"], 0.0)
        self.assertEqual(m["earns_keep"]["momentum_absent_share"], 1.0)
        self.assertEqual(m["earns_keep"]["p_bonsai_win_given_momentum_absent"], 0.5)
        self.assertEqual(m["earns_keep"]["data_driven_region_share"], 0.5)   # 20/40 focus_num>0.9
        self.assertTrue(_verdict(m).startswith("DATA-DRIVEN REGION"))

    def test_correctness_alert(self):
        from tools.check_arbiter_competition import measure, _verdict
        # winner_kind logged as momentum but surprise (0.80) is the real max -> tripwire fires
        bad = self._row("momentum", ("momentum", 0.55), ("surprise", 0.80))
        path = self._write([bad] * 40)
        try:
            m = measure(path, window=5000)
        finally:
            os.unlink(path)
        self.assertEqual(m["R_correct"], 1.0)
        self.assertTrue(_verdict(m).startswith("CORRECTNESS ALERT"))

    def test_insufficient(self):
        from tools.check_arbiter_competition import measure
        path = self._write([self._row("bonsai", ("bonsai", 0.45))] * 5)
        try:
            m = measure(path)
        finally:
            os.unlink(path)
        self.assertIn("error", m)


if __name__ == "__main__":
    unittest.main()
