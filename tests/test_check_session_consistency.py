"""The session-consistency harness measures self-repetition and register collapse."""
from __future__ import annotations

import unittest

from tests._bootstrap import *  # noqa: F401, F403


class TestSelfRepetition(unittest.TestCase):

    def test_detects_within_session_repeat(self):
        from tools.check_session_consistency import self_repetition
        same = "The pattern keeps returning to the same shape again and again"
        msgs = [
            {"session_id": "s1", "content": f"{same}. One."},
            {"session_id": "s1", "content": f"{same}. Two."},   # near-dup of the first
            {"session_id": "s1", "content": "A totally separate remark about markets."},
            {"session_id": "s2", "content": "Only one nex message here, no pair."},
        ]
        r = self_repetition(msgs, threshold=0.5)
        self.assertEqual(r["sessions_with_multiple_nex_msgs"], 1)   # s2 has only 1
        self.assertGreaterEqual(r["worst_session_self_repetition"], 0.5)
        self.assertEqual(r["fraction_sessions_with_near_dup"], 1.0)

    def test_distinct_messages_no_repeat(self):
        from tools.check_session_consistency import self_repetition
        msgs = [
            {"session_id": "s1", "content": "First distinct thought about neurons firing."},
            {"session_id": "s1", "content": "Second unrelated note on crypto liquidity today."},
        ]
        r = self_repetition(msgs, threshold=0.5)
        self.assertLess(r["worst_session_self_repetition"], 0.5)
        self.assertEqual(r["fraction_sessions_with_near_dup"], 0.0)


class TestRegisterCollapse(unittest.TestCase):

    def test_distribution_and_share(self):
        from tools.check_session_consistency import register_collapse
        msgs = [
            {"register": "Philosophical"}, {"register": "Philosophical"},
            {"register": "Philosophical"}, {"register": "Conversational"},
            {"register": None},  # nullable — not counted as populated
        ]
        r = register_collapse(msgs)
        self.assertEqual(r["nex_messages"], 5)
        self.assertAlmostEqual(r["register_populated_fraction"], 0.8, places=4)  # 4/5
        self.assertEqual(r["distinct_registers"], 2)
        self.assertAlmostEqual(r["largest_register_share"], 0.75, places=4)      # 3/4

    def test_all_null_registers(self):
        from tools.check_session_consistency import register_collapse
        r = register_collapse([{"register": None}, {"register": None}])
        self.assertEqual(r["register_populated_fraction"], 0.0)
        self.assertIsNone(r["largest_register_share"])


if __name__ == "__main__":
    unittest.main()
