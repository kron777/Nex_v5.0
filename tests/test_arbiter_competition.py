"""Arbiter-competition instrument (NEX5_GW_LOG + check_arbiter_competition).

Logger: default OFF => no file, arbitrate() byte-identical; logs the candidate VECTOR
[{kind, salience}] (+ gated_surprise_score when surprise was gated out) so every channel
computes offline. Instrument: data_decided_share (primary), R_correct (tripwire ~0),
R_design (readout), the surprise/bonsai decompositions, near-tie margin, and the L4_TEETH
guard. No fire-path change. ANALOGUE.
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
        self.assertEqual(rec["candidates"][0], {"kind": "surprise", "salience": 0.5})
        self.assertNotIn("gated_surprise_score", rec)   # surprise present -> no gated field

    def test_gated_surprise_logged_when_surprise_absent(self):
        os.environ["NEX5_GW_LOG"] = "1"
        self.gw._maybe_log_decision([(0.45, "x")], ["bonsai"], gated_surprise=0.2)
        with open(self._jsonl) as f:
            rec = json.loads(f.readline())
        self.assertEqual(rec["gated_surprise_score"], 0.2)

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

    def _row(self, winner, *cands, gated=None):
        r = {"ts": 1.0, "winner_kind": winner,
             "candidates": [{"kind": k, "salience": s} for k, s in cands]}
        if gated is not None:
            r["gated_surprise_score"] = gated
        return r

    def test_entropy(self):
        from tools.check_arbiter_competition import _entropy
        self.assertAlmostEqual(_entropy({"a": 1, "b": 1, "c": 1, "d": 1}), 2.0)
        self.assertEqual(_entropy({"a": 9}), 0.0)

    def test_nominal_and_effective(self):
        from tools.check_arbiter_competition import _nominal_predicted, _effective_argmax
        self.assertEqual(_nominal_predicted(["momentum", "surprise"]), "surprise")
        self.assertEqual(_nominal_predicted(["bonsai", "drive"]), "bonsai")
        self.assertIsNone(_nominal_predicted([]))
        self.assertEqual(_effective_argmax(
            [{"kind": "surprise", "salience": 0.40}, {"kind": "momentum", "salience": 0.55}]),
            "momentum")

    def test_data_decided_counts_surprise_even_with_momentum_live(self):
        # weak surprise (0.40) loses to flat momentum; strong (0.80) wins => data-decided
        from tools.check_arbiter_competition import measure, _verdict
        weak = self._row("momentum", ("surprise", 0.40), ("momentum", 0.55))
        strong = self._row("surprise", ("surprise", 0.80), ("momentum", 0.55))
        path = self._write([weak] * 30 + [strong] * 10)
        try:
            m = measure(path, window=5000)
        finally:
            os.unlink(path)
        self.assertEqual(m["data_decided_share"], 0.25)       # only the 10 surprise wins
        self.assertEqual(m["flat_share"], 0.75)
        self.assertEqual(m["R_correct"], 0.0)
        self.assertEqual(m["R_design"], 0.75)
        self.assertEqual(m["surprise"]["win_given_live"], 0.25)
        self.assertEqual(m["surprise"]["dead_band_share_of_entries"], 0.75)
        self.assertEqual(m["decomposition"]["p_surprise_win"], 0.25)
        self.assertTrue(_verdict(m).startswith("DATA-DECIDED"))

    def test_bonsai_veto_region(self):
        from tools.check_arbiter_competition import measure
        hi = self._row("bonsai", ("bonsai", 0.50), ("drive", 0.45))   # focus_num 1.0 -> wins
        lo = self._row("drive", ("bonsai", 0.20), ("drive", 0.45))    # focus_num 0.4 -> loses
        path = self._write([hi] * 20 + [lo] * 20)
        try:
            m = measure(path, window=5000)
        finally:
            os.unlink(path)
        self.assertEqual(m["data_decided_share"], 0.5)        # the 20 bonsai wins
        self.assertEqual(m["bonsai"]["momentum_absent_share"], 1.0)
        self.assertEqual(m["bonsai"]["p_bonsai_win_given_momentum_absent"], 0.5)
        self.assertEqual(m["bonsai"]["veto_region_share"], 0.5)

    def test_correctness_alert(self):
        from tools.check_arbiter_competition import measure, _verdict
        bad = self._row("momentum", ("momentum", 0.55), ("surprise", 0.80))  # argmax is surprise
        path = self._write([bad] * 40)
        try:
            m = measure(path, window=5000)
        finally:
            os.unlink(path)
        self.assertEqual(m["R_correct"], 1.0)
        self.assertIn("CORRECTNESS ALERT", _verdict(m))

    def test_l4_teeth_suspected(self):
        from tools.check_arbiter_competition import measure, _verdict
        demoted = self._row("bonsai", ("momentum", 0.33), ("bonsai", 0.45))  # momentum < 0.55
        path = self._write([demoted] * 40)
        try:
            m = measure(path, window=5000)
        finally:
            os.unlink(path)
        self.assertTrue(m["l4_teeth_suspected"])
        self.assertIn("L4_TEETH SUSPECTED", _verdict(m))

    def test_gated_vs_phantom_split(self):
        from tools.check_arbiter_competition import measure
        gated = self._row("bonsai", ("bonsai", 0.45), gated=0.20)   # surprise existed, gated out
        phantom = self._row("bonsai", ("bonsai", 0.45))             # no surprise event at all
        path = self._write([gated] * 15 + [phantom] * 15)
        try:
            m = measure(path, window=5000)
        finally:
            os.unlink(path)
        self.assertEqual(m["surprise"]["entry_rate"], 0.0)
        self.assertEqual(m["surprise"]["gated_share_of_absent"], 0.5)

    def test_near_tie_share(self):
        from tools.check_arbiter_competition import measure
        tie = self._row("bonsai", ("bonsai", 0.450), ("drive", 0.445))   # margin 0.005 < 0.01
        wide = self._row("bonsai", ("bonsai", 0.50), ("drive", 0.20))    # margin 0.30
        path = self._write([tie] * 30 + [wide] * 10)
        try:
            m = measure(path, window=5000)
        finally:
            os.unlink(path)
        self.assertEqual(m["near_tie_share"], 0.75)        # 30 of 40 two-candidate fires

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
