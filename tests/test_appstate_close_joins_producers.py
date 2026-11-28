"""AppState.close() must quiesce its registered producer families before closing Writers.

Backlog G-84, step 2. Step 1 made close() stop and join the Stage 2 dynamic
loops. The additional registered producers -- World Model loops, Fountain,
HoldingZoneResolver, SignalLoop, DiversityLoop, ArcLoop, SpeechQueueConsumer,
ThrowNetMonitor, CounterfactualNode, PredictiveSubstrate, SelfMindView and
SenseScheduler adapters -- must also stop and join before Writers close.
Pinned here, on isolated temporary databases:

- every registered producer is asked to stop and is joined BEFORE any Writer closes,
  so each one's in-flight write lands;
- producers are signalled first and joined against ONE shared deadline, so
  several stuck producers cannot multiply the shutdown time;
- if any producer remains alive or its stop fails, no shared Writer is closed
  underneath it; the supervisor enforces the final hard deadline;
- build_world_model() keeps its loop threads, so they can be joined.

Fountain and HoldingZoneResolver are now included through explicit stop and
join handles. Scheduler adapter threads are also joined against the same
remaining deadline. Workers created only in run.py and not handed to AppState
(e.g. the decoder and several optional loops) remain outside this increment.
"""
from __future__ import annotations

import threading
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from tests import _bootstrap  # noqa: F401
from tests.test_fountain import _cleanup, _make_env, _mock_voice_client, _mock_dynamic_state


def _state(writers, readers, **producers):
    from gui.server import AppState
    from voice.llm import VoiceClient
    return AppState(writers=writers, readers=readers,
                    voice=VoiceClient(request_fn=lambda *a, **k: None), **producers)


class _Finisher:
    """Runs until its stop event is set, then completes one more write."""

    def __init__(self, writer, key, delay=0.2):
        self.event = threading.Event()
        self.writer, self.key, self.delay = writer, key, delay
        self.wrote = None
        self.thread = threading.Thread(target=self._run, name=f"fake_{key}", daemon=True)
        self.thread.start()

    def _run(self):
        while not self.event.wait(0.01):
            pass
        time.sleep(self.delay)
        try:
            self.writer.write(
                "INSERT INTO daemon_kv (key, value, updated_at) VALUES (?, 'done', ?)",
                (self.key, time.time()))
            self.wrote = True
        except Exception as exc:
            self.wrote = exc


class _LoopLike:
    """SignalLoop / DiversityLoop / ArcLoop shape: stop() + _thread."""

    def __init__(self, finisher):
        self._f, self._thread = finisher, finisher.thread

    def stop(self):
        self._f.event.set()


class _ConsumerLike(threading.Thread):
    """SpeechQueueConsumer shape: a Thread with stop()."""

    def __init__(self, writer, key):
        super().__init__(name=f"fake_{key}", daemon=True)
        self._stop_evt = threading.Event()
        self.writer, self.key, self.wrote = writer, key, None
        self.start()

    def stop(self):
        self._stop_evt.set()

    def run(self):
        while not self._stop_evt.wait(0.01):
            pass
        time.sleep(0.2)
        try:
            self.writer.write(
                "INSERT INTO daemon_kv (key, value, updated_at) VALUES (?, 'done', ?)",
                (self.key, time.time()))
            self.wrote = True
        except Exception as exc:
            self.wrote = exc


class TestAppStateCloseJoinsProducers(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _landed(self, key):
        row = self.readers["dynamic"].read_one(
            "SELECT value FROM daemon_kv WHERE key = ?", (key,))
        return row is not None and row["value"] == "done"

    def test_every_held_producer_finishes_before_writers_close(self):
        w = self.writers["dynamic"]
        wm = _Finisher(w, "world_model")
        sig, div, arc = (_Finisher(w, k) for k in ("signal_loop", "diversity_loop", "arc_loop"))
        throw_net, counterfactual, predictive, self_mind = (
            _Finisher(w, k) for k in (
                "throw_net_monitor", "counterfactual_node",
                "predictive_substrate", "self_mind_view",
            )
        )
        speech = _ConsumerLike(w, "speech_consumer")

        report = _state(self.writers, self.readers,
               world_model=SimpleNamespace(_stop=wm.event, _threads=[wm.thread]),
               signal_loop=_LoopLike(sig), diversity_loop=_LoopLike(div),
               arc_loop=_LoopLike(arc), speech_consumer=speech,
               throw_net_monitor=_LoopLike(throw_net),
               counterfactual_node=_LoopLike(counterfactual),
               predictive_substrate=_LoopLike(predictive),
               self_mind_view=_LoopLike(self_mind)).close()
        self.assertTrue(report["success"], report)

        for name, wrote in (("world_model", wm.wrote), ("signal_loop", sig.wrote),
                            ("diversity_loop", div.wrote), ("arc_loop", arc.wrote),
                            ("speech_consumer", speech.wrote),
                            ("throw_net_monitor", throw_net.wrote),
                            ("counterfactual_node", counterfactual.wrote),
                            ("predictive_substrate", predictive.wrote),
                            ("self_mind_view", self_mind.wrote)):
            with self.subTest(producer=name):
                self.assertIs(wrote, True, f"{name}'s in-flight write was lost: {wrote!r}")
                self.assertTrue(self._landed(name))

    def test_one_shared_deadline_for_all_producers(self):
        import gui.server as srv
        stuck = [threading.Thread(target=lambda: time.sleep(4), name=f"stuck_{i}", daemon=True)
                 for i in range(3)]
        for t in stuck:
            t.start()
        events = [threading.Event() for _ in stuck]
        recorded = []

        class StuckScheduler:
            def __init__(self):
                self.stopped = False
                self.join_timeout = None

            def shutdown(self):
                self.stopped = True

            def join(self, timeout=None):
                self.join_timeout = timeout
                return ["sense.stuck_adapter"]

        scheduler = StuckScheduler()
        with mock.patch.object(srv, "_PRODUCER_STOP_TIMEOUT_S", 0.5, create=True), \
             mock.patch.object(srv.error_channel, "record",
                               side_effect=lambda msg, **k: recorded.append(msg)):
            started = time.monotonic()
            report = _state(self.writers, self.readers,
                   scheduler=scheduler,
                   dynamic=SimpleNamespace(_stop=events[0], _threads=[stuck[0]]),
                   world_model=SimpleNamespace(_stop=events[1], _threads=[stuck[1]]),
                   signal_loop=SimpleNamespace(stop=events[2].set, _thread=stuck[2])).close()
            elapsed = time.monotonic() - started

        self.assertFalse(report["success"], report)
        self.assertTrue(report["producer_threads_alive"])
        self.assertTrue(all(e.is_set() for e in events))
        self.assertTrue(scheduler.stopped)
        self.assertEqual(scheduler.join_timeout, 0.0)
        self.assertLess(elapsed, 1.4, "budget was spent per producer, not shared")
        joined = " ".join(recorded)
        for i in range(3):
            self.assertIn(f"stuck_{i}", joined)
        self.assertIn("sense.stuck_adapter", joined)

    def test_a_failing_stop_does_not_skip_the_other_producers(self):
        def boom():
            raise RuntimeError("stop() exploded")
        w = self.writers["dynamic"]
        later = _Finisher(w, "after_the_bad_one")
        report = _state(self.writers, self.readers,
               signal_loop=SimpleNamespace(stop=boom, _thread=None),
               diversity_loop=_LoopLike(later)).close()
        self.assertFalse(report["success"], report)
        self.assertTrue(any("stop failed" in e for e in report["producer_errors"]))
        self.assertEqual(set(report["writer_close_skipped"]), set(self.writers))
        self.assertIs(later.wrote, True)
        self.assertTrue(self._landed("after_the_bad_one"))

    def test_fountain_and_resolver_are_stopped_and_joined(self):
        import theory_x.stage6_fountain as fountain_module
        from theory_x.stage6_fountain import build_fountain
        from theory_x.stage_gate.holding_zone import HoldingZone
        from theory_x.stage_gate.resolver import HoldingZoneResolver

        with mock.patch.object(
            fountain_module, "FOUNTAIN_CHECK_INTERVAL_SECONDS", 3600
        ):
            fountain = build_fountain(
                self.writers, self.readers,
                voice_client=_mock_voice_client(),
                dynamic_state=_mock_dynamic_state(),
            )
        zone = HoldingZone(self.writers["beliefs"], self.readers["beliefs"])
        resolver = HoldingZoneResolver(zone, beliefs_writer=self.writers["beliefs"])
        resolver.start_loop(interval_seconds=3600)

        state = _state(
            self.writers, self.readers, fountain=fountain, resolver=resolver
        )
        state.close()

        self.assertFalse(fountain._thread.is_alive())
        self.assertFalse(resolver._thread.is_alive())
        with self.assertRaises(Exception):
            self.writers["dynamic"].write("SELECT 1")
        with self.assertRaises(Exception):
            self.writers["beliefs"].write("SELECT 1")

    def test_fountain_finishes_inflight_write_before_writer_close(self):
        import theory_x.stage6_fountain as fountain_module
        from theory_x.stage6_fountain import build_fountain
        from theory_x.stage6_fountain.generator import FountainGenerator

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

        with mock.patch.object(FountainGenerator, "generate", new=in_flight_tick), \
             mock.patch.object(fountain_module, "FOUNTAIN_CHECK_INTERVAL_SECONDS", 0.01):
            fountain = build_fountain(
                self.writers, self.readers,
                voice_client=_mock_voice_client(),
                dynamic_state=_mock_dynamic_state(),
            )
            self.assertTrue(entered.wait(1.0), "Fountain did not enter its tick")

        state = _state(self.writers, self.readers, fountain=fountain)
        closer = threading.Thread(target=state.close, name="test_appstate_close")
        closer.start()
        self.assertTrue(fountain._stop.wait(1.0), "close did not request Fountain stop")
        self.assertTrue(closer.is_alive(), "close did not wait for the in-flight Fountain tick")
        release.set()
        closer.join(timeout=1.0)

        self.assertFalse(closer.is_alive(), "close exceeded its bounded join")
        self.assertTrue(wrote.is_set(), "in-flight Fountain write was not completed")
        self.assertTrue(self._landed("g84-fountain-final-tick"))
        self.assertFalse(fountain._thread.is_alive())

    def test_unstarted_or_missing_producers_are_skipped(self):
        never_started = SimpleNamespace(stop=lambda: None, _thread=None)
        speech = threading.Thread(target=lambda: None)          # never started
        speech.stop = lambda: None
        _state(self.writers, self.readers, signal_loop=never_started,
               speech_consumer=speech).close()
        with self.assertRaises(Exception):
            self.writers["dynamic"].write("SELECT 1")             # Writers closed


    def test_all_writers_share_one_remaining_shutdown_deadline(self):
        class RecordingWriter:
            def __init__(self, delay):
                self.delay = delay
                self.timeouts = []

            def close(self, timeout=10.0):
                self.timeouts.append(timeout)
                time.sleep(min(self.delay, timeout))

        first = RecordingWriter(0.03)
        second = RecordingWriter(0.03)
        deadline = time.monotonic() + 0.3
        report = _state({"first": first, "second": second}, {}).close(deadline=deadline)

        self.assertTrue(report["success"], report)
        self.assertEqual(len(first.timeouts), 1)
        self.assertEqual(len(second.timeouts), 1)
        self.assertGreater(first.timeouts[0], second.timeouts[0])
        self.assertLessEqual(first.timeouts[0], 0.3)
        self.assertLessEqual(second.timeouts[0], 0.3)

    def test_live_producer_prevents_all_writer_closure(self):
        import gui.server as srv

        writer = self.writers["dynamic"]
        finisher = _Finisher(writer, "late_producer", delay=0.2)
        original_close = writer.close
        with mock.patch.object(srv, "_PRODUCER_STOP_TIMEOUT_S", 0.05), \
             mock.patch.object(writer, "close", wraps=original_close) as close_spy:
            report = _state(
                self.writers, self.readers,
                signal_loop=_LoopLike(finisher),
            ).close()

        self.assertFalse(report["success"], report)
        self.assertIn("fake_late_producer", report["producer_threads_alive"])
        self.assertEqual(set(report["writer_close_skipped"]), set(self.writers))
        self.assertIn("dynamic", report["writer_threads_alive"])
        close_spy.assert_not_called()

        # The producer is still allowed to finish its in-flight logical write
        # while the shared Writer remains open; tearDown closes it afterwards.
        finisher.thread.join(timeout=1.0)
        self.assertFalse(finisher.thread.is_alive())
        self.assertIs(finisher.wrote, True)
        self.assertTrue(self._landed("late_producer"))

    def test_writer_timeout_is_returned_as_shutdown_failure(self):
        class TimeoutWriter:
            def __init__(self):
                self.timeout = None

            def close(self, timeout=10.0):
                self.timeout = timeout
                raise TimeoutError("simulated writer did not drain")

        writer = TimeoutWriter()
        report = _state({"slow": writer}, {}).close(
            deadline=time.monotonic() + 0.2
        )

        self.assertFalse(report["success"], report)
        self.assertEqual(len(report["writer_errors"]), 1)
        self.assertIn("slow", report["writer_errors"][0])
        self.assertGreaterEqual(writer.timeout, 0.0)



class TestWorldModelKeepsItsThreads(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_build_world_model_retains_joinable_threads(self):
        from theory_x.stage3_world_model import build_world_model
        wm = build_world_model(self.writers, self.readers)
        threads = getattr(wm, "_threads", None)
        self.assertTrue(threads, "build_world_model() does not keep its loop threads")
        self.assertEqual(
            sorted(t.name for t in threads),
            sorted(["world_model.decay", "world_model.harmonizer", "world_model.cross_domain",
                    "world_model.erosion", "world_model.synergizer",
                    "world_model.world_consolidation"]))
        self.assertTrue(all(t.ident is not None for t in threads))   # all were started
        wm._stop.set()
        for t in threads:
            t.join(5)
        self.assertFalse(any(t.is_alive() for t in threads))


if __name__ == "__main__":
    unittest.main()
