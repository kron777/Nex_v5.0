"""Round 11, item 3 — honest scorecard (3a) + closed-loop threshold update (3c).

Fixture test over a temp conversations.db. No live endpoint, no network.
"""
import os
import tempfile
import time
import unittest

from tests import _bootstrap  # noqa: F401

from theory_x.stage_world import self_prediction as SP


def _seed(db, rows):
    """rows: list of (predicted, readiness, actual)."""
    SP.ensure_schema(db)
    conn = SP._connect(db)
    now = time.time()
    try:
        for i, (pred, readiness, actual) in enumerate(rows):
            conn.execute(
                "INSERT INTO self_predictions (made_at, source, predicted, readiness, "
                "baseline_fires, resolve_at, resolved_at, actual, outcome) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (now - 10000 + i, "self", pred, readiness, 0, now - 9000 + i,
                 now - 9000 + i, actual,
                 "correct" if pred == actual else "wrong"),
            )
        conn.commit()
    finally:
        conn.close()


class TestSelfPredCognitive(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self._tmp.name, "conversations.db")

    def tearDown(self):
        self._tmp.cleanup()

    def test_honest_scorecard_on_imbalanced_target(self):
        # 98 fires (all predicted fire, correct) + 2 nofire, 1 of which the model
        # caught by predicting nofire at low readiness. Accuracy is high but the
        # story is in the minority class.
        rows = [("fire", 0.95, "fire")] * 98
        rows += [("nofire", 0.10, "nofire"),      # caught (TP)
                 ("fire", 0.95, "nofire")]        # missed (FN)
        _seed(self.db, rows)
        sc = SP.scorecard_detailed(self.db)
        self.assertEqual(sc["resolved"], 100)
        self.assertAlmostEqual(sc["base_rate_fire"], 0.98, places=6)
        self.assertAlmostEqual(sc["majority_floor"], 0.98, places=6)
        self.assertEqual(sc["minority_class"], "nofire")
        # one nofire predicted, one correct -> precision 1.0; recall 1/2
        self.assertAlmostEqual(sc["minority_precision"], 1.0, places=6)
        self.assertAlmostEqual(sc["minority_recall"], 0.5, places=6)
        # lift = precision / minority_base = 1.0 / 0.02 = 50x
        self.assertAlmostEqual(sc["minority_lift"], 50.0, places=4)
        self.assertIsNotNone(sc["brier_skill"])

    def test_adapt_threshold_learns_from_curve(self):
        # readiness < 0.5 -> mostly nofire; >= 0.5 -> mostly fire. A balanced gate
        # (op=0.5) should land near 0.5, not the static 0.70.
        rows = []
        for _ in range(40):
            rows.append(("nofire", 0.2, "nofire"))   # low readiness, no fire
        for _ in range(40):
            rows.append(("fire", 0.8, "fire"))       # high readiness, fire
        _seed(self.db, rows)
        upd = SP.adapt_threshold(self.db, operating_p=0.5, bins=10)
        self.assertIsNotNone(upd)
        # first bin with P(fire) >= 0.5 is the 0.8 bin; low bins are P(fire)=0
        self.assertGreaterEqual(upd["threshold"], 0.5)
        self.assertLessEqual(upd["threshold"], 0.8)
        # and it persisted -> _current_threshold returns the learned value
        self.assertAlmostEqual(SP._current_threshold(self.db), upd["threshold"], places=6)

    def test_current_threshold_falls_back_to_constant(self):
        # no params table yet -> static constant, never raises
        self.assertAlmostEqual(SP._current_threshold(self.db), SP.FIRE_THRESHOLD, places=6)

    def test_calibration_curve_bins(self):
        _seed(self.db, [("fire", 0.85, "fire"), ("fire", 0.85, "nofire"),
                        ("fire", 0.15, "fire")])
        curve = SP.calibration_curve(self.db, bins=10)
        hi = [b for b in curve if b["readiness_lo"] == 0.8][0]
        self.assertAlmostEqual(hi["p_fire"], 0.5, places=6)  # 1 fire of 2 in that bin
        self.assertEqual(hi["n"], 2)


if __name__ == "__main__":
    unittest.main()
