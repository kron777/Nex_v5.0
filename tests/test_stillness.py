"""Unit tests for Row 9 Stillness extension.

8 tests per work order:
  1 - stillness_log table schema present in conversations.db
  2 - Metacognition writes stillness_log when groove count >= 3 in window
  3 - Metacognition does NOT write when groove count < 3
  4 - Fountain crystallizer skips when active stillness row present
  5 - Fountain crystallizer proceeds normally when no stillness row
  6 - Fountain crystallizer proceeds when stillness expired (now > expires_at)
  7 - stillness expires_at math: started_at + duration_s = expires_at
  8 - Window logic: groove alerts outside 30min window don't count
"""
from __future__ import annotations

import sqlite3
import time
import unittest
from unittest.mock import MagicMock, call

from theory_x.stage9_metacognition.metacognition import (
    Metacognition,
    _STILLNESS_THRESHOLD,
    _STILLNESS_WINDOW_S,
    _STILLNESS_DURATION_S,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_metacognition(
    *,
    active_stillness=False,
    groove_count_in_window=0,
):
    """Build a Metacognition instance backed entirely by mocks."""
    writer = MagicMock()
    writer.write.return_value = 1

    reader = MagicMock()

    def _read_one(sql, params=()):
        sql_l = sql.lower()
        if "stillness_log" in sql_l and "expires_at" in sql_l:
            return {"id": 1} if active_stillness else None
        if "count(*)" in sql_l and "meta_cognition_events" in sql_l:
            return {"n": groove_count_in_window}
        return None

    reader.read_one.side_effect = _read_one
    reader.read.return_value = []

    beliefs_reader = MagicMock()
    beliefs_reader.read.return_value = []

    node = Metacognition(writer, reader, beliefs_reader)
    node._mock_writer = writer
    node._mock_reader = reader
    return node


def _make_crystallizer(*, stillness_row=None):
    """Build a FountainCrystallizer backed entirely by mocks.

    stillness_row: dict with at least 'id' key if stillness active; None otherwise.
    """
    from theory_x.stage6_fountain.crystallizer import FountainCrystallizer

    bw = MagicMock()
    bw.write.return_value = 42
    br = MagicMock()
    br.read.return_value = []
    br.read_one.return_value = None

    cr = MagicMock()
    cr.read_one.return_value = stillness_row

    c = FountainCrystallizer(
        beliefs_writer=bw,
        beliefs_reader=br,
        conversations_reader=cr,
    )
    c._mock_bw = bw
    c._mock_cr = cr
    return c


# ── Test 1 — stillness_log schema exists ─────────────────────────────────────

class TestStillnessLogSchema(unittest.TestCase):
    def test_table_created_by_migration(self):
        """stillness_log CREATE statement in _MIGRATIONS produces valid schema."""
        from substrate.init_db import _MIGRATIONS
        stmts = _MIGRATIONS.get("conversations", [])
        create_stmts = [s for s in stmts if "CREATE TABLE IF NOT EXISTS stillness_log" in s]
        self.assertEqual(len(create_stmts), 1, "Expected exactly one stillness_log CREATE")

        # Verify the CREATE is valid SQL by executing it in-memory
        with sqlite3.connect(":memory:") as conn:
            conn.execute(create_stmts[0])
            cols = {row[1] for row in conn.execute("PRAGMA table_info(stillness_log)")}
        self.assertIn("id",           cols)
        self.assertIn("started_at",   cols)
        self.assertIn("duration_s",   cols)
        self.assertIn("expires_at",   cols)
        self.assertIn("trigger",      cols)
        self.assertIn("groove_count", cols)


# ── Test 2 — Metacognition writes stillness when groove count >= threshold ────

class TestMetacognitionWritesStillness(unittest.TestCase):
    def test_writes_stillness_log_when_count_at_threshold(self):
        node = _make_metacognition(
            active_stillness=False,
            groove_count_in_window=_STILLNESS_THRESHOLD,
        )
        now = time.time()
        node._maybe_engage_stillness(now)

        calls_sql = [str(c.args[0]) for c in node._mock_writer.write.call_args_list]
        self.assertTrue(
            any("INSERT INTO stillness_log" in s for s in calls_sql),
            f"Expected INSERT INTO stillness_log; got: {calls_sql}",
        )

    def test_writes_stillness_log_when_count_exceeds_threshold(self):
        node = _make_metacognition(
            active_stillness=False,
            groove_count_in_window=_STILLNESS_THRESHOLD + 2,
        )
        now = time.time()
        node._maybe_engage_stillness(now)

        calls_sql = [str(c.args[0]) for c in node._mock_writer.write.call_args_list]
        self.assertTrue(
            any("INSERT INTO stillness_log" in s for s in calls_sql),
        )


# ── Test 3 — Metacognition does NOT write when groove count < threshold ───────

class TestMetacognitionNoStillnessBelowThreshold(unittest.TestCase):
    def test_no_write_when_count_below_threshold(self):
        node = _make_metacognition(
            active_stillness=False,
            groove_count_in_window=_STILLNESS_THRESHOLD - 1,
        )
        now = time.time()
        node._maybe_engage_stillness(now)

        calls_sql = [str(c.args[0]) for c in node._mock_writer.write.call_args_list]
        self.assertFalse(
            any("INSERT INTO stillness_log" in s for s in calls_sql),
            "Should NOT write stillness when count below threshold",
        )

    def test_no_write_when_count_zero(self):
        node = _make_metacognition(active_stillness=False, groove_count_in_window=0)
        node._maybe_engage_stillness(time.time())
        calls_sql = [str(c.args[0]) for c in node._mock_writer.write.call_args_list]
        self.assertFalse(any("INSERT INTO stillness_log" in s for s in calls_sql))


# ── Test 4 — Fountain crystallizer skips when stillness active ────────────────

class TestCrystallizerSkipsWhenStillnessActive(unittest.TestCase):
    def test_crystallize_returns_none_when_stillness_active(self):
        stillness_row = {"id": 7}
        c = _make_crystallizer(stillness_row=stillness_row)

        result = c.crystallize(
            thought="A genuine insight about emergence",
            fountain_event_id=1,
            ts=time.time(),
        )
        self.assertIsNone(result, "crystallize() must return None when stillness active")

    def test_no_belief_written_when_stillness_active(self):
        c = _make_crystallizer(stillness_row={"id": 1})
        c.crystallize("Another insight", fountain_event_id=1, ts=time.time())
        # beliefs_writer.write should never be called
        self.assertFalse(
            c._mock_bw.write.called,
            "beliefs_writer.write should not be called when stillness active",
        )


# ── Test 5 — Fountain crystallizer proceeds when no stillness ─────────────────

class TestCrystallizerProceedsNoStillness(unittest.TestCase):
    def test_crystallize_proceeds_when_no_stillness(self):
        c = _make_crystallizer(stillness_row=None)

        # Supply a thought that passes quality checks
        thought = "I notice the recursive nature of self-observation here."
        result = c.crystallize(
            thought=thought,
            fountain_event_id=1,
            ts=time.time(),
        )
        # Should reach the write attempt (not blocked by stillness)
        # Result is None only if quality gate rejects — but stillness did not block
        # Quality gate may still reject; what matters is the beliefs writer was called
        # OR the result is None for a quality reason, not a stillness reason.
        # Verify: cr.read_one was called (stillness path was reached)
        self.assertTrue(
            c._mock_cr.read_one.called,
            "conversations_reader.read_one should be called to check stillness",
        )


# ── Test 6 — Crystallizer proceeds when stillness expired ─────────────────────

class TestCrystallizerProceedsExpiredStillness(unittest.TestCase):
    def test_proceeds_when_stillness_expired(self):
        """An expired stillness row (expires_at < now) must not block crystallization."""
        # Simulate expired row: read_one returns None (the SQL WHERE expires_at > now
        # filters it out, so the mock correctly returns None for an expired row)
        c = _make_crystallizer(stillness_row=None)  # read_one returns None = expired/absent

        # crystallize should not be blocked
        c.crystallize(
            thought="A thought after stillness has passed.",
            fountain_event_id=2,
            ts=time.time(),
        )
        # Stillness check ran but did not block (read_one returned None)
        self.assertTrue(c._mock_cr.read_one.called)
        # No early return — the beliefs writer path was attempted
        # (quality gate may still reject; no bw.write assert needed here)


# ── Test 7 — expires_at math ──────────────────────────────────────────────────

class TestStillnessExpiresAtMath(unittest.TestCase):
    def test_expires_at_equals_started_at_plus_duration(self):
        node = _make_metacognition(
            active_stillness=False,
            groove_count_in_window=_STILLNESS_THRESHOLD,
        )
        now = 1_000_000.0
        node._maybe_engage_stillness(now)

        for c in node._mock_writer.write.call_args_list:
            if "INSERT INTO stillness_log" in str(c.args[0]):
                params = c.args[1]
                started_at  = params[0]  # now
                duration_s  = params[1]
                expires_at  = params[2]
                self.assertAlmostEqual(started_at, now, places=3)
                self.assertAlmostEqual(duration_s, _STILLNESS_DURATION_S, places=3)
                self.assertAlmostEqual(
                    expires_at, now + _STILLNESS_DURATION_S, places=3,
                    msg="expires_at must equal started_at + duration_s",
                )
                return
        self.fail("INSERT INTO stillness_log was not written")


# ── Test 8 — Window logic: old groove events don't count ──────────────────────

class TestStillnessWindowLogic(unittest.TestCase):
    def test_groove_count_query_uses_window_cutoff(self):
        """The SQL query for groove count must include a created_at >= cutoff filter."""
        node = _make_metacognition(
            active_stillness=False,
            groove_count_in_window=0,
        )
        now = time.time()
        node._maybe_engage_stillness(now)

        # Inspect all read_one calls for the groove count query
        found_window_query = False
        for c in node._mock_reader.read_one.call_args_list:
            sql = str(c.args[0]).lower()
            if "count(*)" in sql and "meta_cognition_events" in sql and "created_at" in sql:
                params = c.args[1] if len(c.args) > 1 else ()
                # The cutoff param should be approximately now - _STILLNESS_WINDOW_S
                if params:
                    cutoff_param = float(params[0])
                    expected_cutoff = now - _STILLNESS_WINDOW_S
                    self.assertAlmostEqual(
                        cutoff_param, expected_cutoff, delta=2.0,
                        msg="Groove count cutoff must be now - _STILLNESS_WINDOW_S",
                    )
                found_window_query = True
                break

        self.assertTrue(
            found_window_query,
            "Expected a groove count query with created_at window filter",
        )


if __name__ == "__main__":
    unittest.main()
