"""Phase 0 tests for explicit, fail-safe speech-consumer provenance.

These tests establish row-identity linkage and consumer event semantics. They do
not claim an atomic producer/consumer hand-off or physical audio audibility.
"""
import json
import sqlite3

import speech.queue_consumer as queue_consumer
from speech.config import SpeechConfig


class FakeWriter:
    def __init__(self, fail=None):
        self.calls = []
        self.fail = fail

    def write(self, sql, params=()):
        self.calls.append((sql, params))
        if self.fail is not None and self.fail(sql, params):
            raise RuntimeError("simulated status persistence failure")
        return len(self.calls)


class FakeReader:
    def read(self, sql, params=()):
        return []


class FakePlayer:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def play(self, audio, sample_rate):
        self.calls.append((audio, sample_rate))
        if self.fail:
            raise RuntimeError("audio device unavailable")


class FakeBackend:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    def synth(self, content, voice):
        self.calls.append((content, voice))
        if self.fail:
            raise RuntimeError("synthesis unavailable")
        return b"audio-bytes", 24000


def _enable_trace(monkeypatch, tmp_path):
    path = tmp_path / "speech-trace.jsonl"
    monkeypatch.setenv("NEX5_TRACE_OVERLAY", "1")
    monkeypatch.setenv("NEX5_TRACE_PATH", str(path))
    monkeypatch.setenv("NEX5_DATA_DIR", str(tmp_path / "nex-data"))
    return path


def _events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _consumer(monkeypatch, backend=None, writer=None):
    consumer = queue_consumer.SpeechQueueConsumer(
        writer=writer or FakeWriter(),
        reader=FakeReader(),
        config=SpeechConfig(enabled=True),
        backend=backend or FakeBackend(),
    )
    consumer.player = FakePlayer()
    return consumer


def _producer_link(trace_overlay, entity_ref):
    producer = trace_overlay.begin_trace(
        "fountain_cycle", source_ref="fountain_loop"
    )
    enqueue_id = trace_overlay.record(
        "output_queued",
        producer="FountainCrystallizer.crystallize",
        consumer="SpeechQueueConsumer",
        source_ref="crystallizer.py::speech_queue_insert",
        entity_ref=entity_ref,
        outcome="queued",
        parent_ids=[producer.start_record_id] if producer.start_record_id else [],
    )
    assert enqueue_id
    assert trace_overlay.link_entity(entity_ref, enqueue_id)
    trace_overlay.end_trace(producer, source_ref="fountain_loop")
    return enqueue_id


def test_consumer_events_use_explicit_operation_parents(monkeypatch, tmp_path):
    path = _enable_trace(monkeypatch, tmp_path)
    from substrate import trace_overlay

    entity_ref = "beliefs.speech_queue:5101"
    enqueue_id = _producer_link(trace_overlay, entity_ref)
    consumer = _consumer(monkeypatch)
    consumer._speak_one({
        "id": 5101, "belief_id": 91, "content": "A speakable sentence.",
        "voice": "af_sarah",
    })

    rows = _events(path)
    start = next(row for row in rows if row["event_type"] == "trace_start"
                 and row["entity_ref"] == entity_ref)
    by_event = {row["event_type"]: row for row in rows
                if row["trace_id"] == start["trace_id"]}
    assert start["parent_ids"] == [enqueue_id]
    assert by_event["queue_item_processing_started"]["parent_ids"] == [
        start["record_id"]
    ]
    assert by_event["queue_status_persisted"]["outcome"] == "spoken"
    speaking = next(row for row in rows if row["trace_id"] == start["trace_id"]
                    and row["event_type"] == "queue_status_persisted"
                    and row["outcome"] == "speaking")
    synthesis_started = by_event["synthesis_started"]
    synthesis_completed = by_event["synthesis_completed"]
    player_started = by_event["player_invocation_started"]
    player_returned = by_event["player_call_returned"]
    assert synthesis_started["parent_ids"] == [speaking["record_id"]]
    assert synthesis_completed["parent_ids"] == [synthesis_started["record_id"]]
    assert player_started["parent_ids"] == [synthesis_completed["record_id"]]
    assert player_returned["parent_ids"] == [player_started["record_id"]]
    spoken = next(row for row in rows if row["trace_id"] == start["trace_id"]
                  and row["event_type"] == "queue_status_persisted"
                  and row["outcome"] == "spoken")
    assert spoken["parent_ids"] == [player_returned["record_id"]]
    event_types = {row["event_type"] for row in rows}
    assert "claimed" not in {row.get("outcome") for row in rows}
    assert "audio_playback_completed" not in event_types
    assert "player_call_returned" in event_types
    assert rows[-1]["outcome"] == "player_call_returned_spoken_status_persisted"


def test_synthesis_failure_is_distinct_and_does_not_call_player(monkeypatch, tmp_path):
    path = _enable_trace(monkeypatch, tmp_path)
    backend = FakeBackend(fail=True)
    consumer = _consumer(monkeypatch, backend=backend)

    consumer._speak_one({
        "id": 5102, "belief_id": 92, "content": "A speakable sentence.",
        "voice": "af_sarah",
    })

    rows = _events(path)
    events = [row["event_type"] for row in rows]
    assert "synthesis_failed" in events
    assert "player_invocation_started" not in events
    assert consumer.player.calls == []
    assert any(row["event_type"] == "queue_status_persisted"
               and row["outcome"] == "failed" for row in rows)
    assert rows[-1]["outcome"] == "synthesis_failed"


def test_player_failure_is_distinct_from_synthesis_failure(monkeypatch, tmp_path):
    path = _enable_trace(monkeypatch, tmp_path)
    consumer = _consumer(monkeypatch)
    consumer.player = FakePlayer(fail=True)

    consumer._speak_one({
        "id": 5103, "belief_id": 93, "content": "A speakable sentence.",
        "voice": "af_sarah",
    })

    rows = _events(path)
    events = [row["event_type"] for row in rows]
    assert "synthesis_completed" in events
    assert "player_invocation_started" in events
    assert "player_call_failed" in events
    assert "synthesis_failed" not in events
    assert any(row["event_type"] == "queue_status_persisted"
               and row["outcome"] == "failed" for row in rows)
    assert rows[-1]["outcome"] == "player_call_failed"


def test_player_return_remains_visible_when_spoken_status_write_fails(
    monkeypatch, tmp_path
):
    path = _enable_trace(monkeypatch, tmp_path)

    def fail_spoken(sql, params):
        return "status='spoken'" in sql

    writer = FakeWriter(fail=fail_spoken)
    consumer = _consumer(monkeypatch, writer=writer)
    consumer._speak_one({
        "id": 5104, "belief_id": 94, "content": "A speakable sentence.",
        "voice": "af_sarah",
    })

    rows = _events(path)
    events = [row["event_type"] for row in rows]
    assert "player_call_returned" in events
    assert "queue_status_write_failed" in events
    assert any(row["event_type"] == "queue_status_persisted"
               and row["outcome"] == "failed_fallback" for row in rows)
    assert rows[-1]["outcome"] == (
        "player_returned_spoken_status_failed_fallback_persisted"
    )


def test_trace_off_preserves_speech_path(monkeypatch, tmp_path):
    path = tmp_path / "must-not-exist.jsonl"
    monkeypatch.setenv("NEX5_TRACE_OVERLAY", "0")
    monkeypatch.setenv("NEX5_TRACE_PATH", str(path))
    consumer = _consumer(monkeypatch)

    consumer._speak_one({
        "id": 5105, "belief_id": 95, "content": "A speakable sentence.",
        "voice": "af_sarah",
    })

    assert any("status='spoken'" in sql for sql, _ in consumer.writer.calls)
    assert not path.exists()


def _real_sqlite_consumer(tmp_path, monkeypatch):
    from substrate import Reader, Writer

    db_path = tmp_path / "speech.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE speech_queue ("
        "id INTEGER PRIMARY KEY, belief_id INTEGER NOT NULL, "
        "content TEXT NOT NULL, voice TEXT, queued_at REAL NOT NULL, "
        "status TEXT NOT NULL DEFAULT 'pending', spoken_at REAL, error TEXT)"
    )
    conn.commit()
    conn.close()
    writer = Writer(db_path, name="speech-phase0-test")
    reader = Reader(db_path)
    consumer = queue_consumer.SpeechQueueConsumer(
        writer=writer,
        reader=reader,
        config=SpeechConfig(enabled=True),
        backend=FakeBackend(),
    )
    consumer.player = FakePlayer()
    return writer, reader, consumer


def test_real_reader_selection_exposes_sqlite_row_mapping_limitation(
    monkeypatch, tmp_path
):
    writer, reader, consumer = _real_sqlite_consumer(tmp_path, monkeypatch)
    try:
        writer.write(
            "INSERT INTO speech_queue "
            "(id, belief_id, content, voice, queued_at) VALUES (?, ?, ?, ?, ?)",
            (5203, 103, "A persisted speech item.", "af_sarah", 1.0),
        )
        selected = consumer._pending()
        assert len(selected) == 1
        # Reader.read() returns sqlite3.Row, while the existing consumer uses
        # row.get("voice"). This is a pre-existing runtime defect, deliberately
        # not changed by this Phase 0 instrumentation PR.
        assert isinstance(selected[0], sqlite3.Row)
        assert not hasattr(selected[0], "get")
    finally:
        writer.close()


def test_real_writer_reader_and_consumer_preserve_registered_row_link(
    monkeypatch, tmp_path
):
    path = _enable_trace(monkeypatch, tmp_path)
    from substrate import trace_overlay

    writer, reader, consumer = _real_sqlite_consumer(tmp_path, monkeypatch)
    try:
        producer = trace_overlay.begin_trace(
            "fountain_cycle", source_ref="fountain_loop"
        )
        qid = writer.write(
            "INSERT INTO speech_queue "
            "(id, belief_id, content, voice, queued_at) VALUES (?, ?, ?, ?, ?)",
            (5201, 101, "A persisted speech item.", "af_sarah", 1.0),
        )
        entity_ref = f"beliefs.speech_queue:{qid}"
        enqueue_id = trace_overlay.record(
            "output_queued",
            producer="FountainCrystallizer.crystallize",
            consumer="SpeechQueueConsumer",
            source_ref="crystallizer.py::speech_queue_insert",
            entity_ref=entity_ref,
            outcome="queued",
        )
        assert enqueue_id
        assert trace_overlay.link_entity(entity_ref, enqueue_id)
        trace_overlay.end_trace(producer, source_ref="fountain_loop")

        selected = consumer._pending()
        assert len(selected) == 1
        consumer._speak_one(dict(selected[0]))

        rows = _events(path)
        consumer_start = next(row for row in rows
                              if row["event_type"] == "trace_start"
                              and row["entity_ref"] == entity_ref)
        assert consumer_start["parent_ids"] == [enqueue_id]
        stored = reader.read(
            "SELECT status FROM speech_queue WHERE id=?", (qid,)
        )
        assert stored[0]["status"] == "spoken"
    finally:
        writer.close()


def test_commit_before_registration_is_explicitly_unlinked(
    monkeypatch, tmp_path
):
    path = _enable_trace(monkeypatch, tmp_path)
    from substrate import trace_overlay

    writer, reader, consumer = _real_sqlite_consumer(tmp_path, monkeypatch)
    try:
        producer = trace_overlay.begin_trace(
            "fountain_cycle", source_ref="fountain_loop"
        )
        qid = writer.write(
            "INSERT INTO speech_queue "
            "(id, belief_id, content, voice, queued_at) VALUES (?, ?, ?, ?, ?)",
            (5202, 102, "A persisted speech item.", "af_sarah", 1.0),
        )
        # This is the reproduced boundary: the committed row is visible to the
        # production poll query before output_queued/link_entity registration.
        selected = consumer._pending()
        assert len(selected) == 1
        consumer._speak_one(selected[0])

        enqueue_id = trace_overlay.record(
            "output_queued",
            producer="FountainCrystallizer.crystallize",
            consumer="SpeechQueueConsumer",
            source_ref="crystallizer.py::speech_queue_insert",
            entity_ref=f"beliefs.speech_queue:{qid}",
            outcome="queued",
        )
        assert enqueue_id
        assert trace_overlay.link_entity(f"beliefs.speech_queue:{qid}", enqueue_id)
        trace_overlay.end_trace(producer, source_ref="fountain_loop")

        rows = _events(path)
        consumer_start = next(row for row in rows
                              if row["event_type"] == "trace_start"
                              and row["entity_ref"] == f"beliefs.speech_queue:{qid}")
        assert consumer_start["parent_ids"] == []
        assert rows[-1]["event_type"] == "trace_end"
        assert reader.read(
            "SELECT status FROM speech_queue WHERE id=?", (qid,)
        )[0]["status"] == "spoken"
    finally:
        writer.close()


def _run_paired_sqlite_cycle(tmp_path, monkeypatch, trace_on):
    from substrate import Reader, Writer

    data_dir = tmp_path / "nex-data"
    data_dir.mkdir(parents=True)
    trace_path = tmp_path / "paired-trace.jsonl"
    monkeypatch.setenv("NEX5_DATA_DIR", str(data_dir))
    monkeypatch.setenv("NEX5_TRACE_OVERLAY", "1" if trace_on else "0")
    if trace_on:
        monkeypatch.setenv("NEX5_TRACE_PATH", str(trace_path))
    else:
        monkeypatch.delenv("NEX5_TRACE_PATH", raising=False)

    db_path = tmp_path / "paired-speech.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE speech_queue ("
        "id INTEGER PRIMARY KEY, belief_id INTEGER NOT NULL, "
        "content TEXT NOT NULL, voice TEXT, queued_at REAL NOT NULL, "
        "status TEXT NOT NULL DEFAULT 'pending', spoken_at REAL, error TEXT)"
    )
    conn.commit()
    conn.close()

    actual_writer = Writer(db_path, name="speech-paired-test")
    writer_calls = []

    class RecordingWriter:
        def write(self, sql, params=()):
            writer_calls.append((sql, tuple(params)))
            return actual_writer.write(sql, params)

    actual_reader = Reader(db_path)
    read_queries = []

    class RecordingReader:
        def read(self, sql, params=()):
            read_queries.append((sql, tuple(params)))
            return actual_reader.read(sql, params)

    backend = FakeBackend()
    consumer = queue_consumer.SpeechQueueConsumer(
        writer=RecordingWriter(),
        reader=RecordingReader(),
        config=SpeechConfig(enabled=True),
        backend=backend,
    )
    consumer.player = FakePlayer()
    try:
        if trace_on:
            from substrate import trace_overlay
            producer = trace_overlay.begin_trace(
                "fountain_cycle", source_ref="fountain_loop"
            )
        qid = consumer.writer.write(
            "INSERT INTO speech_queue "
            "(id, belief_id, content, voice, queued_at) VALUES (?, ?, ?, ?, ?)",
            (5301, 111, "A paired speech item.", "af_sarah", 1.0),
        )
        if trace_on:
            entity_ref = f"beliefs.speech_queue:{qid}"
            enqueue_id = trace_overlay.record(
                "output_queued",
                producer="FountainCrystallizer.crystallize",
                consumer="SpeechQueueConsumer",
                source_ref="crystallizer.py::speech_queue_insert",
                entity_ref=entity_ref,
                outcome="queued",
            )
            assert enqueue_id
            assert trace_overlay.link_entity(entity_ref, enqueue_id)
            trace_overlay.end_trace(producer, source_ref="fountain_loop")

        selected = consumer._pending()
        assert len(selected) == 1
        consumer._speak_one(selected[0])
        query_sequence = list(read_queries)
        final_status = actual_reader.read(
            "SELECT status FROM speech_queue WHERE id=?", (qid,)
        )[0]["status"]
        result = {
            "query_sequence": query_sequence,
            "writer_calls": writer_calls,
            "final_status": final_status,
            "backend_calls": backend.calls,
            "player_calls": consumer.player.calls,
        }
        assert trace_path.exists() is trace_on
        return result
    finally:
        actual_writer.close()


def test_speech_trace_on_off_preserves_database_and_processing_operations(
    monkeypatch, tmp_path
):
    off = _run_paired_sqlite_cycle(
        tmp_path / "off", monkeypatch, trace_on=False
    )
    on = _run_paired_sqlite_cycle(
        tmp_path / "on", monkeypatch, trace_on=True
    )

    assert on["query_sequence"] == off["query_sequence"]
    assert on["writer_calls"] == off["writer_calls"]
    assert on["final_status"] == off["final_status"] == "spoken"
    assert on["backend_calls"] == off["backend_calls"]
    assert on["player_calls"] == off["player_calls"]
