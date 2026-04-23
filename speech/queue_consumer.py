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


class SpeechQueueConsumer(threading.Thread):
    def __init__(self, writer, reader, config: Optional[SpeechConfig] = None) -> None:
        super().__init__(name="nex5.speech.consumer", daemon=True)
        self.writer = writer
        self.reader = reader
        self.config = config or SpeechConfig.from_env()
        self.backend = KokoroBackend(
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
        try:
            self.backend.load()
        except Exception as e:
            log.error("Kokoro did not load, speech disabled: %s", e)
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
        self.writer.write(
            "UPDATE speech_queue SET status='speaking' WHERE id=?", (qid,)
        )
        try:
            audio, sr = self.backend.synth(content)
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
