"""Throw-Net Trigger Detector — TN-1.

Watches two trigger sources:
  1. CoherenceGate REJECT decisions (substrate-level contradiction signal)
  2. Gap gate deflections (interaction-level missing-belief signal)

Logs every detected event to throw_net_triggers. Returns True from
record_*() when the threshold for that trigger type is crossed —
the caller (or TN-4 ThrowNetEngine) may use this to fire a session.

Phase 25a TN-1 scope: detect and log only.
Session firing is wired in TN-4 (ThrowNetEngine).

Thresholds (v1 starting values, calibrated from nex_core observation):
  gate_reject:     4 same-topic REJECTs in a 15-minute window
  gap_deflection:  3 same-topic deflections in a 30-minute window
"""
from __future__ import annotations

import json
import time
from collections import Counter
from typing import Optional

import errors

_LOG_SOURCE = "throw_net.trigger_detector"

_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "do", "does", "did", "have", "has", "had", "will", "would",
    "can", "could", "should", "may", "might", "shall",
    "i", "you", "he", "she", "it", "we", "they",
    "what", "how", "why", "when", "where", "which", "who",
    "this", "that", "these", "those", "and", "or", "but",
    "of", "in", "on", "at", "to", "for", "with", "about",
    "not", "no", "so", "if", "as", "its", "my", "your",
})

# Threshold: consecutive (windowed) REJECTs on same topic before TN fires
_GATE_REJECT_THRESHOLD = 4
# Threshold: gap deflections in 30 min on same topic before TN fires
_GAP_DEFLECTION_THRESHOLD = 3
# Time windows (seconds)
_GATE_REJECT_WINDOW = 900    # 15 min
_GAP_DEFLECTION_WINDOW = 1800  # 30 min


class TriggerDetector:
    """Detect and log conditions that should trigger a throw-net session.

    Purely reactive: no background thread. Called inline from gate
    REJECT path and gap gate deflection path.
    """

    def __init__(self, beliefs_writer, beliefs_reader) -> None:
        self._writer = beliefs_writer
        self._reader = beliefs_reader

    # ── Public API ────────────────────────────────────────────────────────────

    def record_gate_reject(self, packet, decision) -> bool:
        """Log a CoherenceGate REJECT to throw_net_triggers.

        Returns True if the same-topic reject count in the last 15 min
        reaches or exceeds _GATE_REJECT_THRESHOLD (4).
        Caller may use this to schedule a throw-net session via TN-4.
        Never raises.
        """
        try:
            topic = self._extract_topic(packet.content)
            count_before = self._gate_rejects_in_window(topic)
            self._writer.write(
                "INSERT INTO throw_net_triggers "
                "(ts, trigger_type, topic, source_event_id, "
                "threshold_state, fired, session_id) "
                "VALUES (?, 'gate_reject', ?, ?, ?, 0, NULL)",
                (
                    time.time(),
                    topic,
                    decision.reason,
                    json.dumps({"window_count": count_before + 1}),
                ),
            )
            return (count_before + 1) >= _GATE_REJECT_THRESHOLD
        except Exception as exc:
            errors.record(
                f"trigger_detector.record_gate_reject: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )
            return False

    def record_gap_deflection(self, query: str, deflection_reason: str) -> bool:
        """Log a gap gate deflection to throw_net_triggers.

        Returns True if same-topic deflection count in the last 30 min
        reaches or exceeds _GAP_DEFLECTION_THRESHOLD (3).
        Never raises.
        """
        try:
            topic = self._extract_topic(query)
            count_before = self._gap_deflections_in_window(topic)
            self._writer.write(
                "INSERT INTO throw_net_triggers "
                "(ts, trigger_type, topic, source_event_id, "
                "threshold_state, fired, session_id) "
                "VALUES (?, 'gap_deflection', ?, ?, ?, 0, NULL)",
                (
                    time.time(),
                    topic,
                    deflection_reason,
                    json.dumps({"window_count": count_before + 1}),
                ),
            )
            return (count_before + 1) >= _GAP_DEFLECTION_THRESHOLD
        except Exception as exc:
            errors.record(
                f"trigger_detector.record_gap_deflection: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )
            return False

    def pending_triggers(self) -> list[dict]:
        """Return unfired trigger rows ordered by ts ASC.

        TN-4 ThrowNetEngine consumes these to decide whether to launch
        a session. Capped at 50 to avoid large reads.
        """
        try:
            return self._reader.read(
                "SELECT id, trigger_type, topic, threshold_state, ts "
                "FROM throw_net_triggers WHERE fired = 0 "
                "ORDER BY ts ASC LIMIT 50"
            )
        except Exception as exc:
            errors.record(
                f"trigger_detector.pending_triggers: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )
            return []

    def mark_fired(self, trigger_id: int, session_id: str) -> None:
        """Mark trigger as fired and link it to the launched session.

        Called by TN-4 ThrowNetEngine when a session is created.
        Never raises.
        """
        try:
            self._writer.write(
                "UPDATE throw_net_triggers SET fired=1, session_id=? "
                "WHERE id=?",
                (session_id, trigger_id),
            )
        except Exception as exc:
            errors.record(
                f"trigger_detector.mark_fired: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _extract_topic(self, text: str) -> str:
        """Return the most frequent non-stopword content token.

        Falls back to 'unknown' if text yields no content words.
        """
        if not text:
            return "unknown"
        punct = '.,?!;:\'"()'
        tokens = [
            w.strip(punct).lower()
            for w in text.split()
            if w.strip(punct).lower() not in _STOPWORDS
            and len(w.strip(punct)) > 2
        ]
        if not tokens:
            return "unknown"
        counter = Counter(tokens)
        return counter.most_common(1)[0][0]

    def _gate_rejects_in_window(self, topic: str) -> int:
        """Count gate_reject rows for topic in the last 15 minutes."""
        try:
            cutoff = time.time() - _GATE_REJECT_WINDOW
            rows = self._reader.read(
                "SELECT COUNT(*) AS n FROM throw_net_triggers "
                "WHERE trigger_type='gate_reject' AND topic=? AND ts > ?",
                (topic, cutoff),
            )
            return int(rows[0]["n"]) if rows else 0
        except Exception:
            return 0

    def _gap_deflections_in_window(self, topic: str) -> int:
        """Count gap_deflection rows for topic in the last 30 minutes."""
        try:
            cutoff = time.time() - _GAP_DEFLECTION_WINDOW
            rows = self._reader.read(
                "SELECT COUNT(*) AS n FROM throw_net_triggers "
                "WHERE trigger_type='gap_deflection' AND topic=? AND ts > ?",
                (topic, cutoff),
            )
            return int(rows[0]["n"]) if rows else 0
        except Exception:
            return 0
