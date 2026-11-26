"""Pipeline hooks — connects A-F pipeline output to the promotion system.

PipelineHooks.on_pipeline_event() is called after step F. High-magnitude
events corroborate matching beliefs.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

import errors
from substrate import Reader
from .retrieval import _tokenize
from .promotion import BeliefPromoter

if TYPE_CHECKING:
    pass

THEORY_X_STAGE = 3

_LOG_SOURCE = "pipeline_hooks"
_CORROBORATION_MAGNITUDE_THRESHOLD = 0.6
_OVERLAP_THRESHOLD = 0.7


class PipelineHooks:
    def __init__(self, promoter: BeliefPromoter, beliefs_reader: Reader) -> None:
        self._promoter = promoter
        self._beliefs_reader = beliefs_reader
        self._t6_climb_cursor = 0

    def _load_t6_climb_candidates(self, limit: int = 500) -> tuple[list[dict], int]:
        """Load a rotating, bounded window of eligible Tier-6 beliefs."""
        cursor = self._t6_climb_cursor
        rows = [dict(r) for r in self._beliefs_reader.read(
            "SELECT id, content FROM beliefs "
            "WHERE tier = 6 AND paused = 0 AND locked = 0 AND id > ? "
            "ORDER BY id ASC LIMIT ?",
            (cursor, limit),
        )]
        if len(rows) < limit:
            rows.extend(dict(r) for r in self._beliefs_reader.read(
                "SELECT id, content FROM beliefs "
                "WHERE tier = 6 AND paused = 0 AND locked = 0 AND id <= ? "
                "ORDER BY id ASC LIMIT ?",
                (cursor, limit - len(rows)),
            ))
        next_cursor = int(rows[-1]["id"]) if rows else cursor
        return rows, next_cursor

    def on_pipeline_event(self, event: dict) -> None:
        """Called after step F. Corroborate beliefs if magnitude is high enough."""
        magnitude = event.get("magnitude") or 0.0
        if magnitude < _CORROBORATION_MAGNITUDE_THRESHOLD:
            return

        source = event.get("sensation_source") or ""
        branch_id = event.get("branch_id") or ""
        query_tokens = _tokenize(source) | _tokenize(branch_id)
        if not query_tokens:
            return

        try:
            rows = self._beliefs_reader.read(
                "SELECT id, content FROM beliefs "
                "WHERE tier <= 7 AND paused = 0 AND locked = 0 "
                "ORDER BY id DESC LIMIT 50",
            )
        except Exception as exc:
            errors.record(f"pipeline_hooks read error: {exc}", source=_LOG_SOURCE, exc=exc)
            return

        # NEX5_TIER_CLIMB (default OFF): the 50-newest window ages T6 beliefs out
        # before they can accrue the corroborations needed to promote to T5 (the
        # "6->5 wall"). When armed, also give the whole T6 population a corroboration
        # shot, not just whichever few are newest. Fail-safe; bounded at 500.
        t6_next_cursor = None
        t6_ids = set()
        if os.environ.get("NEX5_TIER_CLIMB") == "1":
            try:
                t6, t6_next_cursor = self._load_t6_climb_candidates(limit=500)
                seen = {r["id"] for r in rows}
                t6_ids = {r["id"] for r in t6 if r["id"] not in seen}
                rows = list(rows) + [r for r in t6 if r["id"] not in seen]
            except Exception as exc:
                errors.record(f"pipeline_hooks T6-climb read error: {exc}",
                              source=_LOG_SOURCE, exc=exc)

        t6_scan_ok = True
        for row in rows:
            content_tokens = _tokenize(row["content"])
            if not content_tokens:
                continue
            overlap = len(query_tokens & content_tokens) / max(1, len(query_tokens))
            if overlap >= _OVERLAP_THRESHOLD:
                try:
                    self._promoter.corroborate(row["id"])
                except Exception as exc:
                    if row["id"] in t6_ids:
                        t6_scan_ok = False
                    errors.record(
                        f"pipeline_hooks corroborate error: {exc}",
                        source=_LOG_SOURCE, exc=exc,
                    )

        # Commit the T6 window only after every T6-only candidate was handled.
        # A failed corroboration retries the same bounded window next event.
        if t6_next_cursor is not None and t6_scan_ok:
            self._t6_climb_cursor = t6_next_cursor

    def register(self, dynamic_state) -> None:
        """Inject hook into DynamicState so the sense_poll_loop calls it."""
        dynamic_state._pipeline_hook = self.on_pipeline_event
