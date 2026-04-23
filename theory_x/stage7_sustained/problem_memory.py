"""Problem Memory — working memory that persists open problems across conversations.

NEX can hold a problem, accumulate observations over days, and resume it
in any future conversation where the topic matches.
"""
from __future__ import annotations

import json
import time
from typing import Optional

import errors
from substrate import Writer, Reader

THEORY_X_STAGE = 7

_LOG_SOURCE = "problem_memory"


class ProblemMemory:
    def __init__(self, conversations_writer: Writer,
                 conversations_reader: Reader) -> None:
        self._writer = conversations_writer
        self._reader = conversations_reader

    def open(self, title: str, description: str) -> int:
        """Write a new open problem. Returns its id."""
        now = time.time()
        rowid = self._writer.write(
            "INSERT INTO open_problems "
            "(title, description, state, created_at, last_touched_at) "
            "VALUES (?, ?, 'open', ?, ?)",
            (title, description, now, now),
        )
        errors.record(
            f"problem opened: '{title}' (id={rowid})",
            source=_LOG_SOURCE, level="INFO",
        )
        return rowid

    def observe(self, problem_id: int, observation: str) -> None:
        """Append an observation to the problem's observations list."""
        row = self._reader.read_one(
            "SELECT observations FROM open_problems WHERE id = ?",
            (problem_id,),
        )
        if row is None:
            return
        try:
            obs_list = json.loads(row["observations"] or "[]")
        except (json.JSONDecodeError, TypeError):
            obs_list = []
        obs_list.append({"text": observation, "ts": time.time()})
        self._writer.write(
            "UPDATE open_problems SET observations = ?, last_touched_at = ? WHERE id = ?",
            (json.dumps(obs_list), time.time(), problem_id),
        )

    def update_plan(self, problem_id: int, plan: str) -> None:
        """Update the plan field."""
        self._writer.write(
            "UPDATE open_problems SET plan = ?, last_touched_at = ? WHERE id = ?",
            (plan, time.time(), problem_id),
        )

    def close(self, problem_id: int) -> None:
        """Mark problem as closed."""
        now = time.time()
        self._writer.write(
            "UPDATE open_problems SET state = 'closed', resolved_at = ?, "
            "last_touched_at = ? WHERE id = ?",
            (now, now, problem_id),
        )
        errors.record(
            f"problem {problem_id} closed",
            source=_LOG_SOURCE, level="INFO",
        )

    def resume(self, problem_id: int) -> Optional[dict]:
        """Return full problem record with parsed observations list."""
        row = self._reader.read_one(
            "SELECT id, title, description, state, created_at, last_touched_at, "
            "plan, observations, resolved_at FROM open_problems WHERE id = ?",
            (problem_id,),
        )
        if row is None:
            return None
        d = dict(row)
        try:
            d["observations"] = json.loads(d["observations"] or "[]")
        except (json.JSONDecodeError, TypeError):
            d["observations"] = []
        return d

    def list_open(self) -> list[dict]:
        """Return all open problems ordered by last_touched_at DESC."""
        rows = self._reader.read(
            "SELECT id, title, description, state, created_at, last_touched_at, "
            "plan, observations FROM open_problems WHERE state = 'open' "
            "ORDER BY last_touched_at DESC"
        )
        result = []
        for row in rows:
            d = dict(row)
            try:
                d["observations"] = json.loads(d["observations"] or "[]")
            except (json.JSONDecodeError, TypeError):
                d["observations"] = []
            result.append(d)
        return result

    def format_for_prompt(self, problem_id: int) -> str:
        """Format a problem as a compact block for system prompt injection."""
        p = self.resume(problem_id)
        if p is None:
            return ""
        plan_str = p["plan"] or "none yet"
        lines = [
            f"Open problem: {p['title']}",
            f"Description: {p['description']}",
            f"Plan: {plan_str}",
        ]
        obs = p["observations"]
        if obs:
            lines.append("Observations so far:")
            for o in obs:
                text = o["text"] if isinstance(o, dict) else str(o)
                lines.append(f"- {text}")
        return "\n".join(lines)

    def find_matching(self, query: str) -> list[dict]:
        """Return open problems whose title or description share keywords with query."""
        open_problems = self.list_open()
        if not query or not open_problems:
            return []
        query_words = set(query.lower().split())
        matches = []
        for p in open_problems:
            candidate = (p["title"] + " " + p["description"]).lower()
            candidate_words = set(candidate.split())
            if query_words & candidate_words:
                matches.append(p)
        return matches
