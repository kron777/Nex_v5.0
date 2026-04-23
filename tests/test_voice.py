"""Voice — system-prompt assembly and mockable HTTP client."""
import unittest

from tests import _bootstrap  # noqa: F401

from voice.llm import VoiceClient, VoiceRequest, build_system_prompt
from voice.registers import (
    ANALYTICAL,
    CONVERSATIONAL,
    PHILOSOPHICAL,
    TECHNICAL,
    by_name,
    classify,
    default_register,
)


class TestRegisters(unittest.TestCase):
    def test_classify_is_conversational_stub(self):
        self.assertIs(classify("anything at all"), CONVERSATIONAL)
        self.assertIs(classify(""), CONVERSATIONAL)
        self.assertIs(default_register(), CONVERSATIONAL)

    def test_by_name_case_insensitive(self):
        self.assertIs(by_name("Analytical"), ANALYTICAL)
        self.assertIs(by_name("philosophical"), PHILOSOPHICAL)
        self.assertIs(by_name("TECHNICAL"), TECHNICAL)
        self.assertIsNone(by_name("nope"))


class TestSystemPrompt(unittest.TestCase):
    def test_alpha_present(self):
        sp = build_system_prompt(CONVERSATIONAL)
        self.assertIn("By pure chance", sp)
        self.assertIn("Conversational", sp)

    def test_no_disclaimer_language(self):
        sp = build_system_prompt(CONVERSATIONAL)
        lowered = sp.lower()
        # Affirmation-only discipline: the specific spec-§5 anti-patterns
        # must not appear as things NEX is being told to say. (An instruction
        # to AVOID disclaimers is itself allowed — hence we check phrases,
        # not the bare word "disclaimer".)
        self.assertNotIn("i'm not a financial advisor", lowered)
        self.assertNotIn("not financial advice", lowered)
        self.assertNotIn("i cannot tell you", lowered)
        self.assertNotIn("please consult", lowered)

    def test_context_included(self):
        sp = build_system_prompt(CONVERSATIONAL, context=["u:jon", "t:ai"])
        self.assertIn("u:jon", sp)
        self.assertIn("t:ai", sp)


class TestVoiceClient(unittest.TestCase):
    def test_mock_roundtrip(self):
        calls = []

        def mock_req(url, payload):
            calls.append((url, payload))
            return {"choices": [{"message": {"content": "she speaks"}}]}

        client = VoiceClient(request_fn=mock_req)
        resp = client.speak(VoiceRequest(prompt="hello"))
        self.assertEqual(resp.text, "she speaks")
        self.assertIs(resp.register, CONVERSATIONAL)
        self.assertEqual(len(calls), 1)
        _, payload = calls[0]
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(payload["messages"][1]["role"], "user")
        self.assertEqual(payload["messages"][1]["content"], "hello")


if __name__ == "__main__":
    unittest.main()
