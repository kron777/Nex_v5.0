"""L4 phrasing rotation (NEX5_PHRASING_ROTATE): _rotate_item_referent swaps the
'the/this item' referent for a rotated one per fire, so the "this item is about..."
opener frame can't lock in. Default OFF at the call site => prompt byte-identical. ANALOGUE.
"""
from __future__ import annotations

import unittest

from tests._bootstrap import *  # noqa: F401, F403


class TestRotateItemReferent(unittest.TestCase):

    def test_replaces_the_item_with_a_non_item_referent(self):
        from theory_x.stage6_fountain.generator import _rotate_item_referent, _ITEM_REFERENTS
        out = _rotate_item_referent("Use ONLY what is in the item.", 0)
        self.assertNotIn("the item", out)
        self.assertIn(_ITEM_REFERENTS[0], out)          # "the passage"
        self.assertEqual(out, "Use ONLY what is in the passage.")

    def test_replaces_this_item_too(self):
        from theory_x.stage6_fountain.generator import _rotate_item_referent
        out = _rotate_item_referent("Reflect on this item now.", 0)
        self.assertNotIn("this item", out)
        self.assertIn("the passage", out)

    def test_preserves_leading_capitalization(self):
        from theory_x.stage6_fountain.generator import _rotate_item_referent
        out = _rotate_item_referent("The item matters.", 1)   # -> "the material"
        self.assertTrue(out.startswith("The material"))        # capital preserved

    def test_rotates_by_fire_count(self):
        from theory_x.stage6_fountain.generator import _rotate_item_referent, _ITEM_REFERENTS
        seen = {_rotate_item_referent("in the item", i).split("in ", 1)[1]
                for i in range(len(_ITEM_REFERENTS))}
        self.assertEqual(seen, set(_ITEM_REFERENTS))           # all referents cycled through

    def test_leaves_unrelated_text_untouched(self):
        from theory_x.stage6_fountain.generator import _rotate_item_referent
        t = "A historic cathedral charges an entry fee; itemize later."
        self.assertEqual(_rotate_item_referent(t, 0), t)       # no 'the/this item' token

    def test_fail_safe_on_bad_input(self):
        from theory_x.stage6_fountain.generator import _rotate_item_referent
        self.assertIsNone(_rotate_item_referent(None, 0))      # re.sub raises -> returns input (None)


if __name__ == "__main__":
    unittest.main()
