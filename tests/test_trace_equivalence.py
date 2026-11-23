"""Paired Chat replay: the Phase 0 trace overlay must be observational only.

This test runs the same deterministic Chat turn against two fresh substrates,
with tracing OFF and ON. It compares model request bytes, returned behaviour,
conversation persistence and per-table write counts. The only permitted
difference is the external JSONL trace artifact.
"""
from __future__ import annotations

import copy
import json
import time
from pathlib import Path

from tests import _bootstrap  # noqa: F401


def _run_chat_once(tmp_path: Path, *, trace_on: bool, monkeypatch, read_query_log):
    data_dir = tmp_path / "nex-data"
    data_dir.mkdir(parents=True)
    trace_path = tmp_path / "influence.jsonl"

    monkeypatch.setenv("NEX5_DATA_DIR", str(data_dir))
    monkeypatch.setenv("NEX5_ADMIN_HASH_FILE", str(data_dir / "admin.argon2"))
    monkeypatch.setenv("NEX5_TRACE_OVERLAY", "1" if trace_on else "0")
    if trace_on:
        monkeypatch.setenv("NEX5_TRACE_PATH", str(trace_path))
    else:
        monkeypatch.delenv("NEX5_TRACE_PATH", raising=False)

    from substrate.init_db import init_all
    from substrate import Reader, Writer, db_paths
    from voice.llm import VoiceClient
    from gui.server import AppState, create_app, _working_memory_by_session

    init_all()
    paths = db_paths()
    writers = {name: Writer(path, name=name) for name, path in paths.items()}
    readers = {name: Reader(path) for name, path in paths.items()}
    model_requests = []

    def deterministic_model(url, payload):
        model_requests.append(copy.deepcopy(payload))
        return {"choices": [{"message": {"content": "A deterministic reply."}}]}

    # Clear process-global per-session working memory between paired runs.
    _working_memory_by_session.clear()
    state = AppState(
        writers=writers,
        readers=readers,
        voice=VoiceClient(request_fn=deterministic_model),
        now_fn=lambda: 1_700_000_000,
    )
    # Use the same pre-existing session identity in both runs. This removes
    # UUID variation without changing the route's normal session behaviour.
    writers["conversations"].write(
        "INSERT INTO sessions (id, started_at, admin) VALUES (?, ?, ?)",
        ("phase0-equivalence-session", 1_700_000_000, 0),
    )
    try:
        client = create_app(state).test_client()
        with client.session_transaction() as session:
            session["chat_session_id"] = "phase0-equivalence-session"

        # Count actual SELECT/WITH statements issued through NEX Reader
        # connections during the Chat request. The callback is test-only and
        # observes SQL already executed; it does not alter query behaviour.
        read_query_log.clear()
        started = time.perf_counter()
        response = client.post(
            "/api/chat",
            json={"prompt": "Hello, NEX. Give me one observation."},
        )
        elapsed_seconds = time.perf_counter() - started
        request_read_queries = list(read_query_log)
        read_query_log.clear()
        assert response.status_code == 200, response.get_json()
        payload = response.get_json()

        messages = [
            tuple(row[key] for key in
                  ("role", "content", "register", "timestamp", "tool_used"))
            for row in readers["conversations"].read(
                "SELECT role, content, register, timestamp, tool_used "
                "FROM messages ORDER BY id"
            )
        ]
        sessions = [
            tuple(row[key] for key in ("id", "started_at", "admin"))
            for row in readers["conversations"].read(
                "SELECT id, started_at, admin FROM sessions ORDER BY id"
            )
        ]

        table_counts = {}
        database_snapshot = {}
        for db_name, reader in readers.items():
            tables = reader.read(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
            table_counts[db_name] = {}
            database_snapshot[db_name] = {}
            for table_row in tables:
                table_name = table_row["name"]
                table_counts[db_name][table_name] = reader.count(table_name)
                rows = reader.read(f'SELECT * FROM "{table_name}"')
                normalized = [
                    tuple((key, row[key]) for key in row.keys())
                    for row in rows
                ]
                database_snapshot[db_name][table_name] = sorted(
                    normalized, key=repr
                )

        trace_rows = []
        if trace_on:
            trace_rows = [
                json.loads(line)
                for line in trace_path.read_text(encoding="utf-8").splitlines()
            ]
        else:
            assert not trace_path.exists()

        return {
            "behaviour": {
                key: payload.get(key)
                for key in ("text", "register", "voice_ok", "deflection_fired")
            },
            "model_requests": model_requests,
            "messages": messages,
            "sessions": sessions,
            "table_counts": table_counts,
            "database_snapshot": database_snapshot,
            "trace_rows": trace_rows,
            "trace_path": trace_path,
            "read_queries": request_read_queries,
            "elapsed_seconds": elapsed_seconds,
        }
    finally:
        state.close()


def test_chat_trace_overlay_on_off_equivalence(tmp_path, monkeypatch, record_property):
    # SQLite's trace callback lets the fixture count reads on every Reader
    # connection without changing production code or adding queries.
    from substrate import Reader

    read_query_log = []
    original_reader_open = Reader._open

    def observed_reader_open(self):
        connection = original_reader_open(self)

        def observe_statement(statement):
            normalized = statement.lstrip().upper()
            if normalized.startswith(("SELECT", "WITH")):
                read_query_log.append(statement.strip())

        connection.set_trace_callback(observe_statement)
        return connection

    monkeypatch.setattr(Reader, "_open", observed_reader_open)
    # Keep both executions on the same controlled feature-flag baseline.
    for key in list(__import__("os").environ):
        if key.startswith("NEX5_") and key not in {
            "NEX5_DATA_DIR", "NEX5_ADMIN_HASH_FILE",
            "NEX5_TRACE_OVERLAY", "NEX5_TRACE_PATH",
        }:
            monkeypatch.delenv(key, raising=False)

    off = _run_chat_once(
        tmp_path / "off", trace_on=False, monkeypatch=monkeypatch,
        read_query_log=read_query_log,
    )
    on = _run_chat_once(
        tmp_path / "on", trace_on=True, monkeypatch=monkeypatch,
        read_query_log=read_query_log,
    )

    assert on["behaviour"] == off["behaviour"]
    assert on["model_requests"] == off["model_requests"]
    assert on["messages"] == off["messages"]
    assert on["sessions"] == off["sessions"]
    assert on["table_counts"] == off["table_counts"]
    # Compare complete contents of every non-internal table across all six
    # databases, not only selected conversation rows and aggregate counts.
    assert on["database_snapshot"] == off["database_snapshot"]

    # Exact SQL read sequence equality is stronger than comparing counts:
    # it catches extra reads as well as changed read ordering/path coverage.
    assert on["read_queries"] == off["read_queries"]
    record_property("chat_trace_off_read_query_count", len(off["read_queries"]))
    record_property("chat_trace_on_read_query_count", len(on["read_queries"]))
    record_property("chat_trace_off_elapsed_ms", round(off["elapsed_seconds"] * 1000, 3))
    record_property("chat_trace_on_elapsed_ms", round(on["elapsed_seconds"] * 1000, 3))
    record_property(
        "chat_trace_elapsed_delta_ms",
        round((on["elapsed_seconds"] - off["elapsed_seconds"]) * 1000, 3),
    )
    # One paired wall-clock sample is diagnostic only, not a latency pass/fail:
    # statistically meaningful latency claims require repeated controlled runs.

    # The trace is the sole allowed delta and contains metadata/digests only.
    assert on["trace_rows"]
    rows = on["trace_rows"]
    assert rows[0]["event_type"] == "trace_start"
    assert rows[-1]["event_type"] == "trace_end"
    assert {"input_arrival", "model_input", "model_output",
            "output_sanitized", "writer_delta"} <= {
                row["event_type"] for row in rows
            }
    assert len({row["record_id"] for row in rows}) == len(rows)
    assert len({row["trace_id"] for row in rows}) == 1
    seen = set()
    for row in rows:
        assert all(parent in seen for parent in row["parent_ids"])
        seen.add(row["record_id"])
        assert row["flag_state"] is True

    serialized = on["trace_path"].read_text(encoding="utf-8")
    assert "Hello, NEX. Give me one observation." not in serialized
    assert "A deterministic reply." not in serialized
