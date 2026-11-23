"""Daemon thread that reads speech_queue and speaks pending entries."""
from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime
from typing import Optional

from .config import SpeechConfig
from .kokoro_backend import KokoroBackend
from .player import Player

log = logging.getLogger("nex5.speech.consumer")


def _trace_record(trace_api, trace_handle, event_type: str, **fields):
    """Best-effort trace emission; return the ID only when append succeeds."""
    if trace_api is None or trace_handle is None:
        return None
    try:
        return trace_api.record(event_type, **fields)
    except Exception:
        return None




def _is_speakable(content: str) -> bool:
    """Return False if content looks like raw JSON or machine-generated data."""
    if not content:
        return False
    stripped = content.strip()
    # Raw JSON object or array
    if stripped.startswith(("{", "[")) and stripped.endswith(("}", "]")):
        return False
    # Source-prefixed JSON: "[stream.name] {...}" or "[stream.name] [...]"
    if stripped.startswith("[") and "]" in stripped[:40]:
        after_bracket = stripped[stripped.index("]") + 1:].strip()
        if after_bracket.startswith(("{", "[")):
            return False
    # Absurdly long strings are probably data, not speech
    if len(stripped) > 400:
        return False
    return True


class SpeechQueueConsumer(threading.Thread):
    def __init__(self, writer, reader, config: Optional[SpeechConfig] = None,
                 voice_state=None, backend=None) -> None:
        super().__init__(name="nex5.speech.consumer", daemon=True)
        self.writer = writer
        self.reader = reader
        self.config = config or SpeechConfig.from_env()
        self._voice_state = voice_state
        self.backend = backend if backend is not None else KokoroBackend(
            voice=self.config.voice,
            speed=self.config.speed,
        )
        self.player = Player()
        self._stop = threading.Event()
        self._paused = not self.config.enabled

    def stop(self) -> None:
        self._stop.set()

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    @property
    def paused(self) -> bool:
        return self._paused

    def flush(self) -> int:
        rows = self.reader.read(
            "SELECT id FROM speech_queue WHERE status='pending'"
        )
        ids = [r["id"] for r in rows]
        for _id in ids:
            self.writer.write(
                "UPDATE speech_queue SET status='skipped' WHERE id=?",
                (_id,),
            )
        return len(ids)

    def _pending(self):
        return self.reader.read(
            "SELECT id, belief_id, content, voice FROM speech_queue "
            "WHERE status='pending' ORDER BY queued_at ASC LIMIT 1"
        )

    def run(self) -> None:
        if self.backend.is_loaded:
            log.info("SpeechQueueConsumer thread starting (Kokoro pre-loaded, voice=%s)",
                     self.config.voice)
        else:
            log.info("SpeechQueueConsumer thread starting, loading Kokoro (voice=%s)...",
                     self.config.voice)
        try:
            self.backend.load()  # no-op if already pre-loaded on main thread
            log.info("SpeechQueueConsumer: Kokoro ready, entering poll loop")
        except Exception as e:
            log.error("SpeechQueueConsumer: Kokoro load failed, speech disabled: %s", e)
            return

        while not self._stop.is_set():
            try:
                if self._paused:
                    time.sleep(self.config.poll_interval_sec)
                    continue

                from nex_config import local_now
                now_hour = local_now().hour
                if self.config.in_quiet_hours(now_hour):
                    time.sleep(self.config.poll_interval_sec * 5)
                    continue

                rows = self._pending()
                if not rows:
                    time.sleep(self.config.poll_interval_sec)
                    continue

                self._speak_one(rows[0])

            except Exception as e:
                log.error("consumer loop error: %s", e)
                time.sleep(self.config.poll_interval_sec)

    def _speak_one(self, row) -> None:
        qid = row["id"]
        entity_ref = f"beliefs.speech_queue:{qid}"
        content = row["content"]
        trace_api = None
        trace_handle = None
        trace_outcome = "processing_interrupted"

        # _speak_one is entered only after run() has received a row from
        # _pending(). This records processing hand-off, not an exclusive claim.
        if os.environ.get("NEX5_TRACE_OVERLAY", "0") == "1":
            try:
                from substrate import trace_overlay as trace_api
                trace_handle = trace_api.begin_linked_trace(
                    "speech_queue_item",
                    source_ref="speech/queue_consumer.py::SpeechQueueConsumer._speak_one",
                    entity_ref=entity_ref,
                    payload={"queue_id": qid},
                )
                if trace_handle is not None:
                    processing_id = _trace_record(
                        trace_api, trace_handle, "queue_item_processing_started",
                        producer="SpeechQueueConsumer.run",
                        consumer="SpeechQueueConsumer._speak_one",
                        source_ref="speech/queue_consumer.py::_speak_one",
                        entity_ref=entity_ref,
                        outcome="processing_started",
                        payload={"queue_id": qid},
                        parent_ids=(
                            [trace_handle.start_record_id]
                            if trace_handle.start_record_id else []
                        ),
                    )
                else:
                    processing_id = None
            except Exception:
                # A failed observer must not prevent speech processing.
                if trace_api is not None:
                    try:
                        trace_api.close_current_trace(
                            source_ref="speech/queue_consumer.py::trace_start",
                            outcome="trace_start_failed",
                        )
                    except Exception:
                        pass
                trace_api = None
                trace_handle = None
                processing_id = None
        else:
            processing_id = None

        def trace_event(event_type, *, producer, consumer, source_ref,
                        outcome=None, parent_id=None, payload=None):
            return _trace_record(
                trace_api, trace_handle, event_type,
                producer=producer,
                consumer=consumer,
                source_ref=source_ref,
                entity_ref=entity_ref,
                outcome=outcome,
                payload=payload,
                parent_ids=[parent_id] if parent_id else [],
            )

        try:
            # Use voice from VoiceState if available, else fall back to row voice or config.
            voice = None
            if self._voice_state is not None:
                try:
                    voice = self._voice_state.current_name()
                except Exception:
                    pass
            if not voice:
                voice = row.get("voice") or self.config.voice

            if not _is_speakable(content):
                try:
                    self.writer.write(
                        "UPDATE speech_queue SET status='suppressed' WHERE id=?", (qid,)
                    )
                except Exception as exc:
                    trace_event(
                        "queue_status_write_failed",
                        producer="SpeechQueueConsumer._speak_one",
                        consumer="speech_queue",
                        source_ref="speech/queue_consumer.py::_speak_one",
                        outcome="suppressed_status_write_failed",
                        parent_id=processing_id,
                        payload={"queue_id": qid, "error_type": type(exc).__name__},
                    )
                    trace_outcome = "suppressed_status_write_failed"
                    raise
                trace_event(
                    "queue_status_persisted",
                    producer="SpeechQueueConsumer._speak_one",
                    consumer="speech_queue",
                    source_ref="speech/queue_consumer.py::_speak_one",
                    outcome="suppressed",
                    parent_id=processing_id,
                    payload={"queue_id": qid},
                )
                log.info("speech suppressed (non-speakable content) id=%s chars=%d",
                         qid, len(content))
                trace_outcome = "suppressed"
                return

            try:
                self.writer.write(
                    "UPDATE speech_queue SET status='speaking' WHERE id=?", (qid,)
                )
            except Exception as exc:
                trace_event(
                    "queue_status_write_failed",
                    producer="SpeechQueueConsumer._speak_one",
                    consumer="speech_queue",
                    source_ref="speech/queue_consumer.py::_speak_one",
                    outcome="speaking_status_write_failed",
                    parent_id=processing_id,
                    payload={"queue_id": qid, "error_type": type(exc).__name__},
                )
                trace_outcome = "speaking_status_write_failed"
                raise

            speaking_status_id = trace_event(
                "queue_status_persisted",
                producer="SpeechQueueConsumer._speak_one",
                consumer="speech_queue",
                source_ref="speech/queue_consumer.py::_speak_one",
                outcome="speaking",
                parent_id=processing_id,
                payload={"queue_id": qid},
            )
            synthesis_started_id = trace_event(
                "synthesis_started",
                producer="SpeechQueueConsumer._speak_one",
                consumer="KokoroBackend.synth",
                source_ref="speech/queue_consumer.py::_speak_one",
                outcome="started",
                parent_id=speaking_status_id or processing_id,
                payload={"queue_id": qid, "voice": voice},
            )

            try:
                audio, sr = self.backend.synth(content, voice=voice)
            except Exception as exc:
                synthesis_failed_id = trace_event(
                    "synthesis_failed",
                    producer="KokoroBackend.synth",
                    consumer="SpeechQueueConsumer._speak_one",
                    source_ref="speech/queue_consumer.py::_speak_one",
                    outcome="failed",
                    parent_id=synthesis_started_id or speaking_status_id or processing_id,
                    payload={"queue_id": qid, "error_type": type(exc).__name__},
                )
                log.error("speech synthesis failed on id=%s: %s", qid, exc)
                try:
                    self.writer.write(
                        "UPDATE speech_queue SET status='failed', error=? WHERE id=?",
                        (str(exc), qid),
                    )
                except Exception as status_exc:
                    trace_event(
                        "queue_status_write_failed",
                        producer="SpeechQueueConsumer._speak_one",
                        consumer="speech_queue",
                        source_ref="speech/queue_consumer.py::_speak_one",
                        outcome="failed_status_write_failed",
                        parent_id=synthesis_failed_id,
                        payload={"queue_id": qid, "error_type": type(status_exc).__name__},
                    )
                    trace_outcome = "synthesis_failed_status_write_failed"
                    raise
                trace_event(
                    "queue_status_persisted",
                    producer="SpeechQueueConsumer._speak_one",
                    consumer="speech_queue",
                    source_ref="speech/queue_consumer.py::_speak_one",
                    outcome="failed",
                    parent_id=synthesis_failed_id,
                    payload={"queue_id": qid},
                )
                trace_outcome = "synthesis_failed"
                return

            player_started_id = trace_event(
                "player_invocation_started",
                producer="SpeechQueueConsumer._speak_one",
                consumer="Player.play",
                source_ref="speech/queue_consumer.py::_speak_one",
                outcome="invoked",
                parent_id=synthesis_started_id or speaking_status_id or processing_id,
                payload={"queue_id": qid, "sample_rate": sr},
            )
            try:
                self.player.play(audio, sr)
            except Exception as exc:
                player_failed_id = trace_event(
                    "player_call_failed",
                    producer="Player.play",
                    consumer="SpeechQueueConsumer._speak_one",
                    source_ref="speech/queue_consumer.py::_speak_one",
                    outcome="raised",
                    parent_id=player_started_id,
                    payload={"queue_id": qid, "error_type": type(exc).__name__},
                )
                log.error("audio player failed on id=%s: %s", qid, exc)
                try:
                    self.writer.write(
                        "UPDATE speech_queue SET status='failed', error=? WHERE id=?",
                        (str(exc), qid),
                    )
                except Exception as status_exc:
                    trace_event(
                        "queue_status_write_failed",
                        producer="SpeechQueueConsumer._speak_one",
                        consumer="speech_queue",
                        source_ref="speech/queue_consumer.py::_speak_one",
                        outcome="failed_status_write_failed",
                        parent_id=player_failed_id,
                        payload={"queue_id": qid, "error_type": type(status_exc).__name__},
                    )
                    trace_outcome = "player_call_failed_status_write_failed"
                    raise
                trace_event(
                    "queue_status_persisted",
                    producer="SpeechQueueConsumer._speak_one",
                    consumer="speech_queue",
                    source_ref="speech/queue_consumer.py::_speak_one",
                    outcome="failed",
                    parent_id=player_failed_id,
                    payload={"queue_id": qid},
                )
                trace_outcome = "player_call_failed"
                return

            player_returned_id = trace_event(
                "player_call_returned",
                producer="Player.play",
                consumer="SpeechQueueConsumer._speak_one",
                source_ref="speech/queue_consumer.py::_speak_one",
                outcome="returned",
                parent_id=player_started_id,
                payload={"queue_id": qid, "sample_rate": sr},
            )

            try:
                self.writer.write(
                    "UPDATE speech_queue SET status='spoken', spoken_at=? WHERE id=?",
                    (time.time(), qid),
                )
            except Exception as status_exc:
                trace_event(
                    "queue_status_write_failed",
                    producer="SpeechQueueConsumer._speak_one",
                    consumer="speech_queue",
                    source_ref="speech/queue_consumer.py::_speak_one",
                    outcome="spoken_status_write_failed",
                    parent_id=player_returned_id,
                    payload={"queue_id": qid, "error_type": type(status_exc).__name__},
                )
                # Preserve the existing fallback status attempt. A successful
                # Player.play() return remains a separate historical fact.
                try:
                    self.writer.write(
                        "UPDATE speech_queue SET status='failed', error=? WHERE id=?",
                        (str(status_exc), qid),
                    )
                except Exception as fallback_exc:
                    trace_event(
                        "queue_status_write_failed",
                        producer="SpeechQueueConsumer._speak_one",
                        consumer="speech_queue",
                        source_ref="speech/queue_consumer.py::_speak_one",
                        outcome="failed_fallback_status_write_failed",
                        parent_id=player_returned_id,
                        payload={"queue_id": qid, "error_type": type(fallback_exc).__name__},
                    )
                    trace_outcome = "player_returned_status_persistence_failed"
                    raise
                trace_event(
                    "queue_status_persisted",
                    producer="SpeechQueueConsumer._speak_one",
                    consumer="speech_queue",
                    source_ref="speech/queue_consumer.py::_speak_one",
                    outcome="failed_fallback",
                    parent_id=player_returned_id,
                    payload={"queue_id": qid},
                )
                trace_outcome = "player_returned_spoken_status_failed_fallback_persisted"
                return

            trace_event(
                "queue_status_persisted",
                producer="SpeechQueueConsumer._speak_one",
                consumer="speech_queue",
                source_ref="speech/queue_consumer.py::_speak_one",
                outcome="spoken",
                parent_id=player_returned_id,
                payload={"queue_id": qid},
            )
            log.info("spoke belief_id=%s (%d chars)", row["belief_id"], len(content))
            trace_outcome = "player_call_returned_spoken_status_persisted"
        finally:
            if trace_handle is not None:
                try:
                    trace_api.end_trace(
                        trace_handle,
                        source_ref="speech/queue_consumer.py::SpeechQueueConsumer._speak_one",
                        entity_ref=entity_ref,
                        outcome=trace_outcome,
                    )
                except Exception:
                    pass
