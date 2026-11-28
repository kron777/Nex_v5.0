"""Stage-4 membrane behavioural worker shutdown regression."""
import threading
from unittest.mock import MagicMock

from theory_x.stage4_membrane.behavioural_self_model import BehaviouralSelfModel


def test_behavioural_model_does_not_write_after_stop_during_comparison():
    stop = threading.Event()
    model = BehaviouralSelfModel(MagicMock())
    writer = MagicMock()
    reader = MagicMock()

    def compare(*, stop_event=None):
        stop.set()
        return [{
            "divergence": "A test divergence",
            "metric": "hedge_rate",
            "value": 0.5,
        }]

    model.compare_to_seeds = compare
    written = model.write_behavioural_beliefs(
        writer, reader, stop_event=stop
    )

    assert written == 0
    writer.write.assert_not_called()
    reader.read_one.assert_not_called()
