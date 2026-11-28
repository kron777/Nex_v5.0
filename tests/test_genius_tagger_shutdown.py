"""Shutdown regressions for GeniusTagger's first-run backfill and live window."""
import threading
from pathlib import Path
from unittest.mock import MagicMock

from theory_x.genius.tagger import GeniusTagger


def _tagger():
    return GeniusTagger(
        conversations_writer=MagicMock(),
        conversations_reader=MagicMock(),
        dynamic_reader=MagicMock(),
        beliefs_reader=MagicMock(),
        weights_path=Path("/tmp/nex5-test-weights-unused.json"),
    )


def _fires():
    return [
        {"id": 1, "ts": 1.0, "thought": "first fire", "hot_branch": "alpha"},
        {"id": 2, "ts": 2.0, "thought": "second fire", "hot_branch": "beta"},
        {"id": 3, "ts": 3.0, "thought": "third fire", "hot_branch": "gamma"},
    ]


def test_backfill_discards_scored_fire_if_stop_arrives_during_scoring():
    started = threading.Event()
    release = threading.Event()
    stop = threading.Event()
    tagger = _tagger()
    tagger._load_weights = MagicMock(return_value={
        "version": "test-v1", "weights": [0.1] * 5, "bias": 0.0, "threshold": 0.5,
    })
    tagger._load_fires_window = MagicMock(return_value=_fires())
    tagger._existing_tag_ids = MagicMock(return_value=set())
    tagger._get_t6_beliefs = MagicMock(return_value=[])

    def blocked_score(*_args):
        started.set()
        release.wait(timeout=3.0)
        return 0.8, "STRIKING"

    tagger._score_fire = blocked_score
    tagger._write_tag = MagicMock()
    thread = threading.Thread(
        target=tagger.tick,
        kwargs={"stop_event": stop},
    )
    thread.start()
    assert started.wait(timeout=2.0)
    stop.set()
    release.set()
    thread.join(timeout=2.0)

    assert not thread.is_alive()
    tagger._write_tag.assert_not_called()
    assert tagger._backfill_done is False


def test_backfill_stops_between_fires_and_remains_resumable():
    stop = threading.Event()
    tagger = _tagger()
    tagger._load_fires_window = MagicMock(return_value=_fires())
    tagger._existing_tag_ids = MagicMock(return_value=set())
    tagger._get_t6_beliefs = MagicMock(return_value=[])
    tagger._score_fire = MagicMock(return_value=(0.8, "STRIKING"))

    def write_then_stop(*_args):
        stop.set()

    tagger._write_tag = MagicMock(side_effect=write_then_stop)

    completed = tagger._backfill(
        {"version": "test-v1"}, 10.0, stop_event=stop
    )

    assert completed is False
    tagger._write_tag.assert_called_once()


def test_already_stopped_tick_does_not_load_weights_or_start_backfill():
    stop = threading.Event()
    stop.set()
    tagger = _tagger()
    tagger._load_weights = MagicMock()
    tagger._backfill = MagicMock()

    tagger.tick(stop_event=stop)

    tagger._load_weights.assert_not_called()
    tagger._backfill.assert_not_called()


def test_continuous_tagging_stops_after_scoring_before_next_write():
    stop = threading.Event()
    tagger = _tagger()
    tagger._load_fires_window = MagicMock(return_value=_fires())
    tagger._existing_tag_ids = MagicMock(return_value=set())
    tagger._get_t6_beliefs = MagicMock(return_value=[])

    def score_then_stop(*_args):
        stop.set()
        return 0.8, "STRIKING"

    tagger._score_fire = MagicMock(side_effect=score_then_stop)
    tagger._write_tag = MagicMock()

    completed = tagger._tag_window(
        {"version": "test-v1"}, 10.0, 180.0, stop_event=stop
    )

    assert completed is False
    tagger._write_tag.assert_not_called()
