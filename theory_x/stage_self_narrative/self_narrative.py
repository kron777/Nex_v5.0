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

    # §9 self-rut-awareness: when recent quality has been flat for a sustained
    # stretch, write HER a first-person self-observation that she circled the
    # same frames without surprising herself. This is a MIRROR, not a command —
    # it enters narrative_log, surfaces back via format_for_prompt(), and her
    # own reflective loops decide what to do with it. Throttled so she does not
    # spam herself. Reads genius_tags.tagged_at (same signal the governor uses).
    _RUT_MIN_INTERVAL = 7200   # at most one rut-notice every 2h
    _RUT_WINDOW       = 5400   # look back 90 min for striking-rate
    _RUT_RATE_MAX     = 0.05   # <=5% striking = trough

    def tick(self, context=None) -> dict[str, Any]:
        try:
            import os as _os
            if _os.environ.get("NEX5_RUT_MIRROR_OFF") != "1":
                self._maybe_notice_rut()
        except Exception as _e:
            errors.record(f"self_narrative.rut_tick: {_e}", source=_LOG_SOURCE, exc=_e)
        return self.state()

    def _maybe_notice_rut(self) -> None:
        now = time.time()
        # throttle: skip if we wrote a rut-notice recently
        try:
            last = self._reader.read(
                "SELECT MAX(created_at) AS t FROM narrative_log WHERE trigger = ?",
                ("rut_notice",),
            )
            last_t = (last[0]["t"] if last and last[0]["t"] is not None else 0) or 0
            if now - float(last_t) < self._RUT_MIN_INTERVAL:
                return
        except Exception:
            pass
        # read recent striking-rate
        try:
            rows = self._reader.read(
                "SELECT class FROM genius_tags WHERE tagged_at >= ?",
                (now - self._RUT_WINDOW,),
            )
        except Exception:
            return
        if not rows or len(rows) < 4:
            return
        striking = sum(
            1 for r in rows
            if (r["class"] if hasattr(r, "__getitem__") else getattr(r, "class", "")) == "STRIKING"
        )
        rate = striking / len(rows)
        if rate > self._RUT_RATE_MAX:
            return
        # in a trough — write her a self-observation she will encounter
        note = (
            "I notice my recent thinking has circled the same few frames "
            "without surprising me. Many thoughts, little that landed. "
            "Perhaps it is time to reach for something I have not touched."
        )
        self.write_narrative(note, trigger="rut_notice", source_id=None)
        try:
            log = __import__("logging").getLogger(_LOG_SOURCE)
            log.info("self_narrative: RUT NOTICE written (striking=%.0f%%, n=%d)",
                     rate * 100, len(rows))
        except Exception:
            pass

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
