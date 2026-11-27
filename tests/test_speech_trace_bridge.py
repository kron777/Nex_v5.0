"""Regression coverage for the bounded Fountain-to-speech trace bridge."""
from __future__ import annotations

from types import SimpleNamespace

import influence_trace
from influence_trace import TraceContext
from speech.queue_consumer import SpeechQueueConsumer


def _trace(tmp_path, monkeypatch):
    monkeypatch.setattr(TraceContext, "_safe_sink", lambda self: True)
    return TraceContext(
        "speech-test", sink_path=tmp_path / "speech-trace.jsonl", context="fixture"
    )


def test_speech_trace_registry_is_one_shot_and_expiring(tmp_path, monkeypatch):
    trace = _trace(tmp_path, monkeypatch)
    parent = trace.record("speech_queue", "enqueue_intent")
    now = [100.0]
    monkeypatch.setattr(influence_trace.time, "monotonic", lambda: now[0])

    influence_trace.register_speech_queue_trace(901, trace, parent)
    linked = influence_trace.take_speech_queue_trace(901)
    assert linked == (trace, parent)
    assert influence_trace.take_speech_queue_trace(901) is None

    influence_trace.register_speech_queue_trace(902, trace, parent)
    now[0] += influence_trace._TRACE_LINK_TTL_SECONDS + 1
    assert influence_trace.take_speech_queue_trace(902) is None


def test_speech_trace_registry_is_bounded(tmp_path, monkeypatch):
    trace = _trace(tmp_path, monkeypatch)
    parent = trace.record("speech_queue", "enqueue_intent")
    for belief_id in range(1, influence_trace._TRACE_LINK_MAX + 2):
        influence_trace.register_speech_queue_trace(belief_id, trace, parent)
    assert influence_trace.take_speech_queue_trace(1) is None
    assert influence_trace.take_speech_queue_trace(
        influence_trace._TRACE_LINK_MAX + 1
    ) == (trace, parent)


def test_speech_consumer_records_parent_linked_outcomes(tmp_path, monkeypatch):
    trace = _trace(tmp_path, monkeypatch)
    parent = trace.record("speech_queue", "enqueue_intent",
                          metadata={"belief_id": 77})
    influence_trace.register_speech_queue_trace(77, trace, parent)

    writes = []

    class FakeWriter:
        def write(self, sql, params=()):
            writes.append((sql, params))
            return 1

    class FakeBackend:
        def synth(self, content, voice=None):
            return object(), 24000

    class FakePlayer:
        def play(self, audio, sample_rate):
            return None

    consumer = SpeechQueueConsumer.__new__(SpeechQueueConsumer)
    consumer.writer = FakeWriter()
    consumer._voice_state = None
    consumer.config = SimpleNamespace(voice="test-voice")
    consumer.backend = FakeBackend()
    consumer.player = FakePlayer()
    consumer._speak_one({
        "id": 501, "belief_id": 77,
        "content": "A complete and speakable sentence for trace testing.",
        "voice": "test-voice",
    })

    events = list(trace.events)
    stages = [item["event"] for item in events]
    assert stages[-5:] == [
        "dequeued", "synthesis_started", "synthesis_completed",
        "playback_started", "playback_completed",
    ] or stages[-6:] == [
        "dequeued", "synthesis_started", "synthesis_completed",
        "playback_started", "playback_completed", "queue_status_spoken",
    ]
    by_event = {item["event"]: item for item in events}
    assert by_event["dequeued"]["parent_ids"] == [parent]
    assert by_event["dequeued"]["metadata"]["queue_id"] == 501
    assert by_event["playback_completed"]["parent_ids"] == [
        by_event["playback_started"]["event_id"]
    ]
    assert any("status='spoken'" in sql for sql, _ in writes)


def test_speech_consumer_records_failure_without_text_payload(tmp_path, monkeypatch):
    trace = _trace(tmp_path, monkeypatch)
    parent = trace.record("speech_queue", "enqueue_intent")
    influence_trace.register_speech_queue_trace(78, trace, parent)

    class FakeWriter:
        def __init__(self):
            self.writes = []

        def write(self, sql, params=()):
            self.writes.append((sql, params))
            return 1

    class FakeBackend:
        def synth(self, content, voice=None):
            raise RuntimeError("synthetic failure")

    consumer = SpeechQueueConsumer.__new__(SpeechQueueConsumer)
    consumer.writer = FakeWriter()
    consumer._voice_state = None
    consumer.config = SimpleNamespace(voice="test-voice")
    consumer.backend = FakeBackend()
    consumer.player = SimpleNamespace(play=lambda *args: None)
    consumer._speak_one({
        "id": 502, "belief_id": 78,
        "content": "A complete and speakable sentence for trace testing.",
        "voice": "test-voice",
    })

    events = list(trace.events)
    by_event = {item["event"]: item for item in events}
    assert "synthesis_failed" in by_event
    assert "queue_status_failed" in by_event
    assert by_event["synthesis_failed"]["metadata"]["error_type"] == "RuntimeError"
    assert by_event["queue_status_failed"]["parent_ids"] == [
        by_event["synthesis_failed"]["event_id"]
    ]
    assert "content" not in by_event["synthesis_failed"]["metadata"]
    assert any("status='failed'" in sql for sql, _ in consumer.writer.writes)



def test_speech_consumer_records_playback_failure(tmp_path, monkeypatch):
    trace = _trace(tmp_path, monkeypatch)
    parent = trace.record("speech_queue", "enqueue_intent")
    influence_trace.register_speech_queue_trace(79, trace, parent)

    class FakeWriter:
        def __init__(self):
            self.writes = []

        def write(self, sql, params=()):
            self.writes.append((sql, params))
            return 1

    class FakeBackend:
        def synth(self, content, voice=None):
            return object(), 24000

    class FakePlayer:
        def play(self, audio, sample_rate):
            raise OSError("synthetic playback failure")

    consumer = SpeechQueueConsumer.__new__(SpeechQueueConsumer)
    consumer.writer = FakeWriter()
    consumer._voice_state = None
    consumer.config = SimpleNamespace(voice="test-voice")
    consumer.backend = FakeBackend()
    consumer.player = FakePlayer()
    consumer._speak_one({
        "id": 503, "belief_id": 79,
        "content": "A complete and speakable sentence for trace testing.",
        "voice": "test-voice",
    })

    by_event = {item["event"]: item for item in trace.events}
    assert "playback_failed" in by_event
    assert by_event["queue_status_failed"]["parent_ids"] == [
        by_event["playback_failed"]["event_id"]
    ]
    assert any("status='failed'" in sql for sql, _ in consumer.writer.writes)


def test_speech_consumer_records_suppression(tmp_path, monkeypatch):
    trace = _trace(tmp_path, monkeypatch)
    parent = trace.record("speech_queue", "enqueue_intent")
    influence_trace.register_speech_queue_trace(80, trace, parent)

    writes = []

    class FakeWriter:
        def write(self, sql, params=()):
            writes.append((sql, params))
            return 1

    consumer = SpeechQueueConsumer.__new__(SpeechQueueConsumer)
    consumer.writer = FakeWriter()
    consumer._voice_state = None
    consumer.config = SimpleNamespace(voice="test-voice")
    consumer.backend = SimpleNamespace(synth=lambda *args, **kwargs: None)
    consumer.player = SimpleNamespace(play=lambda *args: None)
    consumer._speak_one({
        "id": 504, "belief_id": 80,
        "content": '{"machine":"payload"}',
        "voice": "test-voice",
    })

    by_event = {item["event"]: item for item in trace.events}
    assert "suppressed" in by_event
    assert by_event["suppressed"]["parent_ids"] == [
        by_event["dequeued"]["event_id"]
    ]
    assert any("status='suppressed'" in sql for sql, _ in writes)



def test_speech_consumer_preserves_playback_parent_when_spoken_status_write_fails(
    tmp_path, monkeypatch
):
    trace = _trace(tmp_path, monkeypatch)
    parent = trace.record("speech_queue", "enqueue_intent")
    influence_trace.register_speech_queue_trace(81, trace, parent)

    class FakeWriter:
        def __init__(self):
            self.writes = []

        def write(self, sql, params=()):
            self.writes.append((sql, params))
            if "status='spoken'" in sql:
                raise OSError("synthetic status-write failure")
            return 1

    consumer = SpeechQueueConsumer.__new__(SpeechQueueConsumer)
    consumer.writer = FakeWriter()
    consumer._voice_state = None
    consumer.config = SimpleNamespace(voice="test-voice")
    consumer.backend = SimpleNamespace(
        synth=lambda content, voice=None: (object(), 24000)
    )
    consumer.player = SimpleNamespace(play=lambda *args: None)
    consumer._speak_one({
        "id": 505, "belief_id": 81,
        "content": "A complete and speakable sentence for trace testing.",
        "voice": "test-voice",
    })

    by_event = {item["event"]: item for item in trace.events}
    assert by_event["queue_status_failed"]["parent_ids"] == [
        by_event["playback_completed"]["event_id"]
    ]
    assert any("status='failed'" in sql for sql, _ in consumer.writer.writes)
