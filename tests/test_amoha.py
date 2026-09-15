"""Tests for amoha (clear-seeing) — NEX5_AMOHA, the antidote sibling.

Semantic read (embeddings, not a keyword table) of whether recent thinking is
clouded (false certainty / absolutes) or clear. Prompt-only modulator: the
antidote note surfaces only when armed (NEX5_AMOHA) and seeing is clouded.
Guard 2: writes nothing to a belief/world table.
"""
from __future__ import annotations

import os
import unittest

from tests import _bootstrap  # noqa: F401

_CLOUDED = [
    "it always breaks down the same way, it never works, everything fails",
    "I am completely certain about this, there is nothing more to question",
    "clearly this must be true, anyone can see there's no alternative",
]
_CLEAR = [
    "this could be one reading, though I might be missing something",
    "in this particular instance it held, but elsewhere it may not",
    "I'm not sure yet — the evidence is partial, I'll hold it loosely",
]
_NEUTRAL = [
    "the parser handles nested quotes by tracking depth on a stack",
    "next I should benchmark the two approaches and compare latency",
    "the cache key includes the tenant id and the query hash",
]


class TestAmoha(unittest.TestCase):
    def setUp(self):
        from theory_x.stage_tom import amoha_detector as a
        self.a = a

    def tearDown(self):
        os.environ.pop("NEX5_AMOHA", None)

    def test_semantic_read_separates_clouded_from_clear(self):
        # clouded certainty scores; clear/neutral working thoughts ~0
        self.assertGreater(max(self.a.clouded_salience(t) for t in _CLOUDED), 0.3)
        self.assertLess(max(self.a.clouded_salience(t) for t in _CLEAR), 0.2)
        self.assertLess(max(self.a.clouded_salience(t) for t in _NEUTRAL), 0.2)
        self.assertEqual(self.a.clouded_salience(""), 0.0)
        self.assertEqual(self.a.clouded_salience(None), 0.0)   # fail-safe

    def test_state_bands(self):
        self.assertEqual(self.a.read_thoughts(_CLOUDED)["state"], "clouded")
        self.assertEqual(self.a.read_thoughts(_CLEAR)["state"], "clear")
        self.assertEqual(self.a.read_thoughts(_NEUTRAL)["state"], "clear")  # no wolf-crying
        self.assertEqual(self.a.read_thoughts([])["state"], "clear")        # fail-safe

    def test_note_gated_and_conditional(self):
        # flag off -> never; flag on -> only when clouded
        self.a.detect = lambda: {"state": "clouded"}   # type: ignore
        os.environ.pop("NEX5_AMOHA", None)
        self.assertEqual(self.a.format_for_prompt(), "")
        os.environ["NEX5_AMOHA"] = "1"
        self.assertIn("Clear-seeing (amoha)", self.a.format_for_prompt())
        self.a.detect = lambda: {"state": "clear"}     # type: ignore
        self.assertEqual(self.a.format_for_prompt(), "")


if __name__ == "__main__":
    unittest.main()
