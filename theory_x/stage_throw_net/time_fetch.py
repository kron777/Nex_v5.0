"""Throw-Net Time Fetch — TN-2.

Sweeps four substrate sources for candidates resonant with a constraint:
  1. beliefs          — present knowledge (LIKE keyword match)
  2. novel_association — cross-branch synthesis pairs
  3. arcs             — thematic arc clusters (groove arcs excluded, D6)
  4. problems         — open gaps via ProblemMemory

Returns a deduplicated, capped candidate list with provenance markers.
Read-only. No gate calls, no session writes, no background thread.
TN-4 ThrowNetEngine wires this into the orchestration loop.

Design decisions (2026-05-10 session):
  D1 = α (LIKE %keyword% matching; arc match against theme_summary)
  D2 = 20 beliefs, 10 novel_associations, 10 arcs, 10 problems; cap 40
  D3 = confidence DESC reinforce_count DESC / similarity DESC /
       quality_grade DESC / ProblemMemory default
  D4 = ProblemMemory.find_matching(); content = title + ': ' + desc[:100]
  D5 = source key: belief/novel_association/arc/gap + origin_id
  D6 = filter return_transformation arcs (groove fingerprint)
"""
from __future__ import annotations

import time
from typing import Any, Optional

import errors

_LOG_SOURCE = "throw_net.time_fetch"

_STOPWORDS = frozenset({
    "the", "and", "is", "are", "it", "that", "this", "of",
    "a", "an", "in", "on", "to", "for", "with", "be", "was",
    "were", "has", "have", "had", "not", "but", "or", "at",
    "by", "from", "as", "do", "did", "does", "so", "if",
    "its", "my", "we", "you", "he", "she", "they", "their",
    "what", "how", "why", "when", "where", "which", "who",
    "can", "will", "would", "could", "should", "may", "might",
    "about", "than", "then", "each", "all", "any", "some",
    "into", "over", "such", "also", "been", "being",
})

_PUNCT = '.,?!;:\'"()[]{}—-'


class TimeFetch:
    """Read-only substrate sweep for throw-net candidates.

    Searches four sources for beliefs/associations/arcs/problems
    that resonate with the given constraint string.
    """

    def __init__(self, beliefs_reader, problem_memory) -> None:
        self._reader = beliefs_reader
        self._problem_memory = problem_memory
        self._belief_limit = 20
        self._novel_assoc_limit = 10
        self._arc_limit = 10
        self._problem_limit = 10
        self._dedup_cap = 40

    # ── Public API ────────────────────────────────────────────────────────────

    def fetch_from_beliefs(
        self, constraint: str, limit: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """LIKE %keyword% across beliefs.

        Filters: confidence > 0.4, LENGTH(content) > 30.
        Orders by confidence DESC, reinforce_count DESC (D3).
        """
        keywords = self._extract_keywords(constraint, min_len=3)
        if not keywords:
            return []
        limit = limit or self._belief_limit
        where = " OR ".join("LOWER(content) LIKE ?" for _ in keywords)
        params = tuple(f"%{k}%" for k in keywords) + (limit,)
        try:
            rows = self._reader.read(
                f"SELECT id, content, branch_id, confidence, reinforce_count "
                f"FROM beliefs "
                f"WHERE confidence > 0.4 AND LENGTH(content) > 30 "
                f"AND ({where}) "
                f"ORDER BY confidence DESC, reinforce_count DESC "
                f"LIMIT ?",
                params,
            )
        except Exception as exc:
            errors.record(
                f"TimeFetch.fetch_from_beliefs: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )
            return []
        return [
            {
                "content": r["content"],
                "source": "belief",
                "branch_id": r["branch_id"],
                "confidence": r["confidence"],
                "origin_id": r["id"],
            }
            for r in rows
        ]

    def fetch_from_novel_associations(
        self, constraint: str, limit: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """JOIN novel_association_log → beliefs.

        Matches keywords against content of either belief in the pair.
        Orders by similarity DESC (D3).
        Content field: "content_a ↔ content_b" synthesis preview.
        """
        keywords = self._extract_keywords(constraint, min_len=3)
        if not keywords:
            return []
        limit = limit or self._novel_assoc_limit
        where = " OR ".join(
            ["LOWER(ba.content) LIKE ?" for _ in keywords]
            + ["LOWER(bb.content) LIKE ?" for _ in keywords]
        )
        params = (
            tuple(f"%{k}%" for k in keywords) * 2
            + (limit,)
        )
        try:
            rows = self._reader.read(
                f"SELECT n.id, n.similarity, n.branch_id_a, n.branch_id_b, "
                f"ba.content AS content_a, bb.content AS content_b "
                f"FROM novel_association_log n "
                f"JOIN beliefs ba ON ba.id = n.belief_id_a "
                f"JOIN beliefs bb ON bb.id = n.belief_id_b "
                f"WHERE {where} "
                f"ORDER BY n.similarity DESC LIMIT ?",
                params,
            )
        except Exception as exc:
            errors.record(
                f"TimeFetch.fetch_from_novel_associations: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )
            return []
        return [
            {
                "content": f"{r['content_a']} ↔ {r['content_b']}",
                "source": "novel_association",
                "branch_id_a": r["branch_id_a"],
                "branch_id_b": r["branch_id_b"],
                "similarity": r["similarity"],
                "origin_id": r["id"],
            }
            for r in rows
        ]

    def fetch_from_arcs(
        self, constraint: str, limit: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """Match theme_summary with LIKE keywords.

        Excludes return_transformation arcs (groove fingerprint, D6).
        Orders by quality_grade DESC (D3).
        """
        keywords = self._extract_keywords(constraint, min_len=3)
        if not keywords:
            return []
        limit = limit or self._arc_limit
        where = " OR ".join("LOWER(theme_summary) LIKE ?" for _ in keywords)
        params = tuple(f"%{k}%" for k in keywords) + (limit,)
        try:
            rows = self._reader.read(
                f"SELECT id, arc_type, theme_summary, quality_grade "
                f"FROM arcs "
                f"WHERE arc_type != 'return_transformation' "
                f"AND quality_grade IS NOT NULL "
                f"AND theme_summary IS NOT NULL "
                f"AND ({where}) "
                f"ORDER BY quality_grade DESC LIMIT ?",
                params,
            )
        except Exception as exc:
            errors.record(
                f"TimeFetch.fetch_from_arcs: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )
            return []
        return [
            {
                "content": r["theme_summary"],
                "source": "arc",
                "arc_type": r["arc_type"],
                "quality_grade": r["quality_grade"],
                "origin_id": r["id"],
            }
            for r in rows
        ]

    def fetch_from_problems(self, constraint: str) -> list[dict[str, Any]]:
        """Open problem gaps via ProblemMemory.find_matching() (D4).

        Converts problem rows to candidate format.
        Content = title + ': ' + description[:100].
        """
        if not constraint or not constraint.strip():
            return []
        try:
            problems = self._problem_memory.find_matching(constraint)
        except Exception as exc:
            errors.record(
                f"TimeFetch.fetch_from_problems: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )
            return []
        return [
            {
                "content": (
                    f"{p.get('title', 'Unknown')}: "
                    f"{(p.get('description') or '')[:100]}"
                ),
                "source": "gap",
                "origin_id": p.get("id"),
            }
            for p in problems[: self._problem_limit]
        ]

    def run(self, constraint: str) -> list[dict[str, Any]]:
        """Full sweep across all four sources.

        Combines, deduplicates by content, caps at _dedup_cap (40).
        Source priority order for dedup: belief > novel_association > arc > gap.
        Returns [] immediately for empty or stopword-only constraints.
        """
        if not constraint or not constraint.strip():
            return []
        if not self._extract_keywords(constraint, min_len=3):
            return []

        all_results: list[dict[str, Any]] = []
        all_results.extend(self.fetch_from_beliefs(constraint))
        all_results.extend(self.fetch_from_novel_associations(constraint))
        all_results.extend(self.fetch_from_arcs(constraint))
        all_results.extend(self.fetch_from_problems(constraint))

        return self._dedup(all_results)[: self._dedup_cap]

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _extract_keywords(self, constraint: str, min_len: int = 3) -> list[str]:
        """Lowercase, strip punctuation, filter stopwords and short tokens."""
        if not constraint:
            return []
        tokens = []
        for word in constraint.lower().split():
            word = word.strip(_PUNCT)
            if word and len(word) >= min_len and word not in _STOPWORDS:
                tokens.append(word)
        return tokens

    def _dedup(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove duplicate content strings; preserve first occurrence."""
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for item in results:
            content = item.get("content", "")
            if content and content not in seen:
                seen.add(content)
                out.append(item)
        return out
