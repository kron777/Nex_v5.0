"""Tests for TN-5 ThrowNetMonitor — SentienceNode wrapper."""
from __future__ import annotations

import threading
import unittest
from unittest.mock import MagicMock, patch

from theory_x.stage_throw_net.monitor import ThrowNetMonitor


def _monitor(sessions=None, engine_error=None, interval=300.0):
    engine = MagicMock()
    if engine_error is not None:
        engine.run_pending.side_effect = engine_error
    else:
        engine.run_pending.return_value = sessions if sessions is not None else []
    return ThrowNetMonitor(engine, interval_seconds=interval), engine


class TestTick(unittest.TestCase):

    def test_tick_calls_engine_run_pending(self):
        mon, engine = _monitor()
        mon.tick()
        engine.run_pending.assert_called_once()

    def test_tick_increments_tick_count(self):
        mon, _ = _monitor()
        mon.tick()
        mon.tick()
        self.assertEqual(mon._tick_count, 2)

    def test_tick_aggregates_sessions_total(self):
        mon, engine = _monitor()
        engine.run_pending.side_effect = [
            [{"session_id": "a"}, {"session_id": "b"}],
            [{"session_id": "c"}],
        ]
        mon.tick()
        mon.tick()
        self.assertEqual(mon._sessions_total, 3)

    def test_tick_handles_engine_error_gracefully(self):
        mon, _ = _monitor(engine_error=Exception("db gone"))
        result = mon.tick()
        self.assertEqual(mon._tick_count, 1)
        self.assertEqual(mon._sessions_total, 0)
        self.assertIn("tick_count", result)

    def test_tick_returns_state_dict(self):
        mon, _ = _monitor()
        result = mon.tick()
        for key in ("name", "tick_count", "sessions_total", "interval_seconds"):
            self.assertIn(key, result)


class TestState(unittest.TestCase):

    def test_state_returns_correct_shape(self):
        mon, _ = _monitor(interval=60.0)
        s = mon.state()
        self.assertEqual(s["name"], "throw_net_monitor")
        self.assertEqual(s["tick_count"], 0)
        self.assertEqual(s["sessions_total"], 0)
        self.assertEqual(s["interval_seconds"], 60.0)

    def test_decay_is_noop(self):
        mon, engine = _monitor()
        mon.decay(1234567890.0)
        engine.run_pending.assert_not_called()


class TestStartLoop(unittest.TestCase):

    def test_start_loop_spawns_daemon_thread(self):
        mon, _ = _monitor()
        mon.start_loop(interval_seconds=3600.0)
        self.assertIsNotNone(mon._thread)
        self.assertTrue(mon._thread.daemon)
        self.assertEqual(mon._thread.name, "throw_net_monitor")
        mon.stop()

    def test_stop_sets_stop_event(self):
        mon, _ = _monitor()
        mon.start_loop(interval_seconds=3600.0)
        self.assertFalse(mon._stop.is_set())
        mon.stop()
        self.assertTrue(mon._stop.is_set())


if __name__ == "__main__":
    unittest.main()
