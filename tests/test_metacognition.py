"""Phase 16 smoke tests — Metacognition (Stage 9).

Covers:
- SentienceNode protocol conformance
- groove_alerts detection → meta_cognition_events written
- goal-drift detection → meta_cognition_event written
- Negative cases (no goals, aligned messages, no alerts)
- Decay: stale events auto-resolved; fresh preserved; cache invalidated
- format_for_prompt() content is non-empty when events exist
- Cross-module: meta_cognition_events persists across Metacognition instantiation
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_mcog_")
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


def _build_mc(writers, readers):
    from theory_x.stage9_metacognition.metacognition import Metacognition
    return Metacognition(
        writers["conversations"],
        readers["conversations"],
        readers["beliefs"],
    )


def _seed_groove_alert(writers, alert_type="ngram_repetition", severity=0.7, pattern="test pattern"):
    writers["beliefs"].write(
        "INSERT INTO groove_alerts "
        "(detected_at, alert_type, severity, pattern, window_size) "
        "VALUES (?, ?, ?, ?, ?)",
        (time.time() - 10, alert_type, severity, pattern, 5),
    )


def _seed_goal(writers, title="Test Goal", description="A goal to validate metacognition"):
    now = time.time()
    return writers["conversations"].write(
        "INSERT INTO goals "
        "(title, description, priority, state, source, created_at, last_touched_at) "
        "VALUES (?, ?, ?, 'open', 'user', ?, ?)",
        (title, description, 0.9, now, now),
    )


def _seed_nex_messages(writers, contents: list[str]):
    now = int(time.time())
    for i, content in enumerate(contents):
        writers["conversations"].write(
            "INSERT INTO messages (session_id, role, content, register, timestamp) "
            "VALUES (?, 'nex', ?, 'Conversational', ?)",
            ("test_session", content, now - i * 10),
        )


# ── SentienceNode protocol ────────────────────────────────────────────────────

class TestSentienceNodeProtocol(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.mc = _build_mc(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_implements_sentience_node_protocol(self):
        from theory_x import SentienceNode
        self.assertIsInstance(self.mc, SentienceNode)

    def test_has_name_attribute(self):
        from theory_x.stage9_metacognition.metacognition import Metacognition
        self.assertEqual(Metacognition.name, "metacognition")
        self.assertEqual(self.mc.name, "metacognition")

    def test_tick_returns_dict_with_name(self):
        result = self.mc.tick()
        self.assertIsInstance(result, dict)
        self.assertEqual(result["name"], "metacognition")

    def test_tick_accepts_context(self):
        result = self.mc.tick(context={"session_id": "test"})
        self.assertIsInstance(result, dict)
        self.assertIn("recent_count", result)

    def test_state_returns_expected_fields(self):
        s = self.mc.state()
        self.assertIn("name", s)
        self.assertIn("recent_count", s)
        self.assertIn("top_anomaly", s)
        self.assertIn("cache_age_s", s)

    def test_state_recent_count_zero_on_empty_db(self):
        s = self.mc.tick()
        self.assertEqual(s["recent_count"], 0)

    def test_decay_accepts_float(self):
        self.mc.decay(time.time())  # must not raise


# ── Groove detection ──────────────────────────────────────────────────────────

class TestGrooveDetection(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.mc = _build_mc(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_groove_alert_writes_meta_event(self):
        _seed_groove_alert(self.writers, alert_type="ngram_repetition")
        self.mc.tick()
        events = self.mc.get_recent(limit=10)
        self.assertGreater(len(events), 0)
        self.assertEqual(events[0]["event_type"], "groove")

    def test_groove_event_description_contains_alert_type(self):
        _seed_groove_alert(self.writers, alert_type="exact_repetition", pattern="I cannot know")
        self.mc.tick()
        events = self.mc.get_recent(limit=5)
        groove_events = [e for e in events if e["event_type"] == "groove"]
        self.assertGreater(len(groove_events), 0)
        self.assertIn("exact_repetition", groove_events[0]["description"])

    def test_format_for_prompt_non_empty_after_groove(self):
        _seed_groove_alert(self.writers)
        self.mc.tick()
        text = self.mc.format_for_prompt()
        self.assertNotEqual(text, "")
        self.assertIn("Self-observation", text)

    def test_acknowledged_groove_alert_ignored(self):
        now = time.time()
        self.writers["beliefs"].write(
            "INSERT INTO groove_alerts "
            "(detected_at, alert_type, severity, pattern, window_size, acknowledged_at) "
            "VALUES (?, 'ngram_repetition', 0.7, 'ack', 5, ?)",
            (now - 10, now - 5),
        )
        self.mc.tick()
        events = self.mc.get_recent(limit=10)
        self.assertEqual(len(events), 0, "Acknowledged alerts must not produce events")

    def test_groove_alert_outside_lookback_ignored(self):
        old_ts = time.time() - 700  # > 600s lookback
        self.writers["beliefs"].write(
            "INSERT INTO groove_alerts "
            "(detected_at, alert_type, severity, pattern, window_size) "
            "VALUES (?, 'ngram_repetition', 0.6, 'old', 5)",
            (old_ts,),
        )
        self.mc.tick()
        events = self.mc.get_recent(limit=10)
        self.assertEqual(len(events), 0, "Alerts outside lookback window must be ignored")


# ── Goal-drift detection ──────────────────────────────────────────────────────

class TestGoalDriftDetection(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.mc = _build_mc(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_no_drift_when_no_goals(self):
        _seed_nex_messages(self.writers, ["hello world", "weather is nice"])
        self.mc.tick()
        events = self.mc.get_recent(limit=10)
        drift_events = [e for e in events if e["event_type"] == "goal_drift"]
        self.assertEqual(drift_events, [], "No goals → no drift events")

    def test_no_drift_when_insufficient_messages(self):
        _seed_goal(self.writers, "Consciousness research", "Exploring emergence in neural systems")
        _seed_nex_messages(self.writers, ["just one message"])
        self.mc.tick()
        events = self.mc.get_recent(limit=10)
        drift_events = [e for e in events if e["event_type"] == "goal_drift"]
        self.assertEqual(drift_events, [], "< 2 messages → no drift detection")

    def test_drift_detected_when_responses_off_topic(self):
        _seed_goal(
            self.writers,
            "Consciousness Emergence Research",
            "Investigating how consciousness emerges in neural systems and cognitive architectures",
        )
        # 5 messages clearly off-topic from consciousness
        _seed_nex_messages(self.writers, [
            "The weather forecast shows rain tomorrow morning.",
            "Pasta cooking time depends on the thickness of the noodles.",
            "Soccer match results from last weekend were surprising.",
            "Stock market indices closed flat on Friday afternoon.",
            "The recipe calls for two cups of flour and one egg.",
        ])
        self.mc.tick()
        events = self.mc.get_recent(limit=10)
        drift_events = [e for e in events if e["event_type"] == "goal_drift"]
        self.assertGreater(len(drift_events), 0, "Off-topic responses must trigger goal_drift")
        self.assertIn("Goal-drift", drift_events[0]["description"])

    def test_no_drift_when_messages_aligned(self):
        _seed_goal(
            self.writers,
            "Consciousness Emergence Research",
            "Investigating how consciousness emerges in neural systems and cognitive architectures",
        )
        _seed_nex_messages(self.writers, [
            "Consciousness may emerge from recursive self-representation in neural networks.",
            "The binding problem suggests awareness arises from integrated information processing.",
            "Neural correlates of consciousness include gamma synchrony and thalamo-cortical loops.",
            "Integrated Information Theory proposes phi as a measure of conscious experience.",
            "Emergence in complex systems is analogous to awareness arising in neural architecture.",
        ])
        self.mc.tick()
        events = self.mc.get_recent(limit=10)
        drift_events = [e for e in events if e["event_type"] == "goal_drift"]
        self.assertEqual(drift_events, [], "Aligned responses must not trigger goal_drift")

    def test_drift_event_has_goal_title_in_description(self):
        _seed_goal(self.writers, "Quantum Computing", "Exploring qubit entanglement protocols")
        _seed_nex_messages(self.writers, [
            "I enjoy thinking about poetry and literature.",
            "The seasons change beautifully in autumn.",
            "Music theory is fascinating for its harmonic structures.",
            "Cooking involves chemistry at its heart.",
            "Ancient history reveals much about human nature.",
        ])
        self.mc.tick()
        events = self.mc.get_recent(limit=10)
        drift_events = [e for e in events if e["event_type"] == "goal_drift"]
        if drift_events:
            self.assertIn("Quantum Computing", drift_events[0]["description"])


# ── Decay ─────────────────────────────────────────────────────────────────────

class TestDecay(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.mc = _build_mc(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _seed_event(self, event_type, days_ago=0):
        created_at = time.time() - days_ago * 86400
        self.writers["conversations"].write(
            "INSERT INTO meta_cognition_events "
            "(event_type, description, severity, source, created_at) "
            "VALUES (?, ?, 0.5, 'test', ?)",
            (event_type, f"Test {event_type} event", created_at),
        )

    def test_decay_resolves_stale_events(self):
        self._seed_event("groove", days_ago=20)
        self.mc._cached_recent = None
        self.mc.decay(time.time())
        events = self.mc.get_recent(limit=10)
        self.assertEqual(len(events), 0, "Events stale > 14 days must be auto-resolved")

    def test_decay_preserves_fresh_events(self):
        self._seed_event("groove", days_ago=1)
        self.mc.decay(time.time())
        events = self.mc.get_recent(limit=10)
        self.assertEqual(len(events), 1, "Fresh events must survive decay()")

    def test_decay_invalidates_cache(self):
        self.mc.tick()  # populate cache
        self.assertIsNotNone(self.mc._cached_recent)
        self.mc.decay(time.time())
        self.assertIsNone(self.mc._cached_recent, "decay() must invalidate cache")


# ── Same-turn injection regression ───────────────────────────────────────────

class TestSameTurnInjection(unittest.TestCase):
    """Regression: detected events must surface in format_for_prompt() on the
    same tick() call, not the following one.

    Without the fix (_cached_recent not invalidated after write), tick() writes
    the event but the TTL gate skips the cache refresh — format_for_prompt()
    reads stale [] and returns empty. This test fails without the fix.
    """

    def test_drift_injects_on_same_tick(self):
        writers, readers, tmp = _make_env()
        try:
            _seed_goal(
                writers,
                "Consciousness Emergence Research",
                "Investigating how consciousness emerges in neural systems",
            )
            _seed_nex_messages(writers, [
                "The weather forecast shows rain tomorrow morning.",
                "Pasta cooking time depends on the thickness of noodles.",
                "Soccer match results from last weekend were surprising.",
                "Stock market indices closed flat on Friday afternoon.",
                "The recipe calls for two cups of flour and one egg.",
            ])
            mc = _build_mc(writers, readers)
            mc.tick()
            text = mc.format_for_prompt()
            self.assertNotEqual(
                text, "",
                "format_for_prompt() must return non-empty on the same tick() "
                "that detected and wrote the goal_drift event — not the next tick.",
            )
            self.assertIn("drifting", text)
        finally:
            _cleanup(writers, tmp)


# ── Cross-restart persistence ─────────────────────────────────────────────────

class TestCrossRestartPersistence(unittest.TestCase):

    def test_events_survive_new_instantiation(self):
        writers, readers, tmp = _make_env()
        try:
            mc1 = _build_mc(writers, readers)
            _seed_groove_alert(writers)
            mc1.tick()

            # Simulate restart: new Metacognition instance
            mc2 = _build_mc(writers, readers)
            events = mc2.get_recent(limit=10)
            self.assertGreater(len(events), 0,
                "meta_cognition_events must persist across Metacognition instantiation")
        finally:
            _cleanup(writers, tmp)


if __name__ == "__main__":
    unittest.main()
