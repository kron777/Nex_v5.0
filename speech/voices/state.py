"""VoiceState — thread-safe current-voice holder with DB persistence."""
from __future__ import annotations

import logging
import threading
from typing import Optional

import errors
from speech.voices.registry import Voice, DEFAULT_VOICE, get_voice

log = logging.getLogger("nex5.speech.voices")
_LOG_SOURCE = "speech.voices"


class VoiceState:
    """Thread-safe current-voice holder, persisted to config table."""

    def __init__(self, beliefs_writer, beliefs_reader, initial_voice: str = DEFAULT_VOICE):
        self._writer = beliefs_writer
        self._reader = beliefs_reader
        self._lock = threading.Lock()
        self._current_id: str = initial_voice
        self._current: Voice = get_voice(initial_voice)

    def current(self) -> Voice:
        with self._lock:
            return self._current

    def current_name(self) -> str:
        with self._lock:
            return self._current_id

    def set_voice(self, voice_id: str) -> bool:
        """Switch to a new voice. Persists. Returns True if changed."""
        new = get_voice(voice_id)
        # get_voice falls back to default if not found — reject if fallback
        if new.id != voice_id:
            errors.record(
                f"Unknown voice '{voice_id}', ignoring",
                source=_LOG_SOURCE, level="WARNING",
            )
            return False
        with self._lock:
            if voice_id == self._current_id:
                return False
            old = self._current_id
            self._current_id = voice_id
            self._current = new
        self._persist(voice_id)
        errors.record(
            f"Voice changed: {old} → {voice_id}",
            source=_LOG_SOURCE, level="INFO",
        )
        return True

    def _persist(self, voice_id: str) -> None:
        try:
            self._writer.write(
                "INSERT OR REPLACE INTO config (key, value, updated_at) "
                "VALUES ('current_voice', ?, strftime('%s','now'))",
                (voice_id,),
            )
        except Exception as e:
            errors.record(
                f"Voice persist failed: {e}", source=_LOG_SOURCE, level="WARNING"
            )

    def _load(self) -> Optional[str]:
        try:
            rows = self._reader.read(
                "SELECT value FROM config WHERE key='current_voice'"
            )
            if rows:
                return rows[0]["value"]
        except Exception:
            pass
        return None


def build_voice_state(writers: dict, readers: dict) -> VoiceState:
    """Factory: load persisted voice if any, else default."""
    from speech.voices.registry import enumerate_voices
    beliefs_writer = writers["beliefs"]
    beliefs_reader = readers["beliefs"]

    state = VoiceState(beliefs_writer, beliefs_reader, DEFAULT_VOICE)
    persisted = state._load()
    if persisted:
        known_ids = {v.id for v in enumerate_voices()}
        if persisted in known_ids:
            state._current_id = persisted
            state._current = get_voice(persisted)

    return state
