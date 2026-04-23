"""Membrane — aperture and accumulator for the A-F pipeline.

The aperture controls how much signal flows through to the tree.
The accumulator collects processed sensations; on flush it synthesises
pattern-sensations and feeds them back through the pipeline.
"""
from __future__ import annotations

import time
from typing import Callable

THEORY_X_STAGE = 2

# Aperture clamps [MIN, MAX]
_APERTURE_MIN = 0.1
_APERTURE_MAX = 1.0
# How fast aperture adjusts toward target (per recalc call)
_APERTURE_STEP = 0.05

# Accumulator flush threshold: flush when total weight exceeds this
_FLUSH_THRESHOLD = 5.0
# Accumulator decay: applied each decay tick
_ACCUM_DECAY = 0.1


class Membrane:
    def __init__(self) -> None:
        self._aperture: float = 0.5
        # accumulator: list of (branch_id, source, weight)
        self._accumulator: list[dict] = []
        self._total_weight: float = 0.0

    @property
    def aperture(self) -> float:
        return self._aperture

    def recalc_aperture(self, aggregate_texture_num: float) -> float:
        """Adjust aperture away from rough texture (overwhelm dampening)."""
        # High texture → close aperture; low texture → open aperture
        target = _APERTURE_MAX - aggregate_texture_num * (_APERTURE_MAX - _APERTURE_MIN)
        if self._aperture < target:
            self._aperture = min(target, self._aperture + _APERTURE_STEP)
        else:
            self._aperture = max(target, self._aperture - _APERTURE_STEP)
        return self._aperture

    def add_to_accumulator(self, branch_id: str, source: str, weight: float) -> None:
        self._accumulator.append({
            "branch_id": branch_id,
            "source": source,
            "weight": weight,
            "ts": time.time(),
        })
        self._total_weight += weight

    def decay_accumulator(self) -> None:
        """Decay all accumulator weights; remove entries that fall to zero."""
        remaining = []
        total = 0.0
        for entry in self._accumulator:
            entry["weight"] *= (1 - _ACCUM_DECAY)
            if entry["weight"] > 0.001:
                remaining.append(entry)
                total += entry["weight"]
        self._accumulator = remaining
        self._total_weight = total

    def flush_accumulator(self) -> list[dict]:
        """Return accumulated entries and reset if above threshold."""
        if self._total_weight < _FLUSH_THRESHOLD:
            return []
        flushed = list(self._accumulator)
        self._accumulator = []
        self._total_weight = 0.0
        return flushed

    def status(self) -> dict:
        return {
            "aperture": self._aperture,
            "accumulator_size": len(self._accumulator),
            "accumulator_total_weight": self._total_weight,
        }
