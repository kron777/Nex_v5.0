"""Characterization tests for the current surprise-consumer admission boundary.

These tests record source behaviour; they do not declare that the behaviour is
correct or establish the governing product contract. In particular, the
weighting consumer currently accepts the newest numeric score independently
of the event's content/flag validity fields.
"""
from __future__ import annotations

import sqlite3
import tempfile
import time
import unittest

from tests import _bootstrap  # noqa: F401
from theory_x.stage_prediction.surprise_weighting import confidence_for_fire


class TestSurpriseWeightingAdmission(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = self.tmp.name + "/dynamic.db"
        con = sqlite3.connect(self.db)
        con.execute(
            "CREATE TABLE surprise_events ("
            "triggered_at REAL, surprise_score REAL, surprise_flag INTEGER, "
            "big_surprise INTEGER, actual_content TEXT)"
        )
        con.commit()
        con.close()

    def tearDown(self):
        self.tmp.cleanup()

    def _insert(self, *, age_s, score, flag, big, actual):
        con = sqlite3.connect(self.db)
        con.execute(
            "INSERT INTO surprise_events "
            "(triggered_at, surprise_score, surprise_flag, big_surprise, actual_content) "
            "VALUES (?, ?, ?, ?, ?)",
            (time.time() - age_s, score, flag, big, actual),
        )
        con.commit()
        con.close()

    def test_latest_unflagged_empty_event_still_weights_confidence(self):
        # Characterizes current implementation only: confidence_for_fire()
        # selects the latest score and does not apply the other selected fields.
        self._insert(age_s=5, score=0.90, flag=0, big=0, actual=None)

        confidence, score = confidence_for_fire(self.db)

        self.assertAlmostEqual(score, 0.90)
        self.assertAlmostEqual(confidence, 0.70 + 0.22 * 0.90)

    def test_latest_empty_event_supersedes_older_content_bearing_event(self):
        self._insert(age_s=30, score=0.30, flag=1, big=0, actual="valid observed content")
        self._insert(age_s=5, score=1.00, flag=0, big=1, actual=None)

        confidence, score = confidence_for_fire(self.db)

        self.assertAlmostEqual(score, 1.00)
        self.assertAlmostEqual(confidence, 0.92)


if __name__ == "__main__":
    unittest.main()
