"""Shutdown regressions for CompetingDrives input and persistence stages."""
import threading
from unittest.mock import MagicMock

from theory_x.stage_drives.competing_drives import CompetingDrives


def _drives():
    writer = MagicMock()
    conversations_reader = MagicMock()
    conversations_reader.read_one.return_value = None
    drives = CompetingDrives(
        conversations_writer=writer,
        conversations_reader=conversations_reader,
        beliefs_reader=MagicMock(),
        dynamic_reader=MagicMock(),
    )
    writer.reset_mock()
    conversations_reader.read_one.reset_mock()
    return drives


def _computed():
    weights = {
        "coherence": 0.2,
        "exploration": 0.2,
        "integration": 0.2,
        "self_preservation": 0.2,
        "curiosity": 0.2,
    }
    return weights, {"src_synergized": 0.1}, {
        "coherence": 0.2,
        "exploration": 0.2,
        "integration": 0.2,
        "self_preservation": 0.2,
        "curiosity": 0.2,
    }


def test_compute_weights_stops_between_input_readers():
    stop = threading.Event()
    drives = _drives()
    drives._source_ratios = MagicMock(side_effect=lambda: (stop.set() or {
        "synergized": 0.0, "sense": 0.0, "own_count": 0.0,
    }))
    drives._groove_severity = MagicMock()

    result = drives._compute_weights(stop_event=stop)

    assert result is None
    drives._groove_severity.assert_not_called()


def test_compute_now_stops_before_persistence_if_input_pass_observes_stop():
    stop = threading.Event()
    drives = _drives()

    def compute_then_stop(**_kwargs):
        stop.set()
        return _computed()

    drives._compute_weights = MagicMock(side_effect=compute_then_stop)

    result = drives.compute_now(stop_event=stop)

    assert result is None
    drives._cw.write.assert_not_called()


def test_compute_now_skips_per_fire_activation_if_stop_arrives_after_current_row():
    stop = threading.Event()
    drives = _drives()
    drives._compute_weights = MagicMock(return_value=_computed())

    def write_then_stop(*_args, **_kwargs):
        stop.set()
        return 1

    drives._cw.write.side_effect = write_then_stop

    result = drives.compute_now(stop_event=stop)

    assert result is None
    drives._cw.write.assert_called_once()
    drives._cr.read_one.assert_not_called()


def test_background_tick_does_not_write_if_stop_arrives_during_measurement():
    stop = threading.Event()
    drives = _drives()

    def compute_then_stop(**_kwargs):
        stop.set()
        return _computed()

    drives._compute_weights = MagicMock(side_effect=compute_then_stop)

    drives._tick_once(stop_event=stop)

    drives._cw.write.assert_not_called()
