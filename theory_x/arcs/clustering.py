"""Cluster recent fires by semantic similarity."""
from __future__ import annotations

import numpy as np
from typing import Dict, List

from theory_x.diversity.embeddings import embed_belief, cosine


def cluster_fires(fires: List[dict], similarity_threshold: float = 0.78) -> List[List[dict]]:
    """Simple agglomerative clustering by cosine similarity.

    fires: list of dicts with keys 'id', 'content', 'created_at'
    Returns: list of clusters (each ≥2 members), ordered by time within cluster.
    """
    if len(fires) < 2:
        return [[f] for f in fires] if fires else []

    embeddings = [embed_belief(f["id"], f["content"]) for f in fires]
    n = len(fires)

    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(n):
        for j in range(i + 1, n):
            if cosine(embeddings[i], embeddings[j]) >= similarity_threshold:
                union(i, j)

    clusters_map: Dict[int, List[int]] = {}
    for i in range(n):
        clusters_map.setdefault(find(i), []).append(i)

    result = []
    for members in clusters_map.values():
        if len(members) >= 2:
            result.append(
                sorted([fires[m] for m in members], key=lambda f: f["created_at"])
            )
    return result


def cluster_centroid(cluster: List[dict]) -> np.ndarray:
    embeddings = [embed_belief(f["id"], f["content"]) for f in cluster]
    return np.mean(embeddings, axis=0).astype(np.float32)
