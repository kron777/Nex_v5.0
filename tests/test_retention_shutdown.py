"""Retention pruning stop-boundary regression."""
import threading
from unittest.mock import MagicMock

from theory_x.stage_gate.retention import _prune_table


def test_retention_finishes_current_delete_batch_then_stops():
    stop = threading.Event()
    reader = MagicMock()
    reader.read.return_value = [{"n": 500_000}]
    writer = MagicMock()
    writer.write.side_effect = lambda *_args, **_kwargs: stop.set()

    deleted = _prune_table(
        writer, reader, "gate_decisions", "ts", 21,
        batch_size=250_000, stop_event=stop,
    )

    assert deleted == 250_000
    assert reader.read.call_count == 1
    writer.write.assert_called_once()
