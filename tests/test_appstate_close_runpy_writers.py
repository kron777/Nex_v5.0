"""G-84 step 4b: run.py's remaining Writer producers are handed to AppState and quiesced.

run.py starts six more background producers that write through the shared
Writers but were never handed to AppState, so close() could close a Writer
under them. Three of them run under flags the launch line sets
(NEX5_WARRANT_RECORD, NEX5_PERSONA_RESPONDER, NEX5_SELF_MAINTAIN_SHADOW):

- SubstrateHarmonic and GeniusTagger (conversations) already had
  stop_loop() + _thread;
- WarrantRecorder (beliefs) and CompetingDrives (conversations) slept with
  time.sleep and kept no thread;
- PersonaResponderLoop (dynamic, sense, conversations) had stop() but slept
  its full interval (600 s by default) and kept no thread;
- SelfMaintainShadow (dynamic) waited on its stop Event but kept no thread,
  and run.py discarded the instance.

Pinned here, on isolated temporary databases and mocks:

- close() signals and joins each one before any Writer closes;
- each converted loop's stop() interrupts its wait and the thread joins;
- run.py hands all six to AppState.
"""
from __future__ import annotations

import ast
import os
import threading
import time
import unittest
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock

from tests import _bootstrap  # noqa: F401
from tests.test_appstate_close_joins_producers import _Finisher, _state
from tests.test_fountain import _cleanup, _make_env

_FIELDS = {
    "substrate_harmonic": "stop_loop",
    "genius_tagger": "stop_loop",
    "warrant_recorder": "stop",
    "competing_drives": "stop",
    "persona_responder": "stop",
    "self_maintain_shadow": "stop",
}


def _worker(finisher, stop_name):
    w = MagicMock(spec=[stop_name, "_thread"])
    setattr(w, stop_name, finisher.event.set)
    w._thread = finisher.thread
    return w


class TestRunPyWritersQuiesced(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_each_producer_finishes_before_writers_close(self):
        w = self.writers["dynamic"]
        finishers = {name: _Finisher(w, name) for name in _FIELDS}
        _state(self.writers, self.readers,
               **{name: _worker(f, _FIELDS[name]) for name, f in finishers.items()}).close()
        for name, f in finishers.items():
            with self.subTest(producer=name):
                self.assertIs(f.wrote, True, f"{name}'s in-flight write was lost: {f.wrote!r}")
                row = self.readers["dynamic"].read_one(
                    "SELECT value FROM daemon_kv WHERE key = ?", (name,))
                self.assertEqual(row["value"] if row else None, "done")


def _mocks():
    w, r = MagicMock(), MagicMock()
    r.read_one.return_value = None
    r.read.return_value = []
    return w, r


class TestConvertedLoopsStop(unittest.TestCase):
    def _assert_stops(self, loop, expect_tick, tick_name):
        ticks = []
        with mock.patch.object(type(loop), tick_name, lambda self, *a, **k: ticks.append(1)):
            loop.start_loop()
            thread = getattr(loop, "_thread", None)
            self.assertIsInstance(thread, threading.Thread,
                                  f"{type(loop).__name__} keeps no joinable thread")
            deadline = time.monotonic() + 2.0
            while expect_tick and not ticks and time.monotonic() < deadline:
                time.sleep(0.01)
            started = time.monotonic()
            loop.stop()
            thread.join(2.0)
        self.assertFalse(thread.is_alive(), f"{type(loop).__name__}.stop() did not interrupt")
        self.assertLess(time.monotonic() - started, 2.0)
        self.assertEqual(len(ticks), 1 if expect_tick else 0)

    def test_warrant_recorder_first_delay_is_interruptible(self):
        from theory_x.stage_warrant.recorder import WarrantRecorder
        w, r = _mocks()
        loop = WarrantRecorder(w, r, r, first_delay_s=3600)
        with mock.patch.dict(os.environ, {"NEX5_WARRANT_RECORD": "1"}):
            self._assert_stops(loop, False, "use_cycle")

    def test_warrant_recorder_interval_is_interruptible(self):
        from theory_x.stage_warrant.recorder import WarrantRecorder
        w, r = _mocks()
        loop = WarrantRecorder(w, r, r, first_delay_s=0, use_interval_s=3600,
                               survival_interval_s=3600)
        with mock.patch.object(WarrantRecorder, "survival_cycle", lambda self, t: 0), \
             mock.patch.dict(os.environ, {"NEX5_WARRANT_RECORD": "1"}):
            self._assert_stops(loop, True, "use_cycle")

    def test_competing_drives(self):
        from theory_x.stage_drives.competing_drives import CompetingDrives
        w, r = _mocks()
        loop = CompetingDrives(w, r, r, tick_interval_s=3600)
        self._assert_stops(loop, True, "_tick_once")

    def test_persona_responder(self):
        from theory_x.stage_tom.persona_responder import PersonaResponderLoop
        loop = PersonaResponderLoop(interval=3600)
        self._assert_stops(loop, True, "tick")

    def test_self_maintain_shadow_keeps_its_thread(self):
        from theory_x.stage_self_maintain.shadow import SelfMaintainShadow
        w, r = _mocks()
        loop = SelfMaintainShadow(w, r, r, r)
        self._assert_stops(loop, False, "tick")   # first wait is 600 s


class TestRunPyHandsThemToAppState(unittest.TestCase):
    def test_runpy_registers_each_producer_with_appstate(self):
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
        for name in _FIELDS:
            with self.subTest(producer=name):
                self.assertIn(name, fields, f"run.py never registers {name} with AppState")


if __name__ == "__main__":
    unittest.main()
