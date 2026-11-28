"""Stage-2 worker stop-boundary regressions."""
import threading
from collections import deque
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from theory_x.stage2_dynamic import _sense_distillation_loop, _sense_poll_loop
from theory_x.stage2_dynamic.crystallization import Crystallizer
from theory_x.stage2_dynamic.emergent_drives import EmergentDriveDetector


def test_sense_poll_finishes_current_pipeline_row_then_stops():
    stop = threading.Event()
    sense_reader = MagicMock()
    sense_reader.read.return_value = [
        {"id": 11, "stream": "external.news", "payload": "one", "provenance": None, "timestamp": 1},
        {"id": 12, "stream": "external.news", "payload": "two", "provenance": None, "timestamp": 2},
    ]
    dynamic_reader = MagicMock()
    dynamic_reader.read_one.return_value = None
    dynamic_writer = MagicMock()
    state = SimpleNamespace(
        readers={"sense": sense_reader, "dynamic": dynamic_reader},
        writers={"dynamic": dynamic_writer},
        tree=MagicMock(),
        membrane=MagicMock(),
        _pipeline_runs=0,
    )

    def process_one(*_args, **_kwargs):
        stop.set()
        return 1

    with patch("theory_x.stage2_dynamic.run_pipeline", side_effect=process_one) as pipeline:
        _sense_poll_loop(state, stop)

    pipeline.assert_called_once()
    assert state._pipeline_runs == 1
    cursor_write = dynamic_writer.write.call_args_list[-1]
    assert cursor_write.args[1] == ("last_sense_id", 11)


def test_sense_distillation_does_not_advance_cursor_past_interrupted_row():
    stop = threading.Event()
    sense_reader = MagicMock()
    sense_reader.read.return_value = [
        {"id": 21, "stream": "external.news", "payload": "headline", "timestamp": 100},
        {"id": 22, "stream": "external.news", "payload": "next headline", "timestamp": 101},
    ]
    dynamic_reader = MagicMock()
    dynamic_reader.read_one.return_value = {"value": "5"}
    dynamic_writer = MagicMock()
    beliefs_reader = MagicMock()

    def stop_after_duplicate_read(*_args, **_kwargs):
        stop.set()
        return None

    beliefs_reader.read_one.side_effect = stop_after_duplicate_read
    beliefs_writer = MagicMock()
    state = SimpleNamespace(
        readers={"sense": sense_reader, "dynamic": dynamic_reader, "beliefs": beliefs_reader},
        writers={"dynamic": dynamic_writer, "beliefs": beliefs_writer},
    )

    with patch(
        "theory_x.stage1_sense.title_extract.extract_sense_title",
        return_value="A distinct headline",
    ):
        _sense_distillation_loop(state, stop)

    beliefs_reader.read_one.assert_called_once()
    beliefs_writer.write.assert_not_called()
    cursor_write = dynamic_writer.write.call_args_list[-1]
    assert cursor_write.args[1] == ("last_distilled_sense_id", 5)


def test_crystallizer_stops_before_starting_next_branch():
    stop = threading.Event()
    now = 10_000.0
    nodes = [
        SimpleNamespace(branch_id="one", focus_increment='e'),
        SimpleNamespace(branch_id="two", focus_increment=HIGH_FOCUS_LEVELS[0]),
    ]
    crystallizer = Crystallizer.__new__(Crystallizer)
    crystallizer._tree = SimpleNamespace(all_nodes=lambda: nodes)
    crystallizer._focus_history = {
        node.branch_id: deque([(now - 1, HIGH_FOCUS_LEVELS[0])] * 100)
        for node in nodes
    }
    crystallizer._last_crystallized = {}

    def crystallize_one(*_args, **_kwargs):
        stop.set()
        return True

    with patch("theory_x.stage2_dynamic.crystallization.time.time", return_value=now):
        with patch.object(crystallizer, "_crystallize", side_effect=crystallize_one) as write:
            result = crystallizer.check_all(stop_event=stop)

    assert result == ["one"]
    write.assert_called_once()


def test_emergent_drive_scan_stops_after_blocked_belief_read():
    stop = threading.Event()
    reader = MagicMock()

    def read_and_stop(*_args, **_kwargs):
        stop.set()
        return [{"id": 1, "content": "a belief", "branch_id": "new", "confidence": 0.9}]

    reader.read.side_effect = read_and_stop
    state = MagicMock()
    detector = EmergentDriveDetector(MagicMock())

    proposals = detector.scan_for_pressure(reader, state, stop_event=stop)

    assert proposals == []
    state.status.assert_not_called()


def test_edge_builder_stops_embedding_pool_before_atomic_edge_batch():
    import theory_x.diversity.edge_builder as module

    stop = threading.Event()
    reader = MagicMock()
    reader.read.side_effect = [
        [{"id": 1, "content": "A sufficiently long source belief about global systems."}],
        [
            {"id": 1, "content": "A sufficiently long source belief about global systems."},
            {"id": 2, "content": "A sufficiently long target belief about global systems."},
        ],
    ]
    writer = MagicMock()

    def embed_and_stop(*_args, **_kwargs):
        stop.set()
        return [1.0, 0.0]

    with patch.object(module, "embed_belief", side_effect=embed_and_stop):
        result = module.edge_builder_tick(
            beliefs_reader=reader, beliefs_writer=writer, stop_event=stop
        )

    assert result["wrote"] == 0
    writer.write_many_with_counts.assert_not_called()
