"""Behavioural Self-Model — NEX's self-knowledge grounded in observed behaviour.

Tracks hedge_rate, position_rate, belief_usage_rate, dominant_register,
and avg_response_length from recent conversations. Compares against
keystone seed assertions and writes divergence beliefs to beliefs.db.
"""
from __future__ import annotations

import re
import threading
import time
from typing import Optional

import errors
from substrate import Writer, Reader

THEORY_X_STAGE = 4

_LOG_SOURCE = "behavioural_self_model"

_CACHE_TTL = 60.0  # seconds between observe() refreshes

_HEDGE_WORDS = {
    "probably", "perhaps", "might", "could be", "i think", "i believe",
    "possibly", "uncertain", "maybe", "seems", "appears",
}

_POSITION_WORDS = {
    " is ", " are ", " will ", " must ", " always ", " never ",
    " clearly ", " definitely ", "without doubt",
}

_KEYSTONE_EXPECTATIONS = [
    {
        "seed": "I speak from what I am, not what I am not.",
        "metric": "hedge_rate",
        "threshold": 0.35,
        "direction": "high",
        "divergence_template": (
            "My observed hedge rate ({value:.0%}) is high relative to my seeded "
            "directness. I hedge more than I assert."
        ),
    },
    {
        "seed": "My beliefs precipitate from attention, not installation.",
        "metric": "belief_usage_rate",
        "threshold": 0.1,
        "direction": "low",
        "divergence_template": (
            "Beliefs are rarely surfaced in my responses (usage rate {value:.0%}). "
            "My precipitated world-model is underused."
        ),
    },
]


class BehaviouralSelfModel:
    name: str = "behavioural_self_model"

    def __init__(self, conversations_reader: Reader) -> None:
        self._reader = conversations_reader
        self._lock = threading.Lock()
        self._cached_metrics: Optional[dict] = None
        self._cache_ts: float = 0.0

    def observe(self) -> dict:
        """Compute behavioural metrics from the last 100 NEX messages."""
        try:
            rows = self._reader.read(
                "SELECT content, register FROM messages "
                "WHERE role = 'nex' ORDER BY id DESC LIMIT 100"
            )
        except Exception as exc:
            errors.record(f"observe read error: {exc}", source=_LOG_SOURCE, exc=exc)
            return self._empty_metrics()

        if not rows:
            return self._empty_metrics()

        total = len(rows)
        hedge_count = 0
        position_count = 0
        belief_usage_count = 0
        register_counts: dict[str, int] = {}
        total_words = 0

        for row in rows:
            content = (row["content"] or "").lower()
            words = content.split()
            total_words += len(words)

            if any(hw in content for hw in _HEDGE_WORDS):
                hedge_count += 1
            if any(pw in content for pw in _POSITION_WORDS):
                position_count += 1
            # Belief injection marker — present if belief_text was included
            if "her current beliefs" in content or "[tier" in content:
                belief_usage_count += 1

            reg = row["register"] or "unknown"
            register_counts[reg] = register_counts.get(reg, 0) + 1

        dominant_register = max(register_counts, key=register_counts.__getitem__) if register_counts else "unknown"
        avg_response_length = round(total_words / total, 1) if total else 0.0

        return {
            "hedge_rate": round(hedge_count / total, 3),
            "position_rate": round(position_count / total, 3),
            "belief_usage_rate": round(belief_usage_count / total, 3),
            "dominant_register": dominant_register,
            "avg_response_length": avg_response_length,
            "sample_size": total,
        }

    def compare_to_seeds(self) -> list[dict]:
        """Compare observed behaviour against keystone seed assertions.

        Returns list of divergences.
        """
        metrics = self.observe()
        divergences = []
        for expectation in _KEYSTONE_EXPECTATIONS:
            metric = expectation["metric"]
            value = metrics.get(metric, 0.0)
            threshold = expectation["threshold"]
            direction = expectation["direction"]

            if direction == "high" and value >= threshold:
                divergences.append({
                    "expected": expectation["seed"],
                    "observed": f"{metric}={value:.3f}",
                    "divergence": expectation["divergence_template"].format(value=value),
                    "metric": metric,
                    "value": value,
                })
            elif direction == "low" and value <= threshold:
                divergences.append({
                    "expected": expectation["seed"],
                    "observed": f"{metric}={value:.3f}",
                    "divergence": expectation["divergence_template"].format(value=value),
                    "metric": metric,
                    "value": value,
                })

        return divergences

    def write_behavioural_beliefs(self, beliefs_writer: Writer,
                                  beliefs_reader: Reader,
                                  coherence_gate=None) -> int:
        """Write beliefs for significant divergences. Returns count written."""
        divergences = self.compare_to_seeds()
        if not divergences:
            return 0

        written = 0
        now = int(time.time())
        for div in divergences:
            content = div["divergence"]
            # Dedup: skip if identical content already exists
            try:
                existing = beliefs_reader.read_one(
                    "SELECT id FROM beliefs WHERE content = ? AND source = 'behavioural_observation'",
                    (content,),
                )
                if existing:
                    continue
            except Exception:
                pass

            # Phase 22 — Coherence Gate (before INSERT)
            if coherence_gate is not None:
                try:
                    from theory_x.stage_gate.coherence_gate import ThoughtPacket, GateOutcome
                    packet = ThoughtPacket(
                        content=content,
                        source_node="bsm",
                        confidence=0.35,
                        branch_id="systems",
                    )
                    decision = coherence_gate.check(packet)
                    if decision.outcome != GateOutcome.ACCEPT:
                        errors.record(
                            f"BSM gate {decision.outcome.value} ({decision.reason}): {content[:60]}",
                            source=_LOG_SOURCE, level="INFO",
                        )
                        continue
                except Exception as exc:
                    errors.record(f"bsm gate check error: {exc}", source=_LOG_SOURCE, exc=exc)

            try:
                beliefs_writer.write(
                    "INSERT INTO beliefs "
                    "(content, tier, confidence, created_at, source, branch_id, locked) "
                    "VALUES (?, 6, 0.35, ?, 'behavioural_observation', 'systems', 0)",
                    (content, now),
                )
                written += 1
                errors.record(
                    f"behavioural belief written: {content[:80]}",
                    source=_LOG_SOURCE, level="INFO",
                )
            except Exception as exc:
                errors.record(f"write_behavioural_beliefs error: {exc}", source=_LOG_SOURCE, exc=exc)

        return written

    # ── SentienceNode protocol ────────────────────────────────────────────────

    def tick(self, context: Optional[dict] = None) -> dict:
        """Refresh observe() cache if stale; return state snapshot."""
        now = time.time()
        with self._lock:
            if self._cached_metrics is None or (now - self._cache_ts) > _CACHE_TTL:
                self._cached_metrics = self.observe()
                self._cache_ts = now
        return self.state()

    def decay(self, now: float) -> None:
        pass  # event-driven; cache refreshes on tick, not on a decay clock

    def state(self, now: Optional[float] = None) -> dict:
        with self._lock:
            m = self._cached_metrics or self._empty_metrics()
            return {
                "name": self.name,
                "hedge_rate": m.get("hedge_rate", 0.0),
                "position_rate": m.get("position_rate", 0.0),
                "belief_usage_rate": m.get("belief_usage_rate", 0.0),
                "dominant_register": m.get("dominant_register", "unknown"),
                "avg_response_length": m.get("avg_response_length", 0.0),
                "sample_size": m.get("sample_size", 0),
                "cache_age_s": round(time.time() - self._cache_ts, 1),
            }

    def format_for_prompt(self) -> str:
        """Format cached metrics as natural-language lines for INSIDE route injection.

        Called after tick() so cache is fresh. Returns empty string when no data.
        """
        with self._lock:
            m = dict(self._cached_metrics or self._empty_metrics())
        if not m.get("sample_size"):
            return ""
        reg = m.get("dominant_register", "unknown")
        avg_len = m.get("avg_response_length", 0.0)
        hedge = m.get("hedge_rate", 0.0)
        bu = m.get("belief_usage_rate", 0.0)
        lines = [
            "Behavioural self-knowledge (from recent responses):",
            f"- Typical response: ~{avg_len:.0f} words, mostly {reg} register",
            f"- Hedging language in ~{hedge:.0%} of responses",
        ]
        if bu < 0.05:
            lines.append("- Belief graph rarely surfaces in responses")
        elif bu > 0.5:
            lines.append(f"- Belief graph actively engaged in {bu:.0%} of responses")
        return "\n".join(lines)

    # ── internals ─────────────────────────────────────────────────────────────

    def _empty_metrics(self) -> dict:
        return {
            "hedge_rate": 0.0,
            "position_rate": 0.0,
            "belief_usage_rate": 0.0,
            "dominant_register": "unknown",
            "avg_response_length": 0.0,
            "sample_size": 0,
        }
