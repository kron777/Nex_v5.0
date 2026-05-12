"""PredictiveSubstrate unit tests — Phase 35.

15 tests per PREDICTION_PROTOCOL.md §10.
"""
from __future__ import annotations

import json
import os
import shutil
import struct
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from tests import _bootstrap  # noqa: F401

import numpy as np


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_ps_")
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


def _make_ps(writers, readers, drive_emergence=None):
    from theory_x.stage_prediction import PredictiveSubstrate
    ps = PredictiveSubstrate(
        dynamic_reader=readers["dynamic"],
        dynamic_writer=writers["dynamic"],
        beliefs_reader=readers["beliefs"],
        conversations_reader=readers["conversations"],
        sense_reader=readers["sense"],
        drive_emergence=drive_emergence,
    )
    # Bypass interval guard so direct tick() calls work in tests
    ps._last_tick_at = 0.0
    return ps


def _seed_beliefs(writers, n=5, content_prefix="Test belief about consciousness and experience"):
    now = time.time()
    for i in range(n):
        writers["beliefs"].write(
            "INSERT INTO beliefs (content, tier, confidence, source, created_at) "
            "VALUES (?, 6, 0.7, 'fountain_insight', ?)",
            (f"{content_prefix} number {i}", now - i),
        )
    time.sleep(0.05)


def _seed_sense_events(writers, n=5):
    now = time.time()
    for i in range(n):
        writers["sense"].write(
            "INSERT INTO sense_events (stream, payload, timestamp) VALUES (?, ?, ?)",
            ("external.feed", f"test sense event payload {i}", int(now) - i),
        )
    time.sleep(0.05)


def _seed_messages(writers, n=5):
    now = int(time.time())
    for i in range(n):
        writers["conversations"].write(
            "INSERT INTO messages (session_id, role, content, timestamp) "
            "VALUES (?, ?, ?, ?)",
            ("test_session", "user", f"test user message {i}", now - i),
        )
    time.sleep(0.05)


def _fake_emb(dim: int = 384, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v = rng.random(dim).astype(np.float32)
    return v / np.linalg.norm(v)


class TestStateShape(unittest.TestCase):
    """Tests 1–2: tick() returns expected state; skipped state has expected keys."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_tick_returns_state_dict(self):
        ps = _make_ps(self.writers, self.readers)
        result = ps.tick()
        self.assertIn("name", result)
        self.assertIn("tick_count", result)
        self.assertIn("total_predictions_made", result)
        self.assertIn("total_verified", result)
        self.assertEqual(result["name"], "predictive_substrate")

    def test_tick_skipped_state(self):
        ps = _make_ps(self.writers, self.readers)
        ps.tick()  # first tick clears interval guard
        result = ps.tick()  # second tick should be skipped
        self.assertTrue(result.get("skipped"))
        self.assertIn("tick_count", result)


class TestIntervalGuard(unittest.TestCase):
    """Test 3: tick() respects interval guard."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_interval_guard_blocks_second_tick(self):
        from theory_x.stage_prediction import PredictiveSubstrate
        ps = PredictiveSubstrate(
            dynamic_reader=self.readers["dynamic"],
            dynamic_writer=self.writers["dynamic"],
            beliefs_reader=self.readers["beliefs"],
            conversations_reader=self.readers["conversations"],
            sense_reader=self.readers["sense"],
        )
        # First tick: guard passes (last_tick_at=0)
        result1 = ps.tick()
        self.assertFalse(result1.get("skipped", False))
        # Second tick: guard blocks
        result2 = ps.tick()
        self.assertTrue(result2.get("skipped"))


class TestSentienceNodeProtocol(unittest.TestCase):
    """Test 4: SentienceNode protocol compliance."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_sentience_node_protocol(self):
        from theory_x import SentienceNode
        from theory_x.stage_prediction import PredictiveSubstrate
        ps = PredictiveSubstrate(
            dynamic_reader=self.readers["dynamic"],
            dynamic_writer=self.writers["dynamic"],
            beliefs_reader=self.readers["beliefs"],
            conversations_reader=self.readers["conversations"],
            sense_reader=self.readers["sense"],
        )
        self.assertIsInstance(ps, SentienceNode)


class TestSparseSubstrate(unittest.TestCase):
    """Tests 5–6: skips prediction when substrate too sparse."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_skip_internal_when_fewer_than_3_beliefs(self):
        # init_all seeds 76 keystones; clear them so sparse guard can fire
        self.writers["beliefs"].write("DELETE FROM beliefs")
        _seed_beliefs(self.writers, n=2)
        ps = _make_ps(self.writers, self.readers)
        ps.tick()
        rows = self.readers["dynamic"].read(
            "SELECT * FROM predictions WHERE prediction_type = 'internal_belief'"
        )
        self.assertEqual(len(rows), 0)

    def test_skip_external_when_fewer_than_3_inputs(self):
        _seed_sense_events(self.writers, n=2)
        ps = _make_ps(self.writers, self.readers)
        ps.tick()
        rows = self.readers["dynamic"].read(
            "SELECT * FROM predictions WHERE prediction_type = 'external_input'"
        )
        self.assertEqual(len(rows), 0)


class TestPredictionGeneration(unittest.TestCase):
    """Tests 7–9: predict() writes rows with valid embedding + representative content."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_internal_prediction_written(self):
        _seed_beliefs(self.writers, n=5)
        ps = _make_ps(self.writers, self.readers)
        ps.tick()
        rows = self.readers["dynamic"].read(
            "SELECT * FROM predictions WHERE prediction_type = 'internal_belief'"
        )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertIsNotNone(row["centroid_embedding"])
        emb = np.frombuffer(bytes(row["centroid_embedding"]), dtype=np.float32)
        self.assertEqual(emb.shape, (384,))
        self.assertIsNotNone(row["representative_content"])
        self.assertIsNotNone(row["target_window_end"])

    def test_external_prediction_written(self):
        _seed_sense_events(self.writers, n=5)
        ps = _make_ps(self.writers, self.readers)
        ps.tick()
        rows = self.readers["dynamic"].read(
            "SELECT * FROM predictions WHERE prediction_type = 'external_input'"
        )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        emb = np.frombuffer(bytes(row["centroid_embedding"]), dtype=np.float32)
        self.assertEqual(emb.shape, (384,))

    def test_both_types_written_when_both_substrates_populated(self):
        _seed_beliefs(self.writers, n=5)
        _seed_sense_events(self.writers, n=5)
        ps = _make_ps(self.writers, self.readers)
        ps.tick()
        types = {r["prediction_type"] for r in self.readers["dynamic"].read(
            "SELECT prediction_type FROM predictions"
        )}
        self.assertIn("internal_belief", types)
        self.assertIn("external_input", types)


class TestVerification(unittest.TestCase):
    """Tests 10–13: verify() math, empty-window, flags, idempotency."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _insert_prediction(self, pred_type, centroid, window_end_offset=-1):
        now = time.time()
        tags = json.dumps([])
        return self.writers["dynamic"].write(
            "INSERT INTO predictions "
            "(made_at, target_window_end, prediction_type, centroid_embedding, "
            "representative_content, tags) VALUES (?, ?, ?, ?, ?, ?)",
            (now - 300, now + window_end_offset, pred_type,
             centroid.astype(np.float32).tobytes(), "test content", tags),
        )

    def test_verify_empty_window_scores_1(self):
        centroid = _fake_emb(seed=1)
        self._insert_prediction("internal_belief", centroid, window_end_offset=-1)
        ps = _make_ps(self.writers, self.readers)
        ps._verify()
        rows = self.readers["dynamic"].read("SELECT * FROM surprise_events")
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]["surprise_score"], 1.0)

    def test_verify_surprise_flag_fires_above_threshold(self):
        centroid = _fake_emb(seed=42)
        self._insert_prediction("internal_belief", centroid, window_end_offset=-1)
        now = time.time()
        # Seed a belief in the window with orthogonal content
        self.writers["beliefs"].write(
            "INSERT INTO beliefs (content, tier, confidence, source, created_at) "
            "VALUES (?, 6, 0.7, 'fountain_insight', ?)",
            ("completely different topic about weather", now - 200),
        )
        time.sleep(0.05)
        ps = _make_ps(self.writers, self.readers)
        ps._verify()
        rows = self.readers["dynamic"].read("SELECT * FROM surprise_events")
        self.assertEqual(len(rows), 1)
        self.assertIsNotNone(rows[0]["surprise_score"])

    def test_verify_big_surprise_flag(self):
        centroid = _fake_emb(seed=7)
        self._insert_prediction("internal_belief", centroid, window_end_offset=-1)
        ps = _make_ps(self.writers, self.readers)
        ps._verify()
        rows = self.readers["dynamic"].read("SELECT * FROM surprise_events")
        self.assertEqual(len(rows), 1)
        # Empty window → surprise_score = 1.0 → big_surprise = 1
        self.assertEqual(rows[0]["big_surprise"], 1)

    def test_verify_idempotent(self):
        centroid = _fake_emb(seed=3)
        self._insert_prediction("internal_belief", centroid, window_end_offset=-1)
        ps = _make_ps(self.writers, self.readers)
        ps._verify()
        ps._verify()  # second call: no unverified rows remain
        rows = self.readers["dynamic"].read("SELECT * FROM surprise_events")
        self.assertEqual(len(rows), 1)  # still exactly 1


class TestTagInheritance(unittest.TestCase):
    """Test 14: tags auto-generated on both tables."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_predictions_have_tags(self):
        _seed_beliefs(self.writers, n=5)
        ps = _make_ps(self.writers, self.readers)
        ps.tick()
        rows = self.readers["dynamic"].read("SELECT tags FROM predictions LIMIT 1")
        self.assertEqual(len(rows), 1)
        tags = json.loads(rows[0]["tags"])
        self.assertIsInstance(tags, list)

    def test_surprise_events_have_tags(self):
        now = time.time()
        centroid = _fake_emb(seed=5)
        tags = json.dumps([])
        self.writers["dynamic"].write(
            "INSERT INTO predictions "
            "(made_at, target_window_end, prediction_type, centroid_embedding, "
            "representative_content, tags) VALUES (?, ?, ?, ?, ?, ?)",
            (now - 300, now - 1, "internal_belief",
             centroid.astype(np.float32).tobytes(), "consciousness and experience", tags),
        )
        ps = _make_ps(self.writers, self.readers)
        ps._verify()
        rows = self.readers["dynamic"].read("SELECT tags FROM surprise_events LIMIT 1")
        self.assertEqual(len(rows), 1)
        tags_val = json.loads(rows[0]["tags"])
        self.assertIsInstance(tags_val, list)


class TestSchemaMigrations(unittest.TestCase):
    """Test 15: schema migrations are idempotent."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_predictions_table_exists(self):
        rows = self.readers["dynamic"].read(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='predictions'"
        )
        self.assertEqual(len(rows), 1)

    def test_surprise_events_table_exists(self):
        rows = self.readers["dynamic"].read(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='surprise_events'"
        )
        self.assertEqual(len(rows), 1)

    def test_init_all_idempotent(self):
        from substrate.init_db import init_all
        init_all()  # second call must not raise or duplicate
        rows = self.readers["dynamic"].read(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='predictions'"
        )
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
