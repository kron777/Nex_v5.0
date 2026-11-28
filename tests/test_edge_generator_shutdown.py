"""Cooperative shutdown tests for the edge generator worker."""
import threading
from unittest.mock import MagicMock, patch

from theory_x.stage3_world_model.edge_generator import (
    EdgeGenerator,
    EdgeGeneratorLoop,
)


def test_edge_proposals_stop_after_source_read():
    stop = threading.Event()
    reader = MagicMock()
    reader.read.side_effect = lambda *_args, **_kwargs: (
        stop.set() or [{"id": 1, "content": "source thought", "source": "x", "branch_id": "a"}]
    )
    generator = EdgeGenerator(MagicMock(), reader)

    result = generator.propose_edges_for_belief(1, stop_event=stop)

    assert result == []
    reader.read.assert_called_once()


def test_edge_proposals_stop_during_candidate_scoring():
    stop = threading.Event()
    reader = MagicMock()
    reader.read.side_effect = [
        [{"id": 1, "content": "source thought", "source": "x", "branch_id": "a"}],
        [{"id": 2, "content": "candidate thought", "source": "x", "branch_id": "b"}],
        [],
    ]
    generator = EdgeGenerator(MagicMock(), reader)

    def score_then_stop(*_args):
        stop.set()
        return 0.6

    with patch(
        "theory_x.stage3_world_model.edge_generator._jaccard",
        side_effect=score_then_stop,
    ):
        result = generator.propose_edges_for_belief(1, stop_event=stop)

    assert result == []
    assert reader.read.call_count == 3


def test_persist_edges_finishes_opposition_audit_pair_then_stops():
    stop = threading.Event()
    writer = MagicMock()
    generator = EdgeGenerator(writer, MagicMock())

    def write_then_stop(*_args, **_kwargs):
        stop.set()
        return 1

    writer.write.side_effect = write_then_stop
    with patch("theory_x.stage3_world_model.edge_generator.log_undo") as log_undo:
        count = generator.persist_edges(
            1,
            [(2, "opposes", 0.8), (3, "supports", 0.5)],
            stop_event=stop,
        )

    assert count == 1
    writer.write.assert_called_once()
    log_undo.assert_called_once()


def test_edge_loop_stops_after_proposal_before_persistence():
    stop = threading.Event()
    writer = MagicMock()
    reader = MagicMock()
    reader.read.return_value = [{"id": 1}, {"id": 2}]
    loop = EdgeGeneratorLoop({"beliefs": writer}, {"beliefs": reader})

    def propose_then_stop(*_args, **_kwargs):
        stop.set()
        return [(2, "supports", 0.6)]

    loop._generator.propose_edges_for_belief = MagicMock(
        side_effect=propose_then_stop
    )
    loop._generator.persist_edges = MagicMock()

    loop._tick(stop_event=stop)

    loop._generator.propose_edges_for_belief.assert_called_once()
    loop._generator.persist_edges.assert_not_called()
