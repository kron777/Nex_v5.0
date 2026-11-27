"""Warrant survival must read promotion_log in the format its producers write.

BeliefPromoter appends every tier event with
``json_insert(promotion_log, '$[#]', json.dumps(event))`` -- SQLite stores the
bound TEXT as a JSON *string* element, so a real promotion_log is an array of
JSON-encoded strings, not of objects. tests/test_warrant.py builds its fixtures
as objects, so it cannot see whether ``_survival`` handles production rows.

These tests pin producer/consumer parity: the same events must score the same
whether encoded as objects (the fixture form) or as strings (the stored form),
including an end-to-end row written by the real BeliefPromoter.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

from theory_x.stage_warrant import warrant as w

_D = 86400.0
_NOW = 1_790_000_000.0


def _events(*events):
    return [{"event": e, "from": f, "to": t, "ts": _NOW - d * _D} for e, f, t, d in events]


def _object_log(*events):
    return json.dumps(_events(*events))


def _stored_log(*events):
    """Exactly the shape json_insert(promotion_log, '$[#]', json.dumps(e)) stores."""
    return json.dumps([json.dumps(e) for e in _events(*events)])


class TestSurvivalReadsStoredFormat(unittest.TestCase):
    def _parity(self, tier, age_days, *events):
        expected = w._survival(tier, 0, _NOW - age_days * _D, _object_log(*events), False, _NOW)
        actual = w._survival(tier, 0, _NOW - age_days * _D, _stored_log(*events), False, _NOW)
        self.assertAlmostEqual(actual, expected, places=12)
        return expected

    def test_contradiction_zeroes_survival_in_stored_form(self):
        self.assertEqual(self._parity(6, 9, ("decisive_contradiction", 4, 6, 1)), 0.0)

    def test_decay_halves_and_resets_interval_in_stored_form(self):
        s = self._parity(6, 30, ("decay", 5, 6, 3))
        self.assertGreater(s, 0.0)
        no_history = w._survival(6, 0, _NOW - 30 * _D, "[]", False, _NOW)
        self.assertLess(s, no_history)   # 3 days held, halved -- not 30 days

    def test_promoted_out_of_risk_keeps_its_interval_in_stored_form(self):
        self.assertGreater(self._parity(3, 10, ("corroboration", 6, 3, 6)), 0.0)

    def test_malformed_element_does_not_discard_valid_events(self):
        plog = json.dumps(["{not json", json.dumps(_events(("decisive_contradiction", 4, 6, 1))[0])])
        self.assertEqual(w._survival(6, 0, _NOW - 9 * _D, plog, False, _NOW), 0.0)


class TestSurvivalReadsRealProducerRow(unittest.TestCase):
    """End to end: a promotion_log written by the real BeliefPromoter."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nex5_warrant_fmt_")
        os.environ["NEX5_DATA_DIR"] = self.tmp
        os.environ["NEX5_ADMIN_HASH_FILE"] = str(Path(self.tmp) / "admin.argon2")
        from substrate.init_db import init_all
        init_all()
        from substrate import Reader, Writer, db_paths
        p = db_paths()["beliefs"]
        self.w, self.r = Writer(p, name="beliefs"), Reader(p)

    def tearDown(self):
        try:
            self.w.close()
        except Exception:
            pass
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.pop("NEX5_DATA_DIR", None)
        os.environ.pop("NEX5_ADMIN_HASH_FILE", None)

    def test_contradicted_belief_scores_zero_from_its_real_log(self):
        from theory_x.stage3_world_model.promotion import BeliefPromoter
        created = int(time.time()) - 9 * 86400
        bid = self.w.write(
            "INSERT INTO beliefs (content, tier, confidence, created_at, source) "
            "VALUES (?, 4, 0.5, ?, 'test')",
            ("Warrant producer/consumer format probe", created),
        )
        self.assertTrue(BeliefPromoter(self.w, self.r).decisive_contradiction(bid))
        row = self.r.read_one(
            "SELECT tier, created_at, promotion_log FROM beliefs WHERE id = ?", (bid,))
        self.assertEqual(row["tier"], 6)

        elements = json.loads(row["promotion_log"])
        self.assertTrue(elements and all(isinstance(e, str) for e in elements),
                        "producer contract: elements are JSON-encoded strings")

        s = w._survival(row["tier"], 0, row["created_at"], row["promotion_log"],
                        False, time.time())
        self.assertEqual(s, 0.0)  # a decisive contradiction zeroes survival


if __name__ == "__main__":
    unittest.main()
