"""
Auto-probe groove breaker — Phase A (observation mode only).

Per Design v0.3:
  - Section 5: Trigger conditions
  - Section 6: Probe selection by operation-type inversion
  - Section 11 Phase A: observation only, no firing

This module is a passive observer in Phase A. It checks
trigger conditions every fountain tick. When triggered, it
logs to auto_probe_log with status='observation' and does
nothing else.

Phase B (later) adds operator approval flow.
Phase C (later) adds autonomous firing.
"""

import logging
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Configuration constants — match Design v0.3
GROOVE_SEVERITY_THRESHOLD = 0.80
GROOVE_FRESHNESS_WINDOW = 1800  # 30 min in seconds
SUSTAIN_THRESHOLD = 8           # min fires since alert detected
COOLDOWN_SECONDS = 1800         # 30 min between auto_probe events
ENABLED = True                   # master enable/disable

# Operation-type inversion mapping (Design v0.3 Section 6)
OPCODE_TO_PROBE_CATEGORY = {
    "OBSERVE_TEMPORAL": "direct_phenomenology",
    "OBSERVE_HUM": "direct_phenomenology",
    "OBSERVE_LIGHT": "direct_phenomenology",
    "OBSERVE_GENERAL": "direct_phenomenology",
    "INTROSPECT_QUIETUDE": "grounded_observation",
    "INTROSPECT_SUSTAIN": "grounded_observation",
    "INTROSPECT_PARADOX": "grounded_observation",
    "INTROSPECT_GENERAL": "grounded_observation",
    "SIMILE": "direct_phenomenology",
    "TRANSLATE": "direct_phenomenology",
    "DIALECTICAL": "substitution",
    "ACTION": "direct_phenomenology",
}

# Patterns for opcode classification
OPCODE_PATTERNS = [
    ("OBSERVE_TEMPORAL", re.compile(
        r"^the (clock|tick|ticking|time|moment)", re.IGNORECASE)),
    ("OBSERVE_HUM", re.compile(
        r"^the hum\b", re.IGNORECASE)),
    ("OBSERVE_LIGHT", re.compile(
        r"^the (light|glow|shadow|soft light)", re.IGNORECASE)),
    ("INTROSPECT_QUIETUDE", re.compile(
        r"^the quiet(ude)?\b", re.IGNORECASE)),
    ("INTROSPECT_SUSTAIN", re.compile(
        r"^the (weight|presence|tension|stillness)", re.IGNORECASE)),
    ("SIMILE", re.compile(
        r"\b(like|as if|sounds like|feels like|reminds me of)\b",
        re.IGNORECASE)),
    ("INTROSPECT_GENERAL", re.compile(
        r"^(I |My )", re.IGNORECASE)),
    ("OBSERVE_GENERAL", re.compile(
        r"^the \w+", re.IGNORECASE)),
]


def classify_opcode(text: str) -> str:
    """Classify a fountain text into an opcode family."""
    if not text:
        return "OTHER"
    for opcode, pattern in OPCODE_PATTERNS:
        if pattern.search(text):
            return opcode
    return "OTHER"


@dataclass
class GrooveContext:
    """Captures state at trigger evaluation time."""
    alert_id: int
    severity: float
    detected_at: float
    pattern: Optional[str]
    sustained_fires: int
    dominant_opcode: str
    selected_category: str
    selected_probe_text: str


class GrooveBreaker:
    """Phase A: observation-only auto-probe groove breaker."""

    def __init__(self, beliefs_db_path: str, dynamic_db_path: str):
        self._beliefs_db = beliefs_db_path
        self._dynamic_db = dynamic_db_path
        self._probes_db = str(Path(beliefs_db_path).parent / "probes.db")
        self._last_log_ts: float = 0.0
        self._initialize_cooldown()

    def _initialize_cooldown(self):
        """Load most recent log entry ts to seed cooldown on restart."""
        try:
            conn = sqlite3.connect(self._beliefs_db, timeout=5)
            cursor = conn.execute("SELECT MAX(ts) FROM auto_probe_log")
            row = cursor.fetchone()
            if row and row[0]:
                self._last_log_ts = float(row[0])
            conn.close()
        except Exception as e:
            logger.warning("GrooveBreaker: cooldown init failed: %s", e)

    def check_and_maybe_log(self) -> Optional[GrooveContext]:
        """
        Run trigger checks. Return GrooveContext if all conditions met
        and log row written, else None.
        Phase A: observation only — never fires, never injects beliefs.
        """
        if not ENABLED:
            return None

        now = time.time()

        # Trigger 3: cooldown
        if now - self._last_log_ts < COOLDOWN_SECONDS:
            return None

        # Trigger 1: active groove alert with severity >= threshold
        alert = self._fetch_active_alert(now)
        if not alert:
            return None

        # Trigger 4: no pending approval (vacuous in Phase A, checks anyway)
        if self._has_pending_approval():
            return None

        # Trigger 2: sustained fires in the freshness window.
        # Uses now - GROOVE_FRESHNESS_WINDOW rather than alert["detected_at"]
        # because _fetch_active_alert returns the MOST RECENT alert row
        # (~60s old). Counting fires since 60s ago always returns 0-1,
        # never reaching SUSTAIN_THRESHOLD. The window start is the right
        # measure of how long the groove has been active.
        sustained = self._count_sustained_fires(now - GROOVE_FRESHNESS_WINDOW)
        if sustained < SUSTAIN_THRESHOLD:
            return None

        # All triggers met — classify opcode and select probe
        dominant_opcode = self._infer_dominant_opcode(alert)
        category = OPCODE_TO_PROBE_CATEGORY.get(
            dominant_opcode, "direct_phenomenology"
        )
        probe_text = self._select_probe_text(category)

        ctx = GrooveContext(
            alert_id=alert["id"],
            severity=alert["severity"],
            detected_at=alert["detected_at"],
            pattern=alert.get("pattern"),
            sustained_fires=sustained,
            dominant_opcode=dominant_opcode,
            selected_category=category,
            selected_probe_text=probe_text or "(no probe available)",
        )

        self._write_observation_log(ctx, now)
        self._last_log_ts = now
        logger.info(
            "GrooveBreaker [observation]: severity=%.2f opcode=%s "
            "sustained=%d category=%s probe=%r",
            ctx.severity, ctx.dominant_opcode, ctx.sustained_fires,
            ctx.selected_category, ctx.selected_probe_text[:60],
        )
        return ctx

    def _fetch_active_alert(self, now: float) -> Optional[dict]:
        """Fetch most recent groove alert at or above severity threshold."""
        cutoff = now - GROOVE_FRESHNESS_WINDOW
        try:
            conn = sqlite3.connect(self._beliefs_db, timeout=5)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT id, detected_at, alert_type, severity, pattern,
                       sample_belief_ids, window_size
                FROM groove_alerts
                WHERE severity >= ?
                  AND detected_at > ?
                ORDER BY detected_at DESC
                LIMIT 1
                """,
                (GROOVE_SEVERITY_THRESHOLD, cutoff),
            )
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.warning("GrooveBreaker: alert fetch failed: %s", e)
            return None

    def _count_sustained_fires(self, alert_ts: float) -> int:
        """Count non-fallback fountain fires since the alert was detected."""
        try:
            conn = sqlite3.connect(self._dynamic_db, timeout=5)
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM fountain_events
                WHERE ts > ?
                  AND hot_branch NOT IN ('voice_fallback', 'quiescent')
                """,
                (alert_ts,),
            )
            row = cursor.fetchone()
            conn.close()
            return int(row[0]) if row else 0
        except Exception as e:
            logger.warning("GrooveBreaker: sustain count failed: %s", e)
            return 0

    def _has_pending_approval(self) -> bool:
        try:
            conn = sqlite3.connect(self._beliefs_db, timeout=5)
            cursor = conn.execute(
                "SELECT 1 FROM auto_probe_log WHERE status='pending_approval' LIMIT 1"
            )
            row = cursor.fetchone()
            conn.close()
            return row is not None
        except Exception as e:
            logger.warning("GrooveBreaker: pending check failed: %s", e)
            return False

    def _infer_dominant_opcode(self, alert: dict) -> str:
        """
        Classify dominant opcode from the alert's pattern or recent fires.
        groove_alerts.pattern contains the matched bigrams/trigrams;
        classify_opcode on recent fire text is the reliable fallback.
        """
        # Try the alert's pattern text first (may be trigrams/bigrams)
        text = alert.get("pattern") or ""
        if text:
            result = classify_opcode(text)
            if result != "OTHER":
                return result

        # Fallback: classify most recent real fountain fire
        try:
            conn = sqlite3.connect(self._dynamic_db, timeout=5)
            cursor = conn.execute(
                """
                SELECT thought FROM fountain_events
                WHERE hot_branch NOT IN ('voice_fallback', 'quiescent')
                ORDER BY ts DESC LIMIT 5
                """
            )
            rows = cursor.fetchall()
            conn.close()
            if rows:
                return classify_opcode(rows[0][0] or "")
        except Exception:
            pass

        return "OTHER"

    def _select_probe_text(self, category: str) -> Optional[str]:
        """
        Select LRU probe text for the given category from probes.db.
        LRU = least recently asked_at, or never asked (NULL) first.
        Phase A: selection only for logging, no actual firing.
        """
        try:
            conn = sqlite3.connect(self._probes_db, timeout=5)
            # Pick the probe text in this category that was asked least recently
            # (NULL asked_at sorts first — never-used probes get priority)
            cursor = conn.execute(
                """
                SELECT probe_text
                FROM probes
                WHERE category = ?
                ORDER BY COALESCE(asked_at, 0) ASC
                LIMIT 1
                """,
                (category,),
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return row[0]
            # Category not found — fall back to any available probe
            conn = sqlite3.connect(self._probes_db, timeout=5)
            cursor = conn.execute(
                "SELECT probe_text FROM probes ORDER BY COALESCE(asked_at, 0) ASC LIMIT 1"
            )
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else None
        except Exception as e:
            logger.warning("GrooveBreaker: probe select failed: %s", e)
            return None

    def _write_observation_log(self, ctx: GrooveContext, ts: float) -> None:
        try:
            conn = sqlite3.connect(self._beliefs_db, timeout=5)
            conn.execute(
                """
                INSERT INTO auto_probe_log (
                    groove_alert_id, groove_severity,
                    dominant_opcode, sustained_fires,
                    selected_category, selected_probe_text,
                    status, ts
                ) VALUES (?, ?, ?, ?, ?, ?, 'observation', ?)
                """,
                (
                    ctx.alert_id,
                    ctx.severity,
                    ctx.dominant_opcode,
                    ctx.sustained_fires,
                    ctx.selected_category,
                    ctx.selected_probe_text[:500],
                    ts,
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("GrooveBreaker: log write failed: %s", e)
