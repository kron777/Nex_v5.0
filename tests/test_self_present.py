"""self_present (W3): the structured present carries salience across turns.

Storing the candidate VECTOR (not the rendered line) is what makes attention
continuous: a block that led last turn keeps momentum this turn.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest

from tests._bootstrap import *  # noqa: F401, F403


class TestEvolve(unittest.TestCase):

    def test_new_kind_is_raw(self):
        from theory_x.stage_tom.self_present import evolve
        self.assertEqual(evolve({}, {"a": 0.5}), {"a": 0.5})

    def test_carried_kind_mean_reverts(self):
        from theory_x.stage_tom.self_present import evolve
        out = evolve({"a": 0.9}, {"a": 0.3}, keep=0.7)
        self.assertAlmostEqual(out["a"], 0.72, places=6)   # 0.7*0.9 + 0.3*0.3

    def test_clamped(self):
        from theory_x.stage_tom.self_present import evolve
        out = evolve({"a": 1.0}, {"a": 1.0})
        self.assertLessEqual(out["a"], 1.0)


class TestUpdateCarry(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nex5_sp_")
        os.environ["NEX5_DATA_DIR"] = self.tmp
        from substrate.init_db import init_all
        init_all()
        from substrate import Writer, Reader, db_paths
        self.w = Writer(str(db_paths()["conversations"]), name="conversations")
        self.r = Reader(str(db_paths()["conversations"]))

    def tearDown(self):
        try:
            self.w.close()
        except Exception:
            pass
        os.environ.pop("NEX5_DATA_DIR", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_attention_has_momentum_across_turns(self):
        from theory_x.stage_tom import self_present as sp
        # turn 1: convo leads
        b1 = sp.update("s1", {"convo": 0.9, "tag": 0.5}, self.w, self.r)
        self.assertEqual(max(b1, key=b1.get), "convo")
        time.sleep(0.15)  # let the writer flush before the next read
        # turn 2: tag is raw-dominant, but convo's carried salience holds the lead
        b2 = sp.update("s1", {"convo": 0.3, "tag": 0.9}, self.w, self.r)
        self.assertEqual(max(b2, key=b2.get), "convo",
                         "carried salience should give convo momentum")
        time.sleep(0.15)
        st = sp.load("s1", self.r)
        self.assertEqual(st["turn_count"], 2)
        self.assertEqual(st["winner_kind"], "convo")

    def test_eventually_yields_to_sustained_signal(self):
        from theory_x.stage_tom import self_present as sp
        sp.update("s2", {"convo": 0.9, "tag": 0.5}, self.w, self.r)
        for _ in range(4):                       # tag sustained-dominant
            time.sleep(0.12)
            b = sp.update("s2", {"convo": 0.2, "tag": 0.9}, self.w, self.r)
        self.assertEqual(max(b, key=b.get), "tag",
                         "a sustained signal should eventually take the lead")

    def test_fail_safe_returns_raw(self):
        from theory_x.stage_tom import self_present as sp
        raw = {"a": 0.5}
        self.assertEqual(sp.update(None, raw, self.w, self.r), raw)
        self.assertEqual(sp.update("s", raw, None, None), raw)


class TestArbiterIntegration(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nex5_spi_")
        os.environ["NEX5_DATA_DIR"] = self.tmp
        from substrate.init_db import init_all
        init_all()
        from substrate import Writer, Reader, db_paths
        self.w = Writer(str(db_paths()["conversations"]), name="conversations")
        self.r = Reader(str(db_paths()["conversations"]))

    def tearDown(self):
        try:
            self.w.close()
        except Exception:
            pass
        for k in ("NEX5_DATA_DIR", "NEX5_CHAT_WORKSPACE", "NEX5_SELF_PRESENT"):
            os.environ.pop(k, None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_assemble_persists_self_present_when_enabled(self):
        from gui.server import _assemble_chat_blocks
        from theory_x.stage_tom import self_present as sp
        os.environ["NEX5_CHAT_WORKSPACE"] = "1"
        os.environ["NEX5_SELF_PRESENT"] = "1"
        ordered = [("convo", "V" * 10), ("tag", "T" * 10), ("compassion", "C" * 10)]
        out = _assemble_chat_blocks(ordered, session_id="sess", conv_writer=self.w,
                                    conv_reader=self.r)
        self.assertIsInstance(out, str)
        time.sleep(0.15)
        st = sp.load("sess", self.r)
        self.assertIsNotNone(st)
        self.assertEqual(st["turn_count"], 1)


if __name__ == "__main__":
    unittest.main()
