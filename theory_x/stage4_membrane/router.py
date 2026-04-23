"""Query router — routes queries to the inside or outside retrieval path.

INSIDE queries (self-inquiry) → self_model snapshot + inside beliefs.
OUTSIDE queries (world-inquiry) → standard belief retrieval.
"""
from __future__ import annotations

from typing import Optional

import errors
from .classifier import CLASSIFIER, MembraneSide
from .self_model import SelfModel, format_self_state

THEORY_X_STAGE = 4

_LOG_SOURCE = "router"


class QueryRouter:
    def __init__(self, classifier=None) -> None:
        self._classifier = classifier or CLASSIFIER

    def route(self, query: str, belief_retriever, self_model: SelfModel,
              dynamic_state=None) -> dict:
        """Route a query to the appropriate retrieval path.

        Returns:
            {
                "side": "INSIDE" | "OUTSIDE",
                "belief_text": str | None,
                "register_hint": str | None,
            }
        """
        side = self._classifier.classify_query(query)

        if side == MembraneSide.INSIDE:
            return self._inside_route(query, belief_retriever, self_model)
        else:
            return self._outside_route(query, belief_retriever, dynamic_state)

    def _inside_route(self, query: str, belief_retriever, self_model: SelfModel) -> dict:
        from theory_x.stage3_world_model.retrieval import format_beliefs_for_prompt
        parts = []
        try:
            snap = self_model.snapshot()
            parts.append(format_self_state(snap))
        except Exception as exc:
            errors.record(f"router inside snapshot error: {exc}", source=_LOG_SOURCE, exc=exc)

        try:
            beliefs = belief_retriever.retrieve(
                query=query, branch_hints=["systems"], limit=5,
                side_filter="INSIDE",
            )
            if beliefs:
                parts.append(format_beliefs_for_prompt(beliefs))
        except Exception as exc:
            errors.record(f"router inside beliefs error: {exc}", source=_LOG_SOURCE, exc=exc)

        return {
            "side": "INSIDE",
            "belief_text": "\n\n".join(parts) if parts else None,
            "register_hint": "philosophical",
        }

    def _outside_route(self, query: str, belief_retriever, dynamic_state) -> dict:
        from theory_x.stage3_world_model.retrieval import format_beliefs_for_prompt
        belief_text = None
        try:
            active_branches: list[str] = []
            if dynamic_state is not None:
                snap = dynamic_state.status()
                active_branches = [
                    b["branch_id"] for b in snap.get("branches", [])
                    if b.get("focus_num", 0) > 0.1
                ]
            beliefs = belief_retriever.retrieve(
                query=query, branch_hints=active_branches, limit=8
            )
            belief_text = format_beliefs_for_prompt(beliefs) if beliefs else None
        except Exception as exc:
            errors.record(f"router outside beliefs error: {exc}", source=_LOG_SOURCE, exc=exc)

        return {
            "side": "OUTSIDE",
            "belief_text": belief_text,
            "register_hint": None,
        }
