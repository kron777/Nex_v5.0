"""G-84 step 4: the remaining AppState-held loops stop and join before the Writers close.

Steps 1-3 quiesce the Stage 2 dynamic loops, the World Model, the managed
loops and the run.py-only producers. Five more producers AppState holds were
still left running while the Writers closed:

- the membrane's behavioural loop (writes beliefs) kept a stop Event but not
  its thread, so close() could not join it;
- NovelAssociation (beliefs), AffectState (conversations) and DriveEmergence
  (conversations) looped ``while True`` over ``time.sleep(interval)`` with no
  stop signal and no thread handle -- 1800 s, 300 s and 600 s by default;
- SocialPresence already had stop() and _thread but was not registered
  (run.py currently constructs none; the field is covered for when it does).

Pinned here, on isolated temporary databases and mocks:

- close() signals and joins each of them before any Writer closes, so an
  in-flight write lands;
- each converted loop's stop() interrupts its interval and the thread joins;
- build_membrane() keeps its behavioural thread.
"""
from __future__ import annotations

import threading
import time
import unittest
from types import SimpleNamespace
from unittest import mock
from unittest.mock import MagicMock

from tests import _bootstrap  # noqa: F401
from tests.test_appstate_close_joins_producers import _Finisher, _LoopLike, _state
from tests.test_fountain import _cleanup, _make_env

_MANAGED = ("novel_association", "affect_state", "drive_emergence", "social_presence")


class TestHeldLoopsQuiesced(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _landed(self, key):
        row = self.readers["dynamic"].read_one(
            "SELECT value FROM daemon_kv WHERE key = ?", (key,))
        return row is not None and row["value"] == "done"

    def test_each_held_loop_finishes_before_writers_close(self):
        w = self.writers["dynamic"]
        membrane = _Finisher(w, "membrane")
        finishers = {name: _Finisher(w, name) for name in _MANAGED}
        _state(self.writers, self.readers,
               membrane=SimpleNamespace(_stop=membrane.event, _threads=[membrane.thread]),
               **{name: _LoopLike(f) for name, f in finishers.items()}).close()
        for name, f in dict(finishers, membrane=membrane).items():
            with self.subTest(producer=name):
                self.assertIs(f.wrote, True, f"{name}'s in-flight write was lost: {f.wrote!r}")
                self.assertTrue(self._landed(name))
                self.assertFalse(f.thread.is_alive())


def _mocks():
    w, r = MagicMock(), MagicMock()
    r.read_one.return_value = None
    r.read.return_value = []
    return w, r


class TestConvertedLoopsStop(unittest.TestCase):
    """stop() interrupts the interval; the thread is kept and joinable."""

    def _assert_stops(self, loop, tick_name):
        ticks = []
        with mock.patch.object(type(loop), tick_name, lambda self, *a, **k: ticks.append(1)):
            loop.start_loop()
            thread = getattr(loop, "_thread", None)
            self.assertIsInstance(thread, threading.Thread,
                                  f"{type(loop).__name__} keeps no joinable thread")
            deadline = time.monotonic() + 2.0
            while tick_name == "_background_tick" and not ticks and time.monotonic() < deadline:
                time.sleep(0.01)
            started = time.monotonic()
            loop.stop()
            thread.join(2.0)
        self.assertFalse(thread.is_alive(), f"{type(loop).__name__}.stop() did not interrupt")
        self.assertLess(time.monotonic() - started, 2.0)
        return ticks

    def test_affect_state(self):
        from theory_x.stage_affect.affect_state import AffectState
        cw, cr = _mocks()
        _, br = _mocks()
        loop = AffectState(cw, cr, br, tick_interval_s=3600)
        self.assertEqual(self._assert_stops(loop, "_background_tick"), [1])

    def test_drive_emergence(self):
        from theory_x.stage_drives.drive_emergence import DriveEmergence
        cw, cr = _mocks()
        _, br = _mocks()
        loop = DriveEmergence(cw, cr, br, tick_interval_s=3600)
        self.assertEqual(self._assert_stops(loop, "_background_tick"), [1])

    def test_novel_association(self):
        from theory_x.stage10_imagination.novel_association import NovelAssociation
        bw, br = _mocks()
        loop = NovelAssociation(bw, br)
        # Its loop waits first (1800 s), so stop() must cut the very first wait.
        self.assertEqual(self._assert_stops(loop, "tick"), [])

    def test_stop_before_start_is_harmless(self):
        from theory_x.stage_affect.affect_state import AffectState
        from theory_x.stage_drives.drive_emergence import DriveEmergence
        from theory_x.stage10_imagination.novel_association import NovelAssociation
        cw, cr = _mocks()
        for loop in (AffectState(cw, cr, cr), DriveEmergence(cw, cr, cr), NovelAssociation(cw, cr)):
            with self.subTest(loop=type(loop).__name__):
                loop.stop()
                self.assertIsNone(getattr(loop, "_thread", None))


class TestRunPyHandsThemToAppState(unittest.TestCase):
    """Boot wiring: run.py publishes each started loop to AppState, so close() sees it."""

    def test_runpy_registers_each_loop_with_appstate(self):
        import ast
        from pathlib import Path
        tree = ast.parse((Path(__file__).resolve().parents[1] / "run.py").read_text())
        fields = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "AppState":
                fields |= {k.arg for k in node.keywords if k.arg}
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (isinstance(target, ast.Attribute)
                            and isinstance(target.value, ast.Name)
                            and target.value.id == "state"):
                        fields.add(target.attr)
        for name in ("membrane", "novel_association", "affect_state", "drive_emergence"):
            with self.subTest(producer=name):
                self.assertIn(name, fields, f"run.py never registers {name} with AppState")


class TestMembraneKeepsItsThread(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_build_membrane_retains_joinable_behavioural_thread(self):
        from theory_x.stage4_membrane import build_membrane
        membrane = build_membrane(self.writers, self.readers)
        threads = getattr(membrane, "_threads", None)
        self.assertTrue(threads, "build_membrane() does not keep its behavioural thread")
        self.assertEqual([t.name for t in threads], ["membrane.behavioural"])
        membrane._stop.set()
        threads[0].join(2.0)
        self.assertFalse(threads[0].is_alive())


if __name__ == "__main__":
    unittest.main()
