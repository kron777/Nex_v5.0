"""Decoder daemon stop checkpoints preserve complete per-fire transactions."""
import threading
from unittest.mock import MagicMock, patch

import theory_x.coincidence.decoder_loop as decoder


class _Cursor:
    def __init__(self, rows=None, one=None):
        self.rows = rows or []
        self.one = one

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.one


class _Connection:
    def __init__(self, stop):
        self.stop = stop
        self.word_inserts = []
        self.last_fid = 0
        self.row_factory = None

    def execute(self, sql, params=()):
        if "SELECT value FROM daemon_kv" in sql:
            return _Cursor(one=(str(self.last_fid),))
        if "SELECT id, ts, thought, hot_branch, tag FROM fountain_events" in sql:
            return _Cursor(rows=[
                {"id": 1, "ts": 1_790_000_000.0, "thought": "quiet signal", "hot_branch": "a", "tag": "x"},
                {"id": 2, "ts": 1_790_000_030.0, "thought": "second signal", "hot_branch": "b", "tag": "y"},
            ])
        if "SELECT membrane_aperture" in sql:
            return _Cursor(one=None)
        if "SELECT COUNT(*), MAX(" in sql:
            return _Cursor(one=(0, None))
        if "SELECT COUNT(*)" in sql:
            return _Cursor(one=(0,))
        if "INSERT INTO word_contexts" in sql:
            self.word_inserts.append(params)
        if "INSERT INTO daemon_kv" in sql:
            self.last_fid = int(params[1])
            if self.last_fid == 1:
                self.stop.set()
        return _Cursor()


class _Writer:
    def __init__(self, cx):
        self.cx = cx

    def transaction(self, callback):
        return callback(self.cx)


def test_decoder_tick_finishes_current_fire_then_stops_before_next():
    stop = threading.Event()
    cx = _Connection(stop)
    sense = MagicMock()
    sense.read_one.return_value = None

    result = decoder.decoder_tick(
        dynamic_writer=_Writer(cx),
        sense_reader=sense,
        stop_event=stop,
    )

    assert result["processed"] == 1
    assert cx.last_fid == 1
    assert len(cx.word_inserts) == 2


def test_decoder_loop_passes_its_stop_event_to_tick():
    stop = threading.Event()
    state = MagicMock()

    def one_tick(**kwargs):
        assert kwargs["stop_event"] is stop
        stop.set()
        return {"processed": 0, "words": 0}

    with patch.object(decoder, "decoder_tick", side_effect=one_tick) as tick:
        with patch.object(stop, "wait", side_effect=[False, True]):
            decoder.decoder_loop(state, stop)

    tick.assert_called_once()
