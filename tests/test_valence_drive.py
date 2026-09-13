"""Tests for valence-as-driver (NEX5_VALENCE_DRIVE).

Mood (affect_state.valence/arousal) tilts the novelty term of the curiosity pick:
up mood reaches for the surprising, flat/down mood favours the steady thread —
never an affective-content channel, so it cannot spiral. Bounded, with explicit
anti-rut suppression in the strong-negative zone.

Covers the two required properties: (a) mood measurably shifts selection vs the
off/neutral state; (b) the anti-rut guard holds — a sustained/strong negative
mood does NOT runaway-amplify (reach returns to neutral, and the factor is
bounded across the whole valence range).
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest

from tests import _bootstrap  # noqa: F401

from theory_x.stage6_fountain.generator import (
    _curiosity_score, _valence_reach, _VALENCE_CAP, _VALENCE_NEG_FLOOR,
)

_SUR = {"quantum", "entanglement"}     # surprise/novelty tokens
_BLD = {"bitcoin", "markets"}          # building/steady thread tokens
_NOVEL = {"quantum", "entanglement"}
_STEADY = {"bitcoin", "markets"}


class TestValenceScoreModulation(unittest.TestCase):

    def _score(self, toks, vr):
        return _curiosity_score(toks, _SUR, set(), _BLD, set(), 1.0, valence_reach=vr)

    def test_default_unchanged(self):
        # default valence_reach=1.0 -> identical to pre-valence behaviour
        self.assertEqual(
            _curiosity_score(_NOVEL, _SUR, set(), _BLD, set(), 1.0),
            _curiosity_score(_NOVEL, _SUR, set(), _BLD, set(), 1.0, valence_reach=1.0),
        )

    def test_up_mood_prefers_novel(self):
        self.assertGreater(self._score(_NOVEL, 1.4), self._score(_STEADY, 1.4))

    def test_neutral_is_a_tie(self):
        self.assertEqual(self._score(_NOVEL, 1.0), self._score(_STEADY, 1.0))

    def test_down_mood_prefers_steady_not_novel(self):
        self.assertGreater(self._score(_STEADY, 0.6), self._score(_NOVEL, 0.6))

    def test_only_novelty_term_scaled(self):
        # a pure-steady candidate (no surprise overlap) is unaffected by reach
        self.assertEqual(self._score(_STEADY, 1.4), self._score(_STEADY, 0.6))


class TestValenceReach(unittest.TestCase):
    """_valence_reach reads affect_state from an isolated tempdir DB."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nex5_valence_")
        os.environ["NEX5_DATA_DIR"] = self.tmp
        from substrate.init_db import init_all
        init_all()
        from substrate import Writer, db_paths
        self.w = Writer(db_paths()["conversations"], name="conversations")

    def tearDown(self):
        try:
            self.w.close()
        except Exception:
            pass
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.pop("NEX5_DATA_DIR", None)

    def _set_mood(self, valence, arousal):
        self.w.write(
            "INSERT OR REPLACE INTO affect_state "
            "(id, valence, arousal, stability, mood_label, updated_at) "
            "VALUES (1, ?, ?, 0.5, 'x', ?)",
            (valence, arousal, time.time()),
        )
        time.sleep(0.02)

    def test_up_mood_reaches_out(self):
        self._set_mood(0.8, 0.9)
        self.assertGreater(_valence_reach(), 1.0)

    def test_mild_down_mood_pulls_in(self):
        self._set_mood(-0.4, 0.6)
        self.assertLess(_valence_reach(), 1.0)

    def test_bounded_both_ends(self):
        self._set_mood(1.0, 1.0)
        self.assertLessEqual(_valence_reach(), 1.0 + _VALENCE_CAP + 1e-9)
        self._set_mood(-0.5, 1.0)   # mild-negative, not yet the anti-rut floor
        self.assertGreaterEqual(_valence_reach(), 1.0 - _VALENCE_CAP - 1e-9)

    # --- ANTI-RUT: strong negative mood must NOT steer (no spiral) ---
    def test_strong_negative_suppressed_to_neutral(self):
        self._set_mood(-0.9, 1.0)   # deep negative + high arousal = spiral zone
        self.assertEqual(_valence_reach(), 1.0)

    def test_antirut_across_sustained_negative_sweep(self):
        # simulate a mood sinking deeper over "time": reach must never amplify
        # (grow past neutral downward without bound) and must snap to neutral
        # once it crosses the floor — no runaway.
        prev = None
        for v in [-0.3, -0.5, -0.69, -0.7, -0.85, -1.0]:
            self._set_mood(v, 1.0)
            r = _valence_reach()
            self.assertGreaterEqual(r, 1.0 - _VALENCE_CAP - 1e-9)  # bounded
            if v <= _VALENCE_NEG_FLOOR:
                self.assertEqual(r, 1.0)   # anti-rut: steering off in the spiral zone
            prev = r
        self.assertIsNotNone(prev)

    def test_no_mood_row_is_neutral(self):
        # fresh DB, no affect_state row -> neutral (no bias), fail-safe
        self.assertEqual(_valence_reach(), 1.0)


if __name__ == "__main__":
    unittest.main()
