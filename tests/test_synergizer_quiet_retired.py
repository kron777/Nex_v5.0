"""Synergizer loop after the quiet-trigger retirement (repair queue 2026-10-05 item 3).

Hermetic: no DB. The loop must still fire on its 25-min timer (respecting the
5-min cooldown) and must no longer read sense_events at all.
"""
from __future__ import annotations

import unittest
from unittest import mock

from tests import _bootstrap  # noqa: F401


class _Stop:
    """stop.wait() advances the fake clock by 60 s; stops after n ticks."""
    def __init__(self, clock, ticks):
        self.clock, self.left = clock, ticks

    def wait(self, secs):
        self.clock[0] += secs
        self.left -= 1

    def is_set(self):
        return self.left <= 0


class TestSynergizerQuietRetired(unittest.TestCase):
    def _run(self, minutes):
        from theory_x.stage3_world_model import _synergizer_loop
        clock = [1_000_000.0]
        sense = mock.Mock()
        state = mock.Mock()
        state.readers = {"sense": sense}
        state.synergizer.synthesize.return_value = None
        state._synergizer_runs = 0
        with mock.patch("theory_x.stage3_world_model.time.time", side_effect=lambda: clock[0]):
            _synergizer_loop(state, _Stop(clock, minutes))
        return state, sense

    def test_timer_fires_every_25_minutes(self):
        state, _ = self._run(minutes=60)
        # first tick fires (last_timer_fire=0), then every 25 min: t=1, 26, 51
        self.assertEqual(state.synergizer.synthesize.call_count, 3)

    def test_no_sense_events_read(self):
        _, sense = self._run(minutes=60)
        sense.read.assert_not_called()

    def test_quiet_constants_gone(self):
        import theory_x.stage3_world_model as wm
        self.assertFalse(hasattr(wm, "SYNERGIZER_QUIET_EVENTS"))
        self.assertFalse(hasattr(wm, "SYNERGIZER_QUIET_THRESHOLD"))
        self.assertEqual(wm.SYNERGIZER_INTERVAL, 25 * 60)


if __name__ == "__main__":
    unittest.main()
