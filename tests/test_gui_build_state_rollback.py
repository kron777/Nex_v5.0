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

    def test_resolver_start_then_raise_is_recovered_by_parent_rollback(self):
        import os
        import tempfile
        from unittest import mock

        import gui.server as server
        import theory_x.stage_gate.coherence_gate as gate_module
        import theory_x.stage_gate.holding_zone as holding_module
        import theory_x.stage_gate.resolver as resolver_module
        import theory_x.stage_throw_net.trigger_detector as trigger_module

        original_thread_start = threading.Thread.start
        started_writers = []
        resolver_instances = []

        class TrackingWriter(server.Writer):
            def __init__(self, path, name=None):
                super().__init__(path, name=name)
                started_writers.append(self)

        class NoopGate:
            def __init__(self, **_kwargs):
                pass

        class NoopHoldingZone:
            def __init__(self, *_args, **_kwargs):
                pass

        class NoopTriggerDetector:
            def __init__(self, *_args, **_kwargs):
                pass

        original_resolver_start = resolver_module.HoldingZoneResolver.start_loop

        def capture_resolver_start(resolver, *args, **kwargs):
            resolver_instances.append(resolver)
            return original_resolver_start(resolver, *args, **kwargs)

        def start_then_fail_resolver(thread):
            original_thread_start(thread)
            if thread.name == "holding_zone_resolver":
                raise RuntimeError("injected resolver start-after-create failure")

        with tempfile.TemporaryDirectory() as tmp:
            paths = {
                name: os.path.join(tmp, f"{name}.db")
                for name in ("sense", "beliefs", "dynamic", "conversations")
            }
            with (
                mock.patch.object(server, "db_paths", return_value=paths),
                mock.patch.object(server, "Writer", TrackingWriter),
                mock.patch.object(gate_module, "CoherenceGate", NoopGate),
                mock.patch.object(holding_module, "HoldingZone", NoopHoldingZone),
                mock.patch.object(trigger_module, "TriggerDetector", NoopTriggerDetector),
                mock.patch.object(
                    resolver_module.HoldingZoneResolver,
                    "start_loop",
                    new=capture_resolver_start,
                ),
                mock.patch.object(
                    threading.Thread,
                    "start",
                    new=start_then_fail_resolver,
                ),
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "injected resolver start-after-create failure"
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

        self.assertEqual(len(resolver_instances), 1)
        resolver = resolver_instances[0]
        self.assertTrue(resolver._stop.is_set())
        self.assertIsNotNone(resolver._thread)
        self.assertFalse(resolver._thread.is_alive())
        self.assertEqual(len(started_writers), 4)
        self.assertTrue(all(writer._thread is None for writer in started_writers))

    def test_cleanup_errors_do_not_escape_rollback_helper(self):
        events = []

        class BrokenProducer:
            _stop = None
            _threads = ()

            def stop(self):
                raise KeyboardInterrupt("injected stop interruption")

        class BrokenWriter:
            def close(self, timeout=10.0):
                raise SystemExit("injected close interruption")

        _rollback_partial_app_state({
            "resolver": BrokenProducer(),
            "writers": {"broken": BrokenWriter()},
        })


if __name__ == "__main__":
    unittest.main()
