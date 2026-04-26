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
                    time.sleep(self.config.poll_interval_sec)
                    continue

                now_hour = datetime.now().hour
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
            log.info("speech suppressed (non-speakable content) id=%s chars=%d",
                     qid, len(content))
            return

        self.writer.write(
            "UPDATE speech_queue SET status='speaking' WHERE id=?", (qid,)
        )
        try:
            audio, sr = self.backend.synth(content, voice=voice)
            self.player.play(audio, sr)
            self.writer.write(
                "UPDATE speech_queue SET status='spoken', spoken_at=? WHERE id=?",
                (time.time(), qid),
            )
            log.info("spoke belief_id=%s (%d chars)", row["belief_id"], len(content))
        except Exception as e:
            log.error("synth/play failed on id=%s: %s", qid, e)
            self.writer.write(
                "UPDATE speech_queue SET status='failed', error=? WHERE id=?",
                (str(e), qid),
            )
