"""Tests for Spark Cycle imprint signature (spec 4.6). Pure logic; no substrate."""

import unittest

from tests import _bootstrap  # noqa: F401
from theory_x.stage6_fountain.spark_cycle.signature import (
    compute_signature, _signed_capped, _direction, _tag_list,
)


class TestSignedCapped(unittest.TestCase):
    def test_zero_is_plus_zero(self):
        self.assertEqual(_signed_capped(0), "+0")

    def test_positive_signed(self):
        self.assertEqual(_signed_capped(2), "+2")

    def test_negative_signed(self):
        self.assertEqual(_signed_capped(-3), "-3")

    def test_caps_high(self):
        self.assertEqual(_signed_capped(9999), "+5")

    def test_caps_low(self):
        self.assertEqual(_signed_capped(-9999), "-5")

    def test_non_numeric_falls_to_zero(self):
        self.assertEqual(_signed_capped(None), "+0")
        self.assertEqual(_signed_capped("garbage"), "+0")


class TestDirection(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(_direction(0.4), "+")

    def test_negative(self):
        self.assertEqual(_direction(-0.001), "-")

    def test_exact_zero(self):
        self.assertEqual(_direction(0.0), "0")

    def test_non_numeric(self):
        self.assertEqual(_direction(None), "0")


class TestTagList(unittest.TestCase):
    def test_empty_and_none(self):
        self.assertEqual(_tag_list(None), "")
        self.assertEqual(_tag_list([]), "")

    def test_sorted(self):
        self.assertEqual(_tag_list(["systems", "ai_research"]), "ai_research,systems")
        self.assertEqual(_tag_list(["ai_research", "systems"]), "ai_research,systems")

    def test_truncates_to_three(self):
        self.assertEqual(_tag_list(["e", "d", "c", "b", "a"]), "a,b,c")

    def test_dedup(self):
        self.assertEqual(_tag_list(["x", "x", "y"]), "x,y")


class TestComputeSignature(unittest.TestCase):
    def _base(self):
        return {
            "belief_delta": 2,
            "edge_delta": 1,
            "temperature_shift": 0.3,
            "branch_reorientation": False,
            "graph_restructure": True,
            "belief_creation": True,
            "branches_shifted": ["systems", "ai_research"],
            "edge_types_created": ["supports", "cross_domain"],
        }

    def test_full_signature_shape(self):
        self.assertEqual(
            compute_signature(self._base()),
            "+2+1+011|ai_research,systems|cross_domain,supports",
        )

    def test_deterministic_repeat(self):
        d = self._base()
        self.assertEqual(compute_signature(d), compute_signature(d))

    def test_order_independence_collision(self):
        a = self._base()
        b = self._base()
        b["branches_shifted"] = ["ai_research", "systems"]
        b["edge_types_created"] = ["cross_domain", "supports"]
        self.assertEqual(compute_signature(a), compute_signature(b))

    def test_content_independence(self):
        self.assertEqual(compute_signature(self._base()), compute_signature(self._base()))

    def test_distinct_diffs_distinct_sigs(self):
        a = self._base()
        b = self._base()
        b["belief_delta"] = -2
        self.assertNotEqual(compute_signature(a), compute_signature(b))

    def test_empty_diff_neutral_signature(self):
        self.assertEqual(compute_signature({}), "+0+00000||")

    def test_capping_in_full_signature(self):
        d = self._base()
        d["belief_delta"] = 100
        d["edge_delta"] = -100
        self.assertTrue(compute_signature(d).startswith("+5-5"))

    def test_temperature_directions(self):
        for shift, expect in [(0.5, "+"), (-0.5, "-"), (0.0, "0")]:
            d = self._base()
            d["temperature_shift"] = shift
            self.assertEqual(compute_signature(d)[4], expect)

    def test_no_pipe_collision_between_branches_and_edges(self):
        d = self._base()
        d["branches_shifted"] = ["supports"]
        d["edge_types_created"] = ["supports"]
        prefix, branches, edges = compute_signature(d).split("|")
        self.assertEqual(branches, "supports")
        self.assertEqual(edges, "supports")


if __name__ == "__main__":
    unittest.main(verbosity=2)
