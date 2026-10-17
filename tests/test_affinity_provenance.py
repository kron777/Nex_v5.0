"""Provenance-based affinity (D-A): the point of the change is ORDERING.

The old LLM self-rating is documented as hollow -- it rated a volcano headline
above her founding axiom. These tests pin the two properties that fix buys:

  1. Her own synthesis outranks a passing observation at equal usage.
  2. The output envelope is unchanged (0.225-0.60), so a shadow comparison
     against the old llm_rating*(0.75+0.25*usage) scores is meaningful.

Pure-function tests: no DB, no voice model.
"""
import os
import unittest

from tests import _bootstrap  # noqa: F401

from theory_x.life import affinity_loop as A


class TestProvenanceAffinity(unittest.TestCase):
    def test_ordering_authored_beats_witnessed_beats_received(self):
        # Equal usage: only provenance differs. This is the bug being fixed.
        for usage in (0.0, 0.3, 0.7, 1.0):
            authored = A._provenance_affinity("fountain_insight", usage)
            witnessed = A._provenance_affinity("surprise", usage)
            received = A._provenance_affinity("identity_loop", usage)
            self.assertGreater(authored, witnessed, f"usage={usage}")
            self.assertGreater(witnessed, received, f"usage={usage}")

    def test_envelope_preserved(self):
        # Old score ranged llm_rating*(0.75+0.25u), llm in {0.3,0.6} -> union
        # [0.225, 0.60]. New min = received@u=0, new max = authored@u=1.
        lo = A._provenance_affinity("identity_loop", 0.0)
        hi = A._provenance_affinity("fountain_insight", 1.0)
        self.assertAlmostEqual(lo, 0.225, places=6)
        self.assertAlmostEqual(hi, 0.600, places=6)
        # Nothing can escape [0,1].
        for src in ("fountain_insight", "surprise", "identity_loop", "mystery"):
            for u in (-1.0, 0.0, 0.5, 1.0, 2.0):
                v = A._provenance_affinity(src, u)
                self.assertGreaterEqual(v, 0.0)
                self.assertLessEqual(v, 1.0)

    def test_bands(self):
        # authored 0.45-0.60, witnessed 0.3375-0.45, received 0.225-0.30.
        self.assertAlmostEqual(A._provenance_affinity("synergized", 0.0), 0.45, 6)
        self.assertAlmostEqual(A._provenance_affinity("synergized", 1.0), 0.60, 6)
        self.assertAlmostEqual(A._provenance_affinity("pattern_loop", 0.0), 0.3375, 6)
        self.assertAlmostEqual(A._provenance_affinity("pattern_loop", 1.0), 0.45, 6)
        self.assertAlmostEqual(A._provenance_affinity("identity_loop", 0.0), 0.225, 6)
        self.assertAlmostEqual(A._provenance_affinity("identity_loop", 1.0), 0.30, 6)

    def test_unknown_source_is_received(self):
        unknown = A._provenance_affinity("brand_new_source_xyz", 0.5)
        received = A._provenance_affinity("identity_loop", 0.5)
        self.assertAlmostEqual(unknown, received, 6)

    def test_mode_defaults_off_and_parses(self):
        saved = os.environ.pop("NEX5_AFFINITY_PROVENANCE", None)
        try:
            self.assertEqual(A._affinity_mode(), "off")
            for val, exp in [("on", "on"), ("SHADOW", "shadow"), (" On ", "on"),
                             ("garbage", "off"), ("", "off")]:
                os.environ["NEX5_AFFINITY_PROVENANCE"] = val
                self.assertEqual(A._affinity_mode(), exp, val)
        finally:
            os.environ.pop("NEX5_AFFINITY_PROVENANCE", None)
            if saved is not None:
                os.environ["NEX5_AFFINITY_PROVENANCE"] = saved


if __name__ == "__main__":
    unittest.main()
