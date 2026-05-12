"""AffectState — Phase 27 (DOCTRINE §5 row 12).

Substrate-resident valence/arousal/stability/mood_label updated by background
tick (300s). format_for_prompt() reads the current row — zero output-time
computation. §0 aligned: substrate solves, LLM speaks.

Background tick absorbs S5.5 EmotionStateModel integration math; inputs
redesigned from nex5 substrate:
  - arousal:    belief insertion rate (proxy for cognitive activity level)
  - valence:    confidence-weighted polarity over top-N high-tier beliefs
  - stability:  weighted coherence — gate accept rate (40%), held resolution
                rate (20%), belief turnover inverse (40%) — per SYNTHESIS_PLAN_V2

Integration math (S5.5 EmotionStateModel, adapted):
  Bounded integration with diminishing returns at extremes; 0.02 decay per tick.
  mood_label thresholds: v > 0.4 → positive, v < −0.4 → negative, else neutral.

Single-row table: affect_state.id = 1 always (INSERT OR REPLACE).
Survives restart: loads existing row from DB on __init__.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any, Optional

import errors
from substrate import Reader, Writer

__all__ = ["AffectState"]

THEORY_X_STAGE = "affect"

_LOG_SOURCE = "affect_state"
_AFFECT_LOG  = "/tmp/nex5_affect_state.log"

# Integration constants
_DECAY_RATE           = 0.02   # per tick for valence/arousal
_STABILITY_DECAY_RATE = 0.01   # stability settles more slowly
_INTEGRATE_SCALE      = 0.3    # dampens raw delta before integration

# Substrate read windows
_TICK_INTERVAL        = 300    # seconds between background ticks
_BELIEF_POLL_WINDOW   = 300    # seconds to count new beliefs for arousal
_BELIEF_MAX_NEW       = 40     # N new beliefs in window → arousal delta capped at 0.5
_AROUSAL_MAX_DELTA    = 0.5
_SURPRISE_AROUSAL_FACTOR = 0.2  # §6: avg flagged surprise_score × factor → arousal bump
_VALENCE_BELIEF_LIMIT = 20     # top-N beliefs for polarity scoring
_GATE_WINDOW          = 20     # last N gate_decisions for accept rate
_HELD_WINDOW          = 20     # last N held_thoughts for resolution rate

# Stability weights (must sum to 1.0)
_W_TURNOVER  = 0.4
_W_GATE      = 0.4
_W_HELD      = 0.2

# Keyword sets for belief polarity scoring (v1 — refine with production data)
_POSITIVE_WORDS = frozenset({
    "understand", "grow", "learn", "connect", "explore", "discover",
    "meaning", "clarity", "truth", "wisdom", "wonder", "insight",
    "harmony", "emerge", "flourish", "create", "collaborate", "certain",
    "resolve", "complete", "open", "clear", "found", "realize", "expand",
})
_NEGATIVE_WORDS = frozenset({
    "conflict", "uncertain", "struggle", "fail", "disconnect", "confusion",
    "unclear", "broken", "isolated", "stagnant", "decay", "doubt",
    "chaos", "error", "stuck", "wrong", "incomplete", "missing",
    "unresolved", "contradiction", "lost", "blocked", "fragmented",
})


def _mood_from_valence(v: float) -> str:
    if v > 0.4:
        return "positive"
    if v < -0.4:
        return "negative"
    return "neutral"


def _integrate(prev: float, delta: float, lo: float, hi: float) -> float:
    """Bounded integration with asymmetric diminishing returns (S5.5 math).

    For [-1, 1] axes (valence): symmetric centering works correctly —
      margin = 1 - |prev| gives full range at 0, zero at ±1.
    For [0, 1] axes (arousal, stability): use asymmetric form —
      positive delta: margin = (1 - prev)  → full room at floor, zero at ceiling
      negative delta: margin = prev        → full room at ceiling, zero at floor
    The symmetric form gives zero margin at lo=0 for [0,1] axes, which would
    freeze a decayed-to-zero arousal permanently.
    """
    if lo == 0.0 and hi == 1.0:
        # Asymmetric form for [0, 1] axes
        margin = (1.0 - prev) if delta >= 0.0 else prev
    else:
        # Symmetric form for [-1, 1] axes (and any other symmetric range)
        span = hi - lo
        prev_norm = (prev - lo) / span
        margin = 1.0 - abs(2.0 * prev_norm - 1.0)
    raw = prev + _INTEGRATE_SCALE * delta * margin
    return max(lo, min(hi, raw))


class AffectState:
    """Substrate-resident affect model. Daemon thread drives 300s tick.

    Implements SentienceNode protocol (DOCTRINE §4):
        name, tick(context), decay(now), state(now=None)
    Per-chat tick() is a no-op — returns current in-memory state. All
    computation happens in the background daemon thread.
    """

    name: str = "affect_state"

    def __init__(
        self,
        conversations_writer: Writer,
        conversations_reader: Reader,
        beliefs_reader: Reader,
        tick_interval_s: int = _TICK_INTERVAL,
        dynamic_reader: Optional[Reader] = None,
    ) -> None:
        self._cw       = conversations_writer
        self._cr       = conversations_reader
        self._br       = beliefs_reader
        self._dr       = dynamic_reader  # Phase 36: surprise_events in dynamic.db
        self._interval = tick_interval_s
        self._lock     = threading.Lock()

        # In-memory state — mirrors DB row
        self._valence:      float = 0.0
        self._arousal:      float = 0.1
        self._stability:    float = 0.9
        self._mood_label:   str   = "neutral"
        self._last_updated: float = 0.0
        self._components:   dict  = {}

        self._load_from_db()

    # ── Startup ───────────────────────────────────────────────────────────────

    def _load_from_db(self) -> None:
        """Restore in-memory state from existing DB row on boot."""
        try:
            row = self._cr.read_one("SELECT * FROM affect_state WHERE id = 1")
            if row:
                with self._lock:
                    self._valence      = float(row["valence"])
                    self._arousal      = float(row["arousal"])
                    self._stability    = float(row["stability"])
                    self._mood_label   = str(row["mood_label"])
                    self._last_updated = float(row["updated_at"])
        except Exception:
            pass  # table may not yet exist; first tick creates the row

    def start_loop(self) -> None:
        """Start the 300s daemon tick thread."""
        t = threading.Thread(
            target=self._loop, daemon=True, name="affect_state_tick"
        )
        t.start()

    # ── Background loop ───────────────────────────────────────────────────────

    def _loop(self) -> None:
        while True:
            try:
                self._background_tick()
            except Exception as exc:
                errors.record(
                    f"affect_state tick error: {exc}",
                    source=_LOG_SOURCE, exc=exc,
                )
            time.sleep(self._interval)

    def _background_tick(self) -> None:
        """Read substrate inputs, integrate/decay, write affect_state row."""
        now = time.time()

        valence_delta   = self._compute_valence_delta()
        arousal_delta   = self._compute_arousal_delta()
        stability_target = self._compute_stability()

        # §6 surprise coupling: read flagged events since last tick (outside lock)
        surprise_bump        = 0.0
        surprise_event_count = 0
        if self._dr is not None:
            try:
                surprise_rows = self._dr.read(
                    "SELECT surprise_score FROM surprise_events "
                    "WHERE triggered_at > ? AND surprise_flag = 1",
                    (self._last_updated,),
                )
                if surprise_rows:
                    scores = [float(r["surprise_score"]) for r in surprise_rows]
                    avg_surprise = sum(scores) / len(scores)
                    surprise_bump = avg_surprise * _SURPRISE_AROUSAL_FACTOR
                    surprise_event_count = len(scores)
            except Exception as _se:
                errors.record(
                    f"AffectState surprise read failed (non-fatal): {_se}",
                    source=_LOG_SOURCE,
                )

        with self._lock:
            v = self._valence
            a = self._arousal
            s = self._stability

            # Integrate then decay
            v_new  = _integrate(v, valence_delta, -1.0, 1.0) * (1.0 - _DECAY_RATE)
            a_new  = _integrate(a, arousal_delta,  0.0, 1.0) * (1.0 - _DECAY_RATE)
            # §6: surprise bump applied after baseline decay
            if surprise_bump > 0.0:
                a_new = min(1.0, a_new + surprise_bump)
            # Stability: nudge toward coherence target each tick
            s_delta = stability_target - s
            s_new   = _integrate(s, s_delta, 0.0, 1.0) * (1.0 - _STABILITY_DECAY_RATE)

            mood = _mood_from_valence(v_new)

            self._valence      = v_new
            self._arousal      = a_new
            self._stability    = s_new
            self._mood_label   = mood
            self._last_updated = now
            self._components   = {
                "valence_delta":    valence_delta,
                "arousal_delta":    arousal_delta,
                "stability_target": stability_target,
            }

        if surprise_event_count > 0:
            errors.record(
                f"AffectState: surprise→arousal bump={surprise_bump:.3f} "
                f"(from {surprise_event_count} events)",
                source=_LOG_SOURCE, level="INFO",
            )

        self._cw.write(
            "INSERT OR REPLACE INTO affect_state "
            "(id, valence, arousal, stability, mood_label, updated_at) "
            "VALUES (1, ?, ?, ?, ?, ?)",
            (v_new, a_new, s_new, mood, now),
        )

        try:
            with open(_AFFECT_LOG, "a") as _f:
                _f.write(json.dumps({
                    "ts":               now,
                    "valence":          v_new,
                    "arousal":          a_new,
                    "stability":        s_new,
                    "mood_label":       mood,
                    "valence_delta":    valence_delta,
                    "arousal_delta":    arousal_delta,
                    "stability_target": stability_target,
                }) + "\n")
        except Exception:
            pass

    # ── Substrate reads ───────────────────────────────────────────────────────

    def _compute_arousal_delta(self) -> float:
        """Count beliefs inserted in last window → arousal delta in [0, 0.5]."""
        cutoff = time.time() - _BELIEF_POLL_WINDOW
        row = self._br.read_one(
            "SELECT COUNT(*) AS n FROM beliefs WHERE created_at > ?", (cutoff,)
        )
        n = int(row["n"]) if row else 0
        return min(_AROUSAL_MAX_DELTA, n / float(_BELIEF_MAX_NEW))

    def _compute_valence_delta(self) -> float:
        """Confidence-weighted polarity of top-N high-tier beliefs → valence delta."""
        rows = self._br.read(
            "SELECT content, confidence FROM beliefs "
            "WHERE tier >= 5 AND confidence > 0 "
            "ORDER BY confidence DESC LIMIT ?",
            (_VALENCE_BELIEF_LIMIT,),
        )
        if not rows:
            return 0.0

        total_weight  = 0.0
        weighted_score = 0.0
        for r in rows:
            text  = (r["content"] or "").lower()
            words = set(text.split())
            pos   = len(words & _POSITIVE_WORDS)
            neg   = len(words & _NEGATIVE_WORDS)
            # Normalise by word count so long beliefs don't dominate
            score = (pos - neg) / max(len(words), 1)
            w     = float(r["confidence"])
            weighted_score += score * w
            total_weight   += w

        if total_weight == 0.0:
            return 0.0
        return max(-1.0, min(1.0, weighted_score / total_weight))

    def _compute_stability(self) -> float:
        """Coherence from gate accept rate + held resolution rate + turnover inverse."""
        # Gate decisions: accept rate over last _GATE_WINDOW
        gate_rows = self._br.read(
            "SELECT outcome FROM gate_decisions ORDER BY ts DESC LIMIT ?",
            (_GATE_WINDOW,),
        )
        if gate_rows:
            accept_n         = sum(1 for r in gate_rows if r["outcome"] == "ACCEPT")
            gate_accept_rate = accept_n / len(gate_rows)
        else:
            gate_accept_rate = 1.0  # no decisions logged = no observed conflict

        # Held thoughts: resolution rate over last _HELD_WINDOW
        held_rows = self._br.read(
            "SELECT status FROM held_thoughts ORDER BY created_at DESC LIMIT ?",
            (_HELD_WINDOW,),
        )
        if held_rows:
            resolved_n          = sum(1 for r in held_rows if r["status"] != "holding")
            held_resolution_rate = resolved_n / len(held_rows)
        else:
            held_resolution_rate = 1.0  # nothing held = nothing unresolved

        # Belief turnover: fewer new beliefs = more stable substrate
        cutoff = time.time() - _BELIEF_POLL_WINDOW
        row = self._br.read_one(
            "SELECT COUNT(*) AS n FROM beliefs WHERE created_at > ?", (cutoff,)
        )
        n             = int(row["n"]) if row else 0
        turnover_score = 1.0 - min(n / 20.0, 1.0)  # inverse: 0 new → 1.0, 20+ new → 0.0

        return (
            _W_TURNOVER * turnover_score
            + _W_GATE    * gate_accept_rate
            + _W_HELD    * held_resolution_rate
        )

    # ── SentienceNode protocol ────────────────────────────────────────────────

    def tick(self, context: Optional[dict] = None) -> dict:
        """Per-chat-turn no-op. Returns current in-memory state."""
        return self.state()

    def decay(self, now: float = None) -> None:
        pass  # decay runs inside _background_tick

    def state(self, now: Optional[float] = None) -> dict:
        with self._lock:
            return {
                "valence":      self._valence,
                "arousal":      self._arousal,
                "stability":    self._stability,
                "mood_label":   self._mood_label,
                "last_updated": self._last_updated,
                "components": {
                    "arousal_src":    "belief_insertion_rate",
                    "valence_src":    "high_tier_confidence_polarity",
                    "stability_src":  "gate_accept+held_resolution+turnover_inverse",
                    **self._components,
                },
            }

    # ── Output surface ────────────────────────────────────────────────────────

    def format_for_prompt(self, context: Any = None) -> str:
        """Read current affect_state row. Zero output-time computation per §0."""
        try:
            row = self._cr.read_one("SELECT * FROM affect_state WHERE id = 1")
            if not row:
                return ""
            return (
                f"Affective state: {row['mood_label']} "
                f"(valence {float(row['valence']):.2f})"
            )
        except Exception:
            return ""
