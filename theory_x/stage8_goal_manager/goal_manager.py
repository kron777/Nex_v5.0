"""Goal Manager — explicit goal stack with priority arbitration (DOCTRINE §5 row 8).

NEX holds explicit goals — directional commitments that organize cognitive effort.
Goals are distinct from open problems (ProblemMemory): a problem is "I don't know X";
a goal is "I am working toward Y." Goals may optionally reference a related problem.

Implements SentienceNode protocol (DOCTRINE §4):
  name, tick(context), decay(now), state(now=None)

PHASE 15 GOAL MANAGER 2026-05-09: §5 row 8 port. Per DOCTRINE §1 framing —
Goal Manager realizes the human function of holding explicit targets that organize
cognitive effort. Option A: minimal port — belief_text injection only; no EC or
retrieval bias. Reversion: drop goals table migration, remove module + tests,
remove server.py wiring.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

import errors
from substrate import Writer, Reader

__all__ = ["GoalManager"]

THEORY_X_STAGE = 8

_LOG_SOURCE = "goal_manager"


class GoalManager:
    name: str = "goal_manager"
    _STALE_DAYS: int = 60
    _CACHE_TTL: float = 120.0

    def __init__(self, conversations_writer: Writer,
                 conversations_reader: Reader) -> None:
        self._writer = conversations_writer
        self._reader = conversations_reader
        self._lock = threading.Lock()
        self._cached_open: Optional[list] = None
        self._cache_ts: float = 0.0

    # ── SentienceNode protocol ────────────────────────────────────────────────

    def tick(self, context=None) -> dict:
        """Refresh open-goal cache; run arbitration; return state."""
        now = time.time()
        with self._lock:
            if self._cached_open is None or (now - self._cache_ts) > self._CACHE_TTL:
                self._cached_open = self.list_open()
                self._cache_ts = now
        return self.state()

    def decay(self, now: float) -> None:
        """Auto-close goals stale > _STALE_DAYS."""
        cutoff = now - self._STALE_DAYS * 86400
        self._writer.write(
            "UPDATE goals SET state='cancelled', completed_at=?, last_touched_at=? "
            "WHERE state='open' AND last_touched_at < ?",
            (now, now, cutoff),
        )
        with self._lock:
            self._cached_open = None

    def state(self, now: Optional[float] = None) -> dict:
        now = now or time.time()
        with self._lock:
            goals = self._cached_open or []
            oldest_age = None
            if goals:
                oldest_ts = min(g["last_touched_at"] for g in goals)
                oldest_age = round((now - oldest_ts) / 86400, 1)
            top3 = sorted(goals, key=lambda g: g["priority"], reverse=True)[:3]
            return {
                "name": self.name,
                "open_count": len(goals),
                "active_top3": [g["title"] for g in top3],
                "oldest_age_days": oldest_age,
                "cache_age_s": round(now - self._cache_ts, 1),
            }

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def open(self, title: str, description: str = "",
             priority: float = 0.5, source: str = "user",
             problem_id: Optional[int] = None) -> int:
        """Create a new open goal. Returns its id."""
        now = time.time()
        priority = max(0.0, min(1.0, float(priority)))
        rowid = self._writer.write(
            "INSERT INTO goals "
            "(title, description, priority, state, source, created_at, "
            "last_touched_at, problem_id) "
            "VALUES (?, ?, ?, 'open', ?, ?, ?, ?)",
            (title, description, priority, source, now, now, problem_id),
        )
        errors.record(
            f"goal opened: '{title}' priority={priority:.2f} (id={rowid})",
            source=_LOG_SOURCE, level="INFO",
        )
        with self._lock:
            self._cached_open = None
        return rowid

    def complete(self, goal_id: int) -> None:
        """Mark goal as completed."""
        now = time.time()
        self._writer.write(
            "UPDATE goals SET state='completed', completed_at=?, "
            "last_touched_at=? WHERE id=?",
            (now, now, goal_id),
        )
        errors.record(f"goal {goal_id} completed", source=_LOG_SOURCE, level="INFO")
        with self._lock:
            self._cached_open = None

    def cancel(self, goal_id: int) -> None:
        """Mark goal as cancelled."""
        now = time.time()
        self._writer.write(
            "UPDATE goals SET state='cancelled', completed_at=?, "
            "last_touched_at=? WHERE id=?",
            (now, now, goal_id),
        )
        errors.record(f"goal {goal_id} cancelled", source=_LOG_SOURCE, level="INFO")
        with self._lock:
            self._cached_open = None

    def update_priority(self, goal_id: int, priority: float) -> None:
        """Update the priority field."""
        priority = max(0.0, min(1.0, float(priority)))
        self._writer.write(
            "UPDATE goals SET priority=?, last_touched_at=? WHERE id=?",
            (priority, time.time(), goal_id),
        )
        with self._lock:
            self._cached_open = None

    def resume(self, goal_id: int) -> Optional[dict]:
        """Return full goal record."""
        row = self._reader.read_one(
            "SELECT id, title, description, priority, state, source, "
            "created_at, last_touched_at, completed_at, problem_id "
            "FROM goals WHERE id=?",
            (goal_id,),
        )
        if row is None:
            return None
        return dict(row)

    def list_open(self) -> list[dict]:
        """Return all open goals ordered by priority DESC."""
        rows = self._reader.read(
            "SELECT id, title, description, priority, state, source, "
            "created_at, last_touched_at, completed_at, problem_id "
            "FROM goals WHERE state='open' "
            "ORDER BY priority DESC, created_at ASC"
        )
        return [dict(r) for r in rows]

    def get_active(self) -> Optional[dict]:
        """Return top-priority open goal for belief_text injection."""
        with self._lock:
            cached = self._cached_open
        if cached is None:
            cached = self.list_open()
        if not cached:
            return None
        return max(cached, key=lambda g: g["priority"])

    def format_for_prompt(self, goal_id: int) -> str:
        """Format active goal as a compact block for belief_text injection."""
        g = self.resume(goal_id)
        if g is None:
            return ""
        lines = [f"Current goal: {g['title']}"]
        if g["description"]:
            lines.append(f"Working on: {g['description']}")
        return "\n".join(lines)
