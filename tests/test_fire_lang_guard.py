"""NEX5_FIRE_LANG_GUARD — exit guard: a non-English fountain fire is
regenerated once in English, or dropped, so it is never stored, carried or
quoted (research log chinese_drift_2026-10-05, variable 2).
Flag off: unchanged.
"""
from __future__ import annotations

import os
import time
import unittest

from tests import _bootstrap  # noqa: F401
from tests.test_fountain import _cleanup, _make_env, _mock_dynamic_state

ZH = "这段时间里，我注意到很多东西都在变化，而且这些变化似乎越来越快。"
EN = "The battery story stuck with me: denser storage changes what a grid can hold."


class _Seq:
    """VoiceClient request_fn returning queued replies; records prompts."""
    def __init__(self, replies):
        self.replies, self.prompts = list(replies), []

    def __call__(self, url, payload):
        self.prompts.append(payload["messages"][-1]["content"])
        text = self.replies.pop(0) if self.replies else EN
        return {"choices": [{"message": {"content": text}}]}


class TestFireLangGuard(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self._prev = os.environ.get("NEX5_FIRE_LANG_GUARD")
        for i in range(21):
            self.writers["beliefs"].write(
                "INSERT INTO beliefs (content, tier, confidence, created_at, source, locked) "
                "VALUES (?, ?, ?, ?, ?, 0)", (f"belief {i}", 5, 0.5, int(time.time()), "auto_growth"))
        time.sleep(0.05)

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("NEX5_FIRE_LANG_GUARD", None)
        else:
            os.environ["NEX5_FIRE_LANG_GUARD"] = self._prev
        _cleanup(self.writers, self.tmp)

    def _fire(self, replies):
        from voice.llm import VoiceClient
        from theory_x.stage6_fountain.generator import FountainGenerator
        seq = _Seq(replies)
        gen = FountainGenerator(sense_writer=self.writers["sense"], dynamic_writer=self.writers["dynamic"],
                                voice_client=VoiceClient(request_fn=seq), dynamic_reader=self.readers["dynamic"])
        out = gen.generate(_mock_dynamic_state(hot_branch="systems", consolidation=True), self.readers["beliefs"])
        return out, seq

    def _stored(self):
        time.sleep(0.05)
        return [r["thought"] for r in self.readers["dynamic"].read("SELECT thought FROM fountain_events")]

    def test_flag_off_chinese_fire_is_stored(self):
        os.environ.pop("NEX5_FIRE_LANG_GUARD", None)
        out, seq = self._fire([ZH])
        self.assertEqual(out, ZH)
        self.assertEqual(len(seq.prompts), 1)

    def test_chinese_then_english_retry_is_kept(self):
        os.environ["NEX5_FIRE_LANG_GUARD"] = "1"
        out, seq = self._fire([ZH, EN])
        self.assertEqual(out, EN)
        self.assertEqual(len(seq.prompts), 2)
        self.assertTrue(seq.prompts[1].endswith("Write your thought in English."))
        self.assertNotIn(ZH, self._stored())

    def test_chinese_twice_drops_the_fire(self):
        os.environ["NEX5_FIRE_LANG_GUARD"] = "1"
        out, seq = self._fire([ZH, ZH])
        self.assertIsNone(out)
        self.assertEqual(len(seq.prompts), 2)
        self.assertFalse(any(ZH in (t or "") for t in self._stored()))

    def test_english_first_output_untouched(self):
        os.environ["NEX5_FIRE_LANG_GUARD"] = "1"
        out, seq = self._fire([EN])
        self.assertEqual(out, EN)
        self.assertEqual(len(seq.prompts), 1)


if __name__ == "__main__":
    unittest.main()
