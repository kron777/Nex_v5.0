"""Shutdown regressions for the active diversity ecology stages."""
import threading
import time
from unittest.mock import MagicMock, patch

from theory_x.diversity.loop import DiversityLoop
from theory_x.diversity.dormancy import DormancyScanner
from theory_x.diversity.groove import GrooveSpotter
from theory_x.diversity.consolidation import ClockRunner
from theory_x.diversity.boost import apply_decay
from theory_x.diversity.evolver import GraderEvolver
from theory_x.harmonic.substrate_harmonic import SubstrateHarmonic


def test_diversity_loop_stops_between_ecology_components():
    stop = threading.Event()
    loop = object.__new__(DiversityLoop)
    loop._stop = stop
    loop.groove = MagicMock()
    loop.dormancy = MagicMock()
    loop.clock = MagicMock()
    loop.groove.detect_all.side_effect = lambda **_kwargs: stop.set()

    loop._run()

    loop.dormancy.scan_incremental.assert_not_called()
    loop.clock.tick.assert_not_called()


def test_dormancy_scanner_stops_after_average_gap_before_writes():
    stop = threading.Event()
    rows = [
        {"id": i, "created_at": time.time() - 100000, "last_referenced_at": None}
        for i in range(10)
    ]
    reader = MagicMock()
    reader.read.return_value = rows
    writer = MagicMock()
    scanner = DormancyScanner(writer, reader)

    def gap_then_stop():
        stop.set()
        return 1.0

    scanner._average_gap = gap_then_stop

    assert scanner.scan_incremental(stop_event=stop) == 0
    writer.write.assert_not_called()


def test_groove_centroid_stops_after_embedding_before_alert_write():
    stop = threading.Event()
    writer = MagicMock()
    spotter = GrooveSpotter(writer, MagicMock())
    current = [{"id": i, "content": f"current belief {i}"} for i in range(5)]
    previous = [{"id": i + 5, "content": f"previous belief {i}"} for i in range(5)]

    def embed_then_stop(_content):
        stop.set()
        return [1.0, 0.0]

    with patch(
        "theory_x.diversity.groove.embed", side_effect=embed_then_stop
    ):
        result = spotter._check_centroid_tightening(
            current, previous, stop_event=stop
        )

    assert result is None
    writer.write.assert_not_called()


def test_clock_runner_stops_before_medium_and_slow_clocks():
    stop = threading.Event()
    runner = ClockRunner({"beliefs": MagicMock()}, {"beliefs": MagicMock()})

    def fast_then_stop(*_args, **_kwargs):
        stop.set()
        return False

    runner._run_fast = MagicMock(side_effect=fast_then_stop)
    runner._run_medium = MagicMock()
    runner._run_slow = MagicMock()

    runner.tick(2000, stop_event=stop)

    runner._run_fast.assert_called_once()
    runner._run_medium.assert_not_called()
    runner._run_slow.assert_not_called()


def test_apply_decay_stops_between_boost_rows():
    stop = threading.Event()
    reader = MagicMock()
    reader.read.return_value = [
        {"belief_id": 1, "boost_value": 1.0, "boosted_at": time.time() - 86400,
         "decay_rate": 0.1},
        {"belief_id": 2, "boost_value": 1.0, "boosted_at": time.time() - 86400,
         "decay_rate": 0.1},
    ]
    writer = MagicMock()

    def write_then_stop(*_args, **_kwargs):
        stop.set()
        return 1

    writer.write.side_effect = write_then_stop
    removed = apply_decay(writer, reader, stop_event=stop)

    assert removed == 1
    writer.write.assert_called_once()


def test_grader_evolver_stops_between_retrospective_samples():
    stop = threading.Event()
    reader = MagicMock()
    reader.read.return_value = [
        {"belief_id": i, "input_distance": 0.2, "output_distance": 0.3,
         "rarity": 0.5, "grade": 0.4, "grader_version": 1}
        for i in range(10)
    ]
    writer = MagicMock()
    evolver = GraderEvolver(writer, reader)

    def retrospective_then_stop(_belief_id, **_kwargs):
        stop.set()
        return 0.5

    evolver._retrospective_value = MagicMock(side_effect=retrospective_then_stop)

    assert evolver.evolve(stop_event=stop) is None
    writer.write.assert_not_called()


def test_substrate_harmonic_stops_between_stream_reads():
    stop = threading.Event()
    writer = MagicMock()
    harmonic = SubstrateHarmonic(
        conversations_writer=writer,
        conversations_reader=MagicMock(),
        beliefs_reader=MagicMock(),
        dynamic_reader=MagicMock(),
    )

    def first_read_then_stop(_ts):
        stop.set()
        return {}

    harmonic._read_drives_current = first_read_then_stop
    harmonic._read_drive_conflict = MagicMock()

    harmonic.tick(stop_event=stop)

    writer.write.assert_not_called()
    harmonic._read_drive_conflict.assert_not_called()
