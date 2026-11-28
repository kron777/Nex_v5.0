"""Cooperative shutdown regressions for DriveEmergence's clustering tick."""
import os
import threading
import time
from unittest.mock import MagicMock, patch

import numpy as np

from theory_x.stage_drives.drive_emergence import DriveEmergence


def _node(candidates=None):
    conversations_reader = MagicMock()
    conversations_reader.read_one.return_value = None
    beliefs_reader = MagicMock()
    beliefs_reader.read.return_value = candidates or []
    return DriveEmergence(
        conversations_writer=MagicMock(),
        conversations_reader=conversations_reader,
        beliefs_reader=beliefs_reader,
    )


def _candidates():
    now = time.time()
    return [
        {"id": i, "content": f"distinct candidate thought {i}", "confidence": 0.8,
         "branch_id": f"branch-{i}", "use_count": 5, "created_at": now - 60}
        for i in range(1, 5)
    ]


def test_drive_emergence_stops_after_blocked_embedding():
    started = threading.Event()
    release = threading.Event()
    stop = threading.Event()
    node = _node(_candidates())

    def blocked_embed(_belief_id, _content):
        started.set()
        release.wait(timeout=3.0)
        return np.array([1.0, 0.0], dtype=np.float32)

    with patch.dict(os.environ, {"NEX5_DRIVE_CONTENT": "0"}), patch(
        "theory_x.diversity.embeddings.embed_belief", side_effect=blocked_embed
    ) as embed:
        thread = threading.Thread(
            target=node._background_tick,
            kwargs={"stop_event": stop},
        )
        thread.start()
        assert started.wait(timeout=2.0)
        stop.set()
        release.set()
        thread.join(timeout=2.0)

    assert not thread.is_alive()
    embed.assert_called_once()
    node._cw.write.assert_not_called()


def test_drive_emergence_stops_after_optional_voice_df_stage():
    stop = threading.Event()
    node = _node(_candidates())
    started = threading.Event()
    release = threading.Event()

    def blocked_df(*_args, **_kwargs):
        started.set()
        release.wait(timeout=3.0)
        return None, 0

    node._own_voice_df = blocked_df
    with patch.dict(os.environ, {"NEX5_DRIVE_CONTENT": "1"}), patch(
        "theory_x.diversity.embeddings.embed_belief"
    ) as embed:
        thread = threading.Thread(
            target=node._background_tick,
            kwargs={"stop_event": stop},
        )
        thread.start()
        assert started.wait(timeout=2.0)
        stop.set()
        release.set()
        thread.join(timeout=2.0)

    assert not thread.is_alive()
    embed.assert_not_called()
    node._cw.write.assert_not_called()


def test_drive_emergence_skips_drive_persistence_if_stop_arrives_after_observability_write():
    stop = threading.Event()
    candidates = _candidates()
    node = _node(candidates)
    calls = []

    def write_then_stop(*_args, **_kwargs):
        calls.append(1)
        stop.set()
        return len(calls)

    node._cw.write.side_effect = write_then_stop
    embeddings = {c["id"]: np.array([1.0, 0.0], dtype=np.float32) for c in candidates}

    with patch.dict(os.environ, {"NEX5_DRIVE_CONTENT": "0"}), patch(
        "theory_x.diversity.embeddings.embed_belief",
        side_effect=lambda belief_id, _content: embeddings[belief_id],
    ), patch(
        "theory_x.stage_drives.drive_emergence._cluster",
        return_value=[candidates],
    ):
        node._background_tick(stop_event=stop)

    # The observability write already began; no subsequent drive-state write starts.
    assert node._cw.write.call_count == 1
    assert node._topic is None


def test_drive_emergence_does_not_start_when_already_stopped():
    stop = threading.Event()
    stop.set()
    node = _node(_candidates())
    # Constructor performs one startup state read; isolate the tick itself.
    node._cr.read_one.reset_mock()
    node._br.read.reset_mock()
    node._cw.write.reset_mock()

    node._background_tick(stop_event=stop)

    node._cr.read_one.assert_not_called()
    node._br.read.assert_not_called()
    node._cw.write.assert_not_called()
