"""Tests for the finished affliction cluster — avidya + moha detectors, and the
cluster note wired into her prompt (NEX5_AFFLICTIONS).

avidya (too sure) and moha (lost) match the exact dvesa/mana pattern: regex over
the belief stream, 2+ signals to fire, graded state. The cluster note surfaces
only when armed AND an affliction fires HIGH — never on the mild register, so it
does not cry wolf on ordinary thinking. Read-only: writes no belief/world table.
"""
from __future__ import annotations

import os
import unittest

from tests import _bootstrap  # noqa: F401

_AVIDYA_SIG = ["it always fails, never works", "obviously the only answer, no doubt",
               "everything reduces to one thing", "this explains everything, every case",
               "certainly true, undeniably so, impossible otherwise"]
_MOHA_SIG = ["I'm confused and it makes no sense", "this contradicts what I just said, at odds",
             "I've lost the thread, going in circles", "can't tell, muddled and baffled",
             "doesn't fit, inconsistent, can't reconcile"]
_ORDINARY = ["the parser tracks quote depth on a stack", "I added a dark mode toggle",
             "next I will benchmark the two approaches", "the cache key uses tenant id",
             "consolidation runs on a background tick"]


def _run(mod, beliefs):
    mod._recent_self = lambda n=20: beliefs
    return mod.detect()


class TestNewDetectors(unittest.TestCase):
    def test_avidya_fires_on_certainty_quiet_otherwise(self):
        from theory_x.stage_tom import avidya_detector as a
        self.assertEqual(_run(a, _AVIDYA_SIG)["state"], "unseeing")
        self.assertNotEqual(_run(a, _ORDINARY)["state"], "unseeing")
        self.assertEqual(_run(a, [])["state"], "seeing")           # fail-safe

    def test_moha_fires_on_confusion_quiet_otherwise(self):
        from theory_x.stage_tom import moha_detector as m
        self.assertEqual(_run(m, _MOHA_SIG)["state"], "confused")
        self.assertEqual(_run(m, _ORDINARY)["state"], "lucid")
        self.assertEqual(_run(m, [])["state"], "lucid")            # fail-safe


class TestClusterNote(unittest.TestCase):
    def setUp(self):
        from theory_x.stage_tom import self_binding as sb
        self._orig_cluster_reads = sb._cluster_reads   # restore so we don't pollute compass

    def tearDown(self):
        from theory_x.stage_tom import self_binding as sb
        sb._cluster_reads = self._orig_cluster_reads
        os.environ.pop("NEX5_AFFLICTIONS", None)

    def test_gated_and_only_on_high(self):
        from theory_x.stage_tom import self_binding as sb
        # flag off -> silent even with an affliction firing
        sb._cluster_reads = lambda: {"avidya": "unseeing"}   # type: ignore
        os.environ.pop("NEX5_AFFLICTIONS", None)
        self.assertEqual(sb.afflictions_for_prompt(), "")
        # armed + firing HIGH -> note names it
        os.environ["NEX5_AFFLICTIONS"] = "1"
        note = sb.afflictions_for_prompt()
        self.assertIn("avidya", note)
        self.assertIn("afflictions colouring your seeing", note)
        # armed but only mild -> silent (no wolf-crying)
        sb._cluster_reads = lambda: {"avidya": "mild", "raga": "mild"}  # type: ignore
        self.assertEqual(sb.afflictions_for_prompt(), "")
        # armed + all quiet -> silent
        sb._cluster_reads = lambda: {"raga": "free", "dvesa": "calm"}   # type: ignore
        self.assertEqual(sb.afflictions_for_prompt(), "")

    def test_raga_suppressed_in_cluster_other_four_emit(self):
        from theory_x.stage_tom import self_binding as sb
        os.environ["NEX5_AFFLICTIONS"] = "1"
        # raga alone firing HIGH -> cluster stays silent (raga speaks via synthesis)
        sb._cluster_reads = lambda: {"raga": "fixated"}   # type: ignore
        self.assertEqual(sb.afflictions_for_prompt(), "")
        # all five HIGH -> cluster names the other four, never raga
        sb._cluster_reads = lambda: {"raga": "fixated", "dvesa": "averse",   # type: ignore
                                     "mana": "inflated", "avidya": "unseeing",
                                     "moha": "confused"}
        note = sb.afflictions_for_prompt()
        self.assertNotIn("raga", note)
        for other in ("dvesa", "mana", "avidya", "moha"):
            self.assertIn(other, note)


if __name__ == "__main__":
    unittest.main()
