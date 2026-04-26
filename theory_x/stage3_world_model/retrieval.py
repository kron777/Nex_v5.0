"""Belief retrieval — fetches relevant beliefs for voice prompt injection.

BeliefRetriever scores beliefs by keyword overlap with the query,
boosts matches on active branches, and returns the top N by
(overlap_score * confidence). When belief_edges exist, spreading
activation is blended in: final = keyword*0.4 + activation*0.6.
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
              "will", "can", "all", "one", "also",
              "what", "how", "who", "why", "when", "where", "which"}


def _tokenize(text: str) -> set[str]:
    """Lowercase words longer than 2 chars, stripped of punctuation, minus stopwords."""
    tokens = re.findall(r"[a-zA-Z]{3,}", text.lower())
    return {t for t in tokens if t not in _STOPWORDS}


def format_beliefs_for_prompt(beliefs: list[dict]) -> str:
    """Format belief dicts as a compact block for system prompt injection.

    Includes role badge when present: BRIDGE, SUPPORT, TENSION, REFINE.
    """
    if not beliefs:
        return ""
    lines = ["Her current beliefs relevant to this topic:"]
    for b in beliefs:
        tier = b.get("tier", "?")
        conf = b.get("confidence", 0.0)
        content = b.get("content", "")
        role = b.get("_role", "")
        role_str = f" | {role}" if role else ""
        lines.append(f"- [Tier {tier} | {conf:.2f}{role_str}] {content}")
    return "\n".join(lines)


class BeliefRetriever:
    def __init__(self, beliefs_reader: Reader, erosion=None) -> None:
        self._reader = beliefs_reader
        self._erosion = erosion  # Optional ProvenanceErosion instance

    def retrieve(self, query: str, branch_hints: Optional[list[str]] = None,
                 limit: int = 10, side_filter: Optional[str] = None) -> list[dict]:
        """Retrieve top beliefs relevant to query.

        Filters: tier <= 6, (locked=1 OR confidence >= 0.15), paused=0.
        Scores by keyword overlap * confidence, boosted by branch match.
        When belief_edges exist, blends in spreading activation (60/40).
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

        # Always include reification_recognition belief on INSIDE self-inquiry queries
        _reification_id: Optional[int] = None
        if side_filter == "INSIDE":
            try:
                rr_row = self._reader.read_one(
                    "SELECT id, content, tier, confidence, branch_id, source, locked "
                    "FROM beliefs WHERE source = 'reification_recognition' LIMIT 1"
                )
                if rr_row:
                    _reification_id = rr_row["id"]
                    existing_ids = {r["id"] for r in rows}
                    if _reification_id not in existing_ids:
                        rows = list(rows) + [rr_row]
            except Exception:
                pass

        query_tokens = _tokenize(query)
        if not query_tokens:
            return [dict(r) for r in rows[:limit]]

        hints = set(branch_hints or [])
        keyword_scores: dict[int, float] = {}
        row_map: dict[int, dict] = {}

        for row in rows:
            content_tokens = _tokenize(row["content"])
            overlap = len(query_tokens & content_tokens)
            if overlap == 0:
                continue
            score = (overlap / max(1, len(query_tokens))) * row["confidence"]
            if row["branch_id"] in hints:
                score *= 1.5
            keyword_scores[row["id"]] = score
            row_map[row["id"]] = dict(row)

        if not keyword_scores:
            return []

        # Spreading activation blend if edges exist
        activation_scores: dict[int, float] = {}
        epistemic_temp = 0.0
        try:
            from .activation import ActivationEngine
            engine = ActivationEngine(self._reader)
            # Use top-5 keyword seeds
            top_seeds = sorted(keyword_scores, key=keyword_scores.__getitem__, reverse=True)[:5]
            activation_scores = engine.activate(top_seeds)
            epistemic_temp = engine.epistemic_temperature(activation_scores)
        except Exception as exc:
            errors.record(f"activation error: {exc}", source=_LOG_SOURCE, exc=exc)

        # Assign roles via typed_roles when activation data is present
        role_map: dict[int, str] = {}
        if activation_scores:
            try:
                from .activation import ActivationEngine
                engine2 = ActivationEngine(self._reader)
                top_seeds = sorted(keyword_scores, key=keyword_scores.__getitem__, reverse=True)[:5]
                roles = engine2.typed_roles(activation_scores, top_seeds)
                for role_name, entries in roles.items():
                    if role_name == "seed":
                        continue
                    for entry in entries:
                        role_map[entry["id"]] = role_name.upper()
            except Exception:
                pass

        has_activation = bool(activation_scores)

        # Normalise activation scores to [0,1]
        if has_activation:
            max_act = max(abs(v) for v in activation_scores.values()) or 1.0
            norm_act = {k: v / max_act for k, v in activation_scores.items()}
        else:
            norm_act = {}

        # Normalise keyword scores
        max_kw = max(keyword_scores.values()) or 1.0
        norm_kw = {k: v / max_kw for k, v in keyword_scores.items()}

        # Merge scores: keyword*0.4 + activation*0.6 (or keyword-only)
        all_ids = set(norm_kw) | (set(norm_act) if has_activation else set())
        final_scores: list[tuple[float, dict]] = []
        for bid in all_ids:
            kw = norm_kw.get(bid, 0.0)
            act = norm_act.get(bid, 0.0)
            if has_activation:
                score = kw * 0.4 + act * 0.6
            else:
                score = kw
            b = row_map.get(bid)
            if b is None:
                continue
            b = dict(b)
            role = role_map.get(bid, "")
            if role:
                b["_role"] = role
            b["_epistemic_temperature"] = round(epistemic_temp, 3)
            final_scores.append((score, b))

        final_scores.sort(key=lambda x: x[0], reverse=True)
        results = [b for _, b in final_scores[:limit]]

        # Record use for provenance erosion
        if self._erosion is not None:
            for b in results:
                try:
                    self._erosion.record_use(b["id"])
                except Exception:
                    pass

        return results
