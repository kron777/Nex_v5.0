"""Prompt budget (D-B): pure-function tests. No model, no DB.

Pins Beam's spec: 70% ceiling, the per-faculty cap table, drop-lowest-first then
truncate-last, the ASCII marker, and the two-flag inert default.
"""
import os
import unittest

from tests import _bootstrap  # noqa: F401

import prompt_budget as B


class TestCeilingAndCaps(unittest.TestCase):
    def test_ceiling(self):
        self.assertEqual(B.ceiling_for(8192), 5734)
        self.assertEqual(B.ceiling_for(4096), 2867)
        self.assertEqual(B.ceiling_for(0), 0)
        self.assertEqual(B.ceiling_for(-1), 0)

    def test_cap_table_8192(self):
        c = B.ceiling_for(8192)
        caps = [B.cap_for(f, c) for f, _ in B.FACULTY_WEIGHTS]
        self.assertEqual(caps, [1433, 1032, 917, 745, 573, 458])

    def test_cap_table_4096(self):
        c = B.ceiling_for(4096)
        caps = [B.cap_for(f, c) for f, _ in B.FACULTY_WEIGHTS]
        self.assertEqual(caps, [716, 516, 458, 372, 286, 229])

    def test_weights_sum_to_090(self):
        self.assertAlmostEqual(sum(w for _, w in B.FACULTY_WEIGHTS), 0.90, 6)

    def test_min_cap_floor(self):
        # Tiny ceiling: the 200-token floor applies.
        self.assertEqual(B.cap_for("peripheral", 100), 200)


class TestMarker(unittest.TestCase):
    def test_marker_is_ascii(self):
        self.assertEqual(B.MARKER, " [...trimmed]")
        self.assertTrue(B.MARKER.isascii())
        self.assertNotIn("…", B.MARKER)


class TestApplyBudget(unittest.TestCase):
    def test_ctx_zero_is_passthrough(self):
        blocks = [("identity", "x" * 100000)]
        kept, rep = B.apply_budget(blocks, 0)
        self.assertEqual(kept, blocks)
        self.assertFalse(rep["applied"])

    def test_small_blocks_untouched(self):
        blocks = [("identity", "short."), ("beliefs", "also short.")]
        kept, rep = B.apply_budget(blocks, 8192)
        self.assertEqual(kept, blocks)
        self.assertEqual(rep["dropped"], [])
        self.assertNotIn(B.MARKER, "".join(t for _, t in kept))

    def test_oversized_block_capped_with_marker(self):
        # identity cap at 8192 is 1433 tokens (~5732 chars). Feed way more.
        big = ("This is a sentence. " * 2000)  # ~40k chars
        kept, rep = B.apply_budget([("identity", big)], 8192)
        text = kept[0][1]
        self.assertTrue(text.endswith(B.MARKER))
        self.assertLessEqual(B.est_tokens(text), B.cap_for("identity", 5734) + 4)

    def test_drop_lowest_priority_first(self):
        # ctx 800 -> ceiling 560; all caps hit the 200 floor. Three blocks each
        # big enough to fill their cap (200 tok) sum to 600 > 560, so the single
        # lowest-priority block is dropped (identity + beliefs = 400 <= 560).
        big = "a. " * 400  # ~300 tokens, truncates to the 200 cap
        blocks = [("identity", big), ("peripheral", big), ("beliefs", big)]
        kept, rep = B.apply_budget(blocks, 800)
        kept_fac = [f for f, _ in kept]
        self.assertIn("identity", kept_fac)          # highest priority survives
        self.assertNotIn("peripheral", kept_fac)     # lowest priority dropped first
        self.assertIn("peripheral", rep["dropped"])
        self.assertLessEqual(rep["total"], rep["ceiling"])

    def test_single_block_over_ceiling_truncated(self):
        big = "word. " * 5000
        kept, rep = B.apply_budget([("identity", big)], 1000)
        self.assertEqual(len(kept), 1)
        self.assertTrue(kept[0][1].endswith(B.MARKER))
        self.assertLessEqual(rep["total"], rep["ceiling"])

    def test_unknown_faculty_treated_as_peripheral(self):
        c = B.ceiling_for(8192)
        self.assertEqual(B.cap_for("mystery", c), B.cap_for("peripheral", c))

    def test_priority_order_preserved(self):
        blocks = [("identity", "i."), ("affect", "a."), ("beliefs", "b.")]
        kept, _ = B.apply_budget(blocks, 8192)
        self.assertEqual([f for f, _ in kept], ["identity", "affect", "beliefs"])


class TestEnableGate(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.get(k)
                       for k in ("NEX5_PROMPT_BUDGET", "NEX5_PROMPT_CTX")}
        for k in self._saved:
            os.environ.pop(k, None)

    def tearDown(self):
        for k, v in self._saved.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v

    def test_default_off(self):
        on, ctx = B.is_enabled()
        self.assertFalse(on)
        self.assertEqual(ctx, 0)

    def test_flag_on_but_ctx_unset_stays_off(self):
        os.environ["NEX5_PROMPT_BUDGET"] = "on"
        on, ctx = B.is_enabled()
        self.assertFalse(on)  # ctx 0 -> refuses to guess a ceiling

    def test_both_set_enables(self):
        os.environ["NEX5_PROMPT_BUDGET"] = "on"
        os.environ["NEX5_PROMPT_CTX"] = "8192"
        on, ctx = B.is_enabled()
        self.assertTrue(on)
        self.assertEqual(ctx, 8192)


if __name__ == "__main__":
    unittest.main()
