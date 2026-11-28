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


if __name__ == "__main__":
    unittest.main()
