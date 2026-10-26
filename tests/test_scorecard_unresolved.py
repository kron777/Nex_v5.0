"""Fresh store: nothing resolved yet, so scorecard_by_source reports
hit_rate=None. Both consumers must treat that as "still measuring", not crash
(ground_self_belief) or fall into the "tested and not reliable" branch
(calibration_consult) -- a false claim when she has not been tested at all."""
import unittest
from unittest import mock

from tests import _bootstrap  # noqa: F401

_EMPTY = {"resolved": 0, "correct": 0, "hit_rate": None}


class TestUnresolvedScorecard(unittest.TestCase):

    def test_self_belief_sentence_says_still_measuring(self):
        import ground_self_belief as gsb
        s = gsb._compose_sentence(dict(_EMPTY), dict(_EMPTY))
        self.assertIn("do not yet have enough resolved guesses", s)
        self.assertIn("0 right out of 0", s)

    def test_consult_is_provisional_not_unreliable(self):
        from theory_x.stage_world import calibration_consult as cc
        reader = mock.Mock()
        reader.read_one.return_value = {"content": "the shelved self-belief"}
        with mock.patch.object(cc, "_beliefs_reader", return_value=reader), \
                mock.patch.object(cc, "_live_numbers",
                                  return_value=(dict(_EMPTY), dict(_EMPTY))):
            v = cc.consult_self_trust()
        self.assertEqual(v["level"], "provisional")
        self.assertEqual(v["n"], 0)
        self.assertNotIn("not reliable", v["phrase"])
        self.assertIn("still measuring", v["phrase"])


if __name__ == "__main__":
    unittest.main()
