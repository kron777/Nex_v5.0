"""Governor: regulates speech rate. Not every crystallized belief is spoken.

Reference: Architectural Doctrine v1 Section III.6
"""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import Optional

import errors

log = logging.getLogger(__name__)
_LOG_SOURCE = "speech.governor"


@dataclass
class GovernorDecision:
    speak: bool
    reason: str


class SpeechGovernor:
    """Decides whether a crystallized belief should be spoken.

    Principles (Doctrine VI):
    - Real minds speak rarely relative to thinking
    - Speech is selected, not automatic
    - Situation determines fit (user present/absent)
    - Recent speech creates a gap — don't crowd it

    Knobs (overridable via env):
    - min_gap_seconds: minimum gap between speech events (default 180)
    - base_speak_probability: fraction spoken when no other factors apply (default 1.0)
    - quiet_hours_damping: multiplier applied 22:00-07:00 local (default 0.3)
    """

    def __init__(
        self,
        min_gap_seconds: float = 180.0,
        base_speak_probability: float = 1.0,
        quiet_hours_damping: float = 0.3,
        initial_ts: float = 0.0,
    ):
        import os
        self._min_gap = min_gap_seconds
        self._base_prob = base_speak_probability
        self._quiet_damping = float(os.environ.get("NEX5_SPEECH_QUIET_DAMPING", quiet_hours_damping))
        self._last_speech_ts: float = initial_ts

    def decide(
        self,
        belief_content: str,
        valence: Optional[dict] = None,
        situation: Optional[dict] = None,
        mode=None,
    ) -> GovernorDecision:
        if mode is not None and not mode.speech_enabled:
            log.info("Governor HOLD: reason=speech_disabled_by_mode")
            return GovernorDecision(speak=False, reason="speech_disabled_by_mode")

        now = time.time()

        min_gap = self._min_gap * (mode.governor_min_gap_multiplier if mode else 1.0)
        elapsed = now - self._last_speech_ts
        if elapsed < min_gap:
            log.info("Governor HOLD: reason=min_gap elapsed=%ds min_gap=%ds",
                     int(elapsed), int(min_gap))
            return GovernorDecision(
                speak=False,
                reason=f"within_min_gap ({int(elapsed)}s < {min_gap}s)",
            )

        prob = self._base_prob * (mode.governor_base_prob_multiplier if mode else 1.0)

        if valence:
            magnitude = abs(valence.get("weight", 0.0))
            prob = min(0.95, prob + (magnitude * 0.3))

        if situation:
            if situation.get("user_active_recently"):
                prob *= 0.3
            if situation.get("user_asleep"):
                prob *= 0.1
            if situation.get("open_problems"):
                prob = min(0.95, prob * 1.5)

        hour = time.localtime(now).tm_hour
        if hour >= 22 or hour < 7:
            prob *= self._quiet_damping

        roll = random.random()
        if roll < prob:
            self._last_speech_ts = now
            log.info("Governor SPEAK: reason=roll base=%.2f effective=%.3f elapsed=%ds",
                     self._base_prob, prob, int(elapsed))
            return GovernorDecision(speak=True, reason=f"roll {roll:.3f} < prob {prob:.3f}")
        log.info("Governor HOLD: reason=roll base=%.2f effective=%.3f elapsed=%ds",
                 self._base_prob, prob, int(elapsed))
        return GovernorDecision(speak=False, reason=f"roll {roll:.3f} >= prob {prob:.3f}")

    def mark_spoken_externally(self, ts: Optional[float] = None) -> None:
        """Update last-speech timestamp from an external event (e.g. chat response)."""
        self._last_speech_ts = ts if ts is not None else time.time()
