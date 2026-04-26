"""Detect meta-reflective fires — fires that name their own recent thinking."""
from __future__ import annotations

import re
from typing import Optional

import numpy as np

from theory_x.diversity.embeddings import embed_belief, cosine

_META_PATTERNS = [
    r"\b(reveals?|shows?|suggests?)\s+(the|a)\s+\w+\s+(of|between)",
    r"\bthe\s+(interplay|dance|rhythm|balance|tension)\s+(of|between)",
    r"\b(noticing|seeing|recognizing)\s+(the|a)\s+(pattern|connection|thread)",
    r"\bwhat\s+(connects|links|ties)\s+these",
    r"\bthese\s+(thoughts|observations|fires)\s+",
    r"\b(throughout|across)\s+(the|this)\s+(day|hour|morning|afternoon|evening)",
    r"\breturning\s+to\s+this",
    r"\b(keep|keeps?)\s+coming\s+back",
    r"\bi've\s+been\s+(noticing|tracking|following)",
]


def is_meta_reflective_content(content: str) -> tuple[bool, float]:
    content_lower = content.lower()
    matches = sum(1 for p in _META_PATTERNS if re.search(p, content_lower))
    if matches == 0:
        return False, 0.0
    return True, min(0.3 + 0.2 * matches, 1.0)


def find_closed_arc(
    meta_fire: dict,
    recent_arcs: list[dict],
    _embedding_cache: dict,
) -> Optional[tuple[int, float]]:
    """Return (arc_id, proximity_score) if meta_fire closes an arc, else None."""
    if not recent_arcs:
        return None

    meta_emb = embed_belief(meta_fire["id"], meta_fire["content"])
    best_arc = None
    best_sim = 0.0

    for arc in recent_arcs:
        raw = arc.get("centroid_embedding")
        if raw is None:
            continue
        centroid = np.frombuffer(raw, dtype=np.float32)
        sim = cosine(meta_emb, centroid)
        if sim > best_sim:
            best_sim = sim
            best_arc = arc

    if best_arc and best_sim > 0.7:
        return (best_arc["id"], best_sim)
    return None
