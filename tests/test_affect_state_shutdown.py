"""Shutdown regressions for the AffectState background tick."""
import threading
from unittest.mock import MagicMock, patch

from theory_x.stage_affect.affect_state import AffectState


def _affect_state():
    conversations_reader = MagicMock()
    conversations_reader.read_one.return_value = None
    return AffectState(
        conversations_writer=MagicMock(),
        conversations_reader=conversations_reader,
        beliefs_reader=MagicMock(),
        dynamic_reader=None,
    )


def test_affect_state_discards_prepared_tick_when_stop_arrives_during_read():
    started = threading.Event()
    release = threading.Event()
    stop = threading.Event()
    affect = _affect_state()
    initial = affect.state()

    def blocked_valence():
        started.set()
        release.wait(timeout=3.0)
        return 0.4

    affect._compute_valence_delta = blocked_valence
    affect._compute_arousal_delta = MagicMock(return_value=0.2)

    thread = threading.Thread(
        target=affect._background_tick,
        kwargs={"stop_event": stop},
    )
    thread.start()
    assert started.wait(timeout=2.0)
    stop.set()
    release.set()
    thread.join(timeout=2.0)

    assert not thread.is_alive()
    affect._cw.write.assert_not_called()
    assert affect.state() == initial
    affect._compute_arousal_delta.assert_not_called()


def test_affect_state_discards_prepared_tick_if_stop_arrives_before_commit():
    stop = threading.Event()
    affect = _affect_state()
    initial = affect.state()
    affect._compute_valence_delta = MagicMock(return_value=0.2)
    affect._compute_arousal_delta = MagicMock(return_value=0.1)

    def stop_during_stability():
        stop.set()
        return 0.8

    affect._compute_stability = stop_during_stability

    affect._background_tick(stop_event=stop)

    affect._cw.write.assert_not_called()
    assert affect.state() == initial


def test_affect_state_finishes_current_persistence_unit_if_stop_arrives_mid_commit():
    stop = threading.Event()
    affect = _affect_state()
    affect._compute_valence_delta = MagicMock(return_value=0.2)
    affect._compute_arousal_delta = MagicMock(return_value=0.1)
    affect._compute_stability = MagicMock(return_value=0.7)
    calls = []

    def write_and_signal(*_args, **_kwargs):
        calls.append(1)
        if len(calls) == 1:
            stop.set()
        return len(calls)

    affect._cw.write.side_effect = write_and_signal

    with patch("theory_x.stage_world.expectations.mood_on", return_value=False):
        affect._background_tick(stop_event=stop)

    # The affect row and history row are one completed logical persistence unit.
    assert affect._cw.write.call_count == 2
    assert affect.state()["last_updated"] > 0


def test_affect_state_does_not_start_tick_when_already_stopped():
    stop = threading.Event()
    stop.set()
    affect = _affect_state()
    affect._compute_valence_delta = MagicMock()

    affect._background_tick(stop_event=stop)

    affect._compute_valence_delta.assert_not_called()
    affect._cw.write.assert_not_called()
