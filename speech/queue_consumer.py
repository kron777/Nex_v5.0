"""Daemon thread that reads speech_queue and speaks pending entries."""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Optional

from .config import SpeechConfig
from .kokoro_backend import KokoroBackend
from .player import Player

log = logging.getLogger("nex5.speech.consumer")


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
                    if self._stop.wait(self.config.poll_interval_sec):
                        return
                    continue

                from nex_config import local_now
                now_hour = local_now().hour
                if self.config.in_quiet_hours(now_hour):
                    if self._stop.wait(self.config.poll_interval_sec * 5):
                        return
                    continue

                rows = self._pending()
                if self._stop.is_set():
                    return
                if not rows:
                    if self._stop.wait(self.config.poll_interval_sec):
                        return
                    continue

                self._speak_one(rows[0], stop_event=self._stop)

            except Exception as e:
                log.error("consumer loop error: %s", e)
                if self._stop.wait(self.config.poll_interval_sec):
                    return

    def _speak_one(self, row, *, stop_event: Optional[threading.Event] = None) -> None:
        if stop_event is not None and stop_event.is_set():
            return
        qid = row["id"]
        content = row["content"]
        trace = None
        trace_parent = None
        try:
            from influence_trace import take_speech_queue_trace
            linked = take_speech_queue_trace(row.get("belief_id"))
            if linked:
                trace, trace_parent = linked
        except Exception:
            trace = None
            trace_parent = None

        def trace_event(event: str, *, parent: Optional[str] = None,
                        metadata: Optional[dict] = None) -> Optional[str]:
            if trace is None:
                return None
            try:
                parents = [parent or trace_parent] if (parent or trace_parent) else []
                details = {"queue_id": qid, "belief_id": row.get("belief_id")}
                details.update(metadata or {})
                return trace.record("speech_queue", event, metadata=details,
                                    parent_ids=parents)
            except Exception:
                return None

        def _requeue_if_stopping(parent: Optional[str] = None) -> bool:
            if stop_event is None or not stop_event.is_set():
                return False
            self.writer.write(
                "UPDATE speech_queue SET status='pending' WHERE id=? AND status='speaking'",
                (qid,),
            )
            trace_event("synthesis_abandoned_shutdown", parent=parent)
            return True

        dequeue_event = trace_event("dequeued")
        # Use voice from VoiceState if available, else fall back to row voice or config
        voice = None
        if self._voice_state is not None:
            try:
                voice = self._voice_state.current_name()
            except Exception:
                pass
        if not voice:
            voice = row.get("voice") or self.config.voice
        if stop_event is not None and stop_event.is_set():
            return
        if not _is_speakable(content):
            try:
                self.writer.write(
                    "UPDATE speech_queue SET status='suppressed' WHERE id=?", (qid,)
                )
            except Exception as e:
                trace_event(
                    "queue_status_suppressed_write_failed", parent=dequeue_event,
                    metadata={"error_type": type(e).__name__},
                )
                raise
            trace_event("suppressed", parent=dequeue_event)
            log.info("speech suppressed (non-speakable content) id=%s chars=%d",
                     qid, len(content))
            return

        try:
            self.writer.write(
                "UPDATE speech_queue SET status='speaking' WHERE id=?", (qid,)
            )
        except Exception as e:
            trace_event("queue_status_speaking_write_failed", parent=dequeue_event,
                        metadata={"error_type": type(e).__name__})
            raise
        synthesis_started = trace_event("synthesis_started", parent=dequeue_event)
        failure_parent = trace_parent
        if _requeue_if_stopping(synthesis_started):
            return
        try:
            try:
                audio, sr = self.backend.synth(content, voice=voice)
                synthesis_completed = trace_event(
                    "synthesis_completed", parent=synthesis_started
                )
                if _requeue_if_stopping(synthesis_completed):
                    return
            except Exception as e:
                failure_parent = trace_event(
                    "synthesis_failed", parent=synthesis_started,
                    metadata={"error_type": type(e).__name__},
                ) or synthesis_started or trace_parent
                raise
            playback_started = trace_event(
                "playback_started", parent=synthesis_completed or synthesis_started
            )
            try:
                self.player.play(audio, sr)
                playback_completed = trace_event(
                    "playback_completed", parent=playback_started or synthesis_completed
                )
            except Exception as e:
                failure_parent = trace_event(
                    "playback_failed", parent=playback_started or synthesis_completed,
                    metadata={"error_type": type(e).__name__},
                ) or playback_started or synthesis_completed or trace_parent
                raise
            failure_parent = (
                playback_completed or playback_started
                or synthesis_completed or trace_parent
            )
            try:
                self.writer.write(
                    "UPDATE speech_queue SET status='spoken', spoken_at=? WHERE id=?",
                    (time.time(), qid),
                )
            except Exception as e:
                failure_parent = trace_event(
                    "queue_status_spoken_write_failed", parent=playback_completed,
                    metadata={"error_type": type(e).__name__},
                ) or playback_completed or playback_started or trace_parent
                raise
            trace_event("queue_status_spoken",
                        parent=playback_completed or playback_started)
            log.info("spoke belief_id=%s (%d chars)", row["belief_id"], len(content))
        except Exception as e:
            log.error("synth/play failed on id=%s: %s", qid, e)
            try:
                self.writer.write(
                    "UPDATE speech_queue SET status='failed', error=? WHERE id=?",
                    (str(e), qid),
                )
            except Exception as write_error:
                trace_event(
                    "queue_status_failed_write_failed", parent=failure_parent,
                    metadata={"error_type": type(write_error).__name__},
                )
                raise
            trace_event(
                "queue_status_failed", parent=failure_parent,
                metadata={"error_type": type(e).__name__},
            )
