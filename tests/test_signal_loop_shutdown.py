"""SignalLoop stop-boundary regression."""
import threading
from unittest.mock import MagicMock, patch

from theory_x.signals.detectors import Signal
from theory_x.signals.loop import SignalLoop


def test_signal_loop_stops_after_detector_returns_before_persisting():
    writer = MagicMock()
    loop = SignalLoop(writer, MagicMock(), MagicMock())
    stop = threading.Event()
    entered = threading.Event()
    release = threading.Event()

    first = MagicMock()
    second = MagicMock()

    def blocked_detect(*, stop_event=None):
        entered.set()
        release.wait(timeout=3.0)
        return [Signal(
            detector_name="co_occurrence",
            signal_type="2_branch",
            payload={"entity": "Test"},
            branches=["a", "b"],
            entities=["Test"],
            confidence=0.7,
        )]

    first.detect.side_effect = blocked_detect
    loop._detectors = [first, second]
    loop._library = MagicMock()

    with patch("theory_x.signals.reaper.reap"):
        worker = threading.Thread(
            target=lambda: loop._tick(stop_event=stop),
            name="signal-loop-shutdown-test",
        )
        worker.start()
        assert entered.wait(timeout=2.0)
        stop.set()
        release.set()
        worker.join(timeout=2.0)

    assert not worker.is_alive()
    first.detect.assert_called_once_with(stop_event=stop)
    second.detect.assert_not_called()
    writer.write.assert_not_called()
    loop._library.match.assert_not_called()
