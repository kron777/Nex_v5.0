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

PHASE 40 2026-05-12: drift detection from SelfMindView.aspect_history() and
SocialPresence.voice_history() / engagement_history(). Records four additional
event types: topic_diversity_collapse, vocab_narrowing, attention_groove,
uncertainty_stagnation. §0 — events are recorded only; no hardcoded action.

Implements SentienceNode protocol (DOCTRINE §4):
  name, tick(context), decay(now), state(now=None)
"""
from __future__ import annotations

import json
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

# Stillness — Row 9 extension (SYNTHESIS_PLAN_V2 §3)
_STILLNESS_THRESHOLD  = 3       # groove events in window before stillness fires
_STILLNESS_WINDOW_S   = 1800    # 30-min sliding window for groove count
_STILLNESS_DURATION_S = 60.0    # fixed suppression duration (build-tunable)

# Phase 40 drift detection calibration
_DRIFT_WINDOW_S           = 3600   # look-back window for history queries
_DRIFT_SEVERITY_THRESHOLD = 0.3    # below this magnitude, suppress the event
_MIN_SAMPLES_FOR_DRIFT    = 4      # need at least this many history rows


class Metacognition:
    name: str = "metacognition"

    def __init__(
        self,
        conversations_writer: Writer,
        conversations_reader: Reader,
        beliefs_reader: Reader,
        narrative=None,
        self_mind_view=None,
        social_presence=None,
    ) -> None:
        self._writer = conversations_writer
        self._reader = conversations_reader
        self._beliefs_reader = beliefs_reader
        self._narrative = narrative
        self._smv = self_mind_view
        self._sp = social_presence
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
            if self._narrative is not None:
                try:
                    pattern = ev.get("pattern") or ""
                    self._narrative.write_narrative(
                        f"I noticed I am repeatedly returning to {pattern}",
                        "groove",
                        ev.get("groove_id"),
                    )
                except Exception as exc:
                    errors.record(
                        f"metacognition narrative write failed: {exc}",
                        source=_LOG_SOURCE, exc=exc,
                    )

        if groove_events:
            self._maybe_engage_stillness(now)

        drift_event = self._detect_goal_drift(now)
        if drift_event:
            self._write_event(drift_event, now)

        # Phase 40 — substrate-history drift signals
        drift_findings = self._detect_drift()
        for finding in drift_findings:
            self._write_event(finding, now)

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
        if etype == "topic_diversity_collapse":
            return "Self-observation: topic range has been narrowing recently."
        if etype == "vocab_narrowing":
            return "Self-observation: vocabulary has been growing less distinctive recently."
        if etype == "attention_groove":
            return "Self-observation: same themes have been recurring across recent snapshots."
        if etype == "uncertainty_stagnation":
            return "Self-observation: open problems are holding or growing — no resolution lately."
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
                "groove_id": row["id"],
                "pattern": row["pattern"],
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

    # ── Phase 40 drift detection ──────────────────────────────────────────────

    def _compute_slope(self, samples: list) -> float:
        """(last - first) / count — simple linear trend proxy."""
        if len(samples) < 2:
            return 0.0
        return (samples[-1] - samples[0]) / len(samples)

    def _detect_drift(self) -> list[dict]:
        """Return drift event dicts for each signal that crosses threshold."""
        findings: list[dict] = []

        # 1. Topic diversity collapse
        if self._sp is not None:
            try:
                rows = self._sp.engagement_history(window_s=_DRIFT_WINDOW_S)
                if len(rows) >= _MIN_SAMPLES_FOR_DRIFT:
                    diversity = [float(r["topic_diversity"]) for r in rows]
                    slope = self._compute_slope(diversity)
                    max_d = max(diversity) or 1.0
                    # Use raw absolute change (not slope) for severity so count
                    # normalization in _compute_slope doesn't shrink the signal.
                    severity = abs(diversity[-1] - diversity[0]) / max_d
                    if slope < 0 and severity >= _DRIFT_SEVERITY_THRESHOLD:
                        findings.append({
                            "event_type": "topic_diversity_collapse",
                            "description": (
                                f"Topic diversity declining (slope {slope:.3f}, "
                                f"severity {severity:.2f})"
                            ),
                            "severity": float(min(1.0, severity)),
                            "source": "drift_detector",
                        })
            except Exception as exc:
                errors.record(
                    f"drift topic_diversity: {exc}", source=_LOG_SOURCE, exc=exc
                )

        # 2. Vocabulary narrowing
        if self._sp is not None:
            try:
                rows = self._sp.voice_history(window_s=_DRIFT_WINDOW_S)
                if len(rows) >= _MIN_SAMPLES_FOR_DRIFT:
                    distinct = [
                        float(r["vocab_distinctiveness"])
                        for r in rows
                        if r.get("vocab_distinctiveness") is not None
                    ]
                    if len(distinct) >= _MIN_SAMPLES_FOR_DRIFT:
                        slope = self._compute_slope(distinct)
                        # Raw absolute change for severity (same reason as above).
                        severity = abs(distinct[-1] - distinct[0])
                        if slope < 0 and severity >= _DRIFT_SEVERITY_THRESHOLD:
                            findings.append({
                                "event_type": "vocab_narrowing",
                                "description": (
                                    f"Vocabulary narrowing (slope {slope:.3f}, "
                                    f"severity {severity:.2f})"
                                ),
                                "severity": float(min(1.0, severity)),
                                "source": "drift_detector",
                            })
            except Exception as exc:
                errors.record(
                    f"drift vocab_narrowing: {exc}", source=_LOG_SOURCE, exc=exc
                )

        # 3. Attention groove — recurring themes across snapshots
        if self._smv is not None:
            try:
                rows = self._smv.aspect_history("attention", window_s=_DRIFT_WINDOW_S)
                if len(rows) >= _MIN_SAMPLES_FOR_DRIFT:
                    all_themes: set = set()
                    per_snapshot: list[set] = []
                    for r in rows:
                        try:
                            themes = json.loads(r.get("current_themes_json") or "[]")
                            per_snapshot.append(set(themes))
                            all_themes.update(themes)
                        except Exception:
                            pass
                    if len(per_snapshot) >= 2:
                        avg_overlap = sum(
                            len(per_snapshot[i] & per_snapshot[i - 1])
                            / max(len(per_snapshot[i]), 1)
                            for i in range(1, len(per_snapshot))
                        ) / max(len(per_snapshot) - 1, 1)
                        if avg_overlap >= 0.7 and len(all_themes) <= 6:
                            findings.append({
                                "event_type": "attention_groove",
                                "description": (
                                    f"Attention groove — {len(all_themes)} themes "
                                    f"recurring (overlap {avg_overlap:.2f})"
                                ),
                                "severity": float(min(1.0, avg_overlap)),
                                "source": "drift_detector",
                            })
            except Exception as exc:
                errors.record(
                    f"drift attention_groove: {exc}", source=_LOG_SOURCE, exc=exc
                )

        # 4. Uncertainty stagnation — open problems holding or growing
        if self._smv is not None:
            try:
                rows = self._smv.aspect_history("uncertainty", window_s=_DRIFT_WINDOW_S)
                if len(rows) >= _MIN_SAMPLES_FOR_DRIFT:
                    counts = [
                        int(r["open_problem_count"])
                        for r in rows
                        if r.get("open_problem_count") is not None
                    ]
                    if len(counts) >= _MIN_SAMPLES_FOR_DRIFT:
                        slope = self._compute_slope(counts)
                        last_count = counts[-1]
                        if slope >= 0 and last_count > 0:
                            severity = min(1.0, last_count / max(_MIN_SAMPLES_FOR_DRIFT, 1))
                            if severity >= _DRIFT_SEVERITY_THRESHOLD:
                                findings.append({
                                    "event_type": "uncertainty_stagnation",
                                    "description": (
                                        f"Open problems holding/growing "
                                        f"(count {last_count}, slope {slope:.3f})"
                                    ),
                                    "severity": float(severity),
                                    "source": "drift_detector",
                                })
            except Exception as exc:
                errors.record(
                    f"drift uncertainty_stagnation: {exc}", source=_LOG_SOURCE, exc=exc
                )

        return findings

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

    def _maybe_engage_stillness(self, now: float) -> None:
        """Write a stillness_log row when sustained groove exceeds threshold.

        Non-reentrant: if a stillness row with expires_at > now exists, returns
        immediately without writing another. Threshold: _STILLNESS_THRESHOLD
        groove events in meta_cognition_events within _STILLNESS_WINDOW_S.
        """
        # Non-reentrant check
        try:
            active = self._reader.read_one(
                "SELECT id FROM stillness_log WHERE expires_at > ? LIMIT 1",
                (now,),
            )
            if active:
                return
        except Exception:
            pass  # table may not exist on old installs; proceed to count

        # Count groove events in rolling window
        cutoff = now - _STILLNESS_WINDOW_S
        try:
            row = self._reader.read_one(
                "SELECT COUNT(*) AS n FROM meta_cognition_events "
                "WHERE event_type = 'groove' AND created_at >= ?",
                (cutoff,),
            )
            count = int(row["n"]) if row else 0
        except Exception as exc:
            errors.record(
                f"stillness count failed: {exc}", source=_LOG_SOURCE, exc=exc
            )
            return

        if count < _STILLNESS_THRESHOLD:
            return

        expires_at = now + _STILLNESS_DURATION_S
        try:
            self._writer.write(
                "INSERT INTO stillness_log "
                "(started_at, duration_s, expires_at, trigger, groove_count) "
                "VALUES (?, ?, ?, ?, ?)",
                (now, _STILLNESS_DURATION_S, expires_at, "sustained_groove", count),
            )
            errors.record(
                f"Stillness engaged: {_STILLNESS_DURATION_S:.0f}s on sustained groove "
                f"({count} groove events in {_STILLNESS_WINDOW_S}s window)",
                source=_LOG_SOURCE,
                level="INFO",
            )
        except Exception as exc:
            errors.record(
                f"stillness write failed: {exc}", source=_LOG_SOURCE, exc=exc
            )
