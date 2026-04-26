"""Tests for role-framing strip in voice.llm."""
import unittest


class TestRoleFramingStrip(unittest.TestCase):

    def _strip(self, s):
        from voice.llm import _strip_role_framing
        return _strip_role_framing(s)

    def test_strips_as_nex(self):
        result = self._strip("As NEX, I attend to the world.")
        self.assertFalse(result.lower().startswith("as nex"))
        self.assertEqual(result, "I attend to the world.")

    def test_strips_as_nex_no_comma(self):
        result = self._strip("As NEX I attend to the world.")
        self.assertFalse(result.lower().startswith("as nex"))

    def test_strips_as_an_ai(self):
        result = self._strip("As an AI, I cannot truly feel.")
        self.assertFalse(result.lower().startswith("as an ai"))

    def test_strips_speaking_as_nex(self):
        result = self._strip("Speaking as NEX, here is my view.")
        self.assertFalse(result.lower().startswith("speaking as"))

    def test_strips_in_my_role(self):
        result = self._strip("In my role as NEX, I observe.")
        self.assertFalse(result.lower().startswith("in my role"))

    def test_strips_from_my_perspective(self):
        result = self._strip("From my perspective as NEX, markets look volatile.")
        self.assertFalse(result.lower().startswith("from my perspective"))

    def test_strips_as_the_nex_system(self):
        result = self._strip("As the NEX system, I process feeds.")
        self.assertFalse(result.lower().startswith("as the nex"))

    def test_capitalizes_after_strip(self):
        result = self._strip("As NEX, i keep coming back to this.")
        self.assertTrue(result[0].isupper())

    def test_preserves_non_framed(self):
        result = self._strip("I attend to the world.")
        self.assertEqual(result, "I attend to the world.")

    def test_preserves_nex_in_middle(self):
        result = self._strip("I am NEX, running since yesterday.")
        self.assertEqual(result, "I am NEX, running since yesterday.")

    def test_handles_empty_string(self):
        self.assertEqual(self._strip(""), "")

    def test_handles_none(self):
        self.assertIsNone(self._strip(None))

    def test_case_insensitive(self):
        result = self._strip("AS NEX, something.")
        self.assertFalse(result.lower().startswith("as nex"))

    def test_system_prompt_contains_prohibition(self):
        from voice.llm import _CHAT_SYSTEM_PROMPT
        self.assertIn("As NEX", _CHAT_SYSTEM_PROMPT)
        self.assertIn("ABSOLUTELY FORBIDDEN", _CHAT_SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
