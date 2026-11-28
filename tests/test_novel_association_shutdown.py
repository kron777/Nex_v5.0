"""Cooperative shutdown tests for the NovelAssociation scan worker."""
import threading
import time
from unittest.mock import MagicMock, patch

from theory_x.stage10_imagination.novel_association import NovelAssociation


def _candidates():
    return [
        {"id": 1, "content": "first candidate", "branch_id": "alpha"},
        {"id": 2, "content": "second candidate", "branch_id": "beta"},
        {"id": 3, "content": "third candidate", "branch_id": "gamma"},
    ]


def test_novel_association_discards_embedding_result_after_stop():
    started = threading.Event()
    release = threading.Event()
    stop = threading.Event()
    worker = NovelAssociation(MagicMock(), MagicMock())
    worker._pull_candidates = MagicMock(return_value=_candidates())

    def blocked_embed(_belief_id, _content):
        started.set()
        release.wait(timeout=3.0)
        return [1.0, 0.0]

    import theory_x.diversity.embeddings as embeddings

    with patch.object(embeddings, "embed_belief", side_effect=blocked_embed) as embed:
        thread = threading.Thread(
            target=worker._scan,
            args=(time.time(),),
            kwargs={"stop_event": stop},
        )
        thread.start()
        assert started.wait(timeout=2.0)
        stop.set()
        release.set()
        thread.join(timeout=2.0)

    assert not thread.is_alive()
    embed.assert_called_once()
    worker._writer.write.assert_not_called()


def test_novel_association_does_not_start_scan_when_already_stopped():
    stop = threading.Event()
    stop.set()
    worker = NovelAssociation(MagicMock(), MagicMock())
    worker._scan = MagicMock(return_value=0)

    worker.tick(stop_event=stop)

    worker._scan.assert_not_called()


def test_novel_association_stops_before_next_pair_after_completed_pair():
    stop = threading.Event()
    worker = NovelAssociation(MagicMock(), MagicMock())
    worker._pull_candidates = MagicMock(return_value=_candidates())

    import theory_x.diversity.embeddings as embeddings

    def write_pair(*_args, **_kwargs):
        stop.set()

    worker._write_association = MagicMock(side_effect=write_pair)
    with patch.object(embeddings, "embed_belief", return_value=[1.0, 0.0]) as embed, patch.object(
        embeddings, "cosine", return_value=0.99
    ):
        worker._scan(time.time(), stop_event=stop)

    worker._write_association.assert_called_once()
    assert embed.call_count == 2
