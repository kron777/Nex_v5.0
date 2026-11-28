"""Regression tests for gui.server.build_state partial-construction rollback."""
from __future__ import annotations

import threading
import unittest

from tests import _bootstrap  # noqa: F401
from gui.server import _rollback_partial_app_state


class _TrackedThread:
    def __init__(self, name, events):
        self.events = events
        self.release = threading.Event()
        self.thread = threading.Thread(
            target=self._run, name=name, daemon=True,
        )
        self.thread.start()

    def _run(self):
        self.release.wait(2.0)
        self.events.append(("worker-exit", self.thread.name))


class _Producer:
    def __init__(self, name, events):
        self.events = events
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._run, name=name, daemon=True,
        )
        self._thread.start()

    def _run(self):
        self._stop.wait(2.0)
        self.events.append(("worker-exit", self._thread.name))

    def stop(self):
        self.events.append(("stop", self._thread.name))
        self._stop.set()


class _Writer:
    def __init__(self, name, events):
        self.name = name
        self.events = events
        self.closed = False

    def close(self, timeout=10.0):
        self.events.append(("writer-close", self.name))
        self.closed = True


class _Scheduler:
    def __init__(self, events):
        self.events = events
        self._threads = {}
        self._workers = []
        for name in ("sense.one", "sense.two"):
            worker = _Producer(name, events)
            self._workers.append(worker)
            self._threads[name] = worker

    def shutdown(self):
        self.events.append(("scheduler-shutdown", None))
        for worker in self._workers:
            worker.stop()

    def join(self, timeout=None):
        self.events.append(("scheduler-join", None))
        alive = []
        for worker in self._workers:
            worker._thread.join(timeout=max(0.0, timeout or 0.0))
            if worker._thread.is_alive():
                alive.append(worker._thread.name)
        return alive


class TestBuildStateRollback(unittest.TestCase):
    def test_all_producers_are_signalled_and_joined_before_writer_close(self):
        events = []
        scheduler = _Scheduler(events)
        dynamic = _Producer("dynamic.worker", events)
        writer = _Writer("beliefs", events)

        _rollback_partial_app_state({
            "scheduler": scheduler,
            "dynamic": type("DynamicState", (), {
                "_stop": dynamic._stop,
                "_threads": [dynamic._thread],
            })(),
            "writers": {"beliefs": writer},
        })

        self.assertTrue(writer.closed)
        self.assertFalse(dynamic._thread.is_alive())
        self.assertTrue(all(not w._thread.is_alive() for w in scheduler._workers))
        close_index = next(i for i, event in enumerate(events)
                           if event[0] == "writer-close")
        exit_indexes = [i for i, event in enumerate(events)
                        if event[0] == "worker-exit"]
        self.assertTrue(exit_indexes)
        self.assertLess(max(exit_indexes), close_index)
        self.assertLess(
            next(i for i, event in enumerate(events)
                 if event[0] == "scheduler-shutdown"),
            next(i for i, event in enumerate(events)
                 if event[0] == "writer-close"),
        )

    def test_writer_decorator_is_unwrapped_and_closed_once(self):
        events = []
        inner = _Writer("beliefs", events)
        wrapper = type("WriterWrapper", (), {"_inner": inner})()
        _rollback_partial_app_state({"writers": {
            "beliefs": wrapper,
            "beliefs_alias": inner,
        }})
        self.assertTrue(inner.closed)
        self.assertEqual(
            [event for event in events if event[0] == "writer-close"],
            [("writer-close", "beliefs")],
        )


    def test_writer_construction_failure_closes_prior_writers_and_reraises_original(self):
        from unittest import mock
        import gui.server as server

        events = []
        created = []

        class PartialWriter:
            def __init__(self, path, name=None):
                if name == "second":
                    raise LookupError("injected second-writer failure")
                self.name = name
                created.append(self)

            def close(self, timeout=10.0):
                events.append(("writer-close", self.name))

        with mock.patch.object(server, "db_paths", return_value={
            "first": "/tmp/first.db",
            "second": "/tmp/second.db",
            "third": "/tmp/third.db",
        }), mock.patch.object(server, "Writer", PartialWriter):
            with self.assertRaisesRegex(
                LookupError, "injected second-writer failure"
            ):
                server.build_state(
                    with_scheduler=False,
                    with_dynamic=False,
                    with_world_model=False,
                    with_membrane=False,
                    with_fountain=False,
                    with_strikes=False,
                    with_tools=False,
                )

        self.assertEqual(len(created), 1)
        self.assertEqual(events, [("writer-close", "first")])

    def test_cleanup_errors_do_not_escape_rollback_helper(self):
        events = []

        class BrokenProducer:
            _stop = None
            _threads = ()

            def stop(self):
                raise RuntimeError("injected stop failure")

        class BrokenWriter:
            def close(self, timeout=10.0):
                raise RuntimeError("injected close failure")

        _rollback_partial_app_state({
            "resolver": BrokenProducer(),
            "writers": {"broken": BrokenWriter()},
        })


if __name__ == "__main__":
    unittest.main()
