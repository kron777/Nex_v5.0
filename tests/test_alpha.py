"""Alpha immutability — mutation attempts raise TypeError."""
import unittest

from tests import _bootstrap  # noqa: F401

from alpha import ALPHA, THEORY_X_STAGE


class TestAlpha(unittest.TestCase):
    def test_five_lines(self):
        self.assertEqual(len(ALPHA.lines), 5)
        for line in ALPHA.lines:
            self.assertIsInstance(line, str)
            self.assertTrue(line)

    def test_first_line_is_sacred(self):
        self.assertIn("By pure chance", ALPHA.lines[0])

    def test_theory_x_stage_is_none(self):
        self.assertIsNone(THEORY_X_STAGE)

    def test_tuple_item_assignment_raises_typeerror(self):
        with self.assertRaises(TypeError):
            ALPHA.lines[0] = "tampered"  # type: ignore[index]

    def test_attribute_reassignment_blocked(self):
        # FrozenInstanceError is a subclass of AttributeError in stdlib.
        with self.assertRaises(AttributeError):
            ALPHA.lines = ("tampered",)  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
