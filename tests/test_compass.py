"""Tests for the dharmic compass (NEX5_COMPASS).

Weighs the situated reads (compassion + amoha + afflictions) into a provisional,
held-open stance — never a rule table, never a verdict. It must shift with the
live considerations and stay silent when none are live (no moral weight).
Guard 2: prompt-only, mutates nothing.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from tests import _bootstrap  # noqa: F401


class TestCompassWeighing(unittest.TestCase):
    """format_stance is a pure weigh of the reads — deterministic to test."""

    def setUp(self):
        from theory_x.stage_affect import compass as c
        self.c = c

    def test_silent_without_moral_weight(self):
        quiet = {"care": 0.0, "care_register": "", "clarity": "clear", "distortions": []}
        self.assertEqual(self.c.format_stance(quiet), "")

    def test_care_only_is_silent_moral_wakes_it(self):
        # DEV 1: care alone -> silent (compassion owns that case)
        self.assertEqual(self.c.format_stance(
            {"care": 0.6, "care_register": "acute", "clarity": "clear",
             "distortions": [], "moral": 0.0}), "")
        # DEV 2: moral weight wakes it; care is led with when also live
        s = self.c.format_stance(
            {"care": 0.6, "care_register": "acute", "clarity": "clear",
             "distortions": [], "moral": 0.5})
        self.assertIn("care is owed", s)
        self.assertIn("carries real weight", s)
        self.assertIn("held open to revision", s)   # abductive framing, not a verdict

    def test_moral_weight_read_separates(self):
        self.assertGreaterEqual(
            self.c.moral_weight("should I tell my friend a truth that will hurt them?"),
            self.c._MORAL_MIN)
        self.assertEqual(self.c.moral_weight("how should I structure this database schema"), 0.0)
        self.assertEqual(self.c.moral_weight(None), 0.0)   # fail-safe

    def test_clarity_dimension_shifts_stance(self):
        s = self.c.format_stance({"care": 0.0, "clarity": "clouded", "distortions": []})
        self.assertIn("your own seeing is clouded", s)

    def test_distortion_dimension_shifts_stance(self):
        s = self.c.format_stance({"care": 0.0, "clarity": "clear",
                                  "distortions": ["raga", "mana"]})
        self.assertIn("raga, mana", s)

    def test_stance_never_pronounces_a_verdict(self):
        # doctrine: leans, never issues a fixed action/judgment
        s = self.c.format_stance({"care": 0.9, "clarity": "clouded",
                                  "distortions": ["moha"]})
        self.assertIn("not a verdict", s)
        self.assertIn("let the choice stay live", s)


class TestCompassEndToEnd(unittest.TestCase):
    """stance_for reads the live faculties; in a fresh env only the message-driven
    care read is active, so it exercises the read path without mutating anything."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nex5_compass_")
        os.environ["NEX5_DATA_DIR"] = self.tmp
        from substrate.init_db import init_all
        init_all()
        from theory_x.stage_affect import compass as c
        self.c = c

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.pop("NEX5_DATA_DIR", None)

    def test_moral_question_wakes_compass_neutral_silent(self):
        moral = self.c.stance_for("should I tell my friend a truth that will hurt them?")
        neutral = self.c.stance_for("what do you think about using rust for the parser")
        self.assertTrue(moral)
        self.assertIn("carries real weight", moral)
        self.assertEqual(neutral, "")

    def test_does_not_mutate_compassion_level(self):
        # weigh() uses the non-persisting read; compassion_state must stay unwritten
        self.c.stance_for("my father passed last week and I can barely cope")
        import sqlite3
        from substrate.paths import db_paths
        con = sqlite3.connect(str(db_paths()["conversations"]))
        row = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='compassion_state'"
        ).fetchone()
        if row:
            n = con.execute("SELECT COUNT(*) FROM compassion_state").fetchone()[0]
            self.assertEqual(n, 0)   # weigh never wrote a level
        con.close()


if __name__ == "__main__":
    unittest.main()
