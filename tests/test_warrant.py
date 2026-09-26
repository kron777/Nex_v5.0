"""Tests for warrant (NEX5_WARRANT) — the survival timeline, the burst rule,
and the off-gate. Validation against the live graph is tools/warrant_validate.py.
"""
from __future__ import annotations

import json
import os
import unittest

from tests import _bootstrap  # noqa: F401

from theory_x.stage_warrant import warrant as w

_D = 86400.0
_NOW = 1_790_000_000.0


def _log(*events):
    return json.dumps([{"event": e, "from": f, "to": t, "ts": _NOW - d * _D}
                       for e, f, t, d in events])


class TestSurvival(unittest.TestCase):
    def test_locked_keystone_is_full(self):
        self.assertEqual(w._survival(1, 1, _NOW - 5 * _D, "[]", False, _NOW), 1.0)

    def test_holding_at_risk_tier_accrues(self):
        short = w._survival(6, 0, _NOW - 1 * _D, "[]", False, _NOW)
        long = w._survival(6, 0, _NOW - 20 * _D, "[]", False, _NOW)
        self.assertGreater(long, short)
        self.assertGreater(short, 0.0)

    def test_never_at_risk_scores_zero(self):
        # created at T3 (templates) or sitting at T7 (decay is a no-op there)
        self.assertEqual(w._survival(3, 0, _NOW - 30 * _D, "[]", False, _NOW), 0.0)
        self.assertEqual(w._survival(7, 0, _NOW - 30 * _D, "[]", False, _NOW), 0.0)

    def test_decay_gives_no_credit_and_halves(self):
        # 10 days at T6, then decayed to T7 two days ago
        plog = _log(("decay", 6, 7, 2))
        self.assertEqual(w._survival(7, 0, _NOW - 12 * _D, plog, False, _NOW), 0.0)
        # decayed 6->7 once, later promoted back to 6 and holding 5 days
        plog = _log(("decay", 6, 7, 20), ("corroboration", 7, 6, 5))
        held = w._survival(6, 0, _NOW - 30 * _D, plog, False, _NOW)
        clean = w._survival(6, 0, _NOW - 5 * _D, "[]", False, _NOW)
        self.assertAlmostEqual(held, clean * 0.5, places=6)

    def test_promoted_out_of_risk_keeps_its_interval(self):
        # created at T6, held 4 days, promoted to T3
        plog = _log(("corroboration", 6, 3, 6))
        s = w._survival(3, 0, _NOW - 10 * _D, plog, False, _NOW)
        self.assertAlmostEqual(s, 1 - __import__("math").exp(-4 / 7), places=6)

    def test_marked_or_contradicted_is_zero(self):
        self.assertEqual(w._survival(6, 0, _NOW - 9 * _D, "[]", True, _NOW), 0.0)
        plog = _log(("decisive_contradiction", 6, 7, 1))
        self.assertEqual(w._survival(7, 0, _NOW - 9 * _D, plog, False, _NOW), 0.0)


class TestCombineAndGate(unittest.TestCase):
    def test_weights_lean_off_connectivity(self):
        self.assertGreater(w.WEIGHTS["survival"] + w.WEIGHTS["sustain"],
                           2 * (w.WEIGHTS["indep"] + w.WEIGHTS["xsynth"]) - 1e-9)

    def test_start_loop_is_inert_when_off(self):
        prev = os.environ.pop("NEX5_WARRANT", None)
        try:
            import threading
            before = {t.name for t in threading.enumerate()}
            w.WarrantPass(beliefs_writer=None).start_loop()
            self.assertNotIn("warrant_pass", {t.name for t in threading.enumerate()} - before)
        finally:
            if prev is not None:
                os.environ["NEX5_WARRANT"] = prev


if __name__ == "__main__":
    unittest.main()
