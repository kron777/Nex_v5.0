"""SignalToProblem tag generation follows the shared Tag Protocol."""
from __future__ import annotations

import json
import unittest

from theory_x.signals.signal_to_problem import _problem_tags


class TestSignalProblemTags(unittest.TestCase):
    def test_content_tags_are_generated_and_origin_tags_normalized(self):
        tags = json.loads(_problem_tags(
            "Investigate quantum coherence",
            "Evidence connects quantum coherence across independent systems.",
            "2_branch",
        ))

        self.assertIn("quantum", tags)
        self.assertIn("coherence", tags)
        self.assertIn("auto", tags)
        self.assertIn("signal2branch", tags)
        self.assertEqual(len(tags), len(set(tags)))
        self.assertTrue(all(tag == tag.lower() for tag in tags))
        self.assertTrue(all(":" not in tag for tag in tags))


if __name__ == "__main__":
    unittest.main()
