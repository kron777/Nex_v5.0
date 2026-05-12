"""SocialPresence unit tests — Phase 38.

15 tests per SOCIAL_PRESENCE_PROTOCOL.md §9.
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
    tmp = tempfile.mkdtemp(prefix="nex5_sp_")
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


def _make_sp(writers, readers):
    from theory_x.stage_social import SocialPresence
    sp = SocialPresence(
        dynamic_reader=readers["dynamic"],
        dynamic_writer=writers["dynamic"],
        beliefs_reader=readers["beliefs"],
        conversations_reader=readers["conversations"],
    )
    sp._last_tick_at = 0.0
    return sp


def _seed_assistant_messages(writers, n=3):
    now = int(time.time())
    for i in range(n):
        writers["conversations"].write(
            "INSERT INTO messages (session_id, role, content, timestamp) "
            "VALUES (?, 'nex', ?, ?)",
            (
                f"session_{i % 2}",
                f"What do you think about consciousness? That tension between "
                f"awareness and experience is fascinating to me. Number {i}.",
                now - i * 10,
            ),
        )
    time.sleep(0.05)


def _seed_user_messages(writers, n=2):
    now = int(time.time())
    for i in range(n):
        writers["conversations"].write(
            "INSERT INTO messages (session_id, role, content, timestamp) "
            "VALUES (?, 'user', ?, ?)",
            (f"session_{i % 2}", f"What do you think? Question {i}.", now - i * 10 - 5),
        )
    time.sleep(0.05)


def _seed_fountain_beliefs(writers, n=5):
    now = int(time.time())
    for i in range(n):
        writers["beliefs"].write(
            "INSERT INTO beliefs (content, tier, confidence, source, created_at, tags) "
            "VALUES (?, 7, 0.6, 'fountain_insight', ?, ?)",
            (
                f"The interplay between attention and awareness reveals {i}.",
                now - i * 5,
                json.dumps(["attention", "consciousness"] if i % 2 == 0 else ["presence"]),
            ),
        )
    time.sleep(0.05)


def _seed_speech_queue(writers, n=2):
    now = time.time()
    for i in range(n):
        writers["beliefs"].write(
            "INSERT INTO speech_queue (belief_id, content, queued_at) VALUES (?, ?, ?)",
            (1, f"Spoken output number {i} about awareness.", now - i * 20),
        )
    time.sleep(0.05)


def _seed_affect_state(writers):
    now = time.time()
    writers["conversations"].write(
        "INSERT OR REPLACE INTO affect_state "
        "(id, valence, arousal, stability, mood_label, updated_at) "
        "VALUES (1, 0.1, 0.35, 0.7, 'neutral', ?)",
        (now,),
    )
    time.sleep(0.05)


# ── 1. SentienceNode protocol ─────────────────────────────────────────────────

class TestSentienceNodeProtocol(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_sentience_node_protocol(self):
        from theory_x import SentienceNode
        sp = _make_sp(self.writers, self.readers)
        self.assertIsInstance(sp, SentienceNode)


# ── 2. tick() returns state dict with expected keys ───────────────────────────

class TestTickStateShape(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_tick_returns_expected_keys(self):
        sp = _make_sp(self.writers, self.readers)
        result = sp.tick()
        self.assertIn("name", result)
        self.assertIn("tick_count", result)
        self.assertIn("total_snapshots", result)
        self.assertEqual(result["name"], "social_presence")

    def test_tick_increments_counts(self):
        sp = _make_sp(self.writers, self.readers)
        sp.tick()
        self.assertEqual(sp._tick_count, 1)
        self.assertEqual(sp._total_snapshots, 1)


# ── 3. tick() respects interval guard ────────────────────────────────────────

class TestIntervalGuard(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_second_tick_skipped(self):
        from theory_x.stage_social import SocialPresence
        sp = SocialPresence(
            dynamic_reader=self.readers["dynamic"],
            dynamic_writer=self.writers["dynamic"],
            beliefs_reader=self.readers["beliefs"],
            conversations_reader=self.readers["conversations"],
        )
        r1 = sp.tick()
        self.assertFalse(r1.get("skipped", False))
        r2 = sp.tick()
        self.assertTrue(r2.get("skipped"))


# ── 4. current_state() returns both aspect groups + self_reports ──────────────

class TestCurrentStateShape(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_current_state_has_both_aspects(self):
        sp = _make_sp(self.writers, self.readers)
        state = sp.current_state()
        self.assertIn("taken_at", state)
        self.assertIn("voice_style", state)
        self.assertIn("engagement", state)

    def test_voice_style_has_expected_keys(self):
        sp = _make_sp(self.writers, self.readers)
        v = sp.current_state()["voice_style"]
        for k in ("total_output_count_5m", "avg_sentence_length_words",
                  "question_ratio", "vocab_distinctiveness",
                  "avg_arousal_during_outputs", "vocabulary_top_words",
                  "self_report"):
            self.assertIn(k, v)

    def test_engagement_has_expected_keys(self):
        sp = _make_sp(self.writers, self.readers)
        e = sp.current_state()["engagement"]
        for k in ("response_count_5m", "avg_response_latency_s",
                  "active_conversation_count", "topic_diversity",
                  "recent_topics", "active_sessions", "self_report"):
            self.assertIn(k, e)


# ── 5. current_state() valid when substrate is sparse ────────────────────────

class TestSparseSubstrate(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_sparse_substrate_no_crash(self):
        sp = _make_sp(self.writers, self.readers)
        state = sp.current_state()
        self.assertEqual(state["voice_style"]["total_output_count_5m"], 0)
        self.assertEqual(state["engagement"]["response_count_5m"], 0)
        self.assertEqual(state["engagement"]["active_conversation_count"], 0)

    def test_sparse_voice_self_report_graceful(self):
        sp = _make_sp(self.writers, self.readers)
        state = sp.current_state()
        report = state["voice_style"]["self_report"]
        self.assertIsInstance(report, str)
        self.assertIn("No recent outputs", report)


# ── 6. current_summary() mentions both aspects ────────────────────────────────

class TestCurrentSummary(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_summary_is_non_empty(self):
        sp = _make_sp(self.writers, self.readers)
        summary = sp.current_summary()
        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 5)

    def test_summary_mentions_conversations(self):
        sp = _make_sp(self.writers, self.readers)
        summary = sp.current_summary()
        self.assertIn("conversations", summary.lower())


# ── 7. snapshot() writes a row with required fields ──────────────────────────

class TestSnapshotPersistence(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_snapshot_writes_row(self):
        sp = _make_sp(self.writers, self.readers)
        sp._snapshot()
        rows = self.readers["dynamic"].read(
            "SELECT * FROM social_presence_snapshots"
        )
        self.assertEqual(len(rows), 1)

    def test_snapshot_fields_populated(self):
        _seed_assistant_messages(self.writers, n=3)
        _seed_affect_state(self.writers)
        sp = _make_sp(self.writers, self.readers)
        sp._snapshot()
        row = self.readers["dynamic"].read(
            "SELECT * FROM social_presence_snapshots"
        )[0]
        self.assertIsNotNone(row["taken_at"])
        self.assertIsNotNone(row["response_count_5m"])
        self.assertIsNotNone(row["active_conversation_count"])


# ── 8. snapshot() JSON fields parse cleanly ──────────────────────────────────

class TestSnapshotJSON(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_json_fields_are_valid(self):
        _seed_fountain_beliefs(self.writers, n=3)
        _seed_assistant_messages(self.writers, n=2)
        sp = _make_sp(self.writers, self.readers)
        sp._snapshot()
        row = self.readers["dynamic"].read(
            "SELECT * FROM social_presence_snapshots"
        )[0]
        for col in ("vocabulary_top_words_json", "recent_topics_json",
                    "active_sessions_json", "tags"):
            val = json.loads(row[col])
            self.assertIsInstance(val, list, f"{col} must parse to list")


# ── 9. voice_self_report reflects metrics ─────────────────────────────────────

class TestVoiceSelfReport(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_voice_self_report_template_fires(self):
        _seed_assistant_messages(self.writers, n=3)
        _seed_affect_state(self.writers)
        sp = _make_sp(self.writers, self.readers)
        state = sp.current_state()
        report = state["voice_style"]["self_report"]
        self.assertIn("arousal", report)
        self.assertIn("words", report)
        self.assertNotIn("No recent outputs", report)

    def test_voice_self_report_mentions_question_ratio(self):
        _seed_assistant_messages(self.writers, n=3)
        sp = _make_sp(self.writers, self.readers)
        state = sp.current_state()
        report = state["voice_style"]["self_report"]
        self.assertIn("questions", report)


# ── 10. engagement_self_report reflects metrics ───────────────────────────────

class TestEngagementSelfReport(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_engagement_self_report_template_fires(self):
        sp = _make_sp(self.writers, self.readers)
        state = sp.current_state()
        report = state["engagement"]["self_report"]
        self.assertIn("conversations", report)
        self.assertIn("latency", report)
        self.assertIn("responses", report)

    def test_engagement_self_report_mentions_focus(self):
        _seed_fountain_beliefs(self.writers, n=3)
        sp = _make_sp(self.writers, self.readers)
        state = sp.current_state()
        report = state["engagement"]["self_report"]
        self.assertIn("focus", report)


# ── 11. recent_snapshots(limit=N) ────────────────────────────────────────────

class TestRecentSnapshots(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_recent_snapshots_limit(self):
        sp = _make_sp(self.writers, self.readers)
        for _ in range(5):
            sp._snapshot()
        rows = sp.recent_snapshots(limit=3)
        self.assertEqual(len(rows), 3)

    def test_recent_snapshots_newest_first(self):
        sp = _make_sp(self.writers, self.readers)
        sp._snapshot()
        time.sleep(0.02)
        sp._snapshot()
        rows = sp.recent_snapshots(limit=2)
        self.assertGreaterEqual(rows[0]["taken_at"], rows[1]["taken_at"])


# ── 12. voice_history() returns time series ───────────────────────────────────

class TestVoiceHistory(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_voice_history_returns_series(self):
        sp = _make_sp(self.writers, self.readers)
        sp._snapshot()
        rows = sp.voice_history(window_s=3600)
        self.assertEqual(len(rows), 1)
        self.assertIn("taken_at", rows[0])
        self.assertIn("total_output_count_5m", rows[0])
        self.assertIn("question_ratio", rows[0])


# ── 13. engagement_history() returns time series ─────────────────────────────

class TestEngagementHistory(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_engagement_history_returns_series(self):
        sp = _make_sp(self.writers, self.readers)
        sp._snapshot()
        rows = sp.engagement_history(window_s=3600)
        self.assertEqual(len(rows), 1)
        self.assertIn("response_count_5m", rows[0])
        self.assertIn("active_conversation_count", rows[0])


# ── 14. Tags produced via Tag Protocol ───────────────────────────────────────

class TestTagInheritance(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_tags_column_is_list(self):
        _seed_assistant_messages(self.writers, n=3)
        _seed_fountain_beliefs(self.writers, n=3)
        sp = _make_sp(self.writers, self.readers)
        sp._snapshot()
        row = self.readers["dynamic"].read(
            "SELECT tags FROM social_presence_snapshots"
        )[0]
        tags = json.loads(row["tags"])
        self.assertIsInstance(tags, list)


# ── 15. Schema migration idempotency ─────────────────────────────────────────

class TestSchemaMigrations(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_table_exists(self):
        rows = self.readers["dynamic"].read(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='social_presence_snapshots'"
        )
        self.assertEqual(len(rows), 1)

    def test_init_all_idempotent(self):
        from substrate.init_db import init_all
        init_all()
        rows = self.readers["dynamic"].read(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='social_presence_snapshots'"
        )
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
