"""SelfNarrative — Phase 26 (DOCTRINE §5 row 11).

Accumulates substrate-resident narrative entries when significant cognitive
events occur. Does NOT generate text at output time.

Write-triggers v1:
  1. Goal completion — called by GoalManager.complete()
  2. Groove alert    — called by Metacognition.tick()

format_for_prompt() reads existing entries and returns them as-is.
No synthesis. No LLM call. Substrate solves the reply; LLM speaks it.
"""
from __future__ import annotations

import time
from typing import Any, Optional

import errors
from substrate import Writer, Reader

__all__ = ["SelfNarrative"]

THEORY_X_STAGE = "self_narrative"

_LOG_SOURCE = "self_narrative"
_DEFAULT_N = 5


def _age_str(created_at: float, now: float) -> str:
    delta = now - created_at
    if delta < 3600:
        return f"{int(delta // 60)}m ago"
    if delta < 86400:
        return f"{int(delta // 3600)}h ago"
    if delta < 172800:
        return "yesterday"
    return f"{int(delta // 86400)} days ago"


class SelfNarrative:
    """Accumulate and retrieve self-oriented narrative entries.

    Implements SentienceNode protocol (DOCTRINE §4).
    tick() and decay() are no-ops for v1.
    """

    name: str = "self_narrative"

    def __init__(
        self,
        conversations_writer: Writer,
        conversations_reader: Reader,
    ) -> None:
        self._writer = conversations_writer
        self._reader = conversations_reader

    # ── Public API ────────────────────────────────────────────────────────────

    def write_narrative(
        self,
        content: str,
        trigger: str,
        source_id: Optional[int],
    ) -> None:
        """Insert one row into narrative_log. Never raises."""
        try:
            self._writer.write(
                "INSERT INTO narrative_log (content, trigger, source_id, created_at) "
                "VALUES (?, ?, ?, ?)",
                (content, trigger, source_id, time.time()),
            )
        except Exception as exc:
            errors.record(
                f"self_narrative.write_narrative: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )

    def format_for_prompt(self, context=None) -> str:
        """Return recent narrative entries as bullet lines, or '' if none.

        Filters by context.current_topic when present (case-insensitive LIKE).
        Returns at most _DEFAULT_N entries.
        """
        try:
            topic = None
            if context is not None:
                topic = getattr(context, "current_topic", None) or None

            now = time.time()
            if topic:
                rows = self._reader.read(
                    "SELECT content, created_at FROM narrative_log "
                    "WHERE LOWER(content) LIKE LOWER(?) "
                    "ORDER BY created_at DESC LIMIT ?",
                    (f"%{topic}%", _DEFAULT_N),
                )
            else:
                rows = self._reader.read(
                    "SELECT content, created_at FROM narrative_log "
                    "ORDER BY created_at DESC LIMIT ?",
                    (_DEFAULT_N,),
                )

            if not rows:
                return ""
            return "\n".join(
                f"- {r['content']} ({_age_str(r['created_at'], now)})"
                for r in rows
            )
        except Exception as exc:
            errors.record(
                f"self_narrative.format_for_prompt: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )
            return ""

    # ── SentienceNode protocol ────────────────────────────────────────────────

    def tick(self, context=None) -> dict[str, Any]:
        return self.state()

    def decay(self, now: float) -> None:
        pass

    def state(self, now: float = None) -> dict[str, Any]:
        try:
            rows = self._reader.read(
                "SELECT COUNT(*) AS n, MAX(created_at) AS last_ts "
                "FROM narrative_log"
            )
            if rows:
                return {
                    "name": self.name,
                    "narrative_count": int(rows[0]["n"] or 0),
                    "last_write_ts": rows[0]["last_ts"],
                }
        except Exception as exc:
            errors.record(
                f"self_narrative.state: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )
        return {"name": self.name, "narrative_count": 0, "last_write_ts": None}
