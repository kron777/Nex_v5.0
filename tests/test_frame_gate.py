"""Tests for the detector-gated register demand (NEX5_FRAME_GATE, variable 3).

The always-on NEX5_FRAME_DEDUP validated the lever but over-pruned range
(frame_dedup_2026-10-08_results). NEX5_FRAME_GATE is the FIRE_LANG_GUARD analogue:
detect a register-template DRAFT, regenerate ONCE with the B1 concreteness demand,
use the clean retry, else keep the original (never drop, never degrade). Default OFF.

Covers: the pure detector (_register_template_trips — structural opener + phrase seed),
and _apply_frame_gate's gate logic (off = no-op/no voice call; clean draft = no-op;
tripped + clean retry = retry used, single regen; tripped + unclean/empty/raising retry
= original kept).
"""
from __future__ import annotations

import os
import unittest

from tests import _bootstrap  # noqa: F401

from theory_x.stage6_fountain import generator as G


class TestRegisterDetector(unittest.TestCase):
    """The pure detector — no DB, no generator, no voice."""

    def test_empty_is_false(self):
        self.assertFalse(G._register_template_trips(""))
        self.assertFalse(G._register_template_trips(None))  # type: ignore[arg-type]

    def test_stock_phrase_trips(self):
        self.assertTrue(G._register_template_trips("This item is about the new chip."))
        self.assertTrue(G._register_template_trips("the curious dance of thoughts and presence"))

    def test_structural_opener_trips_even_when_not_in_phrase_seed(self):
        # "this item talks about" is in the opener regex but NOT in _FRAME_STOCK_PHRASES,
        # so this exercises the structural (generalising) half, not the seed.
        self.assertNotIn("this item talks about", [p.lower() for p in G._FRAME_STOCK_PHRASES])
        self.assertTrue(G._register_template_trips("This item talks about the merger today."))

    def test_opener_is_anchored(self):
        # mid-sentence "this item talks about" does NOT trip (anchored to the start);
        # avoids false positives on legitimate mid-clause uses.
        self.assertFalse(G._register_template_trips("Well, this item talks about the merger."))

    def test_leading_punctuation_still_trips(self):
        self.assertTrue(G._register_template_trips('   "This item talks about the merger."'))

    def test_clean_concrete_draft_passes(self):
        self.assertFalse(G._register_template_trips("The ransomware fixer defrauded clients."))
        self.assertFalse(G._register_template_trips("Kraken BTC is 61,240 right now."))


class _Resp:
    def __init__(self, text):
        self.text = text


class _MockVoice:
    """Records call count; returns a fixed reply (or raises)."""

    def __init__(self, reply="", raises=False):
        self._reply = reply
        self._raises = raises
        self.calls = 0

    def speak(self, req, beliefs=None):
        self.calls += 1
        if self._raises:
            raise RuntimeError("voice down")
        return _Resp(self._reply)


def _gen_with_voice(voice):
    gen = G.FountainGenerator.__new__(G.FountainGenerator)  # no __init__ / no DB needed
    gen._voice = voice
    return gen


_TRIP = "This item is about the new accelerator."   # trips the detector
_CLEAN = "The accelerator is the size of a shoebox."  # passes


class TestApplyFrameGate(unittest.TestCase):
    """The gate logic on _apply_frame_gate."""

    def tearDown(self):
        os.environ.pop("NEX5_FRAME_GATE", None)

    def test_off_is_noop_no_voice_call(self):
        os.environ.pop("NEX5_FRAME_GATE", None)
        v = _MockVoice(reply=_CLEAN)
        gen = _gen_with_voice(v)
        self.assertEqual(gen._apply_frame_gate(_TRIP, "P"), _TRIP)
        self.assertEqual(v.calls, 0)

    def test_flag_must_be_exactly_one(self):
        os.environ["NEX5_FRAME_GATE"] = "0"
        v = _MockVoice(reply=_CLEAN)
        gen = _gen_with_voice(v)
        self.assertEqual(gen._apply_frame_gate(_TRIP, "P"), _TRIP)
        self.assertEqual(v.calls, 0)

    def test_clean_draft_no_regen(self):
        os.environ["NEX5_FRAME_GATE"] = "1"
        v = _MockVoice(reply=_CLEAN)
        gen = _gen_with_voice(v)
        self.assertEqual(gen._apply_frame_gate(_CLEAN, "P"), _CLEAN)
        self.assertEqual(v.calls, 0)

    def test_tripped_regen_clean_uses_retry_single_call(self):
        os.environ["NEX5_FRAME_GATE"] = "1"
        v = _MockVoice(reply=_CLEAN)
        gen = _gen_with_voice(v)
        self.assertEqual(gen._apply_frame_gate(_TRIP, "P"), _CLEAN)
        self.assertEqual(v.calls, 1)   # single regeneration, no loop

    def test_tripped_retry_still_trips_keeps_original(self):
        os.environ["NEX5_FRAME_GATE"] = "1"
        v = _MockVoice(reply="This item is about something else entirely.")
        gen = _gen_with_voice(v)
        self.assertEqual(gen._apply_frame_gate(_TRIP, "P"), _TRIP)  # not degraded
        self.assertEqual(v.calls, 1)

    def test_tripped_retry_empty_keeps_original(self):
        os.environ["NEX5_FRAME_GATE"] = "1"
        v = _MockVoice(reply="")
        gen = _gen_with_voice(v)
        self.assertEqual(gen._apply_frame_gate(_TRIP, "P"), _TRIP)
        self.assertEqual(v.calls, 1)

    def test_voice_exception_keeps_original(self):
        os.environ["NEX5_FRAME_GATE"] = "1"
        v = _MockVoice(raises=True)
        gen = _gen_with_voice(v)
        self.assertEqual(gen._apply_frame_gate(_TRIP, "P"), _TRIP)
        self.assertEqual(v.calls, 1)


if __name__ == "__main__":
    unittest.main()
