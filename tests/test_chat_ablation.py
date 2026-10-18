"""NEX5_CHAT_ABLATE — step-0 assembly ablation instrument.

Drops named chat faculty blocks so their contribution can be A/B measured; default
off = byte-identical concatenation; exempt (safety) blocks never droppable; fail-safe.
"""
import os
import unittest

from tests import _bootstrap  # noqa: F401

from gui.server import _assemble_chat_blocks

_ORDERED = [
    ("operator", "OP. "),
    ("affect_carry", "AFFECT. "),
    ("compassion", "COMPASSION. "),   # exempt
    ("convo", "CONVO. "),
    ("tag", "TAG. "),
]


class TestChatAblation(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("NEX5_CHAT_ABLATE", None)

    def test_default_off_is_full_concat(self):
        os.environ.pop("NEX5_CHAT_ABLATE", None)
        out = _assemble_chat_blocks(list(_ORDERED))
        self.assertEqual(out, "OP. AFFECT. COMPASSION. CONVO. TAG. ")

    def test_drops_named_blocks(self):
        os.environ["NEX5_CHAT_ABLATE"] = "affect_carry,tag"
        out = _assemble_chat_blocks(list(_ORDERED))
        self.assertNotIn("AFFECT.", out)
        self.assertNotIn("TAG.", out)
        self.assertIn("CONVO.", out)
        self.assertIn("OP.", out)

    def test_exempt_block_never_dropped(self):
        os.environ["NEX5_CHAT_ABLATE"] = "compassion,convo"
        out = _assemble_chat_blocks(list(_ORDERED))
        self.assertIn("COMPASSION.", out)   # exempt: refused
        self.assertNotIn("CONVO.", out)     # non-exempt: dropped

    def test_unknown_kind_is_noop(self):
        os.environ["NEX5_CHAT_ABLATE"] = "does_not_exist"
        out = _assemble_chat_blocks(list(_ORDERED))
        self.assertEqual(out, "OP. AFFECT. COMPASSION. CONVO. TAG. ")


if __name__ == "__main__":
    unittest.main()
