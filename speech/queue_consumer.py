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

def _trace_record(trace_api, trace_handle, event_type: str, **fields) -> None:
    """Best-effort trace emission; observability must never affect speech."""
    if trace_api is None or trace_handle is None:
        return
    try:
        trace_api.record(event_type, **fields)
    except Exception:
        pass


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
        content = row["content"]
        trace_api = None
        trace_handle = None
        trace_outcome = "processing_interrupted"

        # The consumer runs on its own thread, outside the Fountain cycle's
        # ContextVar. Start a separately scoped trace anchored to the persisted
        # queue row ID so enqueue and eventual disposition can be correlated
        # without pretending the asynchronous parent context crossed threads.
        if os.environ.get("NEX5_TRACE_OVERLAY", "0") == "1":
            try:
                from substrate import trace_overlay as trace_api
                trace_handle = trace_api.begin_linked_trace(
                    "speech_queue_item",
                    source_ref="speech/queue_consumer.py::SpeechQueueConsumer._speak_one",
                    entity_ref=f"beliefs.speech_queue:{qid}",
                )
                if trace_handle is not None:
                    _trace_record(
                        trace_api, trace_handle, "queue_item_consumed",
                        producer="SpeechQueueConsumer._pending",
                        consumer="SpeechQueueConsumer._speak_one",
                        source_ref="speech/queue_consumer.py::_pending",
                        entity_ref=f"beliefs.speech_queue:{qid}",
                        outcome="claimed",
                        payload={"queue_id": qid},
                    )
            except Exception:
                # begin_trace may have installed a ContextVar before an
                # unexpected trace-start failure; close it defensively.
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

        try:
            # Use voice from VoiceState if available, else fall back to row voice or config
            voice = None
            if self._voice_state is not None:
                try:
                    voice = self._voice_state.current_name()
                except Exception:
                    pass
            if not voice:
                voice = row.get("voice") or self.config.voice
            if not _is_speakable(content):
                self.writer.write(
                    "UPDATE speech_queue SET status='suppressed' WHERE id=?", (qid,)
                )
                if trace_handle is not None:
                    _trace_record(
                        trace_api, trace_handle, "output_suppressed",
                        producer="SpeechQueueConsumer._is_speakable",
                        consumer="speech_queue",
                        source_ref="speech/queue_consumer.py::_speak_one",
                        entity_ref=f"beliefs.speech_queue:{qid}",
                        outcome="suppressed",
                        payload={"queue_id": qid, "reason": "non_speakable_content"},
                    )
                log.info("speech suppressed (non-speakable content) id=%s chars=%d",
                         qid, len(content))
                trace_outcome = "suppressed"
                return

            self.writer.write(
                "UPDATE speech_queue SET status='speaking' WHERE id=?", (qid,)
            )
            if trace_handle is not None:
                _trace_record(
                    trace_api, trace_handle, "synthesis_started",
                    producer="SpeechQueueConsumer._speak_one",
                    consumer="KokoroBackend.synth",
                    source_ref="speech/queue_consumer.py::_speak_one",
                    entity_ref=f"beliefs.speech_queue:{qid}",
                    outcome="speaking",
                    payload={"queue_id": qid, "voice": voice},
                )
            playback_completed = False
            try:
                audio, sr = self.backend.synth(content, voice=voice)
                self.player.play(audio, sr)
                playback_completed = True
                if trace_handle is not None:
                    _trace_record(
                        trace_api, trace_handle, "audio_playback_completed",
                        producer="Player.play",
                        consumer="SpeechQueueConsumer._speak_one",
                        source_ref="speech/queue_consumer.py::_speak_one",
                        entity_ref=f"beliefs.speech_queue:{qid}",
                        outcome="played",
                        payload={"queue_id": qid, "sample_rate": sr},
                    )
                self.writer.write(
                    "UPDATE speech_queue SET status='spoken', spoken_at=? WHERE id=?",
                    (time.time(), qid),
                )
                log.info("spoke belief_id=%s (%d chars)", row["belief_id"], len(content))
                trace_outcome = "spoken"
            except Exception as e:
                log.error("synth/play failed on id=%s: %s", qid, e)
                self.writer.write(
                    "UPDATE speech_queue SET status='failed', error=? WHERE id=?",
                    (str(e), qid),
                )
                if trace_handle is not None:
                    _trace_record(
                        trace_api, trace_handle,
                        "queue_status_write_failed" if playback_completed else "audio_playback_failed",
                        producer="SpeechQueueConsumer._speak_one",
                        consumer="speech_queue",
                        source_ref="speech/queue_consumer.py::_speak_one",
                        entity_ref=f"beliefs.speech_queue:{qid}",
                        outcome="status_write_failed" if playback_completed else "failed",
                        payload={"queue_id": qid, "error_type": type(e).__name__},
                    )
                trace_outcome = "failed"
        finally:
            if trace_handle is not None:
                try:
                    trace_api.end_trace(
                        trace_handle,
                        source_ref="speech/queue_consumer.py::SpeechQueueConsumer._speak_one",
                        entity_ref=f"beliefs.speech_queue:{qid}",
                        outcome=trace_outcome,
                    )
                except Exception:
                    pass
