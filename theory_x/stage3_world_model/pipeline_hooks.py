"""Pipeline hooks — connects A-F pipeline output to the promotion system.

PipelineHooks.on_pipeline_event() is called after step F. High-magnitude
events corroborate matching beliefs.
"""
from __future__ import annotations

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
                "WHERE tier <= 6 AND paused = 0 AND locked = 0 "
                "ORDER BY id DESC LIMIT 50",
            )
        except Exception as exc:
            errors.record(f"pipeline_hooks read error: {exc}", source=_LOG_SOURCE, exc=exc)
            return

        for row in rows:
            content_tokens = _tokenize(row["content"])
            if not content_tokens:
                continue
            overlap = len(query_tokens & content_tokens) / max(1, len(query_tokens))
            if overlap >= _OVERLAP_THRESHOLD:
                try:
                    self._promoter.corroborate(row["id"])
                except Exception as exc:
                    errors.record(
                        f"pipeline_hooks corroborate error: {exc}",
                        source=_LOG_SOURCE, exc=exc,
                    )

    def register(self, dynamic_state) -> None:
        """Inject hook into DynamicState so the sense_poll_loop calls it."""
        dynamic_state._pipeline_hook = self.on_pipeline_event
