"""G-84 step 3: the run.py-only producers are registered and quiesced too.

Steps 1-2 quiesce every producer AppState holds. run.py also starts four
producers it never handed to AppState, so shutdown could close the Writers
under them: WorldPredictionLoop, SelfPredictionLoop, EdgeGeneratorLoop and the
coincidence decoder thread. SelfPredictionLoop could not be stopped promptly
at all -- its loop slept the full interval (900 s by default) and kept no
thread handle. Pinned here, on isolated temporary databases:

- AppState accepts these four producers and close() stops and joins each one
  before the Writers close, so an in-flight write lands;
- SelfPredictionLoop.stop() interrupts its interval and the thread is joinable;
- run.py actually registers all four (source check of the boot wiring).
"""
from __future__ import annotations

import ast
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from tests import _bootstrap  # noqa: F401
from tests.test_appstate_close_joins_producers import _Finisher, _LoopLike, _state
from tests.test_fountain import _cleanup, _make_env

_ROOT = Path(__file__).resolve().parents[1]
_RUNPY_FIELDS = ("world_pred_loop", "self_pred_loop", "edge_generator_loop", "decoder_loop")


class TestRunPyProducersQuiesced(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _landed(self, key):
        row = self.readers["dynamic"].read_one(
            "SELECT value FROM daemon_kv WHERE key = ?", (key,))
        return row is not None and row["value"] == "done"

    def test_each_runpy_producer_finishes_before_writers_close(self):
        w = self.writers["dynamic"]
        finishers = {name: _Finisher(w, name) for name in _RUNPY_FIELDS}
        _state(self.writers, self.readers,
               **{name: _LoopLike(f) for name, f in finishers.items()}).close()
        for name, f in finishers.items():
            with self.subTest(producer=name):
                self.assertIs(f.wrote, True, f"{name}'s in-flight write was lost: {f.wrote!r}")
                self.assertTrue(self._landed(name))
                self.assertFalse(f.thread.is_alive())


class TestSelfPredictionLoopStops(unittest.TestCase):
    def test_stop_interrupts_the_interval_and_thread_is_joinable(self):
        from theory_x.stage_world.self_prediction import SelfPredictionLoop
        ticks = []
        loop = SelfPredictionLoop(interval=3600)
        with mock.patch.object(SelfPredictionLoop, "tick", lambda self: ticks.append(1)):
            loop.start_loop()
            deadline = time.monotonic() + 2.0
            while not ticks and time.monotonic() < deadline:
                time.sleep(0.01)
            thread = getattr(loop, "_thread", None)
            self.assertIsInstance(thread, threading.Thread,
                                  "SelfPredictionLoop keeps no joinable thread")
            started = time.monotonic()
            loop.stop()
            thread.join(2.0)
        self.assertFalse(thread.is_alive(), "stop() did not interrupt the 3600 s interval")
        self.assertLess(time.monotonic() - started, 2.0)
        self.assertEqual(len(ticks), 1)


class TestRunPyRegistersProducers(unittest.TestCase):
    """Boot wiring: run.py hands every one of these producers to AppState."""

    def setUp(self):
        self.tree = ast.parse((_ROOT / "run.py").read_text())

    def test_appstate_call_and_decoder_registration(self):
        kwargs, assigned = set(), set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "AppState":
                kwargs |= {k.arg for k in node.keywords if k.arg}
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if (isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name)
                            and t.value.id == "state"):
                        assigned.add(t.attr)
        registered = kwargs | assigned
        for name in _RUNPY_FIELDS:
            with self.subTest(producer=name):
                self.assertIn(name, registered, f"run.py never registers {name} on AppState")


class TestRunPyGracefulShutdownOutcome(unittest.TestCase):
    def test_clean_marker_follows_successful_deadline_bounded_close(self):
        source = (_ROOT / "run.py").read_text()
        start = source.index("    def _graceful_standby(signum, frame):")
        end = source.index("    signal.signal(signal.SIGTERM, _graceful_standby)", start)
        handler = source[start:end]

        self.assertIn(
            "deadline = _time.monotonic() + _SHUTDOWN_TOTAL_BUDGET_S", handler
        )
        self.assertIn("nonlocal shutdown_started", handler)
        self.assertLess(
            handler.index("shutdown_started = True"),
            handler.index("shutdown_gate.begin_shutdown(deadline)"),
        )
        self.assertIn("request_report = shutdown_gate.begin_shutdown(deadline)", handler)
        self.assertLess(
            handler.index("shutdown_gate.begin_shutdown(deadline)"),
            handler.index("state.close(deadline=deadline)"),
        )
        self.assertIn("report = state.close(deadline=deadline)", handler)
        self.assertNotIn("_time.sleep(min(1.5", handler)
        self.assertIn('if not report.get("success", False):', handler)
        self.assertLess(
            handler.index("state.close(deadline=deadline)"),
            handler.index("mark_clean_shutdown"),
        )
        self.assertLess(
            handler.index("mark_clean_shutdown"),
            handler.index("os._exit(0)"),
        )
        self.assertIn("os._exit(1)", handler)
        self.assertIn("signal.signal(signal.SIGINT, _graceful_standby)", source)
        self.assertIn("create_app(state, shutdown_gate=shutdown_gate)", source)
        self.assertNotIn("mark_clean_shutdown", handler[:handler.index("state.close(deadline=deadline)")])



class TestRunPyEarlyBootOwnership(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_appstate_is_created_before_any_producer_start_path(self):
        main = next(
            node for node in ast.parse((_ROOT / "run.py").read_text()).body
            if isinstance(node, ast.FunctionDef) and node.name == "main"
        )
        state_line = min(
            node.lineno for node in ast.walk(main)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "AppState"
        )
        startup_names = {
            "build_scheduler", "build_dynamic", "build_world_model",
            "build_membrane", "build_fountain", "build_signal_loop",
            "_own_and_start",
        }
        starts = [
            node.lineno for node in ast.walk(main)
            if isinstance(node, ast.Call)
            and (
                (isinstance(node.func, ast.Name) and node.func.id in startup_names)
                or (isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"start", "start_loop"})
            )
        ]
        self.assertTrue(starts)
        self.assertLess(state_line, min(starts))

    def test_owner_is_published_before_start_and_failed_start_is_quiesced(self):
        from run import _own_and_start

        state = _state(self.writers, self.readers)

        class StartThenFail:
            def __init__(self):
                self.stop_event = threading.Event()
                self._thread = threading.Thread(
                    target=self.stop_event.wait, name="boot-start-then-fail", daemon=True
                )
                self.owner_seen_before_start = False

            def start_loop(self):
                self.owner_seen_before_start = state.resolver is self
                self._thread.start()
                raise RuntimeError("injected boot worker start failure")

            def stop_loop(self):
                self.stop_event.set()

        worker = StartThenFail()
        with self.assertRaisesRegex(RuntimeError, "injected boot worker start failure"):
            _own_and_start(state, "resolver", worker, "start_loop", "stop_loop")

        self.assertTrue(worker.owner_seen_before_start)
        self.assertIs(state.resolver, worker)
        self.assertFalse(worker._thread.is_alive())
        report = state.close()
        self.assertTrue(report["success"], report)
        self.assertFalse(worker._thread.is_alive())

    def test_boot_signal_during_start_rolls_back_before_exit(self):
        from run import _own_and_start

        state = _state(self.writers, self.readers)
        state._boot_shutdown_requested = threading.Event()

        class StartOnSignal:
            def __init__(self):
                self.stop_event = threading.Event()
                self._thread = threading.Thread(
                    target=self.stop_event.wait, name="boot-signal-during-start", daemon=True
                )

            def start_loop(self):
                self._thread.start()
                state._boot_shutdown_requested.set()

            def stop_loop(self):
                self.stop_event.set()

        worker = StartOnSignal()
        with self.assertRaises(SystemExit):
            _own_and_start(state, "resolver", worker, "start_loop", "stop_loop")

        self.assertIs(state.resolver, worker)
        self.assertFalse(worker._thread.is_alive())
        report = state.close()
        self.assertTrue(report["success"], report)


if __name__ == "__main__":
    unittest.main()
