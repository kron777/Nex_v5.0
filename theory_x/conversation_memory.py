"""conversation_memory.py — ConversationMemory: dialogue history node (DOCTRINE §5).

Reads the last N messages from conversations.db/messages for the current session.
Decay is implicit via LIMIT. Durable across restarts. No in-memory store.

Implements SentienceNode protocol (DOCTRINE §4):
  name, tick(context), decay(now), state(session_id, now)

Per-session access via state(session_id=...); not registered in the
process-lifetime SentienceNode registry.

Logging: /tmp/nex5_conversation_memory.log
"""
from __future__ import annotations

import datetime
import logging
import sqlite3
from typing import Any, Optional

__all__ = ["ConversationMemory"]

logger = logging.getLogger("theory_x.conversation_memory")

_CM_LOG = "/tmp/nex5_conversation_memory.log"


class ConversationMemory:
    """Dialogue history node — reads last n_turns messages from conversations.db.

    Implements SentienceNode protocol (DOCTRINE §4).
    decay() is a no-op: recency is implicit via ORDER BY DESC + LIMIT.
    Singleton per process; session_id passed at state() call time.
    """

    name: str = "conversation_memory"

    def __init__(self, db_path: str, n_turns: int = 8) -> None:
        self._db_path = db_path
        self._n_turns = n_turns

    # ── SentienceNode protocol ────────────────────────────────────────────────

    def tick(self, context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Lifecycle tick. context may carry {"session_id": str}."""
        session_id = (context or {}).get("session_id")
        return self.state(session_id=session_id)

    def decay(self, now: float) -> None:
        """No-op: decay implicit via LIMIT in state()."""

    def state(
        self,
        session_id: Optional[str] = None,
        now: Optional[float] = None,
    ) -> dict[str, Any]:
        """Return last n_turns messages for session_id, oldest first.

        Returns empty turns list if session_id is None or query fails.
        now is accepted for protocol conformance but unused (no wall-clock decay).
        """
        if session_id is None:
            return {"name": self.name, "session_id": None, "turns": [], "count": 0}

        turns: list[dict] = []
        try:
            con = sqlite3.connect(self._db_path, timeout=2.0)
            con.row_factory = sqlite3.Row
            rows = con.execute(
                "SELECT role, content, register, timestamp "
                "FROM messages "
                "WHERE session_id = ? "
                "ORDER BY timestamp DESC "
                "LIMIT ?",
                (session_id, self._n_turns),
            ).fetchall()
            con.close()
            # Reverse for chronological order (oldest first)
            turns = [dict(r) for r in reversed(rows)]
        except Exception as exc:
            logger.warning("conversation_memory query failed: %s", exc)

        try:
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            lines = [f"[{ts}] session={session_id[:8]} returned={len(turns)}\n"]
            for t in turns:
                t_ts = datetime.datetime.fromtimestamp(t["timestamp"]).strftime("%H:%M:%S")
                lines.append(f"  [{t['role']}] ({t_ts}) {t['content'][:80]!r}\n")
            with open(_CM_LOG, "a") as fh:
                fh.writelines(lines)
        except Exception:
            pass

        return {
            "name": self.name,
            "session_id": session_id,
            "turns": turns,
            "count": len(turns),
        }
