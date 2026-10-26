"""_assemble_chat_blocks (M5 workspace budget).

The load-bearing guarantee: with NEX5_CHAT_WORKSPACE unset (the default), the
assembled prompt is byte-identical to plain concatenation. That is what makes it
safe for the owner to flip the flag on later — off is provably a no-op.
"""
import os
import unittest

from tests import _bootstrap  # noqa: F401

from gui.server import _assemble_chat_blocks, _CHAT_BLOCK_EXEMPT

_ORDERED = [
    ("operator", "OP. "), ("compassion", "CARE. "), ("compass", "MORAL. "),
    ("equanimity", "EQ. "), ("virya", "VIR. "), ("convo", "CONVO. "),
    ("spectrum", "SPEC. "), ("tag", "TAG. "),
]


class TestChatBlocksBudget(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in
                       ("NEX5_CHAT_WORKSPACE", "NEX5_CHAT_WORKSPACE_BUDGET",
                        "NEX5_SELF_PRESENT")}
        for k in self._saved:
            os.environ.pop(k, None)

    def tearDown(self):
        for k, v in self._saved.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v

    def test_default_off_is_byte_identical(self):
        os.environ.pop("NEX5_CHAT_WORKSPACE", None)
        out = _assemble_chat_blocks(_ORDERED)
        self.assertEqual(out, "".join(t for _, t in _ORDERED))

    def test_exempt_blocks_survive_a_tight_budget(self):
        # Safety blocks are never evicted, even at a budget smaller than their size.
        os.environ["NEX5_CHAT_WORKSPACE"] = "1"
        os.environ["NEX5_CHAT_WORKSPACE_BUDGET"] = "1"
        out = _assemble_chat_blocks(_ORDERED)
        for kind, text in _ORDERED:
            if kind in _CHAT_BLOCK_EXEMPT:
                self.assertIn(text, out, f"exempt block {kind} was dropped")

    def test_flag_on_returns_string(self):
        # Fail-safe: whatever happens, it returns a string and never raises.
        os.environ["NEX5_CHAT_WORKSPACE"] = "1"
        self.assertIsInstance(_assemble_chat_blocks(_ORDERED), str)


if __name__ == "__main__":
    unittest.main()
