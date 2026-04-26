"""Detect return-transformation arcs — motif returns with changed framing."""
from __future__ import annotations

import numpy as np

from theory_x.diversity.embeddings import embed_belief, cosine


def compute_transformation_score(cluster: list[dict]) -> float:
    """Score return-with-transformation pattern. Returns 0-1.

    Requires: temporal gaps between appearances AND framing change
    between returns (not literal repetition).
    """
    if len(cluster) < 3:
        return 0.0

    timestamps = [f["created_at"] for f in cluster]
    if timestamps[-1] - timestamps[0] < 120:
        return 0.0

    gaps = [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]
    max_gap = max(gaps)
    if max_gap < 180:
        return 0.0
    gap_score = min(max_gap / 600.0, 1.0)

    embeddings = [embed_belief(f["id"], f["content"]) for f in cluster]
    pairwise_sims = [
        cosine(embeddings[i], embeddings[i + 1])
        for i in range(len(embeddings) - 1)
    ]
    mean_sim = float(np.mean(pairwise_sims))

    if mean_sim > 0.92:
        return 0.0

    framing_change = 1.0 - mean_sim
    return gap_score * 0.4 + framing_change * 0.6
