"""Detect progression arcs — clusters with monotone drift over time."""
from __future__ import annotations

import numpy as np

from theory_x.diversity.embeddings import embed_belief, distance


def compute_progression_score(cluster: list[dict]) -> float:
    """Score monotone progression. Returns 0-1.

    High = consistent drift away from starting centroid (arc).
    Low = oscillation or pure recurrence (rut).
    """
    if len(cluster) < 3:
        return 0.0

    embeddings = [embed_belief(f["id"], f["content"]) for f in cluster]
    n = len(embeddings)

    start_centroid = np.mean(embeddings[: min(3, n // 2)], axis=0)
    dists = [distance(e, start_centroid) for e in embeddings]

    if dists[-1] < dists[0] + 0.05:
        return 0.0

    inversions = sum(
        1 for i in range(n - 1) if dists[i + 1] < dists[i] - 0.03
    )
    monotonicity = 1.0 - (inversions / max(n - 1, 1))
    drift_score = min((dists[-1] - dists[0]) * 2, 1.0)

    return monotonicity * drift_score


def classify_member_roles(cluster: list[dict]) -> list[str]:
    n = len(cluster)
    roles = []
    for i in range(n):
        if i == 0:
            roles.append("introduction")
        elif i == n - 1:
            roles.append("synthesis")
        elif i < n // 3:
            roles.append("development")
        elif i < 2 * n // 3:
            roles.append("variation")
        else:
            roles.append("return")
    return roles
