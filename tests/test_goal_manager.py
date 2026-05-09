"""GoalManager tests.

Covers:
- SentienceNode protocol conformance (name, tick, decay, state)
- CRUD: open/complete/cancel round-trip
- list_open excludes completed and cancelled
- get_active returns top-priority open goal
- format_for_prompt contains title and description
- resume returns full record; nonexistent returns None
- decay auto-closes stale goals > 60 days
- decay invalidates cache
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_gm_")
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


# ── SentienceNode protocol ────────────────────────────────────────────────────

class TestSentienceNodeProtocol(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        from theory_x.stage8_goal_manager.goal_manager import GoalManager
        self.gm = GoalManager(self.writers["conversations"], self.readers["conversations"])

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_implements_sentience_node_protocol(self):
        from theory_x import SentienceNode
        self.assertIsInstance(self.gm, SentienceNode)

    def test_has_name_attribute(self):
        from theory_x.stage8_goal_manager.goal_manager import GoalManager
        self.assertEqual(GoalManager.name, "goal_manager")
        self.assertEqual(self.gm.name, "goal_manager")

    def test_tick_returns_dict_with_name(self):
        result = self.gm.tick()
        self.assertIsInstance(result, dict)
        self.assertEqual(result["name"], "goal_manager")

    def test_tick_accepts_context(self):
        result = self.gm.tick(context={"session_id": "test"})
        self.assertIsInstance(result, dict)
        self.assertIn("open_count", result)

    def test_state_returns_expected_fields(self):
        s = self.gm.state()
        self.assertIn("name", s)
        self.assertIn("open_count", s)
        self.assertIn("active_top3", s)
        self.assertIn("oldest_age_days", s)
        self.assertIn("cache_age_s", s)

    def test_state_open_count_zero_on_empty_db(self):
        s = self.gm.tick()
        self.assertEqual(s["open_count"], 0)

    def test_decay_accepts_float(self):
        self.gm.decay(time.time())  # must not raise

    def test_state_open_count_updates_after_open(self):
        self.gm.open("Protocol Test Goal", "Testing the sentience node count")
        self.gm._cached_open = None  # force refresh
        s = self.gm.tick()
        self.assertEqual(s["open_count"], 1)


# ── Core CRUD and arbitration ─────────────────────────────────────────────────

class TestGoalManagerCore(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        from theory_x.stage8_goal_manager.goal_manager import GoalManager
        self.gm = GoalManager(self.writers["conversations"], self.readers["conversations"])

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_open_returns_id(self):
        gid = self.gm.open("Test goal", "description")
        self.assertIsInstance(gid, int)
        self.assertGreater(gid, 0)

    def test_resume_returns_record(self):
        gid = self.gm.open("Recursion question", "does recursion terminate?", priority=0.7)
        g = self.gm.resume(gid)
        self.assertIsNotNone(g)
        self.assertEqual(g["title"], "Recursion question")
        self.assertEqual(g["state"], "open")
        self.assertAlmostEqual(g["priority"], 0.7, places=4)

    def test_resume_nonexistent_returns_none(self):
        self.assertIsNone(self.gm.resume(9999))

    def test_complete_sets_state(self):
        gid = self.gm.open("Goal to complete", "will be completed")
        self.gm.complete(gid)
        g = self.gm.resume(gid)
        self.assertEqual(g["state"], "completed")
        self.assertIsNotNone(g["completed_at"])

    def test_cancel_sets_state(self):
        gid = self.gm.open("Goal to cancel", "will be cancelled")
        self.gm.cancel(gid)
        g = self.gm.resume(gid)
        self.assertEqual(g["state"], "cancelled")

    def test_list_open_excludes_completed_and_cancelled(self):
        g1 = self.gm.open("Open goal", "still open")
        g2 = self.gm.open("Completed goal", "will complete")
        g3 = self.gm.open("Cancelled goal", "will cancel")
        self.gm.complete(g2)
        self.gm.cancel(g3)
        open_list = self.gm.list_open()
        ids = [g["id"] for g in open_list]
        self.assertIn(g1, ids)
        self.assertNotIn(g2, ids)
        self.assertNotIn(g3, ids)

    def test_get_active_returns_highest_priority(self):
        self.gm.open("Low priority", "low", priority=0.2)
        self.gm.open("High priority", "high", priority=0.9)
        self.gm.open("Mid priority", "mid", priority=0.5)
        active = self.gm.get_active()
        self.assertIsNotNone(active)
        self.assertEqual(active["title"], "High priority")

    def test_get_active_returns_none_when_empty(self):
        self.assertIsNone(self.gm.get_active())

    def test_get_active_returns_none_when_all_completed(self):
        gid = self.gm.open("Only goal", "will complete", priority=0.8)
        self.gm.complete(gid)
        self.gm._cached_open = None
        self.assertIsNone(self.gm.get_active())

    def test_update_priority_changes_ordering(self):
        g1 = self.gm.open("Was low", "bumped up", priority=0.2)
        g2 = self.gm.open("Was high", "stays", priority=0.9)
        self.gm.update_priority(g1, 0.95)
        self.gm._cached_open = None
        active = self.gm.get_active()
        self.assertEqual(active["id"], g1)

    def test_format_for_prompt_contains_title_and_description(self):
        gid = self.gm.open("Fountain recursion", "solve 80/20 groove problem", priority=0.9)
        text = self.gm.format_for_prompt(gid)
        self.assertIn("Fountain recursion", text)
        self.assertIn("solve 80/20 groove problem", text)

    def test_format_for_prompt_nonexistent_returns_empty(self):
        self.assertEqual(self.gm.format_for_prompt(9999), "")

    def test_state_active_top3_reports_highest_priorities(self):
        self.gm.open("Goal A", "", priority=0.9)
        self.gm.open("Goal B", "", priority=0.7)
        self.gm.open("Goal C", "", priority=0.5)
        self.gm.open("Goal D", "", priority=0.1)
        self.gm._cached_open = None
        s = self.gm.tick()
        self.assertEqual(len(s["active_top3"]), 3)
        self.assertIn("Goal A", s["active_top3"])
        self.assertIn("Goal B", s["active_top3"])
        self.assertIn("Goal C", s["active_top3"])
        self.assertNotIn("Goal D", s["active_top3"])

    def test_priority_clamped_to_0_1(self):
        gid = self.gm.open("Clamped goal", "", priority=2.5)
        g = self.gm.resume(gid)
        self.assertLessEqual(g["priority"], 1.0)

    def test_optional_problem_id_nullable(self):
        gid = self.gm.open("No problem link", "standalone goal")
        g = self.gm.resume(gid)
        self.assertIsNone(g["problem_id"])

    def test_problem_id_stored_when_provided(self):
        # Insert a fake problem row first to satisfy the FK reference
        self.writers["conversations"].write(
            "INSERT INTO open_problems (title, description, state, created_at, last_touched_at) "
            "VALUES (?, ?, 'open', ?, ?)",
            ("Test problem", "desc", time.time(), time.time()),
        )
        prob_row = self.readers["conversations"].read_one(
            "SELECT id FROM open_problems LIMIT 1"
        )
        pid = prob_row["id"]
        gid = self.gm.open("Linked goal", "references problem", problem_id=pid)
        g = self.gm.resume(gid)
        self.assertEqual(g["problem_id"], pid)


# ── Decay ──────────────────────────────────────────────────────────────────────

class TestDecay(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        from theory_x.stage8_goal_manager.goal_manager import GoalManager
        self.gm = GoalManager(self.writers["conversations"], self.readers["conversations"])

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_decay_cancels_stale_goals(self):
        now = time.time()
        stale_ts = now - 70 * 86400  # 70 days ago (> 60 day threshold)
        self.writers["conversations"].write(
            "INSERT INTO goals "
            "(title, description, priority, state, source, created_at, last_touched_at) "
            "VALUES (?, ?, ?, 'open', 'user', ?, ?)",
            ("Stale Goal", "Very old unresolved goal", 0.5, stale_ts, stale_ts),
        )
        self.assertEqual(len(self.gm.list_open()), 1)
        self.gm.decay(now)
        self.assertEqual(len(self.gm.list_open()), 0,
            "Goal stale > 60 days must be auto-cancelled by decay()")

    def test_decay_leaves_fresh_goals_open(self):
        self.gm.open("Fresh Goal", "Created just now and should survive")
        self.gm.decay(time.time())
        self.assertEqual(len(self.gm.list_open()), 1,
            "Fresh goal must survive decay()")

    def test_decay_invalidates_cache(self):
        self.gm.tick()  # populate cache
        self.assertIsNotNone(self.gm._cached_open)
        self.gm.decay(time.time())
        self.assertIsNone(self.gm._cached_open,
            "decay() must invalidate the open-goal cache")


if __name__ == "__main__":
    unittest.main()
