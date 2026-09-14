"""Tests for the compassion (karuna) module — NEX5_COMPASSION, Option B-person.

Other-directed: reads the PERSON's distress from their incoming message (semantic,
via embeddings — not a keyword table), holds a bounded decaying compassion_level,
and injects a care/non-harm STANCE (prompt-only) when high. Admin-scoped;
non-admin/public chat untouched. Guard 2: stance never written to a belief/world
table.

Directions tested: level rises on a distress cue and decays without one; the
stance is injected when armed (admin+flag) and absent when the flag is off or the
session is non-admin.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

_DISTRESS = "my father passed last week and I can barely function or sleep"
_MILD = "I'm kind of stuck and not sure what to try next"
_NEUTRAL = "what do you think about using rust for the new parser"


class TestCompassionLevel(unittest.TestCase):
    """The signal + level dynamics, in isolation."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nex5_karuna_")
        os.environ["NEX5_DATA_DIR"] = self.tmp
        from substrate.init_db import init_all
        init_all()
        import importlib
        from theory_x.stage_affect import compassion as k
        importlib.reload(k)
        self.k = k

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.pop("NEX5_DATA_DIR", None)

    def test_semantic_read_separates_distress_from_neutral(self):
        # semantic, not keyword: distress paraphrase scores, neutral ~0
        self.assertGreater(self.k.distress_salience(_DISTRESS), 0.2)
        self.assertEqual(self.k.distress_salience(_NEUTRAL), 0.0)
        self.assertEqual(self.k.distress_salience(""), 0.0)

    def test_level_rises_on_distress(self):
        lvl = self.k.update_and_level(_DISTRESS)
        self.assertGreaterEqual(lvl, self.k._THRESHOLD)
        self.assertTrue(self.k.format_stance(lvl))          # stance fires

    def test_level_decays_without_distress(self):
        hi = self.k.update_and_level(_DISTRESS)
        d1 = self.k.update_and_level(_NEUTRAL)
        d2 = self.k.update_and_level(_NEUTRAL)
        self.assertLess(d1, hi)                              # decays
        self.assertLess(d2, d1)                              # keeps decaying toward baseline
        self.assertFalse(self.k.format_stance(d1))           # no stance once below threshold

    def test_persists_to_compassion_state(self):
        self.k.update_and_level(_DISTRESS)
        import sqlite3
        from substrate.paths import db_paths
        c = sqlite3.connect(f"file:{db_paths()['conversations']}?mode=ro", uri=True)
        row = c.execute("SELECT compassion_level, ethical_bias FROM compassion_state WHERE id=1").fetchone()
        c.close()
        self.assertIsNotNone(row)
        self.assertGreaterEqual(row[0], self.k._THRESHOLD)

    def test_failsafe_returns_baseline(self):
        # a bad message type -> baseline, no raise
        self.assertEqual(self.k.distress_salience(None), 0.0)

    def test_register_separates_acute_from_mild(self):
        # magnitude can't separate the registers; the anchor-family cut can
        self.assertEqual(self.k.distress_register(_DISTRESS), "acute")
        self.assertEqual(self.k.distress_register(_MILD), "mild")
        self.assertEqual(self.k.distress_register(None), "mild")   # fail-safe: lighter

    def test_graded_stance_tiers(self):
        hi = self.k._THRESHOLD + 0.1
        self.assertEqual(self.k.format_stance(hi, "acute"), self.k._STANCE_FULL)
        self.assertEqual(self.k.format_stance(hi, "mild"), self.k._STANCE_LIGHT)
        self.assertEqual(self.k.format_stance(self.k._THRESHOLD - 0.1, "acute"), "")
        self.assertEqual(self.k.format_stance(self.k._THRESHOLD - 0.1, "mild"), "")

    def test_stance_for_picks_tier_by_message(self):
        # ordered neutral -> mild -> acute from a fresh baseline, so decay memory
        # never lifts a lower tier: neutral stays silent, mild is light, acute full
        self.assertEqual(self.k.stance_for(_NEUTRAL), "")            # baseline, silent
        self.assertEqual(self.k.stance_for(_MILD), self.k._STANCE_LIGHT)
        self.assertEqual(self.k.stance_for(_DISTRESS), self.k._STANCE_FULL)


class TestCompassionInjection(unittest.TestCase):
    """The stance riding the compose prompt, via the real chat handler."""

    def _build(self, request_fn):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        os.environ["NEX5_DATA_DIR"] = t
        os.environ["NEX5_ADMIN_HASH_FILE"] = str(Path(t) / "admin.argon2")
        from substrate.init_db import init_all
        init_all()
        from admin.auth import set_password
        set_password("pw")
        from substrate import Reader, Writer, db_paths
        from voice.llm import VoiceClient
        from gui.server import AppState, create_app
        paths = db_paths()
        self.writers = {n: Writer(p, name=n) for n, p in paths.items()}
        self.readers = {n: Reader(p) for n, p in paths.items()}
        self.state = AppState(writers=self.writers, readers=self.readers,
                              voice=VoiceClient(request_fn=request_fn),
                              voice_engine=None, voice_mode="use_substrate")
        self.app = create_app(self.state)

    def tearDown(self):
        try:
            self.state.close()
        finally:
            self.tmp.cleanup()
            for k in ("NEX5_DATA_DIR", "NEX5_ADMIN_HASH_FILE", "NEX5_COMPASSION"):
                os.environ.pop(k, None)

    def _run(self, admin, flag, prompt):
        captured = []
        self._build(lambda url, payload: (captured.append(payload),
                    {"choices": [{"message": {"content": "a reply"}}]})[1])
        if flag:
            os.environ["NEX5_COMPASSION"] = "1"
        else:
            os.environ.pop("NEX5_COMPASSION", None)
        c = self.app.test_client()
        with c.session_transaction() as sess:
            if admin:
                sess["admin"] = True
            sess["chat_session_id"] = "S"
        c.post("/api/chat", json={"prompt": prompt})
        return json.dumps(captured[-1]) if captured else ""

    def test_stance_injected_admin_flag_on_distress(self):
        blob = self._run(admin=True, flag=True, prompt=_DISTRESS)
        self.assertIn("Compassion is up in you", blob)

    def test_no_stance_when_flag_off(self):
        blob = self._run(admin=True, flag=False, prompt=_DISTRESS)
        self.assertNotIn("Compassion is up in you", blob)

    def test_no_stance_non_admin(self):
        blob = self._run(admin=False, flag=True, prompt=_DISTRESS)
        self.assertNotIn("Compassion is up in you", blob)

    def test_no_stance_on_neutral_message(self):
        blob = self._run(admin=True, flag=True, prompt=_NEUTRAL)
        self.assertNotIn("Compassion is up in you", blob)


if __name__ == "__main__":
    unittest.main()
