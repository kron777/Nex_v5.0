"""Crystallization — cumulative high-focus time precipitates a Tier 7 belief.

A branch crystallizes when it accumulates CRYSTALLIZATION_THRESHOLD_SECONDS of
high-focus time (focus at e/f/g) within a rolling CRYSTALLIZATION_WINDOW_SECONDS
window (default: 300s cumulative within 30 minutes).
"""
from __future__ import annotations

import json
import time
from collections import deque
from typing import Optional

import errors
from substrate import Writer, Reader
from .bonsai import BonsaiTree

THEORY_X_STAGE = 2

CRYSTALLIZATION_WINDOW_SECONDS = 1800    # 30-minute rolling window
CRYSTALLIZATION_THRESHOLD_SECONDS = 300  # 300s cumulative high-focus within window
HIGH_FOCUS_LEVELS = {"e", "f", "g"}
_LOG_SOURCE = "crystallization"
_DEDUP_WINDOW_SECONDS = 86400  # 24 hours


class Crystallizer:
    def __init__(self, tree: BonsaiTree, beliefs_writer: Writer,
                 dynamic_writer: Writer, dynamic_reader: Reader) -> None:
        self._tree = tree
        self._beliefs_writer = beliefs_writer
        self._dynamic_writer = dynamic_writer
        self._dynamic_reader = dynamic_reader
        # per-branch: deque of (timestamp, focus_level) records
        self._focus_history: dict[str, deque] = {}
        # per-branch: last crystallization timestamp (to enforce window dedup)
        self._last_crystallized: dict[str, float] = {}

    def check_all(self) -> list[str]:
        """Check all branches; crystallize those with enough cumulative high focus.

        Returns list of branch_ids that crystallized this pass.
        """
        crystallized = []
        now = time.time()
        cutoff = now - CRYSTALLIZATION_WINDOW_SECONDS

        for node in self._tree.all_nodes():
            bid = node.branch_id
            focus = node.focus_increment

            # Append current observation
            if bid not in self._focus_history:
                self._focus_history[bid] = deque()
            self._focus_history[bid].append((now, focus))

            # Trim entries older than window
            hist = self._focus_history[bid]
            while hist and hist[0][0] < cutoff:
                hist.popleft()

            # Count cumulative high-focus seconds (each entry = 60s loop tick)
            high_ticks = sum(1 for _, f in hist if f in HIGH_FOCUS_LEVELS)
            # Each loop tick represents ~60 seconds of observation
            cumulative_seconds = high_ticks * 60

            if cumulative_seconds < CRYSTALLIZATION_THRESHOLD_SECONDS:
                continue

            # No crystallization in last window
            last = self._last_crystallized.get(bid, 0.0)
            if now - last < CRYSTALLIZATION_WINDOW_SECONDS:
                continue

            did_crystallize = self._crystallize(node, now)
            if did_crystallize:
                crystallized.append(bid)
                self._last_crystallized[bid] = now
                # Clear history so branch must re-accumulate
                self._focus_history[bid].clear()

        return crystallized

    def _crystallize(self, node, ts: float) -> bool:
        """Precipitate one Tier 7 belief. Returns True if written."""
        branch_id = node.branch_id
        content = self._extract_content(branch_id)
        if content is None:
            return False

        belief_content = f"[{branch_id}] {content}"

        # Dedup guard
        if self._is_duplicate(belief_content):
            return False

        # Write belief to beliefs.db
        belief_id = self._write_belief(belief_content, branch_id, ts)

        # Log crystallization event to dynamic.db
        self._dynamic_writer.write(
            "INSERT INTO crystallization_events (ts, branch_id, belief_id, content, magnitude) "
            "VALUES (?, ?, ?, ?, ?)",
            (ts, branch_id, belief_id, belief_content, node.focus_num),
        )

        errors.record(
            f"crystallized belief for branch '{branch_id}': {belief_content[:80]}",
            source=_LOG_SOURCE,
            level="INFO",
        )
        return True

    def _extract_content(self, branch_id: str) -> Optional[str]:
        """Get the most prominent content from recent pipeline events for this branch."""
        try:
            rows = self._dynamic_reader.read(
                "SELECT sensation_source, meta, magnitude FROM pipeline_events "
                "WHERE branch_id = ? ORDER BY magnitude DESC, ts DESC LIMIT 10",
                (branch_id,),
            )
        except Exception as exc:
            errors.record(f"crystallization read error: {exc}", source=_LOG_SOURCE, exc=exc)
            return None

        if not rows:
            return f"sustained attention on {branch_id}"

        best_row = rows[0]
        meta_str = best_row["meta"]
        if meta_str:
            try:
                meta = json.loads(meta_str)
                if isinstance(meta, dict) and meta.get("title"):
                    return meta["title"]
            except (json.JSONDecodeError, TypeError):
                pass
        return best_row["sensation_source"] or f"sustained attention on {branch_id}"

    def _is_duplicate(self, content: str) -> bool:
        try:
            cutoff = time.time() - _DEDUP_WINDOW_SECONDS
            row = self._dynamic_reader.read_one(
                "SELECT id FROM crystallization_events "
                "WHERE content = ? AND ts >= ?",
                (content, cutoff),
            )
            return bool(row)
        except Exception as exc:
            errors.record(f"crystallization dedup error: {exc}", source=_LOG_SOURCE, exc=exc)
            return False

    def _write_belief(self, content: str, branch_id: str, ts: float) -> Optional[int]:
        """Write Tier 7 Impression to beliefs.db. Returns rowid or None."""
        try:
            rowid = self._beliefs_writer.write(
                "INSERT INTO beliefs "
                "(content, tier, confidence, created_at, branch_id, source, locked) "
                "VALUES (?, 7, 0.15, ?, ?, 'precipitated_from_dynamic', 0)",
                (content, int(ts), branch_id),
            )
            return rowid
        except Exception as exc:
            errors.record(f"crystallization belief write error: {exc}", source=_LOG_SOURCE, exc=exc)
            return None
