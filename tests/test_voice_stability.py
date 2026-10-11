"""G3 voice-stability instrument: the information-theory math + style classifier.
Observational only (no flag, no fire-path change). ANALOGUE."""
from __future__ import annotations

import math
import unittest

from tests._bootstrap import *  # noqa: F401, F403


class TestVoiceMath(unittest.TestCase):

    def test_entropy_uniform_and_point(self):
        from theory_x.stage6_fountain import generator  # noqa: F401 (ensure import path)
        from tools.check_voice_stability import _entropy
        self.assertAlmostEqual(_entropy({"a": 1, "b": 1, "c": 1, "d": 1}), 2.0)  # log2(4)
        self.assertEqual(_entropy({"a": 5}), 0.0)
        self.assertEqual(_entropy({}), 0.0)

    def test_mutual_info_independent_is_zero(self):
        from tools.check_voice_stability import _mutual_info
        # S and C independent: joint = product of marginals (2x2, all equal)
        joint = {("s0", "c0"): 10, ("s0", "c1"): 10, ("s1", "c0"): 10, ("s1", "c1"): 10}
        self.assertAlmostEqual(_mutual_info(joint), 0.0, places=6)

    def test_mutual_info_perfect_dependence_equals_entropy(self):
        from tools.check_voice_stability import _mutual_info, _entropy
        # S determines C perfectly: I(S;C) == H(S) == H(C)
        joint = {("s0", "c0"): 20, ("s1", "c1"): 20}
        self.assertAlmostEqual(_mutual_info(joint), 1.0, places=6)      # log2(2)

    def test_style_classifier(self):
        from tools.check_voice_stability import _style_class
        self.assertEqual(_style_class("This item is about an ethereum layer network."), "item-frame")
        self.assertEqual(_style_class("The item discusses corporate accountability."), "item-frame")
        self.assertEqual(_style_class("I keep returning to the same half-thought here."), "self-ref")
        self.assertEqual(_style_class("Why does the market react this way to outages?"), "question-open")
        self.assertEqual(_style_class("Bitcoin dropped three percent after the exchange outage."), "topic-direct")
        self.assertEqual(_style_class("A historic cathedral started charging an entry fee."), "deictic-open")
        self.assertEqual(_style_class("The cathedral started charging a fee today."), "deictic-open")


if __name__ == "__main__":
    unittest.main()
