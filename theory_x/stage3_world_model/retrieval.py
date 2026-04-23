"""Belief retrieval — fetches relevant beliefs for voice prompt injection.

BeliefRetriever scores beliefs by keyword overlap with the query,
boosts matches on active branches, and returns the top N by
(overlap_score * confidence).
"""
from __future__ import annotations

import re
from typing import Optional

import errors
from substrate import Reader

THEORY_X_STAGE = 3

_LOG_SOURCE = "retrieval"
_STOPWORDS = {"the", "and", "for", "are", "was", "has", "had", "not", "but",
              "its", "that", "this", "with", "from", "they", "have", "been",
              "will", "can", "all", "one", "also"}


def _tokenize(text: str) -> set[str]:
    """Lowercase words longer than 2 chars, stripped of punctuation, minus stopwords."""
    tokens = re.findall(r"[a-zA-Z]{3,}", text.lower())
    return {t for t in tokens if t not in _STOPWORDS}


def format_beliefs_for_prompt(beliefs: list[dict]) -> str:
    """Format a list of belief dicts as a compact block for system prompt injection."""
    if not beliefs:
        return ""
    lines = ["Her current beliefs relevant to this topic:"]
    for b in beliefs:
        tier = b.get("tier", "?")
        conf = b.get("confidence", 0.0)
        content = b.get("content", "")
        lines.append(f"- [Tier {tier} | {conf:.2f}] {content}")
    return "\n".join(lines)


class BeliefRetriever:
    def __init__(self, beliefs_reader: Reader) -> None:
        self._reader = beliefs_reader

    def retrieve(self, query: str, branch_hints: Optional[list[str]] = None,
                 limit: int = 10, side_filter: Optional[str] = None) -> list[dict]:
        """Retrieve top beliefs relevant to query.

        Filters: tier <= 6, (locked=1 OR confidence >= 0.15), paused=0.
        Scores by keyword overlap * confidence, boosted by branch match.
        Returns top limit results sorted descending.

        side_filter: 'INSIDE', 'OUTSIDE', or None (no filter).
        """
        try:
            rows = self._reader.read(
                "SELECT id, content, tier, confidence, branch_id, source, locked "
                "FROM beliefs "
                "WHERE tier <= 6 AND paused = 0 AND (locked = 1 OR confidence >= 0.15) "
                "ORDER BY tier ASC, confidence DESC "
                "LIMIT 200",
            )
        except Exception as exc:
            errors.record(f"belief retrieval error: {exc}", source=_LOG_SOURCE, exc=exc)
            return []

        if not rows:
            return []

        # Apply membrane side filter if requested
        if side_filter is not None:
            from theory_x.stage4_membrane.classifier import CLASSIFIER, MembraneSide
            target = MembraneSide(side_filter)
            rows = [r for r in rows if CLASSIFIER.classify_belief(dict(r)) == target]

        if not rows:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            # No meaningful query tokens — return top by confidence
            return [dict(r) for r in rows[:limit]]

        hints = set(branch_hints or [])
        scored = []
        for row in rows:
            content_tokens = _tokenize(row["content"])
            overlap = len(query_tokens & content_tokens)
            if overlap == 0:
                continue
            score = (overlap / max(1, len(query_tokens))) * row["confidence"]
            if row["branch_id"] in hints:
                score *= 1.5  # branch boost
            scored.append((score, dict(row)))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [b for _, b in scored[:limit]]
