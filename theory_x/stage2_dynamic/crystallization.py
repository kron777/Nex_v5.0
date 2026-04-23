"""Crystallization — sustained high branch focus precipitates a Tier 7 belief.

When a branch holds focus at level e/f/g for CRYSTALLIZATION_HOLD_SECONDS
continuously, a new Impression (Tier 7) is written to beliefs.db.
"""
from __future__ import annotations

import json
import time
from typing import Optional

import errors
from substrate import Writer, Reader
from .bonsai import BonsaiTree, _num_to_focus

THEORY_X_STAGE = 2

CRYSTALLIZATION_HOLD_SECONDS = 300  # 5 minutes
_HIGH_FOCUS_LEVELS = {"e", "f", "g"}
_LOG_SOURCE = "crystallization"
_DEDUP_WINDOW_SECONDS = 86400  # 24 hours


class Crystallizer:
    def __init__(self, tree: BonsaiTree, beliefs_writer: Writer,
                 dynamic_writer: Writer, dynamic_reader: Reader) -> None:
        self._tree = tree
        self._beliefs_writer = beliefs_writer
        self._dynamic_writer = dynamic_writer
        self._dynamic_reader = dynamic_reader
        # per-branch: timestamp when this branch entered high focus (or None)
        self._focus_high_since: dict[str, Optional[float]] = {}

    def check_all(self) -> list[str]:
        """Check all branches; crystallize those at sustained high focus.

        Returns list of branch_ids that crystallized this pass.
        """
        crystallized = []
        now = time.time()
        for node in self._tree.all_nodes():
            bid = node.branch_id
            focus = node.focus_increment
            if focus in _HIGH_FOCUS_LEVELS:
                if self._focus_high_since.get(bid) is None:
                    self._focus_high_since[bid] = now
                elif now - self._focus_high_since[bid] >= CRYSTALLIZATION_HOLD_SECONDS:
                    did_crystallize = self._crystallize(node, now)
                    if did_crystallize:
                        crystallized.append(bid)
                    # reset regardless so branch can crystallize again
                    self._focus_high_since[bid] = None
            else:
                self._focus_high_since[bid] = None
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
            if row:
                return True
            # Also check beliefs.db via writer read (use beliefs reader if wired in)
            # We check dynamic crystallization_events as the dedup source
            return False
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
