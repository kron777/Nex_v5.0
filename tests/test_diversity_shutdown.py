"""Cooperative shutdown regressions for the always-on diversity worker."""
import threading
from unittest.mock import MagicMock, patch

import numpy as np

from theory_x.diversity.loop import DiversityLoop
from theory_x.diversity.groove import GrooveSpotter


def test_diversity_loop_does_not_start_next_stage_after_stop():
    loop = DiversityLoop.__new__(DiversityLoop)
    loop._stop = threading.Event()
    loop.groove = MagicMock()
    loop.dormancy = MagicMock()
    loop.clock = MagicMock()
    loop.groove.detect_all.side_effect = lambda **kwargs: loop._stop.set()

    loop._run()

    loop.groove.detect_all.assert_called_once_with(stop_event=loop._stop)
    loop.dormancy.scan_incremental.assert_not_called()
    loop.clock.tick.assert_not_called()


def test_groove_centroid_scan_stops_between_embedding_calls():
    writer = MagicMock()
    reader = MagicMock()
    spotter = GrooveSpotter(writer, reader)
    stop = threading.Event()
    current = [{"id": i, "content": f"current belief {i}"} for i in range(5)]
    previous = [{"id": i + 10, "content": f"previous belief {i}"} for i in range(5)]
    calls = []

    def embed_one(_text):
        calls.append(_text)
        stop.set()
        return np.asarray([1.0, 0.0])

    with patch("theory_x.diversity.groove.embed", side_effect=embed_one):
        result = spotter._check_centroid_tightening(
            current, previous, stop_event=stop
        )

    assert result is None
    assert len(calls) == 1
    writer.write.assert_not_called()


def test_grader_evolver_stops_after_blocked_grade_read():
    from theory_x.diversity.evolver import GraderEvolver

    reader = MagicMock()
    writer = MagicMock()
    entered = threading.Event()
    release = threading.Event()
    stop = threading.Event()

    def blocked_read(*_args, **_kwargs):
        entered.set()
        release.wait(timeout=3.0)
        return []

    reader.read.side_effect = blocked_read
    evolver = GraderEvolver(writer, reader)
    result = {}

    worker = threading.Thread(
        target=lambda: result.update(value=evolver.evolve(stop_event=stop)),
        name="grader-evolver-shutdown-test",
    )
    worker.start()
    assert entered.wait(timeout=2.0)
    stop.set()
    release.set()
    worker.join(timeout=2.0)

    assert not worker.is_alive()
    assert result["value"] is None
    assert reader.read.call_count == 1
    writer.write.assert_not_called()
