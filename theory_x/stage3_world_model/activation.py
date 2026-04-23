"""Spreading activation over the belief edge graph.

ActivationEngine propagates activation scores from seed beliefs
through belief_edges, with hop-based decay and edge-type weighting.
"""
from __future__ import annotations

import statistics
from typing import Optional

import errors
from substrate import Reader

THEORY_X_STAGE = 3

_LOG_SOURCE = "activation"

_EDGE_MULTIPLIERS = {
    "supports":    1.0,
    "refines":     1.0,
    "cross_domain": 0.8,
    "synthesises": 1.2,
    "opposes":     None,  # handled separately (inhibitory)
}


class ActivationEngine:
    def __init__(self, beliefs_reader: Reader) -> None:
        self._reader = beliefs_reader

    def activate(self, seed_ids: list[int], hops: int = 3,
                 decay: float = 0.55) -> dict[int, float]:
        """Spread activation from seed_ids through belief_edges.

        Returns dict of belief_id → activation_score.
        Falls back to empty dict if belief_edges is empty.
        """
        try:
            edge_count = self._reader.read_one(
                "SELECT COUNT(*) as cnt FROM belief_edges"
            )
            if not edge_count or edge_count["cnt"] == 0:
                return {}
        except Exception:
            return {}

        scores: dict[int, float] = {sid: 1.0 for sid in seed_ids}
        current_frontier = dict(scores)

        for hop in range(1, hops + 1):
            if not current_frontier:
                break
            factor = decay ** hop
            next_frontier: dict[int, float] = {}

            source_ids = list(current_frontier.keys())
            placeholders = ",".join("?" * len(source_ids))
            try:
                edges = self._reader.read(
                    f"SELECT source_id, target_id, edge_type, weight "
                    f"FROM belief_edges WHERE source_id IN ({placeholders})",
                    tuple(source_ids),
                )
            except Exception as exc:
                errors.record(f"activate read error: {exc}", source=_LOG_SOURCE, exc=exc)
                break

            for edge in edges:
                src = edge["source_id"]
                tgt = edge["target_id"]
                etype = edge["edge_type"]
                w = edge["weight"]
                src_score = current_frontier[src]

                if etype == "opposes":
                    delta = -(src_score * w * factor * 0.5)
                else:
                    mult = _EDGE_MULTIPLIERS.get(etype, 1.0)
                    delta = src_score * w * factor * mult

                scores[tgt] = scores.get(tgt, 0.0) + delta
                if tgt not in seed_ids:
                    next_frontier[tgt] = next_frontier.get(tgt, 0.0) + delta

            current_frontier = {k: v for k, v in next_frontier.items() if v > 0}

        return scores

    def epistemic_temperature(self, activation_scores: dict[int, float]) -> float:
        """0.0 = cold/settled; 1.0 = hot/uncertain.

        min(1.0, len(activated)/20) * variance_factor
        """
        if not activation_scores:
            return 0.0
        values = list(activation_scores.values())
        activated = [v for v in values if v > 0]
        if len(activated) < 2:
            return 0.0
        breadth = min(1.0, len(activated) / 20)
        try:
            var = statistics.variance(activated)
        except statistics.StatisticsError:
            var = 0.0
        variance_factor = min(1.0, var)
        return breadth * variance_factor

    def typed_roles(self, activation_scores: dict[int, float],
                    seed_ids: list[int]) -> dict:
        """Categorize activated beliefs by role.

        Returns {'seed': [...], 'support': [...], 'bridge': [...],
                 'tension': [...], 'refine': [...]}
        """
        seed_set = set(seed_ids)
        seed_branches: dict[int, Optional[str]] = {}

        try:
            if seed_ids:
                placeholders = ",".join("?" * len(seed_ids))
                rows = self._reader.read(
                    f"SELECT id, branch_id FROM beliefs WHERE id IN ({placeholders})",
                    tuple(seed_ids),
                )
                seed_branches = {r["id"]: r["branch_id"] for r in rows}
        except Exception:
            pass

        seed_branch_values = {b for b in seed_branches.values() if b}

        # Get branch_id for all activated beliefs
        activated_ids = [bid for bid in activation_scores if bid not in seed_set]
        branch_map: dict[int, Optional[str]] = {}
        try:
            if activated_ids:
                placeholders = ",".join("?" * len(activated_ids))
                rows = self._reader.read(
                    f"SELECT id, branch_id FROM beliefs WHERE id IN ({placeholders})",
                    tuple(activated_ids),
                )
                branch_map = {r["id"]: r["branch_id"] for r in rows}
        except Exception:
            pass

        # Get refines-edge targets
        refine_targets: set[int] = set()
        try:
            if seed_ids:
                placeholders = ",".join("?" * len(seed_ids))
                rows = self._reader.read(
                    f"SELECT target_id FROM belief_edges "
                    f"WHERE source_id IN ({placeholders}) AND edge_type = 'refines'",
                    tuple(seed_ids),
                )
                refine_targets = {r["target_id"] for r in rows}
        except Exception:
            pass

        result: dict[str, list[dict]] = {
            "seed": [], "support": [], "bridge": [], "tension": [], "refine": [],
        }

        for bid, score in activation_scores.items():
            entry = {"id": bid, "score": round(score, 4)}
            if bid in seed_set:
                result["seed"].append(entry)
            elif score < 0:
                result["tension"].append(entry)
            elif bid in refine_targets and score > 0:
                result["refine"].append(entry)
            elif score > 0:
                b = branch_map.get(bid)
                if b and b in seed_branch_values:
                    result["support"].append(entry)
                else:
                    result["bridge"].append(entry)

        for lst in result.values():
            lst.sort(key=lambda x: x["score"], reverse=True)

        return result
