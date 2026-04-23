"""Fountain readiness evaluator — Theory X Stage 6.

Computes a 0.0–1.0 readiness score from internal state.
The fountain fires when readiness >= FOUNTAIN_THRESHOLD.
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from substrate import Reader

THEORY_X_STAGE = 6

FOUNTAIN_THRESHOLD = 0.7
FOUNTAIN_MIN_INTERVAL_SECONDS = 600   # 10 minutes
FOUNTAIN_CHECK_INTERVAL_SECONDS = 120  # 2 minutes

_HIGH_FOCUS = {"e", "f", "g"}


class ReadinessEvaluator:
    def score(
        self,
        dynamic_state,
        beliefs_reader: Reader,
        last_fire_ts: float = 0.0,
    ) -> float:
        total = 0.0
        try:
            status = dynamic_state.status()
            branches = status.get("branches", [])
            hot = [b for b in branches if b.get("focus_increment") in _HIGH_FOCUS]
            total += min(0.6, len(hot) * 0.3)
            if status.get("consolidation_active"):
                total += 0.2
        except Exception:
            pass

        try:
            rows = beliefs_reader.read("SELECT COUNT(*) as cnt FROM beliefs")
            belief_count = rows[0]["cnt"] if rows else 0
            if belief_count > 20:
                total += 0.1
        except Exception:
            pass

        elapsed = time.time() - last_fire_ts
        if last_fire_ts == 0.0 or elapsed >= FOUNTAIN_MIN_INTERVAL_SECONDS:
            total += 0.2

        return min(1.0, total)

    def is_ready(self, score: float) -> bool:
        return score >= FOUNTAIN_THRESHOLD
