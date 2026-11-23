"""Tests for the default-OFF speech queue consumer trace boundary."""
import json

import speech.queue_consumer as queue_consumer
from speech.config import SpeechConfig


class FakeWriter:
    def __init__(self):
        self.calls = []

    def write(self, sql, params=()):
        self.calls.append((sql, params))
        return len(self.calls)


class FakeReader:
    def read(self, sql, params=()):
        return []


class FakePlayer:
    def play(self, audio, sample_rate):
        return None


class FailingPlayer:
    def play(self, audio, sample_rate):
        raise RuntimeError("audio device unavailable")


class FakeBackend:
    def __init__(self, error=None):
        self.error = error

    def synth(self, content, voice):
        if self.error is not None:
            raise self.error
        return b"audio-bytes", 24000


def _consumer(monkeypatch, backend):
    monkeypatch.setattr(queue_consumer, "Player", FakePlayer)
    return queue_consumer.SpeechQueueConsumer(
        writer=FakeWriter(),
        reader=FakeReader(),
        config=SpeechConfig(enabled=True),
        backend=backend,
    )


def _enable_trace(monkeypatch, tmp_path):
    path = tmp_path / "speech-trace.jsonl"
    monkeypatch.setenv("NEX5_TRACE_OVERLAY", "1")
    monkeypatch.setenv("NEX5_TRACE_PATH", str(path))
    monkeypatch.setenv("NEX5_DATA_DIR", str(tmp_path / "nex-data"))
    return path


def _events(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_suppressed_queue_item_is_traced_without_retaining_content(monkeypatch, tmp_path):
    path = _enable_trace(monkeypatch, tmp_path)
    consumer = _consumer(monkeypatch, FakeBackend())
    private_content = '{"internal": "must not be retained"}'

    consumer._speak_one({
        "id": 41, "belief_id": 9, "content": private_content, "voice": "af_sarah"
    })

    rows = _events(path)
    assert [row["event_type"] for row in rows] == [
        "trace_start", "queue_item_consumed", "output_suppressed", "trace_end"
    ]
    assert rows[2]["entity_ref"] == "beliefs.speech_queue:41"
    assert rows[2]["outcome"] == "suppressed"
    assert private_content not in path.read_text()
    assert any("status='suppressed'" in sql for sql, _ in consumer.writer.calls)
    assert rows[-1]["outcome"] == "suppressed"


def test_successful_playback_is_traced_and_queue_is_marked_spoken(monkeypatch, tmp_path):
    path = _enable_trace(monkeypatch, tmp_path)
    consumer = _consumer(monkeypatch, FakeBackend())
    private_content = "A private sentence that should only be hashed."

    consumer._speak_one({
        "id": 42, "belief_id": 10, "content": private_content, "voice": "af_sarah"
    })

    rows = _events(path)
    events = [row["event_type"] for row in rows]
    assert events == [
        "trace_start", "queue_item_consumed", "synthesis_started",
        "audio_playback_completed", "trace_end"
    ]
    assert rows[3]["entity_ref"] == "beliefs.speech_queue:42"
    assert rows[3]["outcome"] == "played"
    assert private_content not in path.read_text()
    assert any("status='spoken'" in sql for sql, _ in consumer.writer.calls)
    assert rows[-1]["outcome"] == "spoken"


def test_synthesis_failure_is_traced_and_queue_is_marked_failed(monkeypatch, tmp_path):
    path = _enable_trace(monkeypatch, tmp_path)
    consumer = _consumer(monkeypatch, FakeBackend(RuntimeError("backend unavailable")))

    consumer._speak_one({
        "id": 43, "belief_id": 11, "content": "A speakable sentence for testing.",
        "voice": "af_sarah"
    })

    rows = _events(path)
    failure = next(row for row in rows if row["event_type"] == "audio_playback_failed")
    assert failure["entity_ref"] == "beliefs.speech_queue:43"
    assert failure["outcome"] == "failed"
    assert failure["payload_digest"] is not None
    assert any("status='failed'" in sql for sql, _ in consumer.writer.calls)
    assert rows[-1]["outcome"] == "failed"



def test_player_failure_is_traced_and_queue_is_marked_failed(monkeypatch, tmp_path):
    path = _enable_trace(monkeypatch, tmp_path)
    consumer = _consumer(monkeypatch, FakeBackend())
    consumer.player = FailingPlayer()

    consumer._speak_one({
        "id": 46, "belief_id": 14, "content": "A speakable sentence for testing.",
        "voice": "af_sarah"
    })

    rows = _events(path)
    failure = next(row for row in rows if row["event_type"] == "audio_playback_failed")
    assert failure["entity_ref"] == "beliefs.speech_queue:46"
    assert failure["outcome"] == "failed"
    assert any("status='failed'" in sql for sql, _ in consumer.writer.calls)
    assert rows[-1]["outcome"] == "failed"


def test_queue_status_write_failure_is_not_misreported_as_playback_failure(monkeypatch, tmp_path):
    path = _enable_trace(monkeypatch, tmp_path)
    consumer = _consumer(monkeypatch, FakeBackend())

    original_write = consumer.writer.write

    def fail_spoken_status(sql, params=()):
        if "status='spoken'" in sql:
            raise RuntimeError("status store unavailable")
        return original_write(sql, params)

    consumer.writer.write = fail_spoken_status
    consumer._speak_one({
        "id": 47, "belief_id": 15, "content": "A speakable sentence for testing.",
        "voice": "af_sarah"
    })

    rows = _events(path)
    events = [row["event_type"] for row in rows]
    assert "audio_playback_completed" in events
    assert "queue_status_write_failed" in events
    assert "audio_playback_failed" not in events
    assert rows[-1]["outcome"] == "failed"

def test_consumer_trace_is_inert_when_overlay_is_off(monkeypatch, tmp_path):
    path = tmp_path / "must-not-exist.jsonl"
    monkeypatch.setenv("NEX5_TRACE_OVERLAY", "0")
    monkeypatch.setenv("NEX5_TRACE_PATH", str(path))
    consumer = _consumer(monkeypatch, FakeBackend())

    consumer._speak_one({
        "id": 44, "belief_id": 12, "content": "A speakable sentence for testing.",
        "voice": "af_sarah"
    })

    assert any("status='spoken'" in sql for sql, _ in consumer.writer.calls)
    assert not path.exists()

def test_trace_write_errors_do_not_change_speech_outcome(monkeypatch, tmp_path):
    path = _enable_trace(monkeypatch, tmp_path)
    consumer = _consumer(monkeypatch, FakeBackend())

    from substrate import trace_overlay

    original_record = trace_overlay.record

    def fail_after_start(event_type, **fields):
        if event_type == "trace_start":
            return original_record(event_type, **fields)
        raise OSError("trace destination unavailable")

    monkeypatch.setattr(trace_overlay, "record", fail_after_start)
    consumer._speak_one({
        "id": 45, "belief_id": 13, "content": "A speakable sentence for testing.",
        "voice": "af_sarah"
    })

    assert any("status='spoken'" in sql for sql, _ in consumer.writer.calls)
    assert path.exists()
    assert [row["event_type"] for row in _events(path)] == ["trace_start"]



def test_speech_consumer_trace_links_to_actual_enqueue_record(monkeypatch, tmp_path):
    path = _enable_trace(monkeypatch, tmp_path)
    from substrate import trace_overlay

    entity_ref = "beliefs.speech_queue:48"
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
    )
    assert enqueue_id
    assert trace_overlay.link_entity(entity_ref, enqueue_id)
    trace_overlay.end_trace(producer, source_ref="fountain_loop")

    consumer = _consumer(monkeypatch, FakeBackend())
    consumer._speak_one({
        "id": 48, "belief_id": 16, "content": "A speakable sentence for testing.",
        "voice": "af_sarah"
    })

    rows = _events(path)
    consumer_start = next(
        row for row in rows
        if row["trace_kind"] == "speech_queue_item" and row["event_type"] == "trace_start"
    )
    assert consumer_start["parent_ids"] == [enqueue_id]
    assert consumer_start["trace_id"] != producer.trace_id
    assert any(
        row["trace_id"] == consumer_start["trace_id"]
        and row["event_type"] == "audio_playback_completed"
        for row in rows
    )
