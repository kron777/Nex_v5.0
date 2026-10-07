"""Tests for the persona focus staleness bound (NEX5_PERSONA_FOCUS_ROTATE).

The persona keeps interlocutor_state.focus (SOCIAL_DEPTH) and is told to carry it
forward; _focus_from_reply keeps it as long as it reappears, which the instruction
makes near-certain -> a one-way ratchet with no staleness bound. Under a rut it
locks the persona (and, via the fountain SOCIAL block, every fire) onto one topic.
This flag bounds it: after the same focus has been carried _PERSONA_FOCUS_STALE_TURNS
turns, the next would-be carry is forced off it (to a different content word, else
cleared). Topic analogue of the persona language guard (research log
topic_rut_2026-10-07_spec).

Covers: flag OFF is byte-identical to HEAD (carries indefinitely); the streak
accumulates and persists; a healthy short thread (< bound) is untouched; at the
bound a carry is forced to a different word; and when the reply offers no other
content word the focus clears.

Isolated tempdir DB (NEX5_DATA_DIR) — never the live DBs.
"""
from __future__ import annotations

import importlib
import os
import shutil
import tempfile
import unittest

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_focusrot_")
    os.environ["NEX5_DATA_DIR"] = tmp
    from substrate.init_db import init_all
    init_all()
    return tmp


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = _make_env()
        import theory_x.stage_tom.persona_responder as p
        importlib.reload(p)   # pick up NEX5_DATA_DIR for _db()
        self.p = p
        self.K = p._PERSONA_FOCUS_STALE_TURNS

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.pop("NEX5_DATA_DIR", None)
        os.environ.pop("NEX5_PERSONA_FOCUS_ROTATE", None)

    def _carry_optimism(self, n, tail=""):
        """Evolve `n` turns of replies that all contain 'optimism' (so the focus
        latches and then carries). An optional `tail` adds a second content word
        to the final reply so a forced drift has somewhere to go."""
        s = self.p._load_interlocutor_state()
        for i in range(n):
            reply = "optimism scaling matters" if i < n - 1 else f"optimism {tail}".strip()
            s = self.p._evolve_interlocutor_state(s, reply)
        return s


class TestFlagOff(_Base):
    """Default OFF: behaviour identical to HEAD — the focus carries indefinitely."""

    def test_carries_past_bound_when_off(self):
        s = self._carry_optimism(self.K + 3, tail="ethereum bridges")
        self.assertEqual(s["focus"], "optimism")          # never rotated
        self.assertEqual(s["focus_streak"], self.K + 3)   # streak kept growing

    def test_streak_accumulates_and_persists(self):
        self._carry_optimism(3)
        # streak lives in the row even though _load does not surface it
        import sqlite3
        conn = sqlite3.connect(self.p._db("conversations"))
        try:
            row = conn.execute(
                "SELECT focus, focus_streak FROM interlocutor_state WHERE id=1"
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual(row[0], "optimism")
        self.assertEqual(row[1], 3)

    def test_load_shape_unchanged(self):
        # _load still returns exactly the three legacy keys (HEAD contract).
        s = self.p._load_interlocutor_state()
        self.assertEqual(s, {"focus": "", "mood": 0.0, "turn_count": 0})


class TestFlagOn(_Base):
    def setUp(self):
        super().setUp()
        os.environ["NEX5_PERSONA_FOCUS_ROTATE"] = "1"

    def test_healthy_short_thread_not_rotated(self):
        # A genuine thread shorter than the bound carries normally (parallels
        # test_social_depth.test_focus_carries_when_thread_continues).
        self.assertLess(3, self.K + 1)          # guard: 3 is below the bound
        s = self._carry_optimism(3)
        self.assertEqual(s["focus"], "optimism")
        self.assertEqual(s["focus_streak"], 3)

    def test_rotates_to_different_word_at_bound(self):
        # Carry to the bound, then a reply that still names 'optimism' but offers
        # 'ethereum' too: the would-be (K+1)th carry is forced off onto 'ethereum'.
        s = self._carry_optimism(self.K + 1, tail="ethereum bridges")
        self.assertNotEqual(s["focus"], "optimism")       # rotated off the rut
        self.assertEqual(s["focus"], "ethereum")          # to the other content word
        self.assertEqual(s["focus_streak"], 1)            # fresh thread

    def test_clears_when_no_other_content_word(self):
        # At the bound, a reply whose only content word IS the stale focus: there
        # is nothing to drift to, so the focus clears (the next continuity line
        # names no stale topic and the persona resets to a fresh subject).
        s = self.p._load_interlocutor_state()
        for _ in range(self.K + 1):
            s = self.p._evolve_interlocutor_state(s, "optimism optimism")
        self.assertEqual(s["focus"], "")
        self.assertEqual(s["focus_streak"], 0)

    def test_rotation_is_gradual_not_thrash(self):
        # The streak resets after a rotate, so it takes another full K turns to
        # trip again — a sawtooth, not a per-turn thrash.
        s = self._carry_optimism(self.K + 1, tail="ethereum talks")
        self.assertEqual(s["focus"], "ethereum")
        self.assertEqual(s["focus_streak"], 1)
        # one more ethereum turn: carries (below bound again), does not rotate
        s = self.p._evolve_interlocutor_state(s, "ethereum rollups")
        self.assertEqual(s["focus"], "ethereum")
        self.assertEqual(s["focus_streak"], 2)


if __name__ == "__main__":
    unittest.main()
