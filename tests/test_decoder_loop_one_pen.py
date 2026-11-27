"""One-pen persistence tests for the DecoderLoop."""
from __future__ import annotations

import time

from substrate import Reader, Writer, connect
from theory_x.coincidence import decoder_loop


def test_decoder_tick_uses_injected_dynamic_writer(tmp_path):
    dynamic_path = tmp_path / "dynamic.db"
    sense_path = tmp_path / "sense.db"
    now = time.time()

    cx = connect(dynamic_path)
    cx.execute(
        "CREATE TABLE fountain_events (id INTEGER PRIMARY KEY, ts REAL, thought TEXT, "
        "hot_branch TEXT, tag TEXT)"
    )
    cx.execute(
        "INSERT INTO fountain_events VALUES (1, ?, ?, 'attention', 'coin')",
        (now, "I notice patterns in memory and attention"),
    )
    cx.execute(
        "CREATE TABLE tree_snapshots (ts REAL, membrane_aperture REAL, active_branch_count INTEGER)"
    )
    cx.execute("INSERT INTO tree_snapshots VALUES (?, 0.55, 3)", (now-1,))
    cx.execute(
        "CREATE TABLE surprise_events (triggered_at REAL, surprise_flag INTEGER)"
    )
    cx.execute("INSERT INTO surprise_events VALUES (?, 1)", (now-10,))
    for table, column in [
        ("identity_log", "composed_at"),
        ("pattern_log", "composed_at"),
        ("witness_log", "composed_at"),
    ]:
        cx.execute(f"CREATE TABLE {table} ({column} REAL)")
        cx.execute(f"INSERT INTO {table} VALUES (?)", (now-30,))
    cx.execute("CREATE TABLE stillness_log (ts REAL)")
    cx.execute("CREATE TABLE daemon_kv (key TEXT PRIMARY KEY, value TEXT)")
    cx.execute(
        "CREATE TABLE word_contexts ("
        "word TEXT, fountain_event_id INTEGER, ts REAL, aperture REAL, hot_branch TEXT, "
        "surprises_30min INTEGER, daemons_5min INTEGER, belief_delta_1h INTEGER, "
        "fountain_tag TEXT, hour_of_day INTEGER, day_of_week INTEGER, "
        "seconds_since_feed REAL, seconds_since_daemon REAL, "
        "active_branch_count INTEGER, groove_active INTEGER)"
    )
    cx.commit()
    cx.close()

    cx = connect(sense_path)
    cx.execute("CREATE TABLE sense_events (timestamp REAL, stream TEXT)")
    cx.execute("INSERT INTO sense_events VALUES (?, 'feed.rss')", (now-5,))
    cx.commit()
    cx.close()

    d_reader = Reader(dynamic_path)
    s_reader = Reader(sense_path)
    d_writer = Writer(dynamic_path, name="decoder-test")
    try:
        result = decoder_loop.decoder_tick(
            dynamic_reader=d_reader, dynamic_writer=d_writer, sense_reader=s_reader
        )
        expected_words = len(decoder_loop._tokenize("I notice patterns in memory and attention"))
        assert result == {"processed": 1, "words": expected_words}
        rows = d_reader.read(
            "SELECT word, fountain_event_id, aperture, hot_branch, surprises_30min, "
            "daemons_5min, belief_delta_1h, fountain_tag, active_branch_count "
            "FROM word_contexts ORDER BY word"
        )
        assert len(rows) == expected_words
        assert all(row["fountain_event_id"] == 1 for row in rows)
        assert all(row["aperture"] == 0.55 for row in rows)
        assert all(row["hot_branch"] == "attention" for row in rows)
        assert all(row["surprises_30min"] == 1 for row in rows)
        assert all(row["daemons_5min"] == 3 for row in rows)
        assert all(row["belief_delta_1h"] == 1 for row in rows)
        assert all(row["fountain_tag"] == "coin" for row in rows)
        assert all(row["active_branch_count"] == 3 for row in rows)
        marker = d_reader.read_one("SELECT value FROM daemon_kv WHERE key=?", (decoder_loop.KV_KEY,))
        assert marker["value"] == "1"
        assert decoder_loop.decoder_tick(
            dynamic_reader=d_reader, dynamic_writer=d_writer, sense_reader=s_reader
        ) == {"processed": 0, "words": 0}
    finally:
        d_writer.close()
