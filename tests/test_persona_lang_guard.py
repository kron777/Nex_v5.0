"""NEX5_PERSONA_LANG_GUARD — the persona responder stays in English.

Chinese-drift fix (research log chinese_drift_2026-10-05_spec.txt): one
Chinese persona reply became the persisted SOCIAL_DEPTH focus (whitespace
tokenizer -> the whole sentence is one "word"), and every later call was told
to carry that thread forward -> permanent Chinese lock-in, fed into every
fountain prompt via the SOCIAL block. With the guard on:
  (i)  the bouncer discards non-English replies (reason "non_english");
  (ii) the persisted focus is ASCII words only, and a stored non-ASCII focus
       suppresses the continuity line (heals the existing lock).
Flag off: byte-identical behaviour.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tests import _bootstrap  # noqa: F401

ZH = "确实，那些自适应的大模型技术改变了很多。那么，它们在教育领域的发展潜力是什么？"
EN = "Relationships can be complex layers too. How about empathy in building connections?"


class _Base(unittest.TestCase):
    def setUp(self):
        self._prev = os.environ.get("NEX5_PERSONA_LANG_GUARD")

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("NEX5_PERSONA_LANG_GUARD", None)
        else:
            os.environ["NEX5_PERSONA_LANG_GUARD"] = self._prev


class TestFlagOff(_Base):
    def test_off_keeps_old_behaviour(self):
        os.environ.pop("NEX5_PERSONA_LANG_GUARD", None)
        from theory_x.stage_tom import persona_responder as P
        self.assertEqual(P._focus_from_reply(ZH, ""), P._normalize_tokens(ZH)[0])
        discard, reason, _, _ = P._check_reply(ZH, ["an unrelated english thought here"])
        self.assertFalse(discard)


class TestGuardOn(_Base):
    def setUp(self):
        super().setUp()
        os.environ["NEX5_PERSONA_LANG_GUARD"] = "1"

    def test_bouncer_discards_chinese_reply(self):
        from theory_x.stage_tom import persona_responder as P
        discard, reason, _, _ = P._check_reply(ZH, ["an unrelated english thought here"])
        self.assertTrue(discard)
        self.assertEqual(reason, "non_english")

    def test_bouncer_passes_english_and_light_accents(self):
        from theory_x.stage_tom import persona_responder as P
        for txt in (EN, "Café culture in Zürich is a curious case, NEX — what about it?"):
            discard, reason, _, _ = P._check_reply(txt, ["an unrelated english thought here"])
            self.assertFalse(discard, (txt, reason))

    def test_focus_ignores_non_ascii_tokens(self):
        from theory_x.stage_tom import persona_responder as P
        self.assertEqual(P._focus_from_reply(ZH, ""), "")
        self.assertEqual(P._focus_from_reply(ZH + " " + EN, ""), P._focus_from_reply(EN, ""))
        self.assertTrue(P._focus_from_reply(EN, "").isascii())

    def test_non_ascii_stored_focus_drops_continuity_line(self):
        from theory_x.stage_tom import persona_responder as P
        captured = {}

        class _Resp:
            def __init__(self, body): self._b = body
            def read(self): return self._b
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def fake_urlopen(req, timeout=0):
            import json
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _Resp(json.dumps({"choices": [{"message": {"content": EN}}]}).encode())

        with mock.patch.object(P.urllib.request, "urlopen", fake_urlopen):
            P._ask_persona(["a thought"], state={"focus": ZH, "mood": 0.0, "turn_count": 5})
            user = captured["body"]["messages"][1]["content"]
            self.assertNotIn(ZH, user)
            self.assertNotIn("Continuity", user)
            P._ask_persona(["a thought"], state={"focus": "relationships", "mood": 0.0, "turn_count": 5})
            self.assertIn("relationships", captured["body"]["messages"][1]["content"])


if __name__ == "__main__":
    unittest.main()
