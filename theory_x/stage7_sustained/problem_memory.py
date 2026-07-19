"""Problem Memory — working memory that persists open problems across conversations.

NEX can hold a problem, accumulate observations over days, and resume it
in any future conversation where the topic matches.

Implements SentienceNode protocol (DOCTRINE §4):
  name, tick(context), decay(now), state(now=None)

PHASE 13 SUSTAINED ATTENTION 2026-05-09: SentienceNode protocol added per
SUSTAINED_ATTENTION_DESIGN.md §7 (Option A). find_matching() replaced with
stopwords + ≥2 content-word overlap version. Reversion: restore CRUD-only
class and word-overlap find_matching from commit 950e388 parent.
"""
from __future__ import annotations

import json
import sys
import threading
import time
from typing import Optional

import errors
from substrate import Writer, Reader

_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "do", "does", "did", "have", "has", "had", "will", "would",
    "can", "could", "should", "may", "might", "shall",
    "i", "you", "he", "she", "it", "we", "they",
    "what", "how", "why", "when", "where", "which", "who",
    "this", "that", "these", "those", "and", "or", "but",
    "of", "in", "on", "at", "to", "for", "with", "about",
    "not", "no", "so", "if", "as",
}

THEORY_X_STAGE = 7

_LOG_SOURCE = "problem_memory"

# PHASE 13 punctuation fix 2026-05-09: find_matching tokenization stripped via
# _clean_tokens helper. Surfaced by Q4 seeding — P1 title "...recursion?"
# didn't match clean query "recursion". Reversion: inline the set comprehension
# back into find_matching and remove this function.
_PUNCT = '.,?!;:\'"'

def _clean_tokens(text: str) -> set[str]:
    """Lowercase-split text, strip punctuation, filter stopwords and short tokens."""
    tokens = (w.strip(_PUNCT) for w in text.lower().split())
    return {w for w in tokens if w not in _STOPWORDS and len(w) > 2}


class ProblemMemory:
    name: str = "problem_memory"
    _STALE_DAYS: int = 30
    _CACHE_TTL: float = 120.0  # seconds

    def __init__(self, conversations_writer: Writer,
                 conversations_reader: Reader,
                 self_narrative=None) -> None:
        self._writer = conversations_writer
        self._reader = conversations_reader
        self._self_narrative = self_narrative
        self._lock = threading.Lock()
        self._cached_open: Optional[list] = None
        self._cache_ts: float = 0.0

    # ── SentienceNode protocol ────────────────────────────────────────────────

    def tick(self, context=None) -> dict:
        """Refresh open-problem cache; return state."""
        now = time.time()
        with self._lock:
            if self._cached_open is None or (now - self._cache_ts) > self._CACHE_TTL:
                self._cached_open = self.list_open()
                self._cache_ts = now
        return self.state()

    def decay(self, now: float) -> None:
        """Auto-close problems stale > _STALE_DAYS."""
        cutoff = now - self._STALE_DAYS * 86400
        self._writer.write(
            "UPDATE open_problems SET state='closed', resolved_at=?, last_touched_at=? "
            "WHERE state='open' AND last_touched_at < ?",
            (now, now, cutoff),
        )
        with self._lock:
            self._cached_open = None  # invalidate cache after decay

    def state(self, now: Optional[float] = None) -> dict:
        now = now or time.time()
        with self._lock:
            problems = self._cached_open or []
            oldest_age = None
            if problems:
                oldest_ts = min(p["last_touched_at"] for p in problems)
                oldest_age = round((now - oldest_ts) / 86400, 1)
            return {
                "name": self.name,
                "open_count": len(problems),
                "oldest_age_days": oldest_age,
                "cache_age_s": round(now - self._cache_ts, 1),
            }

    def open(self, title: str, description: str) -> int:
        """Write a new open problem. Returns its id."""
        now = time.time()
        _content_for_tags = (title or "") + " " + (description or "")
        try:
            from theory_x.tag_protocol import generate as _tag_gen
            _tags_json = json.dumps(_tag_gen(_content_for_tags))
        except Exception as _e:
            print(f"open_problems tag gen failed: {_e}", file=sys.stderr)
            _tags_json = "[]"
        rowid = self._writer.write(
            "INSERT INTO open_problems "
            "(title, description, state, created_at, last_touched_at, tags) "
            "VALUES (?, ?, 'open', ?, ?, ?)",
            (title, description, now, now, _tags_json),
        )
        errors.record(
            f"problem opened: '{title}' (id={rowid})",
            source=_LOG_SOURCE, level="INFO",
        )
        if self._self_narrative is not None:
            try:
                self._self_narrative.write_narrative(
                    f"Beginning to track open problem: '{title}'",
                    "problem_opened",
                    rowid,
                )
            except Exception as exc:
                errors.record(
                    f"self_narrative problem_opened: {exc}",
                    source=_LOG_SOURCE, exc=exc,
                )
        return rowid

    def observe(self, problem_id: int, observation: str,
                source: Optional[str] = None) -> bool:
        """Append an observation to the problem's observations list.

        No-ops (returns False) if `observation` is byte-identical to the
        last entry already on file. Session 39 found focus_loop.py's own
        append path has no such guard and re-stamps the same stale text on
        every 60s tick with nothing new to say -- that's how a problem hits
        the ocount>=10 close gate in under two hours instead of over days.
        Not fixing focus_loop.py here (separate, untouched call path) but
        this method now refuses to repeat that specific mistake for any
        caller that goes through it, including the new problem-injection
        write-back (source="problem_injection", session 40).

        Returns True if a new entry was actually appended.
        """
        row = self._reader.read_one(
            "SELECT observations FROM open_problems WHERE id = ?",
            (problem_id,),
        )
        if row is None:
            return False
        try:
            obs_list = json.loads(row["observations"] or "[]")
        except (json.JSONDecodeError, TypeError):
            obs_list = []
        if obs_list:
            _last = obs_list[-1]
            _last_text = _last.get("text", "") if isinstance(_last, dict) else str(_last)
            if observation.strip() == _last_text.strip():
                return False
        entry = {"text": observation, "ts": time.time()}
        if source:
            entry["source"] = source
        obs_list.append(entry)
        self._writer.write(
            "UPDATE open_problems SET observations = ?, last_touched_at = ? WHERE id = ?",
            (json.dumps(obs_list), time.time(), problem_id),
        )
        return True

    def update_plan(self, problem_id: int, plan: str) -> None:
        """Update the plan field."""
        self._writer.write(
            "UPDATE open_problems SET plan = ?, last_touched_at = ? WHERE id = ?",
            (plan, time.time(), problem_id),
        )

    def close(self, problem_id: int) -> None:
        """Mark problem as closed."""
        now = time.time()
        _title = f"problem {problem_id}"
        if self._self_narrative is not None:
            try:
                _row = self._reader.read_one(
                    "SELECT title FROM open_problems WHERE id = ?", (problem_id,)
                )
                if _row:
                    _title = _row["title"]
            except Exception:
                pass
        self._writer.write(
            "UPDATE open_problems SET state = 'closed', resolved_at = ?, "
            "last_touched_at = ? WHERE id = ?",
            (now, now, problem_id),
        )
        errors.record(
            f"problem {problem_id} closed",
            source=_LOG_SOURCE, level="INFO",
        )
        if self._self_narrative is not None:
            try:
                self._self_narrative.write_narrative(
                    f"Problem resolved: '{_title}'",
                    "problem_closed",
                    problem_id,
                )
            except Exception as exc:
                errors.record(
                    f"self_narrative problem_closed: {exc}",
                    source=_LOG_SOURCE, exc=exc,
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
        """Return open problems with ≥2 content-word overlap with query.

        Strips stopwords and short tokens before overlap comparison.
        Prevents spurious matches on common function words.
        """
        open_problems = self.list_open()
        if not query or not open_problems:
            return []
        query_words = _clean_tokens(query)
        if not query_words:
            return []
        matches = []
        for p in open_problems:
            candidate_words = _clean_tokens(p["title"] + " " + p["description"])
            if len(query_words & candidate_words) >= 2:
                matches.append(p)
        return matches

    # ── Session 40: problem-feedback loop selection ─────────────────────────

    _INJECTION_LOOKBACK_DAYS = 14
    _INJECTION_COOLDOWN_HOURS = 8.0
    _INJECTION_MIN_POOL = 3

    def select_for_injection(self, now: Optional[float] = None) -> Optional[dict]:
        """Pick a self-posed problem to re-surface into the fountain prompt.

        Pool: non-template, anchor-passing (theory_x.stage7_sustained.
        problem_classify.is_real_question -- one source of truth shared with
        scripts/problem_persistence.py), ANY state including closed --
        session 39 found "closed" currently means "hit the observation-count
        gate", not "resolved"; a closed problem with a real anchor is as
        valid a self-posed question as an open one. Limited to problems
        created within the last _INJECTION_LOOKBACK_DAYS days.

        Excludes any candidate injected within the last
        _INJECTION_COOLDOWN_HOURS, tracked via observations tagged
        source="problem_injection" specifically -- NOT last_touched_at,
        which is also written by focus_loop/reconcile and would wrongly
        suppress a candidate this mechanism has never actually surfaced.

        Returns None (skip injection entirely) if fewer than
        _INJECTION_MIN_POOL candidates survive the filter: LRU among 1-2
        members degenerates into forced repetition regardless of cooldown
        (session 40 Phase 1 boundary condition -- current live pool is 0
        open + 1 stuck, so this guard is not hypothetical on day one).
        """
        from theory_x.stage7_sustained.problem_classify import is_real_question

        now = now or time.time()
        cutoff = now - self._INJECTION_LOOKBACK_DAYS * 86400
        rows = self._reader.read(
            "SELECT id, title, description, observations FROM open_problems "
            "WHERE created_at > ?",
            (cutoff,),
        )

        pool = []
        for row in rows:
            title = row["title"] or ""
            desc = row["description"] or ""
            if not is_real_question(title, desc):
                continue
            try:
                obs = json.loads(row["observations"] or "[]")
            except (json.JSONDecodeError, TypeError):
                obs = []
            last_injected = None
            for o in obs:
                if isinstance(o, dict) and o.get("source") == "problem_injection":
                    ts = o.get("ts")
                    if ts and (last_injected is None or ts > last_injected):
                        last_injected = ts
            if (last_injected is not None
                    and (now - last_injected) < self._INJECTION_COOLDOWN_HOURS * 3600):
                continue
            pool.append({
                "id": row["id"], "title": title, "description": desc,
                "_last_injected": last_injected if last_injected is not None else -1.0,
            })

        if len(pool) < self._INJECTION_MIN_POOL:
            return None

        pool.sort(key=lambda p: p["_last_injected"])  # never-injected first, then oldest
        winner = pool[0]
        return {"id": winner["id"], "title": winner["title"], "description": winner["description"]}
