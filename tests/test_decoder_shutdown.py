"""Shutdown tests for the transactional coincidence decoder."""
import sqlite3
import threading
import time
from unittest.mock import MagicMock, patch

from substrate import Row
from theory_x.coincidence import decoder_loop


class _TxWriter:
    def __init__(self, connection):
        self.connection = connection

    def transaction(self, callback):
        try:
            result = callback(self.connection)
            self.connection.commit()
            return result
        except Exception:
            self.connection.rollback()
            raise


class _SenseReader:
    def __init__(self, callback=None):
        self.callback = callback

    def read_one(self, *_args, **_kwargs):
        return self.callback() if self.callback else None


def _database():
    cx = sqlite3.connect(":memory:")
    cx.row_factory = Row
    cx.executescript("""
        CREATE TABLE daemon_kv (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE fountain_events (
            id INTEGER PRIMARY KEY, ts REAL, thought TEXT, hot_branch TEXT, tag TEXT
        );
        CREATE TABLE tree_snapshots (
            ts REAL, membrane_aperture REAL, active_branch_count INTEGER
        );
        CREATE TABLE surprise_events (triggered_at REAL, surprise_flag INTEGER);
        CREATE TABLE identity_log (composed_at REAL);
        CREATE TABLE pattern_log (composed_at REAL);
        CREATE TABLE witness_log (composed_at REAL);
        CREATE TABLE stillness_log (ts REAL);
        CREATE TABLE word_contexts (
            word TEXT, fountain_event_id INTEGER, ts REAL, aperture REAL,
            hot_branch TEXT, surprises_30min INTEGER, daemons_5min INTEGER,
            belief_delta_1h INTEGER, fountain_tag TEXT, hour_of_day INTEGER,
            day_of_week INTEGER, seconds_since_feed REAL,
            seconds_since_daemon REAL, active_branch_count INTEGER,
            groove_active REAL
        );
    """)
    now = time.time()
    cx.executemany(
        "INSERT INTO fountain_events (id, ts, thought, hot_branch, tag) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            (1, now - 20, "Quiet river remembers silver moon", "quiet", "a"),
            (2, now - 10, "Bright stone carries patient light", "bright", "b"),
        ],
    )
    cx.commit()
    return cx


def test_decoder_returns_without_opening_transaction_when_already_stopped():
    stop = threading.Event()
    stop.set()
    writer = MagicMock()
    result = decoder_loop.decoder_tick(
        dynamic_writer=writer, sense_reader=_SenseReader(), stop_event=stop
    )
    assert result == {"processed": 0, "words": 0}
    writer.transaction.assert_not_called()


def test_decoder_stops_after_feed_read_before_word_inserts_or_cursor_advance():
    cx = _database()
    stop = threading.Event()

    def feed_read_stops():
        stop.set()
        return None

    result = decoder_loop.decoder_tick(
        dynamic_writer=_TxWriter(cx),
        sense_reader=_SenseReader(feed_read_stops),
        stop_event=stop,
    )

    assert result == {"processed": 0, "words": 0}
    assert cx.execute("SELECT COUNT(*) FROM word_contexts").fetchone()[0] == 0
    assert cx.execute("SELECT COUNT(*) FROM daemon_kv").fetchone()[0] == 0
    cx.close()


def test_decoder_finishes_current_fire_row_then_stops_before_next_row():
    cx = _database()
    stop = threading.Event()
    original = decoder_loop._set_last_fid

    def set_cursor_then_stop(connection, fid):
        original(connection, fid)
        if fid == 1:
            stop.set()

    with patch(
        "theory_x.coincidence.decoder_loop._set_last_fid",
        side_effect=set_cursor_then_stop,
    ):
        result = decoder_loop.decoder_tick(
            dynamic_writer=_TxWriter(cx),
            sense_reader=_SenseReader(),
            stop_event=stop,
        )

    assert result["processed"] == 1
    assert result["words"] > 0
    rows = cx.execute(
        "SELECT DISTINCT fountain_event_id FROM word_contexts ORDER BY fountain_event_id"
    ).fetchall()
    assert [r[0] for r in rows] == [1]
    cursor = cx.execute(
        "SELECT value FROM daemon_kv WHERE key=?", (decoder_loop.KV_KEY,)
    ).fetchone()
    assert cursor[0] == "1"
    cx.close()
