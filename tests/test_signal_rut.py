"""Tests for the signal-layer rut fix.

Three tests:
1. Anti-repetition guard: crystallizer rejects content emitted in last 30 min
2. Exact-match detector: groove spotter fires at ≥3 identical strings
3. Cooldown enforcement: cooldown table entry blocks content in crystallizer
"""
from __future__ import annotations

import time
import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _StubWriter:
    def __init__(self):
        self.calls = []
        self._last_id = 0

    def write(self, sql, params=()):
        self._last_id += 1
        self.calls.append((sql, params))
        return self._last_id


class _RowLike(dict):
    """Dict that also supports item access like sqlite3.Row."""
    def __getitem__(self, key):
        return super().__getitem__(key)


class _StubReader:
    """Stub reader whose behaviour is controlled per-test via response_map.

    Keys are SQL substrings (lowercased); values are lists of _RowLike.
    First key whose substring appears in the SQL wins.
    """
    def __init__(self, response_map=None):
        self._map = response_map or {}

    def read(self, sql, params=()):
        for key, rows in self._map.items():
            if key.lower() in sql.lower():
                return rows
        return []


# ---------------------------------------------------------------------------
# Test 1: Anti-repetition guard skips recently-emitted content
# ---------------------------------------------------------------------------

class TestAntiRepetitionGuard(unittest.TestCase):
    """_was_recently_emitted returns True when DB contains same content within 30 min."""

    def _make_crystallizer(self, reader):
        from theory_x.stage6_fountain.crystallizer import FountainCrystallizer
        w = _StubWriter()
        c = FountainCrystallizer(beliefs_writer=w, beliefs_reader=reader)
        return c

    def test_was_recently_emitted_returns_true_when_duplicate_exists(self):
        content = "The clock ticks idly on the table by my side."
        reader = _StubReader({
            "signal_cooldown": [],
            "fountain_insight": [_RowLike({"1": 1})],  # row exists
        })
        # Patch read to return a hit for fountain_insight exact-match query
        reader._map = {
            "source='fountain_insight' and content=?": [_RowLike({"1": 1})],
            "signal_cooldown": [],
        }
        c = self._make_crystallizer(reader)
        self.assertTrue(c._was_recently_emitted(content))

    def test_was_recently_emitted_returns_false_when_no_duplicate(self):
        reader = _StubReader({})
        c = self._make_crystallizer(reader)
        self.assertFalse(c._was_recently_emitted("Some fresh unique thought here."))

    def test_quality_check_rejects_recent_repeat(self):
        content = "The clock ticks idly on the table by my side."
        # Reader returns a hit for recent-emission check
        reader = _StubReader({
            "source='fountain_insight' and content=?": [_RowLike({"1": 1})],
            "signal_cooldown": [],
            "belief_blacklist": [],
            "fountain_insight": [],
            "synergized": [],
            "fountain_events": [],
        })
        c = self._make_crystallizer(reader)
        ok, reason = c._quality_check(content)
        self.assertFalse(ok)
        self.assertEqual(reason, "recent_repeat")


# ---------------------------------------------------------------------------
# Test 2: Exact-match detector fires at ≥3 identical strings
# ---------------------------------------------------------------------------

class TestExactMatchDetector(unittest.TestCase):

    def _make_spotter(self, window):
        from theory_x.diversity.groove import GrooveSpotter
        w = _StubWriter()
        r = _StubReader({})
        spotter = GrooveSpotter(w, r)
        return spotter, w

    def test_exact_repetition_fires_at_three_copies(self):
        content = "The clock ticks idly on the table by my side."
        window = [{"id": i, "content": content} for i in range(3)] + [
            {"id": 10, "content": "Something completely different here now."},
            {"id": 11, "content": "Another unique thought for diversity test."},
        ]
        spotter, writer = self._make_spotter(window)
        alert = spotter._detect_exact_repetition(window)
        self.assertIsNotNone(alert)
        self.assertEqual(alert["alert_type"], "exact_repetition")
        self.assertGreaterEqual(alert["severity"], 0.5)
        self.assertEqual(alert["n"], 3)

    def test_exact_repetition_does_not_fire_at_one_copy(self):
        content = "The clock ticks idly on the table by my side."
        window = [
            {"id": 0, "content": content},
            {"id": 10, "content": "Something different here."},
        ]
        spotter, _ = self._make_spotter(window)
        alert = spotter._detect_exact_repetition(window)
        self.assertIsNone(alert)

    def test_exact_repetition_severity_scales_with_count(self):
        content = "The clock ticks idly on the table by my side."
        window = [{"id": i, "content": content} for i in range(5)]
        spotter, _ = self._make_spotter(window)
        alert = spotter._detect_exact_repetition(window)
        self.assertIsNotNone(alert)
        self.assertAlmostEqual(alert["severity"], 1.0)


# ---------------------------------------------------------------------------
# Test 3: Cooldown table blocks content in crystallizer
# ---------------------------------------------------------------------------

class TestCooldownEnforcement(unittest.TestCase):

    def _make_crystallizer(self, reader):
        from theory_x.stage6_fountain.crystallizer import FountainCrystallizer
        w = _StubWriter()
        c = FountainCrystallizer(beliefs_writer=w, beliefs_reader=reader)
        return c

    def test_is_on_cooldown_true_when_entry_exists(self):
        content = "The clock ticks idly on the table by my side."
        reader = _StubReader({
            "signal_cooldown": [_RowLike({"1": 1})],
        })
        c = self._make_crystallizer(reader)
        self.assertTrue(c._is_on_cooldown(content))

    def test_is_on_cooldown_false_when_no_entry(self):
        reader = _StubReader({})
        c = self._make_crystallizer(reader)
        self.assertFalse(c._is_on_cooldown("Some unique fresh thought."))

    def test_quality_check_rejects_cooled_down_content(self):
        content = "The clock ticks idly on the table by my side."
        reader = _StubReader({
            # No recent duplicate → passes recent_repeat check
            "source='fountain_insight' and content=?": [],
            # But cooldown table has an active entry
            "signal_cooldown": [_RowLike({"1": 1})],
            "belief_blacklist": [],
            "fountain_insight": [],
            "synergized": [],
            "fountain_events": [],
        })
        c = self._make_crystallizer(reader)
        ok, reason = c._quality_check(content)
        self.assertFalse(ok)
        self.assertEqual(reason, "cooldown")

    def test_groove_spotter_pushes_cooldown_on_exact_repetition(self):
        from theory_x.diversity.groove import GrooveSpotter
        content = "The clock ticks idly on the table by my side."
        window = [{"id": i, "content": content} for i in range(5)]

        writer = _StubWriter()
        reader = _StubReader({})
        spotter = GrooveSpotter(writer, reader)

        alert = spotter._detect_exact_repetition(window)
        self.assertIsNotNone(alert)

        spotter._push_cooldown(alert)
        # Writer should have received an INSERT into signal_cooldown
        cooldown_writes = [
            c for c in writer.calls if "signal_cooldown" in c[0].lower()
        ]
        self.assertGreater(len(cooldown_writes), 0)


# ---------------------------------------------------------------------------
# Test 4: Ngram severity reaches threshold at minimum matches
# ---------------------------------------------------------------------------

class TestNgramSeverityFormula(unittest.TestCase):

    def _make_spotter(self):
        from theory_x.diversity.groove import GrooveSpotter
        w = _StubWriter()
        r = _StubReader({})
        return GrooveSpotter(w, r), w

    def test_ngram_severity_hits_threshold_at_min_matches(self):
        """3 matching trigrams (min threshold) should produce severity >= 0.5."""
        phrase = "hum of the server"
        # Build a window where "hum of the" appears exactly NGRAM_REPEAT_THRESHOLD times
        from theory_x.diversity.groove import NGRAM_REPEAT_THRESHOLD
        window = [{"id": i, "content": phrase} for i in range(NGRAM_REPEAT_THRESHOLD)]
        window += [
            {"id": 100 + i, "content": f"Completely different thought number {i}."}
            for i in range(17)
        ]
        spotter, _ = self._make_spotter()
        alert = spotter._check_ngrams(window)
        self.assertIsNotNone(alert)
        self.assertGreaterEqual(alert["severity"], 0.5,
            f"Expected severity >= 0.5 at min matches, got {alert['severity']}")


# ---------------------------------------------------------------------------
# Test 5: Template repetition detected on shared bigrams
# ---------------------------------------------------------------------------

class TestTemplateRepetition(unittest.TestCase):

    def _make_spotter(self):
        from theory_x.diversity.groove import GrooveSpotter
        w = _StubWriter()
        r = _StubReader({})
        return GrooveSpotter(w, r), w

    def test_template_repetition_detected_on_shared_bigrams(self):
        """3+ fires sharing 3+ bigrams should fire template_repetition alert."""
        # These three variations share: "server hum", "cursor dance", "stirs fingers"
        window = [
            {"id": 1, "content": "The server hum fills the room as the cursor dance stirs fingers."},
            {"id": 2, "content": "Again the server hum and cursor dance stirs my fingers tonight."},
            {"id": 3, "content": "Still that server hum, still the cursor dance, still stirs fingers."},
            {"id": 4, "content": "An entirely unrelated thought about philosophy and mathematics."},
            {"id": 5, "content": "Another distinct idea about science and discovery."},
        ]
        spotter, writer = self._make_spotter()
        alert = spotter._detect_template_repetition(window)
        self.assertIsNotNone(alert, "Expected template_repetition alert on shared bigrams")
        self.assertEqual(alert["alert_type"], "template_repetition")
        self.assertGreaterEqual(alert["severity"], 0.5)

        # Cooldown should be written since severity >= 0.5
        spotter._push_cooldown(alert)
        cooldown_writes = [c for c in writer.calls if "signal_cooldown" in c[0].lower()]
        self.assertGreater(len(cooldown_writes), 0, "Expected cooldown to be written")


# ---------------------------------------------------------------------------
# Test 6: Exact repeat fires at 2 (lowered from 3)
# ---------------------------------------------------------------------------

class TestExactRepeatAtTwo(unittest.TestCase):

    def _make_spotter(self):
        from theory_x.diversity.groove import GrooveSpotter
        w = _StubWriter()
        r = _StubReader({})
        return GrooveSpotter(w, r), w

    def test_exact_repeat_fires_at_2(self):
        """2 identical strings should now trigger exact_repetition (EXACT_REPEAT_MIN=2)."""
        content = "The clock ticks idly on the table by my side."
        window = [
            {"id": 0, "content": content},
            {"id": 1, "content": content},
            {"id": 2, "content": "Something completely different here."},
        ]
        spotter, _ = self._make_spotter()
        alert = spotter._detect_exact_repetition(window)
        self.assertIsNotNone(alert)
        self.assertEqual(alert["alert_type"], "exact_repetition")
        self.assertGreaterEqual(alert["severity"], 0.5)


# ---------------------------------------------------------------------------
# Test 7: Semantic dedup rejects near-match in crystallizer
# ---------------------------------------------------------------------------

class TestSemanticDedup(unittest.TestCase):

    def _make_crystallizer(self, reader):
        from theory_x.stage6_fountain.crystallizer import FountainCrystallizer
        w = _StubWriter()
        c = FountainCrystallizer(beliefs_writer=w, beliefs_reader=reader)
        return c

    def test_semantic_dedup_rejects_near_match(self):
        """Crystallizer rejects content with cosine >= 0.85 to a recent emission."""
        import numpy as np
        from unittest.mock import patch

        prev = "The steady hum of the server keeps me company while fingers dance."
        new_thought = "That steady server hum is keeping my fingers dancing again."

        reader = _StubReader({
            # exact-match check → no hit
            "source='fountain_insight' and content=?": [],
            # semantic check: returns previous emission
            "source='fountain_insight' and created_at": [_RowLike({"content": prev})],
            # cooldown → no entry
            "signal_cooldown": [],
            "belief_blacklist": [],
            "fountain_insight": [],
            "synergized": [],
            "fountain_events": [],
        })
        c = self._make_crystallizer(reader)

        high_sim_vec = np.ones(384, dtype=np.float32) / np.sqrt(384)

        with patch("theory_x.diversity.embeddings.embed", return_value=high_sim_vec):
            ok, reason = c._quality_check(new_thought)

        self.assertFalse(ok)
        self.assertEqual(reason, "semantic_repeat")


if __name__ == "__main__":
    unittest.main()
