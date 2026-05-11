"""Throw-Net TriggerDetector tests — Phase 25a TN-1.

Covers:
- record_gate_reject logs row to throw_net_triggers
- record_gap_deflection logs row to throw_net_triggers
- consecutive reject counter resets on topic change (window isolation)
- gate_reject threshold returns True at 4 same-topic events in window
- gap_deflection threshold returns True at 3 same-topic events in window
- gap_deflection window ignores rows older than 30 min
- pending_triggers returns only unfired rows
- mark_fired updates fired=1 and session_id
- _extract_topic returns top content token
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_tn_")
    os.environ["NEX5_DATA_DIR"] = tmp
    os.environ["NEX5_ADMIN_HASH_FILE"] = str(Path(tmp) / "admin.argon2")
    from substrate.init_db import init_all
    init_all()
    from substrate import Reader, Writer, db_paths
    paths = db_paths()
    writers = {n: Writer(p, name=n) for n, p in paths.items()}
    readers = {n: Reader(p) for n, p in paths.items()}
    return writers, readers, tmp


def _cleanup(writers, tmp):
    for w in writers.values():
        try:
            w.close()
        except Exception:
            pass
    shutil.rmtree(tmp, ignore_errors=True)
    os.environ.pop("NEX5_DATA_DIR", None)
    os.environ.pop("NEX5_ADMIN_HASH_FILE", None)


def _make_detector(writers, readers):
    from theory_x.stage_throw_net.trigger_detector import TriggerDetector
    return TriggerDetector(writers["beliefs"], readers["beliefs"])


def _make_decision(reason="redundant:0.85"):
    d = MagicMock()
    d.reason = reason
    return d


def _make_packet(content, source="fountain"):
    from theory_x.stage_gate.coherence_gate import ThoughtPacket
    return ThoughtPacket(
        content=content,
        source_node=source,
        confidence=0.70,
    )


class TestRecordGateReject(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.detector = _make_detector(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_record_gate_reject_logs_row(self):
        """record_gate_reject writes one row to throw_net_triggers."""
        packet = _make_packet("Consciousness emerges from complexity of neural binding.")
        decision = _make_decision("redundant:0.80")
        self.detector.record_gate_reject(packet, decision)
        time.sleep(0.05)

        rows = self.readers["beliefs"].read(
            "SELECT trigger_type, topic FROM throw_net_triggers"
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["trigger_type"], "gate_reject")
        self.assertIsNotNone(rows[0]["topic"])

    def test_record_gap_deflection_logs_row(self):
        """record_gap_deflection writes one row to throw_net_triggers."""
        self.detector.record_gap_deflection(
            "What do you think about quantum consciousness?",
            "gap:belief_count_0",
        )
        time.sleep(0.05)

        rows = self.readers["beliefs"].read(
            "SELECT trigger_type, topic FROM throw_net_triggers"
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["trigger_type"], "gap_deflection")


class TestThresholds(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.detector = _make_detector(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_gate_reject_threshold_returns_true_at_4(self):
        """4th REJECT on same topic returns True; first 3 return False."""
        packet = _make_packet("Emergence arises when complexity reaches critical threshold.")
        decision = _make_decision("redundant:0.75")

        results = []
        for _ in range(4):
            result = self.detector.record_gate_reject(packet, decision)
            results.append(result)
            time.sleep(0.02)

        self.assertFalse(results[0])
        self.assertFalse(results[1])
        self.assertFalse(results[2])
        self.assertTrue(results[3])

    def test_gap_deflection_threshold_returns_true_at_3(self):
        """3rd gap deflection on same topic returns True; first 2 return False."""
        query = "Why does consciousness emerge from matter?"
        results = []
        for _ in range(3):
            result = self.detector.record_gap_deflection(query, "gap:belief_count_0")
            results.append(result)
            time.sleep(0.02)

        self.assertFalse(results[0])
        self.assertFalse(results[1])
        self.assertTrue(results[2])

    def test_different_topics_do_not_share_counts(self):
        """REJECTs on different topics do not accumulate against each other."""
        p1 = _make_packet("Consciousness emerges from neural complexity and binding.")
        p2 = _make_packet("Gravity bends spacetime according to general relativity.")
        decision = _make_decision("redundant:0.80")

        # 3 on consciousness
        for _ in range(3):
            self.detector.record_gate_reject(p1, decision)
            time.sleep(0.02)
        # 1 on gravity — should NOT trigger (only 1 in window)
        result = self.detector.record_gate_reject(p2, decision)
        self.assertFalse(result)

    def test_gap_deflection_window_ignores_old_rows(self):
        """gap deflections older than 30 min do not count toward threshold."""
        from theory_x.stage_throw_net import trigger_detector as _td_mod
        old_threshold = _td_mod._GAP_DEFLECTION_WINDOW
        _td_mod._GAP_DEFLECTION_WINDOW = 1  # 1 second window for test

        try:
            # Write 2 rows that will expire
            query = "Tell me about strange attractors in chaos theory."
            for _ in range(2):
                self.detector.record_gap_deflection(query, "gap:belief_count_0")
                time.sleep(0.01)

            # Wait for them to expire
            time.sleep(1.2)

            # Third call — count should be 1 (only this call), not 3
            result = self.detector.record_gap_deflection(query, "gap:belief_count_0")
            self.assertFalse(result)  # count=1, threshold=3
        finally:
            _td_mod._GAP_DEFLECTION_WINDOW = old_threshold


class TestPendingAndMarkFired(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.detector = _make_detector(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_pending_triggers_returns_only_unfired(self):
        """pending_triggers excludes rows where fired=1."""
        # Write 2 rows
        p = _make_packet("Emergence in complex adaptive systems is fascinating.")
        d = _make_decision("redundant:0.80")
        self.detector.record_gate_reject(p, d)
        self.detector.record_gate_reject(p, d)
        time.sleep(0.05)

        pending = self.detector.pending_triggers()
        self.assertEqual(len(pending), 2)

        # Fire one
        self.detector.mark_fired(pending[0]["id"], "session-abc")
        time.sleep(0.05)

        pending2 = self.detector.pending_triggers()
        self.assertEqual(len(pending2), 1)

    def test_mark_fired_updates_correctly(self):
        """mark_fired sets fired=1 and session_id on the correct row."""
        p = _make_packet("Fractal geometry reveals hidden self-similarity everywhere.")
        d = _make_decision("redundant:0.75")
        self.detector.record_gate_reject(p, d)
        time.sleep(0.05)

        rows = self.readers["beliefs"].read(
            "SELECT id FROM throw_net_triggers WHERE fired=0"
        )
        self.assertEqual(len(rows), 1)
        row_id = rows[0]["id"]

        self.detector.mark_fired(row_id, "session-xyz")
        time.sleep(0.05)

        updated = self.readers["beliefs"].read(
            "SELECT fired, session_id FROM throw_net_triggers WHERE id=?",
            (row_id,),
        )
        self.assertEqual(updated[0]["fired"], 1)
        self.assertEqual(updated[0]["session_id"], "session-xyz")


class TestExtractTopic(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.detector = _make_detector(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_extract_topic_returns_top_content_token(self):
        """_extract_topic returns the most frequent non-stopword token."""
        result = self.detector._extract_topic(
            "consciousness consciousness emerges from neural complexity"
        )
        self.assertEqual(result, "consciousness")

    def test_extract_topic_unknown_on_empty(self):
        """_extract_topic returns 'unknown' for empty string."""
        result = self.detector._extract_topic("")
        self.assertEqual(result, "unknown")

    def test_extract_topic_unknown_on_stopwords_only(self):
        """_extract_topic returns 'unknown' when all words are stopwords."""
        result = self.detector._extract_topic("the a is and or but")
        self.assertEqual(result, "unknown")

    def test_pending_triggers_batch_cap_is_500(self):
        """pending_triggers() returns at most 500 rows when 500+ exist."""
        p = _make_packet("Emergence in complex adaptive systems is fascinating.")
        d = _make_decision("redundant:0.80")
        # Seed 510 triggers
        for _ in range(510):
            self.detector.record_gate_reject(p, d)
        time.sleep(0.1)

        pending = self.detector.pending_triggers()
        self.assertLessEqual(len(pending), 500)
        self.assertEqual(len(pending), 500)

    def test_extract_topic_strips_bracketed_markers(self):
        """[RETIRED] markers are stripped before topic extraction."""
        result = self.detector._extract_topic(
            "[RETIRED] The weight of memory and time"
        )
        self.assertNotEqual(result, "[retired]")
        self.assertNotIn("retired", result.lower())

    def test_extract_topic_strips_multiple_bracketed_markers(self):
        """Multiple [MARKER] prefixes are all stripped."""
        result = self.detector._extract_topic(
            "[RETIRED] [RETIRED] [RETIRED] consciousness emerges here"
        )
        self.assertEqual(result, "consciousness")


if __name__ == "__main__":
    unittest.main()
