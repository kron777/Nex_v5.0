"""Chat attention arbiter (W0 select_within_budget + the gui chat-block assembly).

Default OFF: the block assembly is byte-identical to the old concatenation.
ON (NEX5_CHAT_WORKSPACE=1): keep exempt blocks + highest-salience within budget.
"""
from __future__ import annotations

import os
import unittest

from tests._bootstrap import *  # noqa: F401, F403


class TestSelectWithinBudget(unittest.TestCase):

    def test_exempt_always_kept_rest_by_salience(self):
        from theory_x.stage_tom.global_workspace import select_within_budget
        # (salience, text, exempt); each text length 10
        cands = [
            (0.40, "P" * 10, False),   # low salience, non-exempt
            (0.90, "C" * 10, True),    # exempt — always kept
            (0.90, "V" * 10, False),   # high salience, non-exempt
            (0.50, "T" * 10, False),   # mid salience, non-exempt
        ]
        kept = select_within_budget(cands, char_budget=25)
        # exempt C (10) + highest non-exempt V (10) = 20 <= 25; T would be 30 > 25
        self.assertIn("C" * 10, kept)
        self.assertIn("V" * 10, kept)
        self.assertNotIn("T" * 10, kept)
        self.assertNotIn("P" * 10, kept)
        # original order preserved (P idx0 dropped, C idx1, V idx2)
        self.assertEqual(kept, ["C" * 10, "V" * 10])

    def test_generous_budget_keeps_all(self):
        from theory_x.stage_tom.global_workspace import select_within_budget
        cands = [(0.4, "a", False), (0.9, "b", True), (0.5, "c", False)]
        self.assertEqual(select_within_budget(cands, 1000), ["a", "b", "c"])

    def test_empty_texts_ignored(self):
        from theory_x.stage_tom.global_workspace import select_within_budget
        cands = [(0.9, "", False), (0.9, "x", True)]
        self.assertEqual(select_within_budget(cands, 1000), ["x"])


class TestAssembleChatBlocks(unittest.TestCase):

    def setUp(self):
        from gui.server import _assemble_chat_blocks
        self.assemble = _assemble_chat_blocks

    def tearDown(self):
        os.environ.pop("NEX5_CHAT_WORKSPACE", None)
        os.environ.pop("NEX5_CHAT_WORKSPACE_BUDGET", None)

    def _ordered(self):
        return [
            ("compassion", "C" * 20),     # exempt
            ("convo", "V" * 20),          # salience 0.90
            ("tag", "T" * 20),            # salience 0.50
            ("prasrabdhi", "P" * 20),     # salience 0.40
        ]

    def test_off_is_full_concatenation(self):
        os.environ.pop("NEX5_CHAT_WORKSPACE", None)
        out = self.assemble(self._ordered())
        self.assertEqual(out, "C" * 20 + "V" * 20 + "T" * 20 + "P" * 20)

    def test_on_trims_low_salience_keeps_exempt(self):
        os.environ["NEX5_CHAT_WORKSPACE"] = "1"
        os.environ["NEX5_CHAT_WORKSPACE_BUDGET"] = "45"  # fits compassion(20)+convo(20)=40
        out = self.assemble(self._ordered())
        self.assertIn("C" * 20, out)   # exempt kept
        self.assertIn("V" * 20, out)   # highest non-exempt kept
        self.assertNotIn("T" * 20, out)
        self.assertNotIn("P" * 20, out)
        # original order preserved
        self.assertEqual(out, "C" * 20 + "V" * 20)

    def test_on_generous_budget_is_full(self):
        os.environ["NEX5_CHAT_WORKSPACE"] = "1"
        os.environ["NEX5_CHAT_WORKSPACE_BUDGET"] = "100000"
        out = self.assemble(self._ordered())
        self.assertEqual(out, "C" * 20 + "V" * 20 + "T" * 20 + "P" * 20)


if __name__ == "__main__":
    unittest.main()
