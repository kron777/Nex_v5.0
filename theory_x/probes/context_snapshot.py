"""Capture NEX's full substrate-state at the moment a probe is sent.

Returns a flat dict[str, str] where every value is JSON-stringified
(lists/dicts) or str() (scalars). The probe_context table stores rows
as (probe_id, snapshot_key, snapshot_value TEXT), so all values must
be strings.

Field → source table mapping:
  active_arcs        — beliefs.arcs
  dormant_top5       — beliefs.dormant_beliefs JOIN beliefs
  open_signals       — beliefs.signals (time-windowed; no resolved flag)
  recent_fires       — dynamic.fountain_events (the events themselves)
  groove_alerts      — beliefs.groove_alerts WHERE acknowledged_at IS NULL
  cooldowns          — beliefs.signal_cooldown WHERE cooldown_until > now
  feed_activity      — sense.sense_events GROUP BY stream
  branch_activations — dynamic.pipeline_events recent, grouped by branch
  current_mode       — beliefs.config WHERE key='current_mode'

Design invariants:
- Snapshot must never abort the probe. Every section is try/excepted.
- On failure, value is "[ERROR: <exception>]" — visible as data, not silence.
- Err toward over-capture; readers can ignore fields at analysis time.
"""
from __future__ import annotations

import json
import os
import time

from substrate import Reader

THEORY_X_STAGE = None

_DEFAULT_WINDOW_SEC = 600


def _window() -> int:
    return int(os.environ.get("NEX5_PROBE_SNAPSHOT_WINDOW_SEC", _DEFAULT_WINDOW_SEC))


def snapshot_context(
    beliefs_reader: Reader,
    dynamic_reader: Reader,
    sense_reader: Reader,
) -> dict[str, str]:
    """Return flat dict[str, str] of substrate-state at call time.

    Every key in the REQUIRED FIELDS spec is always present. On exception
    the value is "[ERROR: <msg>]" so missing data is visible at read time.
    """
    now = time.time()
    window = _window()
    snap: dict[str, str] = {}

    # --- active_arcs: arcs with recent activity and low dormancy score ---
    try:
        rows = beliefs_reader.read(
            "SELECT id, arc_type, member_count, progression_score, "
            "transformation_score, theme_summary, last_active_at, dormancy_score "
            "FROM arcs "
            "WHERE last_active_at > ? "
            "ORDER BY last_active_at DESC LIMIT 10",
            (now - 3600,),
        )
        snap["active_arcs"] = json.dumps([dict(r) for r in rows])
    except Exception as e:
        snap["active_arcs"] = f"[ERROR: {e}]"

    # --- dormant_top5: highest-dormancy-score beliefs with content ---
    try:
        rows = beliefs_reader.read(
            "SELECT d.belief_id, b.content, d.dormancy_score, "
            "d.last_active_at, b.branch_id "
            "FROM dormant_beliefs d "
            "JOIN beliefs b ON d.belief_id = b.id "
            "ORDER BY d.dormancy_score DESC LIMIT 5",
        )
        snap["dormant_top5"] = json.dumps([dict(r) for r in rows])
    except Exception as e:
        snap["dormant_top5"] = f"[ERROR: {e}]"

    # --- open_signals: recent structural detections (no resolved flag) ---
    try:
        rows = beliefs_reader.read(
            "SELECT id, detector_name, signal_type, confidence, payload, "
            "branches, entities, detected_at "
            "FROM signals "
            "WHERE detected_at > ? "
            "ORDER BY detected_at DESC LIMIT 20",
            (now - window,),
        )
        snap["open_signals"] = json.dumps([dict(r) for r in rows])
    except Exception as e:
        snap["open_signals"] = f"[ERROR: {e}]"

    # --- recent_fires: fountain events (thought + readiness) in window ---
    try:
        rows = dynamic_reader.read(
            "SELECT id, ts, thought, droplet, readiness, hot_branch, word_count "
            "FROM fountain_events "
            "WHERE ts > ? "
            "ORDER BY ts DESC LIMIT 20",
            (now - window,),
        )
        snap["recent_fires"] = json.dumps([dict(r) for r in rows])
    except Exception as e:
        snap["recent_fires"] = f"[ERROR: {e}]"

    # --- groove_alerts: unacknowledged rut/groove warnings ---
    try:
        rows = beliefs_reader.read(
            "SELECT id, detected_at, alert_type, severity, pattern, "
            "sample_belief_ids, window_size "
            "FROM groove_alerts "
            "WHERE acknowledged_at IS NULL "
            "ORDER BY detected_at DESC LIMIT 10",
        )
        snap["groove_alerts"] = json.dumps([dict(r) for r in rows])
    except Exception as e:
        snap["groove_alerts"] = f"[ERROR: {e}]"

    # --- cooldowns: patterns currently in anti-rut cooldown ---
    try:
        rows = beliefs_reader.read(
            "SELECT content_hash, content, cooldown_until, reason, created_at "
            "FROM signal_cooldown "
            "WHERE cooldown_until > ?",
            (now,),
        )
        snap["cooldowns"] = json.dumps([dict(r) for r in rows])
    except Exception as e:
        snap["cooldowns"] = f"[ERROR: {e}]"

    # --- feed_activity: recent sense intake summarised by stream ---
    try:
        rows = sense_reader.read(
            "SELECT stream, COUNT(*) AS event_count, MAX(timestamp) AS latest_ts "
            "FROM sense_events "
            "WHERE timestamp > ? "
            "GROUP BY stream "
            "ORDER BY event_count DESC LIMIT 20",
            (now - window,),
        )
        snap["feed_activity"] = json.dumps([dict(r) for r in rows])
    except Exception as e:
        snap["feed_activity"] = f"[ERROR: {e}]"

    # --- branch_activations: recent pipeline hits per branch in window ---
    try:
        rows = dynamic_reader.read(
            "SELECT branch_id, COUNT(*) AS hit_count, MAX(ts) AS latest_ts, "
            "AVG(magnitude) AS avg_magnitude "
            "FROM pipeline_events "
            "WHERE ts > ? AND branch_id IS NOT NULL "
            "GROUP BY branch_id "
            "ORDER BY hit_count DESC LIMIT 15",
            (now - window,),
        )
        snap["branch_activations"] = json.dumps([dict(r) for r in rows])
    except Exception as e:
        snap["branch_activations"] = f"[ERROR: {e}]"

    # --- current_mode: persisted mode name from config table ---
    try:
        rows = beliefs_reader.read(
            "SELECT value FROM config WHERE key = 'current_mode'"
        )
        snap["current_mode"] = rows[0]["value"] if rows else "unknown"
    except Exception as e:
        snap["current_mode"] = f"[ERROR: {e}]"

    return snap
