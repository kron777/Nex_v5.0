"""Tests for the signal detection layer."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
import unittest
from unittest.mock import MagicMock


def _make_readers_writers():
    """Create real in-process DBs for a single test run."""
    tmp = tempfile.mkdtemp()
    os.environ["NEX5_DATA_DIR"] = tmp
    from substrate.init_db import init_all
    from substrate import Reader, Writer, db_paths
    init_all()
    paths = db_paths()
    writers = {n: Writer(p, name=n) for n, p in paths.items()}
    readers = {n: Reader(p) for n, p in paths.items()}
    return tmp, writers, readers


def _teardown(tmp, writers, readers):
    for w in writers.values():
        try:
            w.close()
        except Exception:
            pass
    shutil.rmtree(tmp, ignore_errors=True)
    os.environ.pop("NEX5_DATA_DIR", None)


# ---------------------------------------------------------------------------
# CoOccurrenceDetector
# ---------------------------------------------------------------------------

class TestCoOccurrenceDetector(unittest.TestCase):

    def setUp(self):
        self.tmp, self.writers, self.readers = _make_readers_writers()

    def tearDown(self):
        _teardown(self.tmp, self.writers, self.readers)

    def _insert_belief(self, content, branch, offset_sec=60):
        self.writers["beliefs"].write(
            "INSERT INTO beliefs (content, tier, confidence, created_at, "
            "source, branch_id) VALUES (?, 1, 0.5, ?, 'test', ?)",
            (content, time.time() - offset_sec, branch),
        )

    def test_detects_entity_in_two_branches(self):
        from theory_x.signals.detectors import CoOccurrenceDetector
        self._insert_belief("OpenAI released something interesting", "ai_research")
        self._insert_belief("OpenAI mentioned in HN today", "emerging_tech")

        det = CoOccurrenceDetector(self.readers["beliefs"], min_branches=2)
        signals = det.detect()

        entities = [s.entities[0] for s in signals]
        self.assertIn("OpenAI", entities)

    def test_single_branch_no_signal(self):
        from theory_x.signals.detectors import CoOccurrenceDetector
        self._insert_belief("Anthropic update released", "ai_research")

        det = CoOccurrenceDetector(self.readers["beliefs"], min_branches=2)
        signals = det.detect()
        entities = [s.entities[0] for s in signals if "Anthropic" in s.entities]
        self.assertEqual(len(entities), 0)

    def test_confidence_scales_with_branch_count(self):
        from theory_x.signals.detectors import CoOccurrenceDetector
        for branch in ["ai_research", "crypto", "emerging_tech"]:
            self._insert_belief(f"Bitcoin movement today", branch)

        det = CoOccurrenceDetector(self.readers["beliefs"], min_branches=2)
        signals = det.detect()
        btc_sigs = [s for s in signals if "Bitcoin" in s.entities]
        self.assertTrue(len(btc_sigs) > 0)
        # 3 branches → confidence = min(0.3 + 0.2*3, 0.95) = 0.9
        self.assertAlmostEqual(btc_sigs[0].confidence, 0.9, places=5)

    def test_seed_sources_excluded(self):
        from theory_x.signals.detectors import CoOccurrenceDetector
        # Koan beliefs should not contribute to entity extraction
        self.writers["beliefs"].write(
            "INSERT INTO beliefs (content, tier, confidence, created_at, "
            "source, branch_id) VALUES (?, 1, 1.0, ?, 'koan', 'systems')",
            ("Bitcoin appears in ancient wisdom", time.time() - 60),
        )
        self._insert_belief("Bitcoin rising now", "crypto")
        det = CoOccurrenceDetector(self.readers["beliefs"], min_branches=2)
        signals = det.detect()
        # Only one non-seed branch → no co-occurrence
        btc = [s for s in signals if "Bitcoin" in s.entities]
        self.assertEqual(len(btc), 0)

    def test_outside_window_not_counted(self):
        from theory_x.signals.detectors import CoOccurrenceDetector
        # belief 2 hours old, window=1800s → excluded
        self._insert_belief("Tesla announcement made", "auto", offset_sec=7300)
        self._insert_belief("Tesla news today", "emerging_tech", offset_sec=60)
        det = CoOccurrenceDetector(self.readers["beliefs"], window_seconds=1800, min_branches=2)
        signals = det.detect()
        tesla = [s for s in signals if "Tesla" in s.entities]
        self.assertEqual(len(tesla), 0)


# ---------------------------------------------------------------------------
# BurstDetector
# ---------------------------------------------------------------------------

class TestBurstDetector(unittest.TestCase):

    def setUp(self):
        self.tmp, self.writers, self.readers = _make_readers_writers()

    def tearDown(self):
        _teardown(self.tmp, self.writers, self.readers)

    def _insert_t6_belief(self, branch="systems", offset_sec=60):
        self.writers["beliefs"].write(
            "INSERT INTO beliefs (content, tier, confidence, created_at, "
            "source, branch_id) VALUES (?, 6, 0.7, ?, 'fountain_insight', ?)",
            ("A tier 6 belief", time.time() - offset_sec, branch),
        )

    def test_burst_detected_above_threshold(self):
        from theory_x.signals.detectors import BurstDetector
        for _ in range(4):
            self._insert_t6_belief()
        det = BurstDetector(self.readers["beliefs"], burst_threshold=3)
        signals = det.detect()
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].signal_type, "t6_promotion_burst")
        self.assertEqual(signals[0].payload["promotions"], 4)

    def test_no_burst_below_threshold(self):
        from theory_x.signals.detectors import BurstDetector
        for _ in range(2):
            self._insert_t6_belief()
        det = BurstDetector(self.readers["beliefs"], burst_threshold=3)
        signals = det.detect()
        self.assertEqual(len(signals), 0)

    def test_burst_outside_window_ignored(self):
        from theory_x.signals.detectors import BurstDetector
        # All beliefs older than window
        for _ in range(5):
            self._insert_t6_belief(offset_sec=1800)
        det = BurstDetector(self.readers["beliefs"], window_seconds=900, burst_threshold=3)
        signals = det.detect()
        self.assertEqual(len(signals), 0)


# ---------------------------------------------------------------------------
# SilenceDetector
# ---------------------------------------------------------------------------

class TestSilenceDetector(unittest.TestCase):

    def test_silence_detected(self):
        from theory_x.signals.detectors import SilenceDetector
        now = time.time()
        # Stream with 6 events every 60s, then 400s of silence
        events = [{"stream": "web.hn", "timestamp": now - 400 - (5 - i) * 60}
                  for i in range(6)]
        sense_reader = MagicMock()
        sense_reader.read.return_value = events
        det = SilenceDetector(sense_reader, silence_multiplier=3.0, min_history_events=5)
        signals = det.detect()
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].signal_type, "branch_silence_anomaly")
        self.assertEqual(signals[0].branches, ["web.hn"])

    def test_no_silence_when_recent(self):
        from theory_x.signals.detectors import SilenceDetector
        now = time.time()
        # Most recent event just 10s ago, avg gap 60s → no silence
        events = [{"stream": "web.hn", "timestamp": now - 10 - (5 - i) * 60}
                  for i in range(6)]
        sense_reader = MagicMock()
        sense_reader.read.return_value = events
        det = SilenceDetector(sense_reader, silence_multiplier=3.0, min_history_events=5)
        signals = det.detect()
        self.assertEqual(len(signals), 0)

    def test_stream_with_too_few_events_skipped(self):
        from theory_x.signals.detectors import SilenceDetector
        now = time.time()
        events = [{"stream": "rare.stream", "timestamp": now - 200 - i * 60}
                  for i in range(3)]  # only 3, min_history=5
        sense_reader = MagicMock()
        sense_reader.read.return_value = events
        det = SilenceDetector(sense_reader, silence_multiplier=3.0, min_history_events=5)
        signals = det.detect()
        self.assertEqual(len(signals), 0)


# ---------------------------------------------------------------------------
# PatternTemplateLibrary
# ---------------------------------------------------------------------------

class TestPatternTemplateLibrary(unittest.TestCase):

    def _co_signal(self, entity="OpenAI", branches=None):
        return {
            "id": 1,
            "detector_name": "co_occurrence",
            "payload": json.dumps({
                "entity": entity,
                "branches": branches or ["ai_research", "emerging_tech"],
                "window_seconds": 1800,
            }),
        }

    def _burst_signal(self):
        return {
            "id": 2,
            "detector_name": "burst",
            "payload": json.dumps({
                "promotions": 5,
                "window_seconds": 900,
                "branches": ["ai_research", "crypto"],
            }),
        }

    def _silence_signal(self):
        return {
            "id": 3,
            "detector_name": "silence",
            "payload": json.dumps({
                "stream": "web.hn",
                "avg_gap_seconds": 60,
                "current_silence_seconds": 400,
                "multiplier_breach": 6.7,
            }),
        }

    def test_triple_cooccurrence_matches(self):
        from theory_x.signals.templates import PatternTemplateLibrary
        lib = PatternTemplateLibrary()
        matches = lib.match([self._co_signal()])
        names = [m["template_name"] for m in matches]
        self.assertIn("triple_cooccurrence", names)

    def test_burst_matches(self):
        from theory_x.signals.templates import PatternTemplateLibrary
        lib = PatternTemplateLibrary()
        matches = lib.match([self._burst_signal()])
        names = [m["template_name"] for m in matches]
        self.assertIn("pattern_recognition_burst", names)

    def test_silence_matches(self):
        from theory_x.signals.templates import PatternTemplateLibrary
        lib = PatternTemplateLibrary()
        matches = lib.match([self._silence_signal()])
        names = [m["template_name"] for m in matches]
        self.assertIn("branch_silence_anomaly", names)

    def test_no_match_when_no_signals(self):
        from theory_x.signals.templates import PatternTemplateLibrary
        lib = PatternTemplateLibrary()
        matches = lib.match([])
        self.assertEqual(matches, [])

    def test_prediction_text_formatted(self):
        from theory_x.signals.templates import PatternTemplateLibrary
        lib = PatternTemplateLibrary()
        matches = lib.match([self._co_signal("Bitcoin", ["crypto", "finance", "news"])])
        co = next(m for m in matches if m["template_name"] == "triple_cooccurrence")
        self.assertIn("Bitcoin", co["prediction"])
        self.assertIn("3", co["prediction"])

    def test_multiple_templates_in_one_call(self):
        from theory_x.signals.templates import PatternTemplateLibrary
        lib = PatternTemplateLibrary()
        matches = lib.match([self._co_signal(), self._burst_signal(), self._silence_signal()])
        names = {m["template_name"] for m in matches}
        self.assertEqual(names, {"triple_cooccurrence", "pattern_recognition_burst",
                                  "branch_silence_anomaly"})

    def test_prediction_window_set(self):
        from theory_x.signals.templates import PatternTemplateLibrary
        lib = PatternTemplateLibrary()
        matches = lib.match([self._co_signal()])
        co = next(m for m in matches if m["template_name"] == "triple_cooccurrence")
        self.assertEqual(co["predicted_window_seconds"], 86400)


# ---------------------------------------------------------------------------
# SignalLoop integration (light)
# ---------------------------------------------------------------------------

class TestSignalLoop(unittest.TestCase):

    def setUp(self):
        self.tmp, self.writers, self.readers = _make_readers_writers()

    def tearDown(self):
        _teardown(self.tmp, self.writers, self.readers)

    def test_loop_starts_and_status(self):
        from theory_x.signals.loop import SignalLoop
        loop = SignalLoop(
            beliefs_writer=self.writers["beliefs"],
            beliefs_reader=self.readers["beliefs"],
            sense_reader=self.readers["sense"],
            interval_seconds=3600,  # won't tick in test
        )
        loop.start()
        self.assertTrue(loop.status()["running"])
        loop.stop()

    def test_tick_writes_signals(self):
        from theory_x.signals.loop import SignalLoop
        # Seed two beliefs with same entity in different branches
        now = time.time()
        for branch in ["ai_research", "crypto"]:
            self.writers["beliefs"].write(
                "INSERT INTO beliefs (content, tier, confidence, created_at, "
                "source, branch_id) VALUES (?, 1, 0.5, ?, 'test', ?)",
                ("OpenAI moves into crypto market", now - 30, branch),
            )
        loop = SignalLoop(
            beliefs_writer=self.writers["beliefs"],
            beliefs_reader=self.readers["beliefs"],
            sense_reader=self.readers["sense"],
        )
        loop._tick()
        rows = self.readers["beliefs"].read(
            "SELECT COUNT(*) as n FROM signals WHERE detector_name='co_occurrence'"
        )
        self.assertGreater(rows[0]["n"], 0)

    def test_tick_matches_patterns(self):
        from theory_x.signals.loop import SignalLoop
        # Seed enough T6 beliefs for a burst
        now = time.time()
        for i in range(4):
            self.writers["beliefs"].write(
                "INSERT INTO beliefs (content, tier, confidence, created_at, "
                "source, branch_id) VALUES (?, 6, 0.7, ?, 'fountain_insight', 'systems')",
                (f"Belief number {i}", now - 30),
            )
        loop = SignalLoop(
            beliefs_writer=self.writers["beliefs"],
            beliefs_reader=self.readers["beliefs"],
            sense_reader=self.readers["sense"],
        )
        loop._tick()
        rows = self.readers["beliefs"].read(
            "SELECT COUNT(*) as n FROM patterns WHERE template_name='pattern_recognition_burst'"
        )
        self.assertGreater(rows[0]["n"], 0)


if __name__ == "__main__":
    unittest.main()
