"""Mode state — tracks current mode, persists to DB."""
from __future__ import annotations

import logging
import threading
from typing import Optional

import errors
from theory_x.modes.modes import Mode, get_mode, DEFAULT_MODE

log = logging.getLogger(__name__)
_LOG_SOURCE = "modes"


class ModeState:
    """Thread-safe current-mode holder with DB persistence."""

    def __init__(self, beliefs_writer, beliefs_reader, initial_mode: str = DEFAULT_MODE):
        self._writer = beliefs_writer
        self._reader = beliefs_reader
        self._lock = threading.Lock()
        self._current_name: str = initial_mode
        self._current: Mode = get_mode(initial_mode)

    def current(self) -> Mode:
        with self._lock:
            return self._current

    def current_name(self) -> str:
        with self._lock:
            return self._current_name

    def set_mode(self, name: str) -> bool:
        """Switch to a new mode. Persists. Returns True if changed."""
        with self._lock:
            if name == self._current_name:
                return False
            new = get_mode(name)
            if new.name != name:
                errors.record(
                    f"Unknown mode '{name}', ignoring",
                    source=_LOG_SOURCE, level="WARNING",
                )
                return False
            old = self._current_name
            self._current_name = name
            self._current = new
            self._persist(name)
            errors.record(
                f"Mode changed: {old} → {name}",
                source=_LOG_SOURCE, level="INFO",
            )
            return True

    def _persist(self, name: str) -> None:
        try:
            self._writer.write(
                "INSERT OR REPLACE INTO config (key, value, updated_at) "
                "VALUES ('current_mode', ?, strftime('%s','now'))",
                (name,),
            )
        except Exception as e:
            errors.record(
                f"Mode persist failed: {e}",
                source=_LOG_SOURCE, level="WARNING",
            )

    def _load(self) -> Optional[str]:
        try:
            rows = self._reader.read(
                "SELECT value FROM config WHERE key='current_mode'"
            )
            if rows:
                return rows[0]["value"]
        except Exception:
            pass
        return None


def build_mode_state(writers: dict, readers: dict) -> ModeState:
    """Factory: load persisted mode if any, else default."""
    beliefs_writer = writers["beliefs"]
    beliefs_reader = readers["beliefs"]

    state = ModeState(beliefs_writer, beliefs_reader, DEFAULT_MODE)
    persisted = state._load()
    if persisted and persisted in __import__("theory_x.modes.modes", fromlist=["MODES"]).MODES:
        state._current_name = persisted
        state._current = get_mode(persisted)

    return state
