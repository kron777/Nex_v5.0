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
              dynamic_state=None, trace=None) -> dict:
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
            if trace is None:
                return self._inside_route(query, belief_retriever, self_model)
            return self._inside_route(query, belief_retriever, self_model, trace=trace)
        if trace is None:
            return self._outside_route(query, belief_retriever, dynamic_state)
        return self._outside_route(query, belief_retriever, dynamic_state, trace=trace)

    def _inside_route(self, query: str, belief_retriever, self_model: SelfModel,
                      trace=None) -> dict:
        from theory_x.stage3_world_model.retrieval import format_beliefs_for_prompt
        parts = []
        snap = None  # passed through for observability log (Option C, B1)
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
            if trace is not None:
                _inside_candidate_id = trace.candidates(
                    [b.get("id") for b in beliefs],
                    source="membrane.inside_retriever",
                    metadata={"side": "INSIDE", "limit": 5, "branch_hints": ["systems"]},
                    parent_ids=[trace.reference("input_arrival")],
                )
                trace.remember("chat_belief_candidates", _inside_candidate_id)
            if beliefs:
                parts.append(format_beliefs_for_prompt(beliefs))
        except Exception as exc:
            errors.record(f"router inside beliefs error: {exc}", source=_LOG_SOURCE, exc=exc)
            if trace is not None:
                trace.record("candidate_generation", "retrieval_error",
                             metadata={"source": "membrane.inside_retriever",
                                       "error_type": type(exc).__name__},
                             parent_ids=[trace.reference("input_arrival")])

        return {
            "side": "INSIDE",
            "belief_text": "\n\n".join(parts) if parts else None,
            "register_hint": "philosophical",
            "self_model_snap": snap,
        }

    def _outside_route(self, query: str, belief_retriever, dynamic_state,
                       trace=None) -> dict:
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
            if trace is not None:
                _outside_candidate_id = trace.candidates(
                    [b.get("id") for b in beliefs],
                    source="membrane.outside_retriever",
                    metadata={"side": "OUTSIDE", "limit": 8,
                              "branch_hints": active_branches},
                    parent_ids=[trace.reference("input_arrival")],
                )
                trace.remember("chat_belief_candidates", _outside_candidate_id)
            belief_text = format_beliefs_for_prompt(beliefs) if beliefs else None
        except Exception as exc:
            errors.record(f"router outside beliefs error: {exc}", source=_LOG_SOURCE, exc=exc)
            if trace is not None:
                trace.record("candidate_generation", "retrieval_error",
                             metadata={"source": "membrane.outside_retriever",
                                       "error_type": type(exc).__name__},
                             parent_ids=[trace.reference("input_arrival")])

        return {
            "side": "OUTSIDE",
            "belief_text": belief_text,
            "register_hint": None,
        }
