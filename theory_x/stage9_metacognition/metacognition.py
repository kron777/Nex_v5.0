"""Metacognition — self-pattern observation and anomaly detection over cognitive state.

Realizes the human function of observing one's own cognitive patterns.
Reads GrooveSpotter output (groove_alerts in beliefs.db) and detects goal-drift
(FAISS cosine distance of recent NEX responses vs active goal). Writes detected
anomalies to meta_cognition_events (conversations.db). Injects self-observations
into belief_text via format_for_prompt().

PHASE 16 METACOGNITION 2026-05-09: §5 row 9 port. Per DOCTRINE §1 framing —
Metacognition realizes the human function of observing one's own cognitive
patterns. Reads groove_alerts (existing GrooveSpotter output) and detects
goal-drift (FAISS similarity of recent responses vs active goal). Reversion:
drop meta_cognition_events table, remove module + tests, remove server.py and
run.py wiring.

Implements SentienceNode protocol (DOCTRINE §4):
  name, tick(context), decay(now), state(now=None)
"""
from __future__ import annotations

import threading
import time
from typing import Optional

import errors
from substrate import Writer, Reader

THEORY_X_STAGE = 9

_LOG_SOURCE = "metacognition"

# Tunable. Observe /tmp/nex5_metacognition.log for false positives (drift fires
# when goal-aligned) or false negatives (drift doesn't fire when clearly
# off-topic). Adjust based on production data.
_GOAL_DRIFT_THRESHOLD = 0.35

_STALE_DAYS = 14
_CACHE_TTL = 60.0
_GROOVE_LOOKBACK = 600       # seconds to look back for groove alerts
_GOAL_DRIFT_LOOKBACK = 5     # last N nex responses to compare
_DRIFT_COOLDOWN = 600        # seconds between goal-drift events


class Metacognition:
    name: str = "metacognition"

    def __init__(
        self,
        conversations_writer: Writer,
        conversations_reader: Reader,
        beliefs_reader: Reader,
    ) -> None:
        self._writer = conversations_writer
        self._reader = conversations_reader
        self._beliefs_reader = beliefs_reader
        self._lock = threading.Lock()
        self._cached_recent: Optional[list] = None
        self._cache_ts: float = 0.0
        self._last_groove_at: float = 0.0
        self._last_drift_at: float = 0.0

    # ── SentienceNode protocol ────────────────────────────────────────────────

    def tick(self, context: Optional[dict] = None) -> dict:
        """Detect anomalies, write events, refresh cache. Returns state."""
        now = time.time()

        groove_events = self._detect_groove(now)
        for ev in groove_events:
            self._write_event(ev, now)

        drift_event = self._detect_goal_drift(now)
        if drift_event:
            self._write_event(drift_event, now)

        with self._lock:
            if self._cached_recent is None or (now - self._cache_ts) > _CACHE_TTL:
                self._cached_recent = self.get_recent(limit=3)
                self._cache_ts = now

        return self.state(now=now)

    def decay(self, now: float) -> None:
        """Auto-resolve anomalies stale > _STALE_DAYS."""
        cutoff = now - _STALE_DAYS * 86400
        self._writer.write(
            "UPDATE meta_cognition_events SET resolved_at = ? "
            "WHERE resolved_at IS NULL AND created_at < ?",
            (now, cutoff),
        )
        with self._lock:
            self._cached_recent = None

    def state(self, now: Optional[float] = None) -> dict:
        now = now or time.time()
        with self._lock:
            recent = self._cached_recent or []
            top = recent[0] if recent else None
            return {
                "name": self.name,
                "recent_count": len(recent),
                "top_anomaly": top["event_type"] if top else None,
                "cache_age_s": round(now - self._cache_ts, 1),
            }

    # ── public API ───────────────────────────────────────────────────────────

    def get_recent(self, limit: int = 3) -> list[dict]:
        """Return most recent unresolved meta_cognition_events."""
        rows = self._reader.read(
            "SELECT id, event_type, description, severity, source, created_at "
            "FROM meta_cognition_events WHERE resolved_at IS NULL "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in rows]

    def format_for_prompt(self) -> str:
        """1-2 lines for belief_text injection. Empty when nothing notable."""
        with self._lock:
            recent = self._cached_recent or []
        if not recent:
            return ""
        top = recent[0]
        etype = top["event_type"]
        if etype == "groove":
            return "Self-observation: I notice repeated patterns in my recent thinking."
        if etype == "goal_drift":
            return "Self-observation: recent responses may be drifting from the active goal."
        return f"Self-observation: anomaly detected ({etype})."

    # ── detectors ────────────────────────────────────────────────────────────

    def _detect_groove(self, now: float) -> list[dict]:
        """Return event dicts for unacknowledged groove_alerts in lookback window."""
        cutoff = now - _GROOVE_LOOKBACK
        try:
            rows = self._beliefs_reader.read(
                "SELECT id, alert_type, severity, pattern, detected_at "
                "FROM groove_alerts "
                "WHERE detected_at > ? AND acknowledged_at IS NULL "
                "ORDER BY detected_at DESC LIMIT 3",
                (cutoff,),
            )
        except Exception as exc:
            errors.record(f"groove read failed: {exc}", source=_LOG_SOURCE, exc=exc)
            return []

        if not rows:
            return []

        results = []
        for row in rows:
            desc = f"Groove alert: {row['alert_type']}"
            if row["pattern"]:
                desc += f" — pattern: {str(row['pattern'])[:60]}"
            results.append({
                "event_type": "groove",
                "description": desc,
                "severity": float(row["severity"]),
                "source": f"groove_spotter/{row['alert_type']}",
            })
        return results

    def _detect_goal_drift(self, now: float) -> Optional[dict]:
        """Return drift event if active goal is semantically far from recent responses."""
        if now - self._last_drift_at < _DRIFT_COOLDOWN:
            return None

        try:
            goal_row = self._reader.read_one(
                "SELECT id, title, description FROM goals "
                "WHERE state IN ('open', 'active') "
                "ORDER BY priority DESC LIMIT 1",
            )
        except Exception as exc:
            errors.record(f"goal read failed: {exc}", source=_LOG_SOURCE, exc=exc)
            return None

        if goal_row is None:
            return None

        try:
            msg_rows = self._reader.read(
                "SELECT content FROM messages WHERE role = 'nex' "
                "ORDER BY id DESC LIMIT ?",
                (_GOAL_DRIFT_LOOKBACK,),
            )
        except Exception as exc:
            errors.record(f"messages read failed: {exc}", source=_LOG_SOURCE, exc=exc)
            return None

        if len(msg_rows) < 2:
            return None

        try:
            from theory_x.diversity.embeddings import embed, distance as emb_distance
            import numpy as np

            goal_text = f"{goal_row['title']} {goal_row['description']}"
            goal_emb = embed(goal_text)

            msg_embs = [embed(r["content"]) for r in msg_rows if r["content"].strip()]
            if not msg_embs:
                return None
            avg_msg_emb = np.mean(msg_embs, axis=0).astype(np.float32)

            dist = emb_distance(goal_emb, avg_msg_emb)
        except Exception as exc:
            errors.record(f"embedding failed: {exc}", source=_LOG_SOURCE, exc=exc)
            return None

        if dist < _GOAL_DRIFT_THRESHOLD:
            return None

        self._last_drift_at = now
        return {
            "event_type": "goal_drift",
            "description": (
                f"Goal-drift: responses diverging from '{goal_row['title']}' "
                f"(distance {dist:.2f})"
            ),
            "severity": min(1.0, dist),
            "source": "goal_drift_detector",
        }

    # ── internal ─────────────────────────────────────────────────────────────

    def _write_event(self, ev: dict, now: float) -> None:
        try:
            self._writer.write(
                "INSERT INTO meta_cognition_events "
                "(event_type, description, severity, source, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (ev["event_type"], ev["description"], ev["severity"], ev["source"], now),
            )
            errors.record(
                f"metacognition event: {ev['event_type']} — {ev['description'][:60]}",
                source=_LOG_SOURCE, level="INFO",
            )
            # PHASE 16 fix 2026-05-09: invalidate cache after write so events fire
            # same-turn (not next-turn). Surfaced by cognitive-proof validation.
            # Writer is synchronous (req.future.result()), so cache refresh on the
            # next tick() cache block finds the committed event.
            with self._lock:
                self._cached_recent = None
        except Exception as exc:
            errors.record(f"event write failed: {exc}", source=_LOG_SOURCE, exc=exc)
