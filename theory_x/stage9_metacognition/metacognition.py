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

PHASE 41 2026-05-12: value-drift monitoring via keystones (tier=1 AND locked=1).
Three additional event types: value_drift_distance (recent beliefs moving away
from keystones in embedding space), value_drift_contradiction (anchor-reject rate
increasing — more generated content contradicting keystones),
value_drift_abandonment (keystone vocabulary barely appearing in recent activity).
Keystones have empty tags; abandonment uses word-token overlap on content instead.
Contradiction uses rate-change (recent 30min vs prior 30min) because production
gate rejects ~24K/hr normally — absolute count would always fire. §0.

Implements SentienceNode protocol (DOCTRINE §4):
  name, tick(context), decay(now), state(now=None)
"""
from __future__ import annotations

import json
import string
import threading
import time
from collections import deque
from typing import Optional

import errors
from substrate import Writer, Reader
from theory_x.diversity.embeddings import embed_belief

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

# Phase 41 value-drift calibration
# Note: contradiction uses rate-change (recent 30min vs prior 30min) because
# production gate rejects ~24K/hr normally — absolute count would always fire.
_VALUE_DRIFT_CONTRADICTION_THRESHOLD = 100  # min prior-window count before comparing rates
_VALUE_DRIFT_CONTRADICTION_RATE_INCREASE = 0.30  # 30% rate increase flags drift
_VALUE_DRIFT_DISTANCE_INCREASE       = 0.15  # cosine-distance growth over rolling window
_VALUE_DRIFT_ABANDONMENT_OVERLAP_MAX = 0.15  # keystone-token overlap floor
_VALUE_DRIFT_DISTANCE_DEQUE_LEN      = 8    # rolling history length for distance tracking
_VALUE_DRIFT_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "i", "my", "me", "we", "our", "it", "its", "in", "of", "to", "and",
    "or", "but", "not", "no", "on", "at", "by", "for", "with", "from",
    "this", "that", "what", "which", "who", "how", "all", "any", "do",
    "does", "did", "have", "has", "had", "will", "would", "can", "could",
    "may", "might", "shall", "should", "than", "so", "if", "as", "into",
})


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
        # Phase 41 value-drift caches
        self._keystone_matrix = None      # numpy (N, 384) — built on first use
        self._keystone_tokens: Optional[frozenset] = None  # word tokens from all keystones
        self._distance_history: deque = deque(maxlen=_VALUE_DRIFT_DISTANCE_DEQUE_LEN)

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
        if etype == "value_drift_distance":
            return "Self-observation: my recent thoughts are moving away from my deepest beliefs."
        if etype == "value_drift_contradiction":
            return "Self-observation: I've been rejecting more thoughts that conflict with my anchors."
        if etype == "value_drift_abandonment":
            return "Self-observation: my deepest beliefs are barely surfacing in my recent thinking."
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

        # Phase 41 value-drift signals
        findings.extend(self._detect_value_drift())

        return findings

    # ── Phase 41 value-drift detection ───────────────────────────────────────

    def _tokenize_for_value(self, text: str) -> frozenset:
        """Lowercase word tokens, strip punctuation, drop stopwords and short words."""
        trans = str.maketrans("", "", string.punctuation)
        tokens = text.lower().translate(trans).split()
        return frozenset(t for t in tokens if len(t) > 1 and t not in _VALUE_DRIFT_STOPWORDS)

    def _load_keystone_cache(self):
        """Populate _keystone_matrix and _keystone_tokens on first call. Never raises."""
        if self._keystone_matrix is not None:
            return
        try:
            rows = self._beliefs_reader.read(
                "SELECT id, content FROM beliefs WHERE tier=1 AND locked=1"
            )
            if not rows:
                return
            import numpy as np
            from theory_x.diversity.embeddings import embed_belief
            vecs = []
            all_tokens: set = set()
            for r in rows:
                vecs.append(embed_belief(r["id"], r["content"]))
                all_tokens.update(self._tokenize_for_value(r["content"]))
            self._keystone_matrix = np.vstack(vecs).astype(np.float32)  # (N, 384)
            self._keystone_tokens = frozenset(all_tokens)
        except Exception as exc:
            errors.record(
                f"keystone cache load failed: {exc}", source=_LOG_SOURCE, exc=exc
            )

    def _detect_value_drift(self) -> list[dict]:
        """Return value-drift event dicts (three kinds). Never raises."""
        findings: list[dict] = []
        now = time.time()

        self._load_keystone_cache()

        # 5. value_drift_distance — recent beliefs moving away from keystones
        try:
            if self._keystone_matrix is not None and len(self._keystone_matrix) > 0:
                import numpy as np
                recent_rows = self._beliefs_reader.read(
                    "SELECT id, content FROM beliefs "
                    "WHERE created_at > ? ORDER BY created_at DESC LIMIT 200",
                    (now - _DRIFT_WINDOW_S,),
                )
                if recent_rows:
                    ks = self._keystone_matrix  # (N, 384)
                    ks_norms = np.linalg.norm(ks, axis=1, keepdims=True)
                    ks_norms = np.where(ks_norms == 0, 1.0, ks_norms)
                    ks_normed = ks / ks_norms  # (N, 384) unit vectors

                    min_dists = []
                    for r in recent_rows:
                        vec = embed_belief(r["id"], r["content"]).astype(np.float32)
                        norm = np.linalg.norm(vec)
                        if norm == 0:
                            continue
                        vec_normed = vec / norm
                        # cosine similarity to all keystones at once
                        sims = ks_normed @ vec_normed  # (N,)
                        # distance = (1 - cosine_sim) / 2 matching distance() formula
                        max_sim = float(np.max(sims))
                        min_dist = 1.0 - (max_sim + 1.0) / 2.0
                        min_dists.append(min_dist)

                    if min_dists:
                        avg_min_dist = sum(min_dists) / len(min_dists)
                        self._distance_history.append(avg_min_dist)

                        if len(self._distance_history) >= 2:
                            oldest = self._distance_history[0]
                            increase = avg_min_dist - oldest
                            if increase >= _VALUE_DRIFT_DISTANCE_INCREASE:
                                findings.append({
                                    "event_type": "value_drift_distance",
                                    "description": (
                                        f"Recent beliefs moving away from keystones "
                                        f"(avg distance {avg_min_dist:.2f}, "
                                        f"+{increase:.2f} over window)"
                                    ),
                                    "severity": float(min(1.0, increase / 0.5)),
                                    "source": "value_drift_detector",
                                })
        except Exception as exc:
            errors.record(
                f"value_drift_distance: {exc}", source=_LOG_SOURCE, exc=exc
            )

        # 6. value_drift_contradiction — anchor-reject rate increasing
        try:
            mid = now - 1800  # 30-min boundary
            start = now - 3600

            recent_row = self._beliefs_reader.read_one(
                "SELECT COUNT(*) AS n FROM gate_decisions "
                "WHERE outcome='REJECT' AND ts > ? "
                "AND reason LIKE 'contradicts_anchor:locked_id_%'",
                (mid,),
            )
            prior_row = self._beliefs_reader.read_one(
                "SELECT COUNT(*) AS n FROM gate_decisions "
                "WHERE outcome='REJECT' AND ts > ? AND ts <= ? "
                "AND reason LIKE 'contradicts_anchor:locked_id_%'",
                (start, mid),
            )
            recent_count = int(recent_row["n"]) if recent_row else 0
            prior_count = int(prior_row["n"]) if prior_row else 0

            if prior_count >= _VALUE_DRIFT_CONTRADICTION_THRESHOLD and prior_count > 0:
                rate_increase = (recent_count - prior_count) / prior_count
                if rate_increase >= _VALUE_DRIFT_CONTRADICTION_RATE_INCREASE:
                    severity = float(min(1.0, rate_increase))
                    findings.append({
                        "event_type": "value_drift_contradiction",
                        "description": (
                            f"Anchor-reject rate up {rate_increase:.0%} "
                            f"(recent {recent_count}, prior {prior_count})"
                        ),
                        "severity": severity,
                        "source": "value_drift_detector",
                    })
        except Exception as exc:
            errors.record(
                f"value_drift_contradiction: {exc}", source=_LOG_SOURCE, exc=exc
            )

        # 7. value_drift_abandonment — keystone vocabulary absent from recent beliefs
        try:
            if self._keystone_tokens is not None and len(self._keystone_tokens) > 0:
                recent_rows_ab = self._beliefs_reader.read(
                    "SELECT content FROM beliefs "
                    "WHERE created_at > ? ORDER BY created_at DESC LIMIT 200",
                    (now - _DRIFT_WINDOW_S,),
                )
                if recent_rows_ab:
                    recent_tokens: set = set()
                    for r in recent_rows_ab:
                        recent_tokens.update(self._tokenize_for_value(r["content"]))

                    overlap = (
                        len(self._keystone_tokens & recent_tokens)
                        / max(len(self._keystone_tokens), 1)
                    )
                    if overlap <= _VALUE_DRIFT_ABANDONMENT_OVERLAP_MAX:
                        severity = float(min(
                            1.0,
                            (_VALUE_DRIFT_ABANDONMENT_OVERLAP_MAX - overlap)
                            / max(_VALUE_DRIFT_ABANDONMENT_OVERLAP_MAX, 1e-9),
                        ))
                        findings.append({
                            "event_type": "value_drift_abandonment",
                            "description": (
                                f"Keystone vocabulary barely surfacing in recent activity "
                                f"(overlap {overlap:.2f})"
                            ),
                            "severity": severity,
                            "source": "value_drift_detector",
                        })
        except Exception as exc:
            errors.record(
                f"value_drift_abandonment: {exc}", source=_LOG_SOURCE, exc=exc
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
