"""One-pen persistence tests for the scheduled DailyLife writers."""
from __future__ import annotations

from datetime import datetime

from nex_config import local_tz
from substrate import Reader, Writer, connect
from theory_x.life import daily_life
from theory_x.stage_tom import source_kind_audit
from theory_x.stage_world import expectations, learning_guards


def _daily_dbs(tmp_path):
    dynamic_path = tmp_path / "dynamic.db"
    beliefs_path = tmp_path / "beliefs.db"
    conversations_path = tmp_path / "conversations.db"
    sense_path = tmp_path / "sense.db"

    cx = connect(dynamic_path)
    cx.execute(
        "CREATE TABLE daily_activities (activity TEXT, date_local TEXT, fired_at REAL, details TEXT, "
        "PRIMARY KEY(activity, date_local))"
    )
    cx.execute("CREATE TABLE moltbook_posts (status TEXT, ts REAL)")
    cx.execute("CREATE TABLE current_focus (id INTEGER PRIMARY KEY, problem_id INTEGER)")
    cx.execute("CREATE TABLE fountain_events (thought TEXT, ts REAL)")
    cx.execute(
        "CREATE TABLE source_kind_audit_log (ts REAL, rows INTEGER, with_stream INTEGER, "
        "mismatches INTEGER, unstamped INTEGER, identity_claim_fires INTEGER, "
        "identity_support INTEGER, identity_violations INTEGER, ok INTEGER, detail TEXT)"
    )
    cx.commit()
    cx.close()

    cx = connect(beliefs_path)
    cx.execute("CREATE TABLE beliefs (id INTEGER PRIMARY KEY, created_at REAL)")
    cx.commit()
    cx.close()

    cx = connect(conversations_path)
    cx.execute(
        "CREATE TABLE open_problems (id INTEGER PRIMARY KEY, state TEXT, title TEXT, last_touched_at REAL)"
    )
    cx.execute(
        "INSERT INTO open_problems VALUES (1, 'open', 'Understand continuity', 100)"
    )
    cx.execute(
        "CREATE TABLE sessions (id TEXT PRIMARY KEY, started_at INTEGER, admin INTEGER, user_label TEXT)"
    )
    cx.execute(
        "CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, "
        "role TEXT, content TEXT, register TEXT, timestamp INTEGER)"
    )
    cx.execute(
        "CREATE TABLE expectation_canary_log (ts REAL, name TEXT, value REAL, n INTEGER, flag INTEGER, detail TEXT)"
    )
    cx.commit()
    cx.close()

    cx = connect(sense_path)
    cx.execute("CREATE TABLE sense_events (stream TEXT, payload TEXT, timestamp REAL)")
    cx.commit()
    cx.close()
    return dynamic_path, beliefs_path, conversations_path, sense_path


def test_daily_tick_uses_shared_dynamic_and_conversation_writers(tmp_path, monkeypatch):
    dynamic_path, beliefs_path, conversations_path, sense_path = _daily_dbs(tmp_path)
    readers = {
        "dynamic": Reader(dynamic_path),
        "beliefs": Reader(beliefs_path),
        "conversations": Reader(conversations_path),
        "sense": Reader(sense_path),
    }
    writers = {
        "dynamic": Writer(dynamic_path, name="daily-life-dynamic-test"),
        "conversations": Writer(conversations_path, name="daily-life-conversations-test"),
        "beliefs": Writer(beliefs_path, name="daily-life-beliefs-test"),
    }
    fixed_now = datetime(2026, 11, 27, 6, 0, tzinfo=local_tz())
    monkeypatch.setattr(daily_life, "_now_local", lambda: fixed_now)
    monkeypatch.setattr(daily_life, "SCHEDULE", {6: "morning"})
    try:
        result = daily_life.daily_tick(
            dynamic_reader=readers["dynamic"],
            dynamic_writer=writers["dynamic"],
            beliefs_reader=readers["beliefs"],
            conversations_reader=readers["conversations"],
            conversations_writer=writers["conversations"],
            beliefs_writer=writers["beliefs"],
            sense_reader=readers["sense"],
        )
        assert result["fired"] == ["morning"]
        fired = readers["dynamic"].read_one(
            "SELECT activity, date_local FROM daily_activities"
        )
        assert fired["activity"] == "morning"
        assert fired["date_local"] == "2026-11-27"
        message = readers["conversations"].read_one(
            "SELECT content, register FROM messages ORDER BY id DESC LIMIT 1"
        )
        assert message is not None
        assert message["register"] == "Morning"
        assert "Understand continuity" in message["content"]

        second = daily_life.daily_tick(
            dynamic_reader=readers["dynamic"],
            dynamic_writer=writers["dynamic"],
            beliefs_reader=readers["beliefs"],
            conversations_reader=readers["conversations"],
            conversations_writer=writers["conversations"],
            beliefs_writer=writers["beliefs"],
            sense_reader=readers["sense"],
        )
        assert second["fired"] == []
        assert readers["conversations"].read_one("SELECT COUNT(*) FROM messages")[0] == 1
    finally:
        writers["dynamic"].close()
        writers["conversations"].close()
        writers["beliefs"].close()


def test_source_kind_audit_uses_injected_dynamic_writer(tmp_path, monkeypatch):
    dynamic_path, _, _, _ = _daily_dbs(tmp_path)
    writer = Writer(dynamic_path, name="source-audit-test")
    monkeypatch.setattr(
        source_kind_audit, "audit",
        lambda: {
            "ok": True,
            "tier": {"rows": 3, "with_stream": 3, "mismatches": 0, "unstamped": 0,
                     "mismatch_ids": [], "unstamped_ids": []},
            "identity_floor": {"claim_fires": 1, "claim_support": 1,
                               "violations": 0, "violation_ids": []},
            "seeded": {"seeded_affinity_scored": 2, "retrievable": 2},
        },
    )
    try:
        assert source_kind_audit.run_and_record(dynamic_writer=writer).startswith("PASS")
        row = Reader(dynamic_path).read_one("SELECT rows, ok FROM source_kind_audit_log")
        assert row["rows"] == 3
        assert row["ok"] == 1
    finally:
        writer.close()


def test_expectation_canaries_uses_injected_conversations_writer(tmp_path, monkeypatch):
    _, _, conversations_path, _ = _daily_dbs(tmp_path)
    writer = Writer(conversations_path, name="expectation-canary-test")
    monkeypatch.setattr(
        expectations, "canaries",
        lambda now: [("confidence_drift", 0.1, 5, False, "within tolerance")],
    )
    try:
        result = expectations.record_canaries(123.0, conversations_writer=writer)
        assert "confidence_drift" in result
        row = Reader(conversations_path).read_one(
            "SELECT ts, name, value, n, flag, detail FROM expectation_canary_log"
        )
        assert row["ts"] == 123.0
        assert row["name"] == "confidence_drift"
        assert row["value"] == 0.1
        assert row["n"] == 5
        assert row["flag"] == 0
        assert row["detail"] == "within tolerance"
    finally:
        writer.close()


def test_reading_without_feed_preserves_resting_message(tmp_path):
    _, _, conversations_path, sense_path = _daily_dbs(tmp_path)
    conversations_reader = Reader(conversations_path)
    conversations_writer = Writer(conversations_path, name="daily-reading-test")
    try:
        msg = daily_life._activity_reading(
            "1",
            "2026-11-27",
            readers={"sense": Reader(sense_path)},
            writers={"conversations": conversations_writer},
        )
        assert msg == "reading session 1: nothing fresh in the feeds. resting instead."
        saved = conversations_reader.read_one(
            "SELECT content FROM messages ORDER BY id DESC LIMIT 1"
        )
        assert saved["content"] == msg
    finally:
        conversations_writer.close()


def test_journal_preserves_existing_language_and_state_fields(tmp_path, monkeypatch):
    _, _, conversations_path, _ = _daily_dbs(tmp_path)
    conversations_reader = Reader(conversations_path)
    conversations_writer = Writer(conversations_path, name="daily-journal-test")
    now = datetime(2026, 11, 27, 22, 0, tzinfo=local_tz())
    state = {
        "new_beliefs_24h": 3,
        "fountain_fires_24h": 12,
        "moltbook_posts_24h": 2,
        "open_problems": 4,
        "focus_problem_id": 1,
    }
    monkeypatch.setattr(daily_life, "_now_local", lambda: now)
    monkeypatch.setattr(daily_life, "_state_snapshot", lambda readers: state)
    try:
        msg = daily_life._activity_journal(
            "2026-11-27",
            readers={},
            writers={"conversations": conversations_writer},
        )
        expected = (
            "journal — Friday 27 November, 22:00.\n\n"
            "today i made 3 new beliefs, fired 12 thoughts, "
            "posted to moltbook 2 times.\n"
            "i hold 4 open problems. focus right now: problem #1.\n\n"
            "going quieter now. the night is for less."
        )
        assert msg == expected[:200]
        saved = conversations_reader.read_one(
            "SELECT content FROM messages ORDER BY id DESC LIMIT 1"
        )
        assert saved["content"] == expected
    finally:
        conversations_writer.close()


def test_expectation_canary_activity_passes_shared_learning_guard_writers(monkeypatch):
    conversations_writer = object()
    beliefs_writer = object()
    captured = {}

    def fake_run(**kwargs):
        captured.update(kwargs)
        return {"subtracted": 0}

    monkeypatch.setattr(learning_guards, "run", fake_run)
    monkeypatch.setattr(
        expectations, "record_canaries",
        lambda conversations_writer=None: "canaries recorded",
    )
    result = daily_life._activity_expectation_canaries(
        "2026-11-27",
        readers={},
        writers={
            "conversations": conversations_writer,
            "beliefs": beliefs_writer,
        },
    )
    assert result == "canaries recorded"
    assert captured == {
        "conversations_writer": conversations_writer,
        "beliefs_writer": beliefs_writer,
    }
