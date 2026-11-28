"""Cooperative shutdown regressions for EdgeGeneratorLoop."""
import threading
from unittest.mock import MagicMock

from theory_x.stage3_world_model.edge_generator import EdgeGenerator


def test_edge_persistence_finishes_only_the_already_started_edge():
    writer = MagicMock()
    stop = threading.Event()

    def write_one(*_args, **_kwargs):
        stop.set()

    writer.write.side_effect = write_one
    generator = EdgeGenerator(writer, MagicMock())
    edges = [
        (2, "supports", 0.6),
        (3, "supports", 0.5),
        (4, "supports", 0.4),
    ]

    count = generator.persist_edges(1, edges, stop_event=stop)

    assert count == 1
    assert writer.write.call_count == 1


def test_edge_proposal_stops_between_candidates():
    reader = MagicMock()
    reader.read.side_effect = [
        [{"id": 1, "content": "A claim about careful shutdown.", "source": "x", "branch_id": "a"}],
        [
            {"id": 2, "content": "A claim about careful shutdown.", "source": "x", "branch_id": "a"},
            {"id": 3, "content": "Another unrelated idea about cognition.", "source": "y", "branch_id": "b"},
        ],
        [],
    ]
    writer = MagicMock()
    stop = threading.Event()
    generator = EdgeGenerator(writer, reader)

    from theory_x.stage3_world_model import edge_generator as module
    original = module._jaccard
    calls = []

    def stop_after_first(a, b):
        calls.append((a, b))
        stop.set()
        return original(a, b)

    module._jaccard = stop_after_first
    try:
        result = generator.propose_edges_for_belief(1, stop_event=stop)
    finally:
        module._jaccard = original

    assert result == []
    assert len(calls) == 1
    writer.write.assert_not_called()
