import json
import stat
from pathlib import Path

from substrate import trace_overlay as trace


def _read(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_default_off_is_inert(tmp_path, monkeypatch):
    monkeypatch.setenv("NEX5_DATA_DIR", str(tmp_path / "nex-data"))
    monkeypatch.delenv("NEX5_TRACE_OVERLAY", raising=False)
    monkeypatch.setenv("NEX5_TRACE_PATH", str(tmp_path / "trace.jsonl"))

    handle = trace.begin_trace("chat", source_ref="gui/server.py::api_chat")
    assert handle is None
    assert trace.record(
        "input", producer="chat", source_ref="gui/server.py::api_chat",
        payload={"prompt": "private text"},
    ) is None
    assert not (tmp_path / "trace.jsonl").exists()


def test_requires_explicit_artifact_path(tmp_path, monkeypatch):
    monkeypatch.setenv("NEX5_TRACE_OVERLAY", "1")
    monkeypatch.delenv("NEX5_TRACE_PATH", raising=False)

    assert trace.begin_trace("fountain", source_ref="fountain_loop") is None
    assert not list(tmp_path.iterdir())


def test_parentage_is_explicit_and_only_payload_digest_is_retained(tmp_path, monkeypatch):
    monkeypatch.setenv("NEX5_DATA_DIR", str(tmp_path / "nex-data"))
    path = tmp_path / "trace.jsonl"
    monkeypatch.setenv("NEX5_TRACE_OVERLAY", "1")
    monkeypatch.setenv("NEX5_TRACE_PATH", str(path))

    handle = trace.begin_trace(
        "chat", source_ref="gui/server.py::api_chat",
        entity_ref="session-123", payload={"prompt": "private prompt"},
    )
    assert handle is not None
    assert handle.start_record_id == rows[0]["record_id"]
    first = trace.record(
        "input_arrival", producer="gui.server", source_ref="gui/server.py::api_chat",
        entity_ref="message-1", payload={"prompt": "private prompt"},
    )
    second = trace.record(
        "context_selection", producer="gui.server", consumer="voice.speak",
        source_ref="gui/server.py::_assemble_chat_blocks", outcome="serial",
        parent_ids=[first],
    )
    trace.end_trace(
        handle, source_ref="gui/server.py::api_chat", entity_ref="message-2",
        payload={"response": "private response"},
    )

    rows = _read(path)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert len(rows) == 4
    assert len({row["record_id"] for row in rows}) == 4
    assert all(row["trace_id"] == handle.trace_id for row in rows)
    assert rows[0]["event_type"] == "trace_start"
    assert rows[0]["parent_ids"] == []
    assert rows[1]["parent_ids"] == []
    assert rows[2]["parent_ids"] == [first]
    assert rows[3]["parent_ids"] == []
    assert rows[1]["payload_digest"]
    serialized = path.read_text(encoding="utf-8")
    assert "private prompt" not in serialized
    assert "private response" not in serialized
    assert "payload_digest" in serialized


def test_nested_trace_restores_outer_context(tmp_path, monkeypatch):
    monkeypatch.setenv("NEX5_DATA_DIR", str(tmp_path / "nex-data"))
    path = tmp_path / "trace.jsonl"
    monkeypatch.setenv("NEX5_TRACE_OVERLAY", "1")
    monkeypatch.setenv("NEX5_TRACE_PATH", str(path))

    outer = trace.begin_trace("outer", source_ref="outer")
    outer_record = trace.record("outer_event", producer="outer", source_ref="outer")
    inner = trace.begin_trace("inner", source_ref="inner")
    trace.record("inner_event", producer="inner", source_ref="inner")
    trace.end_trace(inner, source_ref="inner")
    resumed = trace.record("outer_resumed", producer="outer", source_ref="outer")
    trace.end_trace(outer, source_ref="outer")

    rows = _read(path)
    outer_rows = [row for row in rows if row["trace_id"] == outer.trace_id]
    inner_rows = [row for row in rows if row["trace_id"] == inner.trace_id]
    assert len(outer_rows) == 4
    assert len(inner_rows) == 3
    assert outer_rows[-2]["event_type"] == "outer_resumed"
    assert outer_rows[-2]["parent_ids"] == []
    assert resumed == outer_rows[-2]["record_id"]


def test_trace_write_failure_is_non_fatal(tmp_path, monkeypatch):
    monkeypatch.setenv("NEX5_DATA_DIR", str(tmp_path / "nex-data"))
    monkeypatch.setenv("NEX5_TRACE_OVERLAY", "1")
    monkeypatch.setenv("NEX5_TRACE_PATH", str(tmp_path / "missing" / "trace.jsonl"))
    handle = trace.begin_trace("chat", source_ref="chat")
    assert handle is not None

    # Turn the destination into a directory after the first successful append.
    target = tmp_path / "missing" / "trace.jsonl"
    target.unlink()
    target.mkdir()
    assert trace.record("event", producer="chat", source_ref="chat") is None
    trace.end_trace(handle, source_ref="chat")

def test_refuses_trace_artifact_inside_nex_data_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "nex-data"
    data_dir.mkdir()
    monkeypatch.setenv("NEX5_TRACE_OVERLAY", "1")
    monkeypatch.setenv("NEX5_DATA_DIR", str(data_dir))
    monkeypatch.setenv("NEX5_TRACE_PATH", str(data_dir / "trace.jsonl"))

    assert trace.begin_trace("chat", source_ref="chat") is None
    assert list(data_dir.iterdir()) == []


def test_turning_flag_off_stops_writes_and_end_restores_context(tmp_path, monkeypatch):
    monkeypatch.setenv("NEX5_DATA_DIR", str(tmp_path / "nex-data"))
    path = tmp_path / "trace.jsonl"
    monkeypatch.setenv("NEX5_TRACE_OVERLAY", "1")
    monkeypatch.setenv("NEX5_TRACE_PATH", str(path))
    handle = trace.begin_trace("chat", source_ref="chat")
    assert handle is not None

    monkeypatch.setenv("NEX5_TRACE_OVERLAY", "0")
    assert trace.record("after_off", producer="chat", source_ref="chat") is None
    trace.end_trace(handle, source_ref="chat")
    rows = _read(path)
    assert [row["event_type"] for row in rows] == ["trace_start"]

def test_teardown_closes_unfinished_trace_context(tmp_path, monkeypatch):
    monkeypatch.setenv("NEX5_DATA_DIR", str(tmp_path / "nex-data"))
    monkeypatch.setenv("NEX5_TRACE_OVERLAY", "1")
    monkeypatch.setenv("NEX5_TRACE_PATH", str(tmp_path / "trace.jsonl"))
    handle = trace.begin_trace("chat", source_ref="chat")
    assert handle is not None

    trace.close_current_trace(source_ref="gui.server::teardown_request", outcome="exception")
    assert trace.record("leak_check", producer="test", source_ref="test") is None
    rows = _read(tmp_path / "trace.jsonl")
    assert [row["event_type"] for row in rows] == ["trace_start", "trace_end"]
    assert rows[-1]["outcome"] == "exception"

def test_refuses_trace_artifact_inside_repository(tmp_path, monkeypatch):
    monkeypatch.setenv("NEX5_DATA_DIR", str(tmp_path / "nex-data"))
    monkeypatch.setenv("NEX5_TRACE_OVERLAY", "1")
    monkeypatch.setenv("NEX5_TRACE_PATH", str(Path(trace._REPO_ROOT) / "trace.jsonl"))

    assert trace.begin_trace("chat", source_ref="chat") is None


def test_refuses_trace_artifact_inside_custom_database_root(tmp_path, monkeypatch):
    db_dir = tmp_path / "custom-db"
    db_dir.mkdir()
    monkeypatch.setenv("NEX5_DATA_DIR", str(tmp_path / "other-data"))
    monkeypatch.setenv("NEX5_BELIEFS_DB", str(db_dir / "beliefs.db"))
    monkeypatch.setenv("NEX5_TRACE_OVERLAY", "1")
    monkeypatch.setenv("NEX5_TRACE_PATH", str(db_dir / "trace.jsonl"))

    assert trace.begin_trace("chat", source_ref="chat") is None



def test_async_consumer_trace_has_enqueue_record_as_cross_thread_parent(tmp_path, monkeypatch):
    monkeypatch.setenv("NEX5_DATA_DIR", str(tmp_path / "nex-data"))
    path = tmp_path / "trace.jsonl"
    monkeypatch.setenv("NEX5_TRACE_OVERLAY", "1")
    monkeypatch.setenv("NEX5_TRACE_PATH", str(path))

    entity_ref = "beliefs.speech_queue:77"
    producer = trace.begin_trace("fountain_cycle", source_ref="fountain_loop")
    enqueue_id = trace.record(
        "output_queued",
        producer="FountainCrystallizer.crystallize",
        consumer="SpeechQueueConsumer",
        source_ref="crystallizer.py::speech_queue_insert",
        entity_ref=entity_ref,
        outcome="queued",
    )
    assert enqueue_id
    assert trace.link_entity(entity_ref, enqueue_id)
    trace.end_trace(producer, source_ref="fountain_loop", outcome="speech_handoff")

    consumer = trace.begin_linked_trace(
        "speech_queue_item",
        source_ref="queue_consumer.py::_speak_one",
        entity_ref=entity_ref,
    )
    assert consumer is not None
    consumed_id = trace.record(
        "queue_item_consumed",
        producer="SpeechQueueConsumer._pending",
        consumer="SpeechQueueConsumer._speak_one",
        source_ref="queue_consumer.py::_pending",
        entity_ref=entity_ref,
        outcome="claimed",
    )
    trace.end_trace(consumer, source_ref="queue_consumer.py::_speak_one")

    rows = _read(path)
    consumer_start = next(
        row for row in rows
        if row["trace_id"] == consumer.trace_id and row["event_type"] == "trace_start"
    )
    consumer_event = next(row for row in rows if row["record_id"] == consumed_id)
    assert consumer.trace_id != producer.trace_id
    assert consumer_start["parent_ids"] == [enqueue_id]
    assert consumer_event["parent_ids"] == []
