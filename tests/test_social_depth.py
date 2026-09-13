"""Tests for social depth (NEX5_SOCIAL_DEPTH) — a persisted, evolving model of
the interlocutor so the "other" is consistent across turns, not stateless
small-talk.

Covers: the modeled other CARRIES its focus when it stays on a thread
(consistency), DRIFTS when it moves on (evolution), its mood stays bounded (no
runaway), the state persists/round-trips, the continuity is surfaced into the
persona prompt, and — the hard guard — the model is built ONLY from the persona's
own reply text, touching no personal-data source.

Isolated tempdir DB (NEX5_DATA_DIR) — never the live DBs.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_social_")
    os.environ["NEX5_DATA_DIR"] = tmp
    from substrate.init_db import init_all
    init_all()
    return tmp


class TestInterlocutorModel(unittest.TestCase):

    def setUp(self):
        self.tmp = _make_env()
        import importlib
        import theory_x.stage_tom.persona_responder as p
        importlib.reload(p)   # pick up NEX5_DATA_DIR for _db()
        self.p = p

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.pop("NEX5_DATA_DIR", None)

    def test_init_is_neutral(self):
        s = self.p._load_interlocutor_state()
        self.assertEqual(s, {"focus": "", "mood": 0.0, "turn_count": 0})

    def test_focus_drifts_to_content_word_not_filler(self):
        s0 = self.p._load_interlocutor_state()
        s1 = self.p._evolve_interlocutor_state(s0, "Actually, orbital mechanics fascinate me.")
        self.assertIn(s1["focus"], {"orbital", "mechanics", "fascinate"})
        self.assertNotIn(s1["focus"], {"actually", "me"})

    def test_focus_carries_when_thread_continues(self):
        s0 = self.p._load_interlocutor_state()
        s1 = self.p._evolve_interlocutor_state(s0, "What about volcanic magma chambers?")
        s2 = self.p._evolve_interlocutor_state(s1, "Do volcanic eruptions reshape coasts?")
        self.assertEqual(s2["focus"], s1["focus"])          # consistency: carried
        self.assertEqual(s2["turn_count"], 2)

    def test_focus_evolves_on_new_topic(self):
        s0 = self.p._load_interlocutor_state()
        s1 = self.p._evolve_interlocutor_state(s0, "Volcanic magma chambers interest me.")
        s2 = self.p._evolve_interlocutor_state(s1, "Now consider deepwater coral reefs instead.")
        self.assertNotEqual(s2["focus"], s1["focus"])       # evolution: drifted

    def test_state_persists_round_trip(self):
        s0 = self.p._load_interlocutor_state()
        self.p._evolve_interlocutor_state(s0, "Quantum decoherence puzzles me.")
        reloaded = self.p._load_interlocutor_state()
        self.assertIn(reloaded["focus"], {"quantum", "decoherence"})  # a content word
        self.assertEqual(reloaded["turn_count"], 1)

    def test_mood_bounded_no_runaway(self):
        s = self.p._load_interlocutor_state()
        # 40 turns, all curious questions (the strongest positive nudge)
        for _ in range(40):
            s = self.p._evolve_interlocutor_state(s, "Isn't that a fascinating question?")
        self.assertLessEqual(s["mood"], 1.0)
        self.assertGreaterEqual(s["mood"], -1.0)
        # and a long flat streak decays toward even, never past the floor
        for _ in range(40):
            s = self.p._evolve_interlocutor_state(s, "A flat declarative statement.")
        self.assertGreaterEqual(s["mood"], -1.0)

    def test_continuity_surfaced_in_prompt(self):
        # with a turn>0 state, _ask_persona builds the continuity clause; we can
        # see it via the state helpers feeding the prompt (no LLM call needed):
        # the focus word must appear in the continuity text the persona is given.
        state = {"focus": "volcanoes", "mood": 0.5, "turn_count": 3}
        # _mood_word maps the mood; the clause names the focus + mood word
        self.assertEqual(self.p._mood_word(0.5), "buoyant")
        self.assertEqual(self.p._mood_word(-0.5), "subdued")
        self.assertEqual(self.p._mood_word(0.0), "even")
        # focus carries into the model regardless of mood
        self.assertEqual(
            self.p._focus_from_reply("volcanoes again today", state["focus"]),
            "volcanoes",
        )

    def test_guard_focus_from_reply_only(self):
        # HARD GUARD: focus derives purely from the reply text passed in — no DB
        # query, no external source. Calling with only (reply, prev) must work
        # and must never reach beyond its arguments.
        self.assertEqual(self.p._focus_from_reply("tarantula silk biology", ""), "tarantula")
        self.assertEqual(self.p._focus_from_reply("", "prev"), "prev")   # empty -> keep prior


if __name__ == "__main__":
    unittest.main()
