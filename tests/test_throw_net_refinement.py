"""Tests for TN-3 RefinementEngine — R1-R6 scoring, 0-6 scale."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from theory_x.stage_throw_net.refinement_engine import RefinementEngine


def _reader(rows=None, raise_exc=None):
    reader = MagicMock()
    if raise_exc is not None:
        reader.read.side_effect = raise_exc
    else:
        reader.read.return_value = rows or []
    return reader


def _engine(rows=None, raise_exc=None):
    return RefinementEngine(_reader(rows=rows, raise_exc=raise_exc))


def _candidate(content: str) -> dict:
    return {"content": content, "source": "belief", "origin_id": 1}


class TestScoreStructure(unittest.TestCase):

    def test_score_returns_required_keys(self):
        eng = _engine(rows=[{"n": 0}])
        result = eng.score(_candidate("Some short text here."))
        self.assertEqual(set(result.keys()), {"candidate", "score", "max_score", "checks", "buildable"})

    def test_score_max_score_is_six(self):
        eng = _engine(rows=[{"n": 5}])
        result = eng.score(_candidate("meaningful content with enough words to score"))
        self.assertEqual(result["max_score"], 6)

    def test_score_checks_has_six_keys(self):
        eng = _engine(rows=[{"n": 0}])
        result = eng.score(_candidate("test"))
        self.assertEqual(len(result["checks"]), 6)
        self.assertIn("r1_wires_to_existing", result["checks"])
        self.assertIn("r6_graceful_degradation", result["checks"])

    def test_score_buildable_true_when_score_gte_3(self):
        reader = MagicMock()
        reader.read.side_effect = [
            [{"n": 5}],  # r1: count >= 5
            [{"n": 3}],  # r2: count >= 3
        ]
        eng = RefinementEngine(reader)
        result = eng.score(_candidate("explore consciousness drives memory learning"))
        self.assertTrue(result["buildable"])
        self.assertGreaterEqual(result["score"], 3)

    def test_score_buildable_false_when_score_lt_3(self):
        reader = MagicMock()
        reader.read.side_effect = [
            [{"n": 0}],  # r1 fails
            [{"n": 0}],  # r2 fails
        ]
        eng = RefinementEngine(reader)
        # r3 fails (risky), r6 fails (blocking) → score = r4+r5 = 2 at most
        result = eng.score(_candidate("delete all memory must succeed now"))
        self.assertFalse(result["buildable"])
        self.assertLess(result["score"], 3)


class TestR1(unittest.TestCase):

    def test_r1_passes_when_count_gte_5(self):
        eng = _engine(rows=[{"n": 5}])
        self.assertTrue(eng._r1("explore consciousness drives learning memory"))

    def test_r1_fails_when_count_lt_5(self):
        eng = _engine(rows=[{"n": 4}])
        self.assertFalse(eng._r1("explore consciousness drives learning memory"))

    def test_r1_fails_on_empty_content(self):
        eng = _engine(rows=[{"n": 5}])
        self.assertFalse(eng._r1(""))

    def test_r1_returns_false_on_db_error(self):
        eng = _engine(raise_exc=Exception("db locked"))
        self.assertFalse(eng._r1("explore consciousness drives learning memory"))


class TestR2(unittest.TestCase):

    def test_r2_passes_when_count_gte_3(self):
        eng = _engine(rows=[{"n": 3}])
        self.assertTrue(eng._r2("explore consciousness drives learning memory"))

    def test_r2_fails_when_count_lt_3(self):
        eng = _engine(rows=[{"n": 2}])
        self.assertFalse(eng._r2("explore consciousness drives learning memory"))

    def test_r2_default_pass_on_db_error(self):
        eng = _engine(raise_exc=Exception("timeout"))
        self.assertTrue(eng._r2("explore consciousness drives learning memory"))

    def test_r2_fails_on_empty_keywords(self):
        eng = _engine(rows=[{"n": 0}])
        self.assertFalse(eng._r2(""))


class TestVestigialChecks(unittest.TestCase):

    def test_r3_passes_clean_content(self):
        eng = _engine()
        self.assertTrue(eng._r3("consciousness drives learning"))

    def test_r3_fails_risky_pattern(self):
        eng = _engine()
        self.assertFalse(eng._r3("delete all old beliefs from memory"))

    def test_r4_passes_clean_content(self):
        eng = _engine()
        self.assertTrue(eng._r4("explore belief synthesis patterns"))

    def test_r4_fails_schema_pattern(self):
        eng = _engine()
        self.assertFalse(eng._r4("drop table beliefs cascade"))

    def test_r6_passes_clean_content(self):
        eng = _engine()
        self.assertTrue(eng._r6("learning may sometimes fail gracefully"))

    def test_r6_fails_blocking_pattern(self):
        eng = _engine()
        self.assertFalse(eng._r6("this must succeed or the system breaks"))


class TestR5(unittest.TestCase):

    def test_r5_passes_short_content(self):
        eng = _engine()
        self.assertTrue(eng._r5("Short content with one signal and also something extra."))

    def test_r5_passes_long_content_with_one_signal(self):
        eng = _engine()
        long_one = ("word " * 85) + " and also "
        self.assertTrue(eng._r5(long_one))

    def test_r5_fails_long_content_with_two_signals(self):
        eng = _engine()
        long_two = ("word " * 85) + " and also something plus another thing"
        self.assertFalse(eng._r5(long_two))


class TestRun(unittest.TestCase):

    def test_run_empty_returns_empty(self):
        eng = _engine()
        self.assertEqual(eng.run([]), [])

    def test_run_sorts_by_score_desc(self):
        reader = MagicMock()
        # Two score() calls; each call consumes two reads (r1+r2)
        reader.read.side_effect = [
            [{"n": 0}], [{"n": 0}],   # candidate 1: r1=F (n<5), r2=F (n<3)
            [{"n": 5}], [{"n": 3}],   # candidate 2: r1=T (n>=5), r2=T (n>=3)
        ]
        eng = RefinementEngine(reader)
        candidates = [
            _candidate("delete all must succeed"),
            _candidate("explore consciousness drives learn"),
        ]
        results = eng.run(candidates)
        self.assertGreaterEqual(results[0]["score"], results[1]["score"])

    def test_run_returns_all_candidates_regardless_of_buildable(self):
        reader = MagicMock()
        reader.read.side_effect = [
            [{"n": 0}], [{"n": 0}],
            [{"n": 0}], [{"n": 0}],
        ]
        eng = RefinementEngine(reader)
        candidates = [
            _candidate("delete all must succeed"),
            _candidate("drop table beliefs cascade"),
        ]
        results = eng.run(candidates)
        self.assertEqual(len(results), 2)


if __name__ == "__main__":
    unittest.main()
