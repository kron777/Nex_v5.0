"""Substrate-state snapshot at tag-time.

Called when a fountain output is tagged coin/maybe/non. Freezes every
piece of substrate state we can cheaply read so later analytics can ask:
"what conditions preceded a hit?"

Returns a dict that the server endpoint writes to coincidence_context table.
All reads are best-effort: any individual failure returns None for that field
rather than failing the whole capture.
"""
from __future__ import annotations
import json
import sqlite3
import time
import urllib.request
from pathlib import Path
from typing import Any

DYN_DB = "/home/rr/Desktop/Desktop/nex5/data/dynamic.db"
BELIEFS_DB = "/home/rr/Desktop/Desktop/nex5/data/beliefs.db"
DYNAMIC_STATUS_URL = "http://localhost:8765/api/dynamic/status"


def _safe(fn):
    """Decorator: any exception -> return None, don't crash capture."""
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception:
            return None
    return wrapper


@_safe
def _read_dynamic_status() -> dict | None:
    """Hit own GUI endpoint for aperture + branch state. In-process server, fast."""
    with urllib.request.urlopen(DYNAMIC_STATUS_URL, timeout=2) as r:
        return json.loads(r.read().decode("utf-8"))


@_safe
def _recent_fountain(cx: sqlite3.Connection, exclude_fid: int, limit: int = 5) -> list[dict]:
    rows = cx.execute(
        "SELECT id, ts, thought, hot_branch, tag "
        "FROM fountain_events "
        "WHERE id != ? AND thought != '' AND thought NOT LIKE '[%' "
        "ORDER BY id DESC LIMIT ?",
        (exclude_fid, limit),
    ).fetchall()
    return [
        {"id": r[0], "ts": r[1], "thought": r[2][:200], "hot_branch": r[3], "tag": r[4]}
        for r in rows
    ]


@_safe
def _recent_surprises(cx: sqlite3.Connection, since_ts: float) -> list[dict]:
    rows = cx.execute(
        "SELECT id, ts, prediction_error, predicted_content, actual_content "
        "FROM surprise_events "
        "WHERE ts > ? AND surprise_flag = 1 "
        "AND predicted_content IS NOT NULL AND actual_content IS NOT NULL "
        "AND predicted_content != '' AND actual_content != '' "
        "ORDER BY ts DESC LIMIT 10",
        (since_ts,),
    ).fetchall()
    return [
        {
            "id": r[0],
            "ts": r[1],
            "error": r[2],
            "predicted": (r[3] or "")[:100],
            "actual": (r[4] or "")[:100],
        }
        for r in rows
    ]


@_safe
def _recent_daemon_fires(cx: sqlite3.Connection, since_ts: float) -> list[dict]:
    """Which daemon log tables fired recently? Returns timestamp + table name."""
    fires = []
    for table, ts_col in [
        ("identity_log", "composed_at"),
        ("pattern_log", "composed_at"),
        ("witness_log", "composed_at"),
        ("stillness_log", "ts"),
        ("crystallization_events", "ts"),
        ("harmonizer_events", "ts"),
        ("pipeline_events", "ts"),
    ]:
        try:
            row = cx.execute(
                f"SELECT {ts_col} FROM {table} WHERE {ts_col} > ? "
                f"ORDER BY {ts_col} DESC LIMIT 1",
                (since_ts,),
            ).fetchone()
            if row:
                fires.append({"daemon": table, "ts": row[0]})
        except sqlite3.OperationalError:
            continue
    fires.sort(key=lambda x: x["ts"], reverse=True)
    return fires


@_safe
def _belief_delta(cx_dyn: sqlite3.Connection, since_ts: float) -> int | None:
    """Count of fountain fires in last hour as a proxy for substrate churn."""
    row = cx_dyn.execute(
        "SELECT COUNT(*) FROM fountain_events WHERE ts > ?", (since_ts,)
    ).fetchone()
    return row[0] if row else None


@_safe
def _last_identity(cx: sqlite3.Connection) -> dict | None:
    row = cx.execute(
        "SELECT composed_at, statement, metrics_json FROM identity_log "
        "ORDER BY composed_at DESC LIMIT 1"
    ).fetchone()
    if not row:
        return None
    return {
        "composed_at": row[0],
        "statement": (row[1] or "")[:500],
        "metrics": row[2],
    }


@_safe
def _last_pattern(cx: sqlite3.Connection) -> dict | None:
    row = cx.execute(
        "SELECT composed_at, statement FROM pattern_log "
        "ORDER BY composed_at DESC LIMIT 1"
    ).fetchone()
    if not row:
        return None
    return {"composed_at": row[0], "statement": (row[1] or "")[:500]}


@_safe
def _last_witness(cx: sqlite3.Connection) -> dict | None:
    row = cx.execute(
        "SELECT composed_at, statement FROM witness_log "
        "ORDER BY composed_at DESC LIMIT 1"
    ).fetchone()
    if not row:
        return None
    return {"composed_at": row[0], "statement": (row[1] or "")[:500]}


def capture(fountain_event_id: int, tag: str) -> dict[str, Any]:
    """Build the full substrate snapshot. Returns a dict ready for DB insert.

    Heavy reads but capped: bounded queries, timeouts, best-effort fields.
    """
    now = time.time()
    one_hour_ago = now - 3600
    thirty_min_ago = now - 1800
    five_min_ago = now - 300

    dyn_status = _read_dynamic_status() or {}
    aperture = dyn_status.get("aperture")
    branches = dyn_status.get("branches") or []

    # Compact branch state for storage
    branch_activations = [
        {
            "id": b.get("branch_id"),
            "focus": b.get("focus_num"),
            "texture": b.get("texture_num"),
            "is_seed": b.get("is_seed"),
            "last_attended_at": b.get("last_attended_at"),
        }
        for b in branches
    ]

    cx_dyn = sqlite3.connect(DYN_DB, timeout=5)

    recent_fountain = _recent_fountain(cx_dyn, fountain_event_id) or []
    recent_surprises = _recent_surprises(cx_dyn, thirty_min_ago) or []
    recent_daemons = _recent_daemon_fires(cx_dyn, five_min_ago) or []
    belief_delta_1h = _belief_delta(cx_dyn, one_hour_ago)
    last_identity = _last_identity(cx_dyn)
    last_pattern = _last_pattern(cx_dyn)
    last_witness = _last_witness(cx_dyn)

    # Find the hot_branch of the tagged thought itself
    hot_branch_row = cx_dyn.execute(
        "SELECT hot_branch FROM fountain_events WHERE id=?",
        (fountain_event_id,),
    ).fetchone()
    hot_branch = hot_branch_row[0] if hot_branch_row else None

    cx_dyn.close()

    snapshot = {
        "fountain_event_id": fountain_event_id,
        "tagged_at": now,
        "tag": tag,
        "aperture": aperture,
        "hot_branch": hot_branch,
        "branch_activations": json.dumps(branch_activations),
        "recent_fountain": json.dumps(recent_fountain),
        "recent_surprises": json.dumps(recent_surprises),
        "recent_daemons": json.dumps(recent_daemons),
        "belief_delta_1h": belief_delta_1h,
        "groove_alerts": None,  # not currently in DB; capture from log later
        "last_identity": json.dumps(last_identity) if last_identity else None,
        "last_pattern": json.dumps(last_pattern) if last_pattern else None,
        "last_witness": json.dumps(last_witness) if last_witness else None,
        "full_snapshot": json.dumps({
            "aperture": aperture,
            "active_branch_count": dyn_status.get("active_branch_count"),
            "aggregate_focus": dyn_status.get("aggregate_focus"),
            "aggregate_texture": dyn_status.get("aggregate_texture"),
            "branches": branch_activations,
            "recent_fountain": recent_fountain,
            "recent_surprises_count": len(recent_surprises),
            "recent_daemons_count": len(recent_daemons),
            "belief_delta_1h": belief_delta_1h,
        }),
    }
    return snapshot


def persist(snapshot: dict[str, Any]) -> bool:
    """Upsert the snapshot into coincidence_context."""
    cx = sqlite3.connect(DYN_DB, timeout=5)
    try:
        cx.execute(
            "INSERT INTO coincidence_context "
            "(fountain_event_id, tagged_at, tag, aperture, hot_branch, "
            " branch_activations, recent_fountain, recent_surprises, "
            " recent_daemons, belief_delta_1h, groove_alerts, "
            " last_identity, last_pattern, last_witness, full_snapshot) "
            "VALUES (:fountain_event_id, :tagged_at, :tag, :aperture, :hot_branch, "
            " :branch_activations, :recent_fountain, :recent_surprises, "
            " :recent_daemons, :belief_delta_1h, :groove_alerts, "
            " :last_identity, :last_pattern, :last_witness, :full_snapshot) "
            "ON CONFLICT(fountain_event_id) DO UPDATE SET "
            " tagged_at=excluded.tagged_at, tag=excluded.tag, "
            " aperture=excluded.aperture, hot_branch=excluded.hot_branch, "
            " branch_activations=excluded.branch_activations, "
            " recent_fountain=excluded.recent_fountain, "
            " recent_surprises=excluded.recent_surprises, "
            " recent_daemons=excluded.recent_daemons, "
            " belief_delta_1h=excluded.belief_delta_1h, "
            " groove_alerts=excluded.groove_alerts, "
            " last_identity=excluded.last_identity, "
            " last_pattern=excluded.last_pattern, "
            " last_witness=excluded.last_witness, "
            " full_snapshot=excluded.full_snapshot",
            snapshot,
        )
        cx.commit()
        return True
    finally:
        cx.close()


def capture_and_persist(fountain_event_id: int, tag: str) -> dict[str, Any]:
    """Convenience: do both. Used by the server endpoint."""
    snapshot = capture(fountain_event_id, tag)
    persist(snapshot)
    return snapshot
