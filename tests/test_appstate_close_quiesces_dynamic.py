"""AppState.close() must quiesce the dynamic layer before closing Writers.

Backlog G-84 (first step). AppState.close() used to shut the scheduler and
close every Writer without stopping the Stage 2 dynamic loops, although
stop_dynamic() exists for exactly that. A loop mid-tick could then submit its
writes to a Writer that was already draining or closed, and lose them.

Pinned here, on isolated temporary databases:
- close() stops and joins the dynamic loops BEFORE any Writer closes, so a
  tick in progress completes its write;
- the wait is bounded: a loop that will not stop does not hold close() past
  the budget, and the Writers still close;
- AppState without a dynamic layer closes exactly as before.
"""
from __future__ import annotations

import threading
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from tests import _bootstrap  # noqa: F401
from tests.test_fountain import _cleanup, _make_env, _mock_voice_client, _mock_dynamic_state


def _state(writers, readers, dynamic=None):
    from gui.server import AppState
    from voice.llm import VoiceClient
    return AppState(writers=writers, readers=readers,
                    voice=VoiceClient(request_fn=lambda *a, **k: None),
                    dynamic=dynamic)


class _FinishingLoop:
    """A dynamic-layer loop that, once asked to stop, finishes the tick in
    progress -- one more write -- before it exits."""

    def __init__(self, writer, delay=0.3):
        self.stop = threading.Event()
        self.writer, self.delay = writer, delay
        self.wrote = None
        self.thread = threading.Thread(target=self._run, name="fake_dynamic_loop",
                                       daemon=True)

    def _run(self):
        while not self.stop.wait(0.01):
            pass
        time.sleep(self.delay)                      # the tick in progress
        try:
            self.writer.write(
                "INSERT INTO daemon_kv (key, value, updated_at) VALUES (?, ?, ?)",
                ("g84-final-tick", "done", time.time()))
            self.wrote = True
        except Exception as exc:                     # Writer already closed
            self.wrote = exc


class TestAppStateCloseQuiescesDynamic(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _final_tick_row(self):
        return self.readers["dynamic"].read_one(
            "SELECT value FROM daemon_kv WHERE key = 'g84-final-tick'")

    def test_tick_in_progress_completes_before_writers_close(self):
        loop = _FinishingLoop(self.writers["dynamic"])
        loop.thread.start()
        dynamic = SimpleNamespace(_stop=loop.stop, _threads=[loop.thread])

        _state(self.writers, self.readers, dynamic).close()

        self.assertTrue(loop.stop.is_set(), "close() never asked the dynamic loops to stop")
        self.assertFalse(loop.thread.is_alive(), "close() did not wait for the loop")
        self.assertIs(loop.wrote, True, f"final tick write was lost: {loop.wrote!r}")
        self.assertEqual(self._final_tick_row()["value"], "done")

    def test_wait_is_bounded_and_writers_still_close(self):
        import gui.server as srv
        stuck_stop = threading.Event()
        stuck = threading.Thread(target=lambda: time.sleep(5), name="stuck_loop",
                                 daemon=True)
        stuck.start()
        dynamic = SimpleNamespace(_stop=stuck_stop, _threads=[stuck])
        recorded = []
        with mock.patch.object(srv, "_DYNAMIC_STOP_TIMEOUT_S", 0.3, create=True), \
             mock.patch.object(srv.error_channel, "record",
                               side_effect=lambda msg, **k: recorded.append(msg)):
            started = time.monotonic()
            _state(self.writers, self.readers, dynamic).close()
            elapsed = time.monotonic() - started

        self.assertTrue(stuck_stop.is_set())
        self.assertLess(elapsed, 3.0)
        self.assertTrue(any("stuck_loop" in m for m in recorded), recorded)
        with self.assertRaises(Exception):              # Writers did close
            self.writers["dynamic"].write(
                "INSERT INTO daemon_kv (key, value, updated_at) VALUES ('late', 'x', 0)")


    def test_fountain_is_stopped_and_joined_before_writers_close(self):
        import theory_x.stage6_fountain as fountain_module
        from theory_x.stage6_fountain import build_fountain

        with mock.patch.object(
            fountain_module, "FOUNTAIN_CHECK_INTERVAL_SECONDS", 3600
        ):
            fountain = build_fountain(
                self.writers, self.readers,
                voice_client=_mock_voice_client(),
                dynamic_state=_mock_dynamic_state(),
            )
            time.sleep(0.05)
            self.assertTrue(fountain.status()["loop_running"])

            state = _state(self.writers, self.readers)
            state.fountain = fountain
            state.close()

        self.assertTrue(fountain.join(timeout=0))
        self.assertFalse(fountain.status()["loop_running"])
        with self.assertRaises(Exception):
            self.writers["dynamic"].write(
                "INSERT INTO daemon_kv (key, value, updated_at) VALUES ('late-fountain', 'x', 0)"
            )

    def test_fountain_finishes_inflight_write_before_writer_close(self):
        import theory_x.stage6_fountain as fountain_module
        from theory_x.stage6_fountain import build_fountain

        entered = threading.Event()
        release = threading.Event()
        wrote = threading.Event()

        def in_flight_tick(_generator, *_args, **_kwargs):
            entered.set()
            release.wait(2.0)
            self.writers["dynamic"].write(
                "INSERT INTO daemon_kv (key, value, updated_at) VALUES (?, ?, ?)",
                ("g84-fountain-final-tick", "done", time.time()),
            )
            wrote.set()
            return None

        from theory_x.stage6_fountain.generator import FountainGenerator
        with mock.patch.object(FountainGenerator, "generate", new=in_flight_tick), \
             mock.patch.object(fountain_module, "FOUNTAIN_CHECK_INTERVAL_SECONDS", 0.01):
            fountain = build_fountain(
                self.writers, self.readers,
                voice_client=_mock_voice_client(),
                dynamic_state=_mock_dynamic_state(),
            )
        self.assertTrue(entered.wait(1.0), "Fountain did not enter its tick")
        state = _state(self.writers, self.readers)
        state.fountain = fountain
        closer = threading.Thread(target=state.close, name="test_appstate_close")
        closer.start()
        time.sleep(0.05)
        self.assertTrue(closer.is_alive(), "close did not wait for the in-flight Fountain tick")
        self.assertTrue(fountain._stop.is_set(), "close did not request Fountain stop")
        release.set()
        closer.join(timeout=1.0)

        self.assertFalse(closer.is_alive(), "close exceeded its bounded join")
        self.assertTrue(wrote.is_set(), "in-flight Fountain write was not completed")
        row = self.readers["dynamic"].read_one(
            "SELECT value FROM daemon_kv WHERE key = 'g84-fountain-final-tick'"
        )
        self.assertEqual(row["value"], "done")
        self.assertFalse(fountain._thread.is_alive())

    def test_close_without_dynamic_is_unchanged(self):
        _state(self.writers, self.readers).close()
        with self.assertRaises(Exception):
            self.writers["beliefs"].write("SELECT 1")


if __name__ == "__main__":
    unittest.main()
