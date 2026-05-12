"""SelfMindView unit tests — Phase 37.

14 tests per THEORY_OF_SELF_PROTOCOL.md §9.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_smv_")
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


def _make_smv(writers, readers, drive_emergence=None):
    from theory_x.stage_tom import SelfMindView
    smv = SelfMindView(
        dynamic_reader=readers["dynamic"],
        dynamic_writer=writers["dynamic"],
        beliefs_reader=readers["beliefs"],
        conversations_reader=readers["conversations"],
        drive_emergence=drive_emergence,
    )
    smv._last_tick_at = 0.0
    return smv


def _seed_beliefs(writers, n=5, tier=7):
    now = time.time()
    for i in range(n):
        writers["beliefs"].write(
            "INSERT INTO beliefs (content, tier, confidence, source, created_at) "
            "VALUES (?, ?, 0.6, 'test', ?)",
            (f"Test belief about consciousness number {i}", tier, now - i),
        )
    time.sleep(0.05)


def _seed_problem(writers):
    now = time.time()
    writers["conversations"].write(
        "INSERT INTO open_problems (title, description, state, created_at, last_touched_at) "
        "VALUES (?, ?, 'open', ?, ?)",
        ("How does attention shape experience?", "Exploring attention.", now, now),
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
        smv = _make_smv(self.writers, self.readers)
        self.assertIsInstance(smv, SentienceNode)


# ── 2. tick() returns state dict with expected keys ───────────────────────────

class TestTickStateShape(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_tick_returns_expected_keys(self):
        smv = _make_smv(self.writers, self.readers)
        result = smv.tick()
        self.assertIn("name", result)
        self.assertIn("tick_count", result)
        self.assertIn("total_snapshots", result)
        self.assertEqual(result["name"], "self_mind_view")

    def test_tick_increments_count(self):
        smv = _make_smv(self.writers, self.readers)
        smv.tick()
        self.assertEqual(smv._tick_count, 1)
        self.assertEqual(smv._total_snapshots, 1)


# ── 3. tick() respects interval guard ────────────────────────────────────────

class TestIntervalGuard(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_second_tick_skipped(self):
        from theory_x.stage_tom import SelfMindView
        smv = SelfMindView(
            dynamic_reader=self.readers["dynamic"],
            dynamic_writer=self.writers["dynamic"],
            beliefs_reader=self.readers["beliefs"],
            conversations_reader=self.readers["conversations"],
        )
        r1 = smv.tick()
        self.assertFalse(r1.get("skipped", False))
        r2 = smv.tick()
        self.assertTrue(r2.get("skipped"))


# ── 4. current_state() returns dict with all 5 aspects ───────────────────────

class TestCurrentStateShape(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_current_state_has_all_aspects(self):
        smv = _make_smv(self.writers, self.readers)
        state = smv.current_state()
        for key in ("taken_at", "beliefs", "intentions", "knowledge",
                    "uncertainty", "attention"):
            self.assertIn(key, state, f"missing key: {key}")

    def test_beliefs_aspect_has_expected_keys(self):
        smv = _make_smv(self.writers, self.readers)
        b = smv.current_state()["beliefs"]
        for k in ("total_count", "t1_count", "t2_count", "t3_count",
                  "t4_count", "avg_confidence", "recent_sample"):
            self.assertIn(k, b)

    def test_intentions_aspect_has_expected_keys(self):
        smv = _make_smv(self.writers, self.readers)
        i = smv.current_state()["intentions"]
        for k in ("open_problem_count", "active_drive_count",
                  "current_problem", "current_drive"):
            self.assertIn(k, i)


# ── 5. current_state() valid when substrate is sparse ────────────────────────

class TestSparseSubstrate(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_sparse_substrate_no_crash(self):
        # Clear keystones so beliefs table is effectively empty
        self.writers["beliefs"].write("DELETE FROM beliefs")
        time.sleep(0.05)
        smv = _make_smv(self.writers, self.readers)
        state = smv.current_state()
        self.assertEqual(state["beliefs"]["total_count"], 0)
        self.assertIsNone(state["beliefs"]["avg_confidence"])
        self.assertEqual(state["beliefs"]["recent_sample"], [])


# ── 6. current_summary() non-empty, all aspects mentioned ────────────────────

class TestCurrentSummary(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_summary_is_non_empty(self):
        smv = _make_smv(self.writers, self.readers)
        summary = smv.current_summary()
        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 10)

    def test_summary_mentions_beliefs(self):
        smv = _make_smv(self.writers, self.readers)
        summary = smv.current_summary()
        self.assertIn("beliefs", summary.lower())

    def test_summary_mentions_review(self):
        smv = _make_smv(self.writers, self.readers)
        summary = smv.current_summary()
        self.assertIn("review", summary.lower())


# ── 7. snapshot() writes a row with required fields ──────────────────────────

class TestSnapshotPersistence(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_snapshot_writes_row(self):
        smv = _make_smv(self.writers, self.readers)
        smv._snapshot()
        rows = self.readers["dynamic"].read("SELECT * FROM self_mind_snapshots")
        self.assertEqual(len(rows), 1)

    def test_snapshot_numerical_fields_populated(self):
        _seed_beliefs(self.writers, n=3, tier=7)
        smv = _make_smv(self.writers, self.readers)
        smv._snapshot()
        row = self.readers["dynamic"].read("SELECT * FROM self_mind_snapshots")[0]
        self.assertIsNotNone(row["taken_at"])
        self.assertGreater(row["belief_total_count"], 0)
        self.assertIsNotNone(row["review_queue_count"])
        self.assertIsNotNone(row["t3_t4_count"])


# ── 8. snapshot() JSON fields parse cleanly ──────────────────────────────────

class TestSnapshotJSON(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_json_fields_are_valid(self):
        _seed_beliefs(self.writers, n=5, tier=7)
        _seed_problem(self.writers)
        smv = _make_smv(self.writers, self.readers)
        smv._snapshot()
        row = self.readers["dynamic"].read("SELECT * FROM self_mind_snapshots")[0]
        for col in ("recent_beliefs_json", "current_intentions_json",
                    "knowledge_anchors_json", "explicit_unknowns_json",
                    "current_themes_json", "tags"):
            val = json.loads(row[col])
            self.assertIsInstance(val, list, f"{col} should parse to list")


# ── 9. recent_snapshots(limit=N) returns most recent N ───────────────────────

class TestRecentSnapshots(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_recent_snapshots_limit(self):
        smv = _make_smv(self.writers, self.readers)
        for _ in range(5):
            smv._snapshot()
        rows = smv.recent_snapshots(limit=3)
        self.assertEqual(len(rows), 3)

    def test_recent_snapshots_ordered_newest_first(self):
        smv = _make_smv(self.writers, self.readers)
        smv._snapshot()
        time.sleep(0.02)
        smv._snapshot()
        rows = smv.recent_snapshots(limit=2)
        self.assertGreaterEqual(rows[0]["taken_at"], rows[1]["taken_at"])


# ── 10. snapshot_at(t) returns closest snapshot ───────────────────────────────

class TestSnapshotAt(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_snapshot_at_returns_closest(self):
        smv = _make_smv(self.writers, self.readers)
        smv._snapshot()
        t = time.time()
        row = smv.snapshot_at(t)
        self.assertIsNotNone(row)
        self.assertIn("taken_at", row)

    def test_snapshot_at_returns_none_when_empty(self):
        smv = _make_smv(self.writers, self.readers)
        row = smv.snapshot_at(time.time())
        self.assertIsNone(row)


# ── 11. aspect_history returns time-series ────────────────────────────────────

class TestAspectHistory(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_aspect_history_beliefs(self):
        smv = _make_smv(self.writers, self.readers)
        smv._snapshot()
        rows = smv.aspect_history("beliefs", window_s=3600)
        self.assertEqual(len(rows), 1)
        self.assertIn("taken_at", rows[0])
        self.assertIn("belief_total_count", rows[0])

    def test_aspect_history_uncertainty(self):
        smv = _make_smv(self.writers, self.readers)
        smv._snapshot()
        rows = smv.aspect_history("uncertainty", window_s=3600)
        self.assertEqual(len(rows), 1)
        self.assertIn("review_queue_count", rows[0])


# ── 12. Tag wrapper produces non-empty tags ───────────────────────────────────

class TestTagInheritance(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_tags_column_is_list(self):
        _seed_beliefs(self.writers, n=5, tier=1)
        smv = _make_smv(self.writers, self.readers)
        smv._snapshot()
        row = self.readers["dynamic"].read("SELECT tags FROM self_mind_snapshots")[0]
        tags = json.loads(row["tags"])
        self.assertIsInstance(tags, list)


# ── 13. Schema migrations idempotent ─────────────────────────────────────────

class TestSchemaMigrations(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_table_exists(self):
        rows = self.readers["dynamic"].read(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='self_mind_snapshots'"
        )
        self.assertEqual(len(rows), 1)

    def test_init_all_idempotent(self):
        from substrate.init_db import init_all
        init_all()
        rows = self.readers["dynamic"].read(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='self_mind_snapshots'"
        )
        self.assertEqual(len(rows), 1)


# ── 14. Empty-substrate edge case doesn't crash ───────────────────────────────

class TestEmptySubstrate(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_tick_with_empty_substrate(self):
        self.writers["beliefs"].write("DELETE FROM beliefs")
        time.sleep(0.05)
        smv = _make_smv(self.writers, self.readers)
        result = smv.tick()
        self.assertIn("tick_count", result)
        rows = self.readers["dynamic"].read("SELECT * FROM self_mind_snapshots")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["belief_total_count"], 0)
        self.assertEqual(row["open_problem_count"], 0)
        self.assertEqual(row["review_queue_count"], 0)


if __name__ == "__main__":
    unittest.main()
