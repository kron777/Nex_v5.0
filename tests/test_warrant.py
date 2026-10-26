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


class TestSustainIgnoresIdentityBlock(unittest.TestCase):
    """The guaranteed identity block (NEX5_IDENTITY_BLOCK) retrieves its beliefs
    every fire by construction -- that is not being relied on, so those
    retrievals must not raise sustain. Other slots still count."""

    def test_identity_block_slot_earns_no_sustain_days(self):
        import tempfile
        from unittest import mock
        from substrate import connect
        from substrate.init_db import init_all
        from substrate.paths import db_paths
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {"NEX5_DATA_DIR": tmp}):
            init_all()
            p = db_paths()
            b = connect(str(p["beliefs"]))
            ids = []
            for txt in ("shown by the identity block", "retrieved on its own merits"):
                ids.append(b.execute(
                    "INSERT INTO beliefs (content, tier, confidence, created_at, "
                    "source, branch_id) VALUES (?, 6, 0.7, ?, 'identity_loop', 'systems')",
                    (txt, _NOW - 10 * _D)).lastrowid)
            b.commit(); b.close()
            d = connect(str(p["dynamic"]))
            # created lazily by FountainGenerator.__init__ (same DDL)
            d.execute("CREATE TABLE IF NOT EXISTS fountain_retrieval_log ("
                      "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                      "fire_id INTEGER NOT NULL, belief_id INTEGER NOT NULL, "
                      "slot TEXT NOT NULL, rank INTEGER, boost_value REAL, "
                      "ts REAL NOT NULL, "
                      "FOREIGN KEY (fire_id) REFERENCES fountain_events(id))")
            for day in range(1, 6):
                d.execute("INSERT INTO fountain_events (id, ts, thought, readiness) "
                          "VALUES (?, ?, 'a fire', 0.8)", (day, _NOW - day * _D))
            for day in range(1, 6):
                for bid, slot in ((ids[0], "identity_block"), (ids[1], "own")):
                    d.execute("INSERT INTO fountain_retrieval_log "
                              "(fire_id, belief_id, slot, rank, boost_value, ts) "
                              "VALUES (?, ?, ?, 1, NULL, ?)",
                              (day, bid, slot, _NOW - day * _D))
            d.commit(); d.close()
            out = w.compute_all(now=_NOW)
        self.assertEqual(out[ids[0]]["sustain_days"], 0)
        self.assertEqual(out[ids[0]]["sustain"], 0.0)
        self.assertEqual(out[ids[1]]["sustain_days"], 5)
        self.assertGreater(out[ids[1]]["sustain"], 0.0)

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
