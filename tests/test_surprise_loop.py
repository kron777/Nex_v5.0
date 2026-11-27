"""Regression tests for stable SurpriseLoop pagination and retry-safe checkpoints."""
import sqlite3
import time

from substrate import Reader, Writer


def _prepare_databases(tmp_path, initial_ts=100.0, initial_id=None):
    from theory_x.life import surprise_loop as loop

    dynamic_path = tmp_path / "dynamic.db"
    beliefs_path = tmp_path / "beliefs.db"
    with sqlite3.connect(dynamic_path) as db:
        db.execute(
            "CREATE TABLE surprise_events ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, triggered_at REAL NOT NULL, "
            "prediction_id INTEGER NOT NULL, prediction_type TEXT NOT NULL, "
            "surprise_score REAL NOT NULL, surprise_flag INTEGER NOT NULL, "
            "big_surprise INTEGER NOT NULL DEFAULT 0, predicted_content TEXT, "
            "actual_content TEXT, tags TEXT NOT NULL DEFAULT '[]')"
        )
        db.execute(
            "CREATE TABLE daemon_kv (key TEXT PRIMARY KEY, value TEXT, updated_at REAL)"
        )
        db.execute(
            "INSERT INTO daemon_kv (key, value, updated_at) VALUES (?, ?, 0)",
            (loop.LAST_PROMOTED_TS_KEY, str(initial_ts)),
        )
        if initial_id is not None:
            db.execute(
                "INSERT INTO daemon_kv (key, value, updated_at) VALUES (?, ?, 0)",
                (loop.LAST_PROMOTED_ID_KEY, str(initial_id)),
            )
    with sqlite3.connect(beliefs_path) as db:
        db.execute(
            "CREATE TABLE beliefs (content TEXT UNIQUE, tier INTEGER, confidence REAL, "
            "created_at INTEGER, source TEXT, branch_id TEXT, tags TEXT)"
        )

    handles = {
        "dynamic_reader": Reader(dynamic_path),
        "dynamic_writer": Writer(dynamic_path, name="surprise_dynamic_test"),
        "beliefs_writer": Writer(beliefs_path, name="surprise_beliefs_test"),
    }
    return loop, dynamic_path, beliefs_path, handles


def _insert_event(db_path, timestamp, index, *, big=False):
    with sqlite3.connect(db_path) as db:
        db.execute(
            "INSERT INTO surprise_events "
            "(triggered_at, prediction_id, prediction_type, surprise_score, "
            "surprise_flag, big_surprise, predicted_content, actual_content) "
            "VALUES (?, ?, 'external_input', 0.9, 1, ?, ?, ?)",
            (timestamp, index, int(big), f"prediction-{index}", f"actual-{index}"),
        )


def _tick(loop, handles):
    return loop.surprise_tick(**handles)


def _close(handles):
    handles["dynamic_writer"].close()
    handles["beliefs_writer"].close()


def test_first_run_promotes_only_events_from_last_ten_minutes(tmp_path):
    loop, dynamic_path, beliefs_path, handles = _prepare_databases(
        tmp_path, initial_ts=0.0
    )
    try:
        now = time.time()
        _insert_event(dynamic_path, now - 7200, 1)
        _insert_event(dynamic_path, now - 120, 2)

        assert _tick(loop, handles) == {"promoted": 1}

        with sqlite3.connect(beliefs_path) as db:
            rows = db.execute("SELECT content FROM beliefs").fetchall()
        assert len(rows) == 1
        assert "prediction-2" in rows[0][0]
        assert "prediction-1" not in rows[0][0]
    finally:
        _close(handles)


def test_equal_timestamp_events_continue_across_batches(tmp_path):
    loop, dynamic_path, beliefs_path, handles = _prepare_databases(tmp_path)
    try:
        for i in range(25):
            _insert_event(dynamic_path, 200.0, i)

        assert _tick(loop, handles) == {"promoted": 20}
        assert _tick(loop, handles) == {"promoted": 5}

        with sqlite3.connect(beliefs_path) as db:
            assert db.execute("SELECT COUNT(*) FROM beliefs").fetchone()[0] == 25
    finally:
        _close(handles)


def test_failed_event_is_retried_without_advancing_cursor(tmp_path, monkeypatch):
    loop, dynamic_path, beliefs_path, handles = _prepare_databases(tmp_path)
    try:
        _insert_event(dynamic_path, 200.0, 1)
        _insert_event(dynamic_path, 201.0, 2)

        original = loop._surprise_to_belief
        failed = {"once": False}

        def fail_once(row):
            if not failed["once"]:
                failed["once"] = True
                raise RuntimeError("transient conversion failure")
            return original(row)

        monkeypatch.setattr(loop, "_surprise_to_belief", fail_once)
        assert _tick(loop, handles) == {"promoted": 0}

        with sqlite3.connect(dynamic_path) as db:
            cursor = dict(db.execute("SELECT key, value FROM daemon_kv"))
            assert cursor[loop.LAST_PROMOTED_TS_KEY] == "100.0"
            assert cursor[loop.LAST_PROMOTED_ID_KEY] == "0"

        monkeypatch.setattr(loop, "_surprise_to_belief", original)
        assert _tick(loop, handles) == {"promoted": 2}
        with sqlite3.connect(beliefs_path) as db:
            assert db.execute("SELECT COUNT(*) FROM beliefs").fetchone()[0] == 2
    finally:
        _close(handles)


def test_failed_belief_write_is_retried_without_advancing_cursor(tmp_path, monkeypatch):
    loop, dynamic_path, beliefs_path, handles = _prepare_databases(tmp_path)
    try:
        _insert_event(dynamic_path, 200.0, 1)
        _insert_event(dynamic_path, 201.0, 2)
        writer = handles["beliefs_writer"]
        original_write = writer.write
        failed = {"once": False}

        def fail_once(sql, params=()):
            if sql.startswith("INSERT INTO beliefs") and not failed["once"]:
                failed["once"] = True
                raise RuntimeError("transient writer failure")
            return original_write(sql, params)

        monkeypatch.setattr(writer, "write", fail_once)
        assert _tick(loop, handles) == {"promoted": 0}
        with sqlite3.connect(dynamic_path) as db:
            cursor = dict(db.execute("SELECT key, value FROM daemon_kv"))
            assert cursor[loop.LAST_PROMOTED_TS_KEY] == "100.0"
            assert loop.LAST_PROMOTED_ID_KEY not in cursor

        monkeypatch.setattr(writer, "write", original_write)
        assert _tick(loop, handles) == {"promoted": 2}
        with sqlite3.connect(beliefs_path) as db:
            assert db.execute("SELECT COUNT(*) FROM beliefs").fetchone()[0] == 2
    finally:
        _close(handles)


def test_legacy_timestamp_cursor_replays_same_timestamp_safely(tmp_path):
    loop, dynamic_path, beliefs_path, handles = _prepare_databases(
        tmp_path, initial_ts=200.0
    )
    try:
        _insert_event(dynamic_path, 150.0, 0)  # historical row before legacy cutoff
        _insert_event(dynamic_path, 200.0, 1)
        _insert_event(dynamic_path, 200.0, 2)
        _insert_event(dynamic_path, 201.0, 3)

        assert _tick(loop, handles) == {"promoted": 3}
        with sqlite3.connect(beliefs_path) as db:
            assert db.execute("SELECT COUNT(*) FROM beliefs").fetchone()[0] == 3
    finally:
        _close(handles)


def test_non_big_surprise_has_one_surprise_tag():
    from theory_x.life.surprise_loop import _surprise_tags
    assert _surprise_tags(False) == ["surprise"]


def test_big_surprise_has_both_distinct_tags():
    from theory_x.life.surprise_loop import _surprise_tags
    tags = _surprise_tags(True)
    assert tags == ["surprise", "big_surprise"]
    assert len(tags) == len(set(tags))


def test_failure_after_success_checkpoints_only_last_handled_event(tmp_path, monkeypatch):
    loop, dynamic_path, beliefs_path, handles = _prepare_databases(tmp_path)
    try:
        _insert_event(dynamic_path, 200.0, 1)
        _insert_event(dynamic_path, 201.0, 2)
        _insert_event(dynamic_path, 202.0, 3)
        original = loop._surprise_to_belief
        failed = {"once": False}

        def fail_second_once(row):
            if row["id"] == 2 and not failed["once"]:
                failed["once"] = True
                raise RuntimeError("transient second-event failure")
            return original(row)

        monkeypatch.setattr(loop, "_surprise_to_belief", fail_second_once)
        assert _tick(loop, handles) == {"promoted": 1}
        with sqlite3.connect(dynamic_path) as db:
            cursor = dict(db.execute("SELECT key, value FROM daemon_kv"))
            assert cursor[loop.LAST_PROMOTED_TS_KEY] == "200.0"
            assert cursor[loop.LAST_PROMOTED_ID_KEY] == "1"

        monkeypatch.setattr(loop, "_surprise_to_belief", original)
        assert _tick(loop, handles) == {"promoted": 2}
        with sqlite3.connect(beliefs_path) as db:
            assert db.execute("SELECT COUNT(*) FROM beliefs").fetchone()[0] == 3
    finally:
        _close(handles)


def test_first_run_cutoff_is_persisted_when_no_rows_are_yet_eligible(tmp_path, monkeypatch):
    loop, dynamic_path, beliefs_path, handles = _prepare_databases(
        tmp_path, initial_ts=0.0
    )
    try:
        monkeypatch.setattr(loop.time, "time", lambda: 1000.0)
        assert _tick(loop, handles) == {"promoted": 0}
        with sqlite3.connect(dynamic_path) as db:
            cursor = dict(db.execute("SELECT key, value FROM daemon_kv"))
        assert cursor[loop.LAST_PROMOTED_TS_KEY] == "400.0"
        assert cursor[loop.LAST_PROMOTED_ID_KEY] == "0"

        # The event was created inside the original ten-minute window, but
        # becomes eligible only after the first tick. A sliding cutoff would
        # now exclude it; the persisted first-run boundary must still include it.
        _insert_event(dynamic_path, 500.0, 9)
        monkeypatch.setattr(loop.time, "time", lambda: 1300.0)
        assert _tick(loop, handles) == {"promoted": 1}
        with sqlite3.connect(beliefs_path) as db:
            assert db.execute("SELECT COUNT(*) FROM beliefs").fetchone()[0] == 1
    finally:
        _close(handles)


def test_duplicate_content_integrity_error_is_safe_to_checkpoint(tmp_path):
    loop, dynamic_path, beliefs_path, handles = _prepare_databases(tmp_path)
    try:
        _insert_event(dynamic_path, 200.0, 1)
        _insert_event(dynamic_path, 201.0, 2)
        with sqlite3.connect(dynamic_path) as db:
            db.execute(
                "UPDATE surprise_events SET predicted_content='same prediction', "
                "actual_content='same outcome' WHERE id IN (1, 2)"
            )
        assert _tick(loop, handles) == {"promoted": 1}
        with sqlite3.connect(dynamic_path) as db:
            cursor = dict(db.execute("SELECT key, value FROM daemon_kv"))
        assert cursor[loop.LAST_PROMOTED_ID_KEY] == "2"
        with sqlite3.connect(beliefs_path) as db:
            assert db.execute("SELECT COUNT(*) FROM beliefs").fetchone()[0] == 1
    finally:
        _close(handles)


def test_non_duplicate_integrity_error_is_not_checkpointed(tmp_path, monkeypatch):
    loop, dynamic_path, beliefs_path, handles = _prepare_databases(tmp_path)
    try:
        _insert_event(dynamic_path, 200.0, 1)
        writer = handles["beliefs_writer"]
        original_write = writer.write
        failed = {"once": False}

        def fail_once(sql, params=()):
            if sql.startswith("INSERT INTO beliefs") and not failed["once"]:
                failed["once"] = True
                raise sqlite3.IntegrityError("NOT NULL constraint failed: beliefs.content")
            return original_write(sql, params)

        monkeypatch.setattr(writer, "write", fail_once)
        assert _tick(loop, handles) == {"promoted": 0}
        with sqlite3.connect(dynamic_path) as db:
            cursor = dict(db.execute("SELECT key, value FROM daemon_kv"))
        assert cursor[loop.LAST_PROMOTED_ID_KEY] == "0"

        monkeypatch.setattr(writer, "write", original_write)
        assert _tick(loop, handles) == {"promoted": 1}
        with sqlite3.connect(beliefs_path) as db:
            assert db.execute("SELECT COUNT(*) FROM beliefs").fetchone()[0] == 1
    finally:
        _close(handles)
