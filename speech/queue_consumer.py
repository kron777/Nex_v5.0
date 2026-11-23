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
        trace_api = trace_handle = None
        trace_outcome = "processing_interrupted"

        # This is the hand-off into processing after _pending() returned a row;
        # it is not an exclusive reservation or a claim on the queue item.
        if os.environ.get("NEX5_TRACE_OVERLAY", "0") == "1":
            try:
                from substrate import trace_overlay as trace_api
                trace_handle = trace_api.begin_linked_trace(
                    "speech_queue_item",
                    source_ref="speech/queue_consumer.py::SpeechQueueConsumer._speak_one",
                    entity_ref=entity_ref,
                    payload={"queue_id": qid},
                )
            except Exception:
                if trace_api is not None:
                    try:
                        trace_api.close_current_trace(
                            source_ref="speech/queue_consumer.py::trace_start",
                            outcome="trace_start_failed",
                        )
                    except Exception:
                        pass
                trace_api = trace_handle = None

        def emit(event_type, producer, consumer, outcome, parent_id, payload=None):
            return _trace_record(
                trace_api, trace_handle, event_type,
                producer=producer, consumer=consumer,
                source_ref="speech/queue_consumer.py::_speak_one",
                entity_ref=entity_ref, outcome=outcome, payload=payload,
                parent_ids=[parent_id] if parent_id else [],
            )

        def persist_status(status, sql, params, parent_id):
            nonlocal trace_outcome
            try:
                self.writer.write(sql, params)
            except Exception as exc:
                trace_outcome = f"{status}_status_write_failed"
                emit(
                    "queue_status_write_failed", "SpeechQueueConsumer._speak_one",
                    "speech_queue", f"{status}_write_failed", parent_id,
                    {"queue_id": qid, "error_type": type(exc).__name__},
                )
                raise
            return emit(
                "queue_status_persisted", "SpeechQueueConsumer._speak_one",
                "speech_queue", status, parent_id, {"queue_id": qid},
            )

        try:
            if trace_handle is not None:
                processing_id = emit(
                    "queue_item_processing_started", "SpeechQueueConsumer.run",
                    "SpeechQueueConsumer._speak_one", "processing_started",
                    trace_handle.start_record_id, {"queue_id": qid},
                )
            else:
                processing_id = None

            voice = None
            if self._voice_state is not None:
                try:
                    voice = self._voice_state.current_name()
                except Exception:
                    pass
            if not voice:
                # Reader returns sqlite3.Row, which supports indexed access,
                # not dict.get(). Keep this path compatible with real rows.
                voice = row["voice"] or self.config.voice

            if not _is_speakable(content):
                persist_status(
                    "suppressed",
                    "UPDATE speech_queue SET status='suppressed' WHERE id=?",
                    (qid,), processing_id,
                )
                log.info("speech suppressed (non-speakable content) id=%s chars=%d",
                         qid, len(content))
                trace_outcome = "suppressed"
                return

            speaking_id = persist_status(
                "speaking",
                "UPDATE speech_queue SET status='speaking' WHERE id=?",
                (qid,), processing_id,
            )
            synthesis_id = emit(
                "synthesis_started", "SpeechQueueConsumer._speak_one",
                "KokoroBackend.synth", "started",
                speaking_id, {"queue_id": qid, "voice": voice},
            )
            try:
                audio, sr = self.backend.synth(content, voice=voice)
            except Exception as exc:
                failed_id = emit(
                    "synthesis_failed", "KokoroBackend.synth",
                    "SpeechQueueConsumer._speak_one", "failed",
                    synthesis_id,
                    {"queue_id": qid, "error_type": type(exc).__name__},
                )
                log.error("speech synthesis failed on id=%s: %s", qid, exc)
                try:
                    persist_status(
                        "failed",
                        "UPDATE speech_queue SET status='failed', error=? WHERE id=?",
                        (str(exc), qid), failed_id,
                    )
                except Exception:
                    trace_outcome = "synthesis_failed_status_write_failed"
                    raise
                trace_outcome = "synthesis_failed"
                return

            synthesis_done_id = emit(
                "synthesis_completed", "KokoroBackend.synth",
                "SpeechQueueConsumer._speak_one", "returned",
                synthesis_id or speaking_id or processing_id,
                {"queue_id": qid, "sample_rate": sr},
            )
            player_id = emit(
                "player_invocation_started", "SpeechQueueConsumer._speak_one",
                "Player.play", "invoked",
                synthesis_done_id,
                {"queue_id": qid, "sample_rate": sr},
            )
            try:
                self.player.play(audio, sr)
            except Exception as exc:
                failed_id = emit(
                    "player_call_failed", "Player.play",
                    "SpeechQueueConsumer._speak_one", "raised", player_id,
                    {"queue_id": qid, "error_type": type(exc).__name__},
                )
                log.error("audio player failed on id=%s: %s", qid, exc)
                try:
                    persist_status(
                        "failed",
                        "UPDATE speech_queue SET status='failed', error=? WHERE id=?",
                        (str(exc), qid), failed_id,
                    )
                except Exception:
                    trace_outcome = "player_call_failed_status_write_failed"
                    raise
                trace_outcome = "player_call_failed"
                return

            # A returned Player.play() call is observable; physical audibility
            # is not established by this interface.
            player_returned_id = emit(
                "player_call_returned", "Player.play",
                "SpeechQueueConsumer._speak_one", "returned", player_id,
                {"queue_id": qid, "sample_rate": sr},
            )
            try:
                persist_status(
                    "spoken",
                    "UPDATE speech_queue SET status='spoken', spoken_at=? WHERE id=?",
                    (time.time(), qid), player_returned_id,
                )
            except Exception as status_exc:
                # Keep the historical player return distinct from persistence.
                try:
                    persist_status(
                        "failed_fallback",
                        "UPDATE speech_queue SET status='failed', error=? WHERE id=?",
                        (str(status_exc), qid), player_returned_id,
                    )
                except Exception:
                    trace_outcome = "player_returned_status_persistence_failed"
                    raise
                trace_outcome = "player_returned_spoken_status_failed_fallback_persisted"
                return

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
