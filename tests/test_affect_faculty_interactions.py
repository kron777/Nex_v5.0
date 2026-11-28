"""Pairwise characterization of existing NEX chat-faculty dependencies.

No environment flags are armed and no runtime state is changed. These tests
exercise the real source-to-source calls with deterministic inputs so that
subtle cross-faculty effects remain explicit.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from tests import _bootstrap  # noqa: F401


class TestCompassionToCompass(unittest.TestCase):
    def test_compass_composes_the_compassion_read_with_other_live_dimensions(self):
        from theory_x.stage_affect import compassion, compass

        with (
            patch.object(compassion, "_distress_read", return_value=(0.8, "acute")),
            patch.object(compass, "moral_weight", return_value=0.5),
            patch("theory_x.stage_tom.amoha_detector.detect",
                  return_value={"state": "clouded"}),
            patch("theory_x.stage_tom.self_binding._cluster_reads", return_value={}),
        ):
            reads = compass.weigh("a difficult choice affecting another person")
            self.assertEqual(reads["care"], 0.8)
            self.assertEqual(reads["clarity"], "clouded")
            self.assertEqual(reads["moral"], 0.5)
            stance = compass.format_stance(reads)

        self.assertIn("care is owed", stance)
        self.assertIn("seeing is clouded", stance)
        self.assertIn("wellbeing", stance)
        self.assertIn("not a verdict", stance)


class TestCompassionToEquanimity(unittest.TestCase):
    def test_live_compassion_silences_equanimity_even_when_internal_pull_is_hot(self):
        from theory_x.stage_affect import compassion, upekkha

        with (
            patch.object(upekkha, "_raga_hot", return_value=1.0),
            patch.object(upekkha, "_dvesa_hot", return_value=1.0),
            patch.object(compassion, "distress_salience", return_value=0.8),
        ):
            read = upekkha.equanimity_read("a person is in genuine distress")

        self.assertEqual(read["grade"], "none")
        self.assertTrue(read["karuna_live"])
        self.assertEqual(read["raga"], 1.0)
        self.assertEqual(read["dvesa"], 1.0)


class TestEquanimityToVirya(unittest.TestCase):
    def test_hot_equanimity_makes_virya_yield_on_a_drifting_hard_thread(self):
        from theory_x.stage_affect import upekkha, virya

        with (
            patch.object(virya, "_hard_thread", return_value="the active hard problem"),
            patch.object(virya, "_drift_fraction", return_value=0.95),
            patch.object(upekkha, "equanimity_read",
                         return_value={"grade": "full", "raga": 1.0,
                                       "dvesa": 0.0, "karuna_live": False}),
        ):
            read = virya.virya_read()

        self.assertEqual(read["thread"], "the active hard problem")
        self.assertEqual(read["drift"], 0.95)
        self.assertEqual(read["grade"], "none")


class TestSharedFocusBetweenViryaAndPrasrabdhi(unittest.TestCase):
    def test_prasrabdhi_does_not_break_a_thread_that_is_still_on_focus(self):
        from theory_x.stage_affect import prasrabdhi, virya

        with (
            patch.object(virya, "_hard_thread", return_value="the active hard problem"),
            patch.object(virya, "_drift_fraction", return_value=0.20),
        ):
            self.assertFalse(prasrabdhi._off_focus())

    def test_prasrabdhi_can_release_circling_that_has_drifted_off_focus(self):
        from theory_x.stage_affect import prasrabdhi, virya

        with (
            patch.object(virya, "_hard_thread", return_value="the active hard problem"),
            patch.object(virya, "_drift_fraction", return_value=0.80),
        ):
            self.assertTrue(prasrabdhi._off_focus())

    def test_no_hard_thread_means_circling_is_aimless(self):
        from theory_x.stage_affect import prasrabdhi, virya

        with patch.object(virya, "_hard_thread", return_value=""):
            self.assertTrue(prasrabdhi._off_focus())


class TestCompassionToAffectCarry(unittest.TestCase):
    def test_affect_carry_seeds_from_the_compassion_distress_read(self):
        from theory_x.stage_affect import affect_carry, compassion

        with (
            patch.object(compassion, "distress_salience", return_value=0.8),
            patch.object(affect_carry, "_cue_weight", return_value=0.0),
        ):
            self.assertEqual(
                affect_carry._this_turn_weight("a paraphrased distress message"),
                0.8,
            )


if __name__ == "__main__":
    unittest.main()
