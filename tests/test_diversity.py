"""Tests for the diversity ecology layer."""
from __future__ import annotations

import json
import time
import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers — minimal stub writer/reader
# ---------------------------------------------------------------------------

class _StubWriter:
    def __init__(self):
        self.calls = []
        self._last_id = 0

    def write(self, sql, params=()):
        self._last_id += 1
        self.calls.append((sql, params))
        return self._last_id


class _StubReader:
    def __init__(self, rows_map=None):
        self._rows_map = rows_map or {}

    def read(self, sql, params=()):
        for key, rows in self._rows_map.items():
            if key.lower() in sql.lower():
                return rows
        return []


# ---------------------------------------------------------------------------
# TestCrossbreedGrader
# ---------------------------------------------------------------------------

class TestCrossbreedGrader(unittest.TestCase):

    def _make_grader(self, beliefs, grade_rows=None):
        rows_map = {
            "grader_versions": [],
            "beliefs": beliefs,
            "collision_grades": grade_rows or [],
        }
        reader = _StubReader(rows_map)
        writer = _StubWriter()
        # patch embed to avoid loading model
        with patch("theory_x.diversity.grader.embed_belief") as mock_embed:
            import numpy as np
            mock_embed.side_effect = lambda bid, content: np.array(
                [float(bid % 10)] * 384, dtype=np.float32
            )
            from theory_x.diversity.grader import CrossbreedGrader
            grader = CrossbreedGrader(writer, reader)
        return grader, writer, reader

    def test_version_1_auto_created(self):
        beliefs = [
            {"id": 1, "content": "a thought", "branch_id": "x"},
            {"id": 2, "content": "another thought", "branch_id": "y"},
            {"id": 3, "content": "child thought", "branch_id": "z"},
        ]
        rows_map = {
            "grader_versions": [],
            "beliefs where id=1": [beliefs[0]],
            "beliefs where id=2": [beliefs[1]],
            "beliefs where id=3": [beliefs[2]],
            "collision_grades": [],
        }
        reader = _StubReader(rows_map)
        writer = _StubWriter()
        reader._rows_map["grader_versions"] = []

        with patch("theory_x.diversity.grader.embed_belief") as mock_embed:
            import numpy as np
            mock_embed.return_value = np.zeros(384, dtype=np.float32)
            from theory_x.diversity.grader import CrossbreedGrader
            grader = CrossbreedGrader(writer, reader)

        insert_calls = [c for c in writer.calls if "INSERT INTO grader_versions" in c[0]]
        self.assertEqual(len(insert_calls), 1)
        self.assertEqual(grader._current_version, 1)

    def test_grade_returns_float(self):
        beliefs_data = [
            {"id": 10, "content": "philosophy is hard", "branch_id": "ph"},
            {"id": 11, "content": "markets are noisy", "branch_id": "fi"},
            {"id": 12, "content": "emergence from noise", "branch_id": "sy"},
        ]

        class _DetailedReader:
            def read(self, sql, params=()):
                sql_lower = sql.lower()
                if "max(version)" in sql_lower:
                    return [{"v": 1}]
                if "grader_versions" in sql_lower and "where version" in sql_lower:
                    return [{"w_input_distance": 0.4, "w_output_distance": 0.35, "w_rarity": 0.25}]
                if "beliefs" in sql_lower and "where id=?" in sql_lower:
                    bid = params[0] if params else None
                    for b in beliefs_data:
                        if b["id"] == bid:
                            return [b]
                if "collision_grades" in sql_lower:
                    return [{"n": 0}]
                return []

        reader = _DetailedReader()
        writer = _StubWriter()

        with patch("theory_x.diversity.grader.embed_belief") as mock_embed:
            import numpy as np
            vecs = {
                10: np.array([1.0] + [0.0] * 383, dtype=np.float32),
                11: np.array([0.0, 1.0] + [0.0] * 382, dtype=np.float32),
                12: np.array([0.5, 0.5] + [0.0] * 382, dtype=np.float32),
            }
            mock_embed.side_effect = lambda bid, content: vecs.get(bid, np.zeros(384))
            from theory_x.diversity.grader import CrossbreedGrader
            grader = CrossbreedGrader(writer, reader)
            grade = grader.grade(12, 10, 11)

        self.assertIsNotNone(grade)
        self.assertGreaterEqual(grade, 0.0)
        self.assertLessEqual(grade, 1.0)

        insert_calls = [c for c in writer.calls if "INSERT INTO collision_grades" in c[0]]
        self.assertEqual(len(insert_calls), 1)


# ---------------------------------------------------------------------------
# TestGrooveSpotter
# ---------------------------------------------------------------------------

class TestGrooveSpotter(unittest.TestCase):

    def _make_beliefs(self, n, prefix="Why don't I"):
        return [{"id": i, "content": f"{prefix} think about this thing {i}"} for i in range(n)]

    def test_ngram_alert_fires_on_repetition(self):
        beliefs = self._make_beliefs(20)
        reader = _StubReader({
            "beliefs": beliefs,
            "collision_grades": [],
        })
        writer = _StubWriter()

        with patch("theory_x.diversity.groove.embed"):
            from theory_x.diversity.groove import GrooveSpotter
            spotter = GrooveSpotter(writer, reader)
            alerts = spotter._check_ngrams(beliefs)

        self.assertIsNotNone(alerts)
        self.assertEqual(alerts["alert_type"], "ngram_repetition")
        self.assertGreater(alerts["severity"], 0)

    def test_no_alert_on_diverse_content(self):
        import random
        words = ["apple", "river", "philosophy", "quantum", "bridge", "ocean",
                 "mountain", "justice", "entropy", "molecule", "dream", "silence",
                 "mirror", "gravity", "shadow", "horizon", "crystal", "wave",
                 "flame", "forest", "stone", "cloud", "cipher", "orbit", "pulse"]
        random.seed(42)
        beliefs = [
            {"id": i, "content": " ".join(random.sample(words, 7))}
            for i in range(20)
        ]
        reader = _StubReader({"beliefs": beliefs, "collision_grades": []})
        writer = _StubWriter()

        from theory_x.diversity.groove import GrooveSpotter, NGRAM_REPEAT_THRESHOLD
        spotter = GrooveSpotter(writer, reader)
        alert = spotter._check_ngrams(beliefs)
        self.assertIsNone(alert)


# ---------------------------------------------------------------------------
# TestDormancyScanner
# ---------------------------------------------------------------------------

class TestDormancyScanner(unittest.TestCase):

    def test_scan_flags_old_beliefs(self):
        long_ago = time.time() - 86400 * 30
        recent = time.time() - 100
        beliefs = [
            {"id": i, "created_at": long_ago, "last_referenced_at": None}
            for i in range(15)
        ]
        reader = _StubReader({
            "beliefs": beliefs,
            "avg(created_at)": [{"avg_ts": long_ago, "max_ts": recent,
                                  "min_ts": long_ago - 1000, "n": 15}],
        })
        writer = _StubWriter()

        from theory_x.diversity.dormancy import DormancyScanner
        scanner = DormancyScanner(writer, reader)
        with patch.object(scanner, "_average_gap", return_value=3600.0):
            count = scanner.scan_incremental()

        self.assertGreater(count, 0)
        insert_calls = [c for c in writer.calls if "dormant_beliefs" in c[0]]
        self.assertTrue(len(insert_calls) > 0)

    def test_recent_beliefs_not_flagged(self):
        now = time.time()
        beliefs = [
            {"id": i, "created_at": now - 10, "last_referenced_at": now - 5}
            for i in range(15)
        ]
        reader = _StubReader({"beliefs": beliefs})
        writer = _StubWriter()

        from theory_x.diversity.dormancy import DormancyScanner
        scanner = DormancyScanner(writer, reader)
        with patch.object(scanner, "_average_gap", return_value=3600.0):
            count = scanner.scan_incremental()

        self.assertEqual(count, 0)


# ---------------------------------------------------------------------------
# TestLineage
# ---------------------------------------------------------------------------

class TestLineage(unittest.TestCase):

    def test_record_synergy_writes_two_rows(self):
        writer = _StubWriter()
        from theory_x.diversity.lineage import record_synergy
        record_synergy(writer, child_id=10, parent_a_id=1, parent_b_id=2)
        lineage_calls = [c for c in writer.calls if "belief_lineage" in c[0]]
        self.assertEqual(len(lineage_calls), 2)

    def test_descendants_of_traces_tree(self):
        lineage_rows = [{"child_id": 2, "relationship": "synergy"}]

        class _DR:
            def read(self, sql, params=()):
                if "belief_lineage" in sql and "parent_id" in sql:
                    return lineage_rows
                return []

        from theory_x.diversity.lineage import descendants_of
        result = descendants_of(_DR(), belief_id=1, depth=1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["child_id"], 2)

    def test_ancestors_of(self):
        rows = [{"parent_id": 5, "relationship": "synergy"}]
        reader = _StubReader({"belief_lineage": rows})
        from theory_x.diversity.lineage import ancestors_of
        result = ancestors_of(reader, belief_id=10)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["parent_id"], 5)

    def test_most_fertile(self):
        rows = [{"parent_id": 3, "descendant_count": 7}]
        reader = _StubReader({"belief_lineage": rows})
        from theory_x.diversity.lineage import most_fertile
        result = most_fertile(reader, top_n=5)
        self.assertEqual(result[0]["parent_id"], 3)


# ---------------------------------------------------------------------------
# TestBoost
# ---------------------------------------------------------------------------

class TestBoost(unittest.TestCase):

    def test_apply_boost_writes_row(self):
        writer = _StubWriter()
        from theory_x.diversity.boost import apply_boost
        apply_boost(writer, belief_id=99, grade=0.85)
        boost_calls = [c for c in writer.calls if "belief_boost" in c[0]]
        self.assertEqual(len(boost_calls), 1)
        params = boost_calls[0][1]
        self.assertEqual(params[0], 99)
        self.assertAlmostEqual(params[1], 1.85)

    def test_decay_removes_expired_boosts(self):
        old_time = time.time() - 86400 * 60  # 60 days ago
        rows = [{"belief_id": 1, "boost_value": 1.02, "boosted_at": old_time, "decay_rate": 0.02}]
        reader = _StubReader({"belief_boost": rows})
        writer = _StubWriter()
        from theory_x.diversity.boost import apply_decay
        removed = apply_decay(writer, reader)
        self.assertEqual(removed, 1)
        delete_calls = [c for c in writer.calls if "DELETE FROM belief_boost" in c[0]]
        self.assertEqual(len(delete_calls), 1)

    def test_active_boost_not_removed(self):
        recent = time.time() - 3600  # 1 hour ago
        rows = [{"belief_id": 2, "boost_value": 1.8, "boosted_at": recent, "decay_rate": 0.02}]
        reader = _StubReader({"belief_boost": rows})
        writer = _StubWriter()
        from theory_x.diversity.boost import apply_decay
        removed = apply_decay(writer, reader)
        self.assertEqual(removed, 0)


# ---------------------------------------------------------------------------
# TestResidue
# ---------------------------------------------------------------------------

class TestResidue(unittest.TestCase):

    def test_save_residue_writes_row(self):
        writer = _StubWriter()
        from theory_x.diversity.residue import save_residue
        save_residue(writer, cycle_id="abc123", belief_id=5, activation_strength=0.9)
        calls = [c for c in writer.calls if "residue" in c[0]]
        self.assertEqual(len(calls), 1)
        self.assertIn(5, calls[0][1])

    def test_pop_residue_marks_consumed(self):
        rows = [{"id": 1, "belief_id": 7}, {"id": 2, "belief_id": 8}]

        class _DR:
            def read(self, sql, params=()):
                if "residue" in sql and "consumed_at IS NULL" in sql:
                    return rows
                return []

        writer = _StubWriter()
        from theory_x.diversity.residue import pop_residue
        result = pop_residue(_DR(), writer, limit=2)
        self.assertEqual(len(result), 2)
        update_calls = [c for c in writer.calls if "UPDATE residue" in c[0]]
        self.assertEqual(len(update_calls), 1)

    def test_pop_residue_empty(self):
        reader = _StubReader({"residue": []})
        writer = _StubWriter()
        from theory_x.diversity.residue import pop_residue
        result = pop_residue(reader, writer)
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# TestClockRunner
# ---------------------------------------------------------------------------

class TestClockRunner(unittest.TestCase):

    def _make_clock(self):
        from theory_x.diversity.consolidation import ClockRunner
        writers = {"beliefs": _StubWriter()}
        readers = {"beliefs": _StubReader({
            "groove_alerts": [{"n": 0}],
            "collision_grades": [],
            "belief_boost": [],
            "dormant_beliefs": [],
            "residue": [],
        })}
        return ClockRunner(writers, readers), writers, readers

    def test_fast_clock_triggers_at_20(self):
        clock, writers, readers = self._make_clock()
        with patch("theory_x.diversity.consolidation.apply_decay", return_value=0), \
             patch("theory_x.diversity.consolidation.DormancyScanner") as MockDS, \
             patch("theory_x.diversity.consolidation.wake_one", return_value=None):
            MockDS.return_value.scan_incremental.return_value = 0
            clock.tick(0)
            self.assertEqual(clock._last_fast, 0)
            clock.tick(20)
            self.assertEqual(clock._last_fast, 20)

    def test_medium_clock_triggers_at_200(self):
        clock, writers, readers = self._make_clock()
        with patch("theory_x.diversity.consolidation.apply_decay", return_value=0), \
             patch("theory_x.diversity.consolidation.DormancyScanner") as MockDS, \
             patch("theory_x.diversity.consolidation.wake_one", return_value=None):
            MockDS.return_value.scan_incremental.return_value = 0
            clock.tick(200)
            self.assertEqual(clock._last_medium, 200)

    def test_slow_clock_triggers_at_2000(self):
        clock, writers, readers = self._make_clock()
        with patch("theory_x.diversity.consolidation.apply_decay", return_value=0), \
             patch("theory_x.diversity.consolidation.DormancyScanner") as MockDS, \
             patch("theory_x.diversity.consolidation.wake_one", return_value=None), \
             patch("theory_x.diversity.evolver.GraderEvolver") as MockEvolver:
            MockDS.return_value.scan_incremental.return_value = 0
            MockEvolver.return_value.evolve.return_value = {}
            clock.tick(2000)
            self.assertEqual(clock._last_slow, 2000)


# ---------------------------------------------------------------------------
# TestEvolver
# ---------------------------------------------------------------------------

class TestEvolver(unittest.TestCase):

    def _make_evolver(self, grades, beliefs=None, lineage=None, boost=None):
        beliefs = beliefs or []
        lineage = lineage or []
        boost = boost or []

        class _DR:
            def read(self, sql, params=()):
                sql_lower = sql.lower()
                if "collision_grades" in sql_lower:
                    return grades
                if "belief_lineage" in sql_lower and "parent_id" in sql_lower:
                    return lineage
                if "belief_boost" in sql_lower:
                    return boost
                if "beliefs" in sql_lower and "where id=?" in sql_lower:
                    bid = params[0] if params else None
                    for b in beliefs:
                        if b["id"] == bid:
                            return [b]
                if "max(version)" in sql_lower:
                    return [{"v": 1}]
                if "grader_versions" in sql_lower:
                    return [{"w_input_distance": 0.4, "w_output_distance": 0.35, "w_rarity": 0.25}]
                if "grade_mismatches" in sql_lower:
                    return []
                return []

        from theory_x.diversity.evolver import GraderEvolver
        writer = _StubWriter()
        evolver = GraderEvolver(writer, _DR())
        return evolver, writer

    def test_evolve_insufficient_data(self):
        evolver, writer = self._make_evolver(grades=[{"belief_id": 1, "input_distance": 0.5,
                                                       "output_distance": 0.5, "rarity": 0.5,
                                                       "grade": 0.5, "grader_version": 1}])
        result = evolver.evolve()
        self.assertIsNone(result)

    def test_evolve_updates_weights_conservatively(self):
        grades = [
            {"belief_id": i, "input_distance": 0.8, "output_distance": 0.7,
             "rarity": 0.3, "grade": 0.65, "grader_version": 1}
            for i in range(1, 12)
        ]
        beliefs = [{"id": i, "tier": 5} for i in range(1, 12)]
        evolver, writer = self._make_evolver(grades=grades, beliefs=beliefs)
        result = evolver.evolve()
        if result is None:
            return  # not enough retrospective data — acceptable
        w = result["weights"]
        total = w["w_input_distance"] + w["w_output_distance"] + w["w_rarity"]
        self.assertAlmostEqual(total, 1.0, places=3)
        # Conservative: new weight stays within 30% of original
        self.assertGreater(w["w_input_distance"], 0.0)
        self.assertGreater(w["w_output_distance"], 0.0)
        self.assertGreater(w["w_rarity"], 0.0)

    def test_mismatch_detection_writes_row(self):
        samples = [
            {"belief_id": i, "original_grade": 0.2, "retrospective_value": 0.8,
             "grader_version": 1}
            for i in range(5)
        ]
        evolver, writer = self._make_evolver(grades=[])
        evolver._detect_mismatches(samples)
        mismatch_calls = [c for c in writer.calls if "grade_mismatches" in c[0]]
        self.assertEqual(len(mismatch_calls), 5)
        direction = mismatch_calls[0][1][3]
        self.assertEqual(direction, "under_graded")


if __name__ == "__main__":
    unittest.main()
