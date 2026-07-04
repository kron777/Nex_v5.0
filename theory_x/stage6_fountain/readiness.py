"""Fountain readiness evaluator — Theory X Stage 6.

Computes a 0.0–1.0 readiness score from internal state.
The fountain fires when readiness >= FOUNTAIN_THRESHOLD.

2026-05-30 — GENIUS_SCORE_v2.md §7 consumer C:
  An optional genius-rate modulation reduces readiness when recent
  fires have been mostly ordinary. Ordinary streaks slow the fountain;
  STRIKING streaks keep normal cadence. Net effect over time: fewer
  but better fires, characteristic voice emerges via accumulation.

  Off by default unless a conversations_reader is supplied to the
  constructor. Set NEX5_FOUNTAIN_READINESS_MOD_OFF=1 to disable at
  runtime even when the reader is wired in.
"""
from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Optional

from substrate import Reader

THEORY_X_STAGE = 6

FOUNTAIN_THRESHOLD = 0.7
FOUNTAIN_MIN_INTERVAL_SECONDS = 600   # 10 minutes
FOUNTAIN_CHECK_INTERVAL_SECONDS = 120  # 2 minutes

_HIGH_FOCUS = {"e", "f", "g"}
_WARM_FOCUS = {"c", "d"}  # building but not yet hot

# 2026-05-30 (consumer C) genius-rate modulation knobs
# Look at recent tags within this window when computing striking rate
_GENIUS_WINDOW_SECONDS = 3600          # last 1 hour
# Below this sample size the modulation does nothing (cold-start safe)
_GENIUS_MIN_SAMPLE = 5
# Striking-rate target: at or above this, no penalty.
# Below this, penalty scales linearly to _GENIUS_MAX_PENALTY at rate 0.
_GENIUS_TARGET_RATE = 0.40
# Maximum penalty subtracted from readiness when rate is 0.0
_GENIUS_MAX_PENALTY = 0.15


class ReadinessEvaluator:
    def __init__(self, conversations_reader: Optional[Reader] = None) -> None:
        self._conv_reader = conversations_reader
        # Light caching: re-poll the tags table at most every 30s.
        # Readiness is checked every 120s anyway, but multiple paths
        # may call score() per tick; this avoids redundant work.
        self._cached_modulation: float = 0.0
        self._cached_at: float = 0.0
        self._cache_ttl: float = 30.0
        # Last computed striking_rate, surfaced for status display
        self._last_striking_rate: Optional[float] = None
        self._last_sample_size: int = 0

    def score(
        self,
        dynamic_state,
        beliefs_reader: Reader,
        last_fire_ts: float = 0.0,
    ) -> float:
        total = 0.0
        # Fair-baseline lift (2026-07-04): small flat floor favoring no topic,
        # plus partial credit for warm branches, so genuine moderate activity
        # can fire without a branch needing maximum focus. Fair replacement for
        # the unfair free-0.6 the internal-telemetry bug used to hand systems.
        total += 0.15
        try:
            status = dynamic_state.status()
            branches = status.get("branches", [])
            hot = [b for b in branches if b.get("focus_increment") in _HIGH_FOCUS]
            total += min(0.6, len(hot) * 0.3)
            warm = [b for b in branches
                    if b.get("focus_increment") in _WARM_FOCUS]
            total += min(0.30, len(warm) * 0.15)
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

        # 2026-05-30 — genius rate modulation (subtractive, opt-in)
        total -= self._genius_modulation()

        return max(0.0, min(1.0, total))

    def is_ready(self, score: float) -> bool:
        return score >= FOUNTAIN_THRESHOLD

    # ── Genius rate modulation (consumer C) ───────────────────────────────────

    def _genius_modulation(self) -> float:
        """Return a positive penalty value to subtract from readiness.

        Reads the last hour of genius_tags. If sample is too small, or
        modulation is disabled, returns 0.0. Penalty scales linearly
        from 0 (at target rate) to _GENIUS_MAX_PENALTY (at 0% rate).
        Never raises — failures return 0.0 (no modulation).
        """
        if self._conv_reader is None:
            return 0.0
        if os.environ.get("NEX5_FOUNTAIN_READINESS_MOD_OFF") == "1":
            return 0.0

        now = time.time()
        if (now - self._cached_at) < self._cache_ttl:
            return self._cached_modulation

        try:
            cutoff = now - _GENIUS_WINDOW_SECONDS
            rows = self._conv_reader.read(
                "SELECT class FROM genius_tags WHERE tagged_at > ?",
                (cutoff,),
            )
        except Exception:
            self._cached_modulation = 0.0
            self._cached_at = now
            return 0.0

        rows = list(rows or [])
        n = len(rows)
        self._last_sample_size = n
        if n < _GENIUS_MIN_SAMPLE:
            self._last_striking_rate = None
            self._cached_modulation = 0.0
            self._cached_at = now
            return 0.0

        striking = sum(1 for r in rows if r["class"] == "STRIKING")
        rate = striking / n
        self._last_striking_rate = rate

        if rate >= _GENIUS_TARGET_RATE:
            penalty = 0.0
        else:
            # Linear: rate=0.0 -> max penalty, rate=target -> 0
            penalty = _GENIUS_MAX_PENALTY * (1.0 - (rate / _GENIUS_TARGET_RATE))

        self._cached_modulation = penalty
        self._cached_at = now
        return penalty

    def status(self) -> dict:
        """Surface genius modulation state for diagnostics."""
        return {
            "conversations_reader_wired": self._conv_reader is not None,
            "modulation_disabled": (
                os.environ.get("NEX5_FOUNTAIN_READINESS_MOD_OFF") == "1"
            ),
            "last_striking_rate": self._last_striking_rate,
            "last_sample_size": self._last_sample_size,
            "current_penalty": round(self._cached_modulation, 4),
            "cached_at": self._cached_at,
        }
