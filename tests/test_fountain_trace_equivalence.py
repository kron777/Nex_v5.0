"""Paired FountainGenerator replay for the Phase 0 trace overlay.

This exercises the actual generator and crystallizer against fresh isolated
SQLite substrates. It does not start the daemon fountain_loop or the speech
consumer; scheduler/loop and asynchronous playback equivalence remain separate
proof obligations.
"""
from __future__ import annotations

import json
import random
import time
from pathlib import Path

from tests import _bootstrap  # noqa: F401


def _run_generator_once(
    tmp_path: Path, *, trace_on: bool, monkeypatch, read_query_log
):
    import os
    data_dir = tmp_path / "nex-data"
    data_dir.mkdir(parents=True)
    trace_path = tmp_path / "fountain.jsonl"

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

    from theory_x.stage6_fountain.generator import FountainGenerator
    from theory_x.stage6_fountain.crystallizer import FountainCrystallizer
    from substrate import trace_overlay

    init_all()
    paths = db_paths()
    writers = {name: Writer(path, name=name) for name, path in paths.items()}
    # init_db seeds undo_log_meta with SQLite julianday('now'), which is not
    # controlled by Python's time.time monkeypatch. Normalize the fixture seed
    # through the ordinary Writer so every other database field stays compared.
    writers["beliefs"].write(
        "UPDATE undo_log_meta SET installed_at=? WHERE id=1",
        (1_700_000_000.0,),
    )
    readers = {name: Reader(path) for name, path in paths.items()}
    model_requests = []

    def deterministic_model(url, payload):
        model_requests.append(json.loads(json.dumps(payload, sort_keys=True)))
        return {"choices": [{"message": {
            "content": "A small observation can change how a familiar pattern is understood."
        }}]}

    class DynamicState:
        def status(self):
            return {
                "branches": [{
                    "branch_id": "phase0-test",
                    "focus_increment": "f",
                    "focus_num": 0.8,
                }],
                "consolidation_active": True,
            }

    # Keep retrieval and any prompt-side random choices paired.
    random.seed(8675309)
    voice = VoiceClient(request_fn=deterministic_model)
    crystallizer = FountainCrystallizer(
        beliefs_writer=writers["beliefs"],
        beliefs_reader=readers["beliefs"],
        conversations_reader=readers.get("conversations"),
        dynamic_reader=readers["dynamic"],
        dynamic_writer=writers["dynamic"],
    )
    generator = FountainGenerator(
        sense_writer=writers["sense"],
        dynamic_writer=writers["dynamic"],
        voice_client=voice,
        dynamic_reader=readers["dynamic"],
        beliefs_writer=writers["beliefs"],
        beliefs_reader=readers["beliefs"],
        crystallizer=crystallizer,
        sense_reader=readers["sense"],
        conversations_reader=readers.get("conversations"),
    )

    handle = None
    if trace_on:
        handle = trace_overlay.begin_trace(
            "fountain_generator_replay",
            source_ref="tests/test_fountain_trace_equivalence.py::_run_generator_once",
            payload={"fixture": "deterministic_generator_replay"},
        )
        trace_overlay.record(
            "input_arrival",
            producer="phase0_test_harness",
            consumer="FountainGenerator.generate",
            source_ref="tests/test_fountain_trace_equivalence.py::_run_generator_once",
            outcome="controlled_generator_invocation",
        )

    try:
        read_query_log.clear()
        thought = generator.generate(DynamicState(), readers["beliefs"])
        request_read_queries = list(read_query_log)
        read_query_log.clear()
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
                # SQLite does not promise row order without ORDER BY. Compare
                # complete row content as a sorted multiset, retaining duplicates.
                normalized = [
                    tuple((key, row[key]) for key in row.keys())
                    for row in rows
                ]
                database_snapshot[db_name][table_name] = sorted(
                    normalized, key=repr
                )
        beliefs = [
            tuple(row[key] for key in ("content", "tier", "confidence", "source", "branch_id"))
            for row in readers["beliefs"].read(
                "SELECT content, tier, confidence, source, branch_id "
                "FROM beliefs ORDER BY id"
            )
        ]
        fires = [
            tuple(row[key] for key in ("thought", "readiness", "hot_branch", "word_count"))
            for row in readers["dynamic"].read(
                "SELECT thought, readiness, hot_branch, word_count "
                "FROM fountain_events ORDER BY id"
            )
        ]
        if handle is not None:
            trace_overlay.end_trace(
                handle,
                source_ref="tests/test_fountain_trace_equivalence.py::_run_generator_once",
                outcome="thought_returned" if thought else "no_fire",
                payload=thought,
            )
        trace_rows = (
            [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
            if trace_on else []
        )
        if not trace_on:
            assert not trace_path.exists()
        return {
            "thought": thought,
            "model_requests": model_requests,
            "table_counts": table_counts,
            "database_snapshot": database_snapshot,
            "read_queries": request_read_queries,
            "beliefs": beliefs,
            "fires": fires,
            "trace_rows": trace_rows,
            "trace_path": trace_path,
        }
    finally:
        if handle is not None:
            # end_trace normally restores the context; this is defensive if the
            # generator raises before the normal teardown above.
            trace_overlay.close_current_trace(
                source_ref="tests/test_fountain_trace_equivalence.py::_run_generator_once",
                outcome="test_exception_cleanup",
            )
        for writer in writers.values():
            writer.close()


def test_fountain_generator_trace_overlay_on_off_equivalence(
    tmp_path, monkeypatch, record_property
):
    # Freeze wall-clock reads so timestamp-bearing DB rows are directly
    # comparable across the paired OFF/ON substrates.
    monkeypatch.setattr(time, "time", lambda: 1_700_000_000.0)
    import os
    from substrate import Reader

    read_query_log = []
    original_reader_open = Reader._open

    def observed_reader_open(self):
        connection = original_reader_open(self)
        sqlite_rng = random.Random(8675309)
        connection.create_function(
            "random", 0, lambda: sqlite_rng.getrandbits(63)
        )

        def observe_statement(statement):
            normalized = statement.lstrip().upper()
            if normalized.startswith(("SELECT", "WITH")):
                read_query_log.append(statement.strip())

        connection.set_trace_callback(observe_statement)
        return connection

    monkeypatch.setattr(Reader, "_open", observed_reader_open)

    # Isolate this replay from the host's runtime flags. Only the trace overlay
    # may differ between the paired runs.
    for key in list(os.environ):
        if key.startswith("NEX5_") and key not in {
            "NEX5_DATA_DIR", "NEX5_ADMIN_HASH_FILE",
            "NEX5_TRACE_OVERLAY", "NEX5_TRACE_PATH",
        }:
            monkeypatch.delenv(key, raising=False)

    off = _run_generator_once(
        tmp_path / "off", trace_on=False, monkeypatch=monkeypatch,
        read_query_log=read_query_log,
    )
    on = _run_generator_once(
        tmp_path / "on", trace_on=True, monkeypatch=monkeypatch,
        read_query_log=read_query_log,
    )

    assert on["thought"] == off["thought"]
    assert on["model_requests"] == off["model_requests"]
    assert on["table_counts"] == off["table_counts"]
    assert on["database_snapshot"] == off["database_snapshot"]
    assert on["read_queries"] == off["read_queries"]
    record_property("fountain_trace_off_read_query_count", len(off["read_queries"]))
    record_property("fountain_trace_on_read_query_count", len(on["read_queries"]))
    assert on["beliefs"] == off["beliefs"]
    assert on["fires"] == off["fires"]

    rows = on["trace_rows"]
    assert rows
    assert rows[0]["event_type"] == "trace_start"
    assert rows[-1]["event_type"] == "trace_end"
    assert {"input_arrival", "candidate_generation", "writer_delta",
            "quality_gate"} <= {row["event_type"] for row in rows}
    assert len({row["record_id"] for row in rows}) == len(rows)
    assert len({row["trace_id"] for row in rows}) == 1
    seen = set()
    for row in rows:
        assert all(parent in seen for parent in row["parent_ids"])
        seen.add(row["record_id"])
        assert row["flag_state"] is True

    serialized = on["trace_path"].read_text(encoding="utf-8")
    assert "A small observation can change how a familiar pattern is understood." not in serialized
