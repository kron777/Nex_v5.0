"""Shutdown regressions for PredictiveSubstrate's embedding and write stages."""
import threading
import time
from unittest.mock import MagicMock, patch

import numpy as np

from theory_x.stage_prediction.predictive_substrate import PredictiveSubstrate


def _node():
    return PredictiveSubstrate(
        dynamic_reader=MagicMock(),
        dynamic_writer=MagicMock(),
        beliefs_reader=MagicMock(),
        conversations_reader=MagicMock(),
        sense_reader=MagicMock(),
    )


def test_internal_prediction_stops_after_blocked_embedding():
    started = threading.Event()
    release = threading.Event()
    stop = threading.Event()
    node = _node()
    node._br.read.return_value = [
        {"id": 1, "content": "belief one", "source_kind": "self", "confidence": 0.7},
        {"id": 2, "content": "belief two", "source_kind": "self", "confidence": 0.7},
        {"id": 3, "content": "belief three", "source_kind": "self", "confidence": 0.7},
    ]

    def blocked_embedding(_belief_id, _content):
        started.set()
        release.wait(timeout=3.0)
        return np.array([1.0, 0.0], dtype=np.float32)

    node._embed_belief = MagicMock(side_effect=blocked_embedding)
    result = {}
    thread = threading.Thread(
        target=lambda: result.update(
            value=node._predict_internal(stop_event=stop)
        )
    )
    thread.start()
    assert started.wait(timeout=2.0)
    stop.set()
    release.set()
    thread.join(timeout=2.0)

    assert not thread.is_alive()
    assert result["value"] == 0
    node._embed_belief.assert_called_once()
    node._cr.read.assert_not_called()
    node._dw.write.assert_not_called()


def test_verify_one_stops_after_blocked_embedding():
    started = threading.Event()
    release = threading.Event()
    stop = threading.Event()
    node = _node()
    node._br.read.return_value = [
        {"id": 10, "content": "a later belief"},
        {"id": 11, "content": "another later belief"},
    ]

    def blocked_embedding(_belief_id, _content):
        started.set()
        release.wait(timeout=3.0)
        return np.array([1.0, 0.0], dtype=np.float32)

    node._embed_belief = MagicMock(side_effect=blocked_embedding)
    prediction = {
        "id": 5,
        "prediction_type": "internal_belief",
        "centroid_embedding": np.array([1.0, 0.0], dtype=np.float32).tobytes(),
        "representative_content": "predicted content",
        "made_at": time.time() - 10,
        "target_window_end": time.time(),
    }
    result = {}
    thread = threading.Thread(
        target=lambda: result.update(
            value=node._verify_one(prediction, time.time(), stop_event=stop)
        )
    )
    thread.start()
    assert started.wait(timeout=2.0)
    stop.set()
    release.set()
    thread.join(timeout=2.0)

    assert not thread.is_alive()
    assert result["value"] is False
    node._embed_belief.assert_called_once()
    node._dw.write.assert_not_called()


def test_tick_does_not_start_prediction_stages_after_verify_observes_stop():
    stop = threading.Event()
    node = _node()

    def stop_after_verify(**_kwargs):
        stop.set()
        return 0

    node._verify = MagicMock(side_effect=stop_after_verify)
    node._predict_internal = MagicMock(return_value=0)
    node._predict_external = MagicMock(return_value=0)

    node.tick(stop_event=stop)

    node._predict_internal.assert_not_called()
    node._predict_external.assert_not_called()


def test_verify_finishes_event_and_prediction_update_pair_if_stop_arrives_mid_commit():
    stop = threading.Event()
    node = _node()
    node._br.read.return_value = []
    calls = []

    def write_and_signal(*_args, **_kwargs):
        calls.append(1)
        if len(calls) == 1:
            stop.set()
        return len(calls)

    node._dw.write.side_effect = write_and_signal
    prediction = {
        "id": 9,
        "prediction_type": "internal_belief",
        "centroid_embedding": np.array([1.0, 0.0], dtype=np.float32).tobytes(),
        "representative_content": "predicted content",
        "made_at": time.time() - 10,
        "target_window_end": time.time(),
    }

    with patch(
        "theory_x.stage_prediction.predictive_substrate._generate_tags",
        return_value=[],
    ):
        completed = node._verify_one(prediction, time.time(), stop_event=stop)

    assert completed is True
    assert node._dw.write.call_count == 2
