"""Substrate snapshots — capture, score, prune.

See SUBSTRATE_SNAPSHOTS.md for the full design.

Public API:
    capture_snapshot(fountain_event_id, substrate_state, writer)
        Capture one snapshot. Fire-and-forget; never raises.

    score_pending_snapshots(reader, writer, weights_path=None)
        Find snapshots with NULL retention_tier, compute v2 score,
        assign tier. Returns count scored.

    prune_snapshots(reader, writer, commit=False)
        Apply retention policy. Dry-run by default.
        Returns dict of {tier: count_to_delete/deleted}.

    pin_snapshot(fountain_event_id, writer)
    unpin_snapshot(fountain_event_id, writer)
    delete_snapshot(fountain_event_id, writer)
    snapshot_stats(reader) -> dict

All functions accept Reader/Writer (substrate.reader.Reader,
substrate.writer.Writer) for dynamic.db.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("theory_x.snapshots")

# Retention windows in seconds.
_DAY = 86400
_RETENTION_SECONDS = {
    "genius":   None,        # None = forever
    "moment":   90 * _DAY,
    "ordinary": 7 * _DAY,
}

# v2 thresholds (must match genius_score_weights.json).
_TIER_GENIUS   = 0.49   # >= this is genius
_TIER_MOMENT   = 0.29   # >= this is moment, below is ordinary


# ── Capture ─────────────────────────────────────────────────────────────────

def capture_snapshot(
    fountain_event_id: int,
    substrate_state: dict[str, Any],
    writer,
) -> bool:
    """Capture a substrate snapshot for a given fountain_event.

    substrate_state should contain (all optional, all may be None):
        coherence: float
        voltage: float
        drives: dict[str, float]
        walk_state: str
        walk_anchor_id: int
        hot_branches: dict[str, float]
        harmonic_pairs: dict[str, float]
        gate_composition: dict
        groove_severity: float
        recent_fires_ids: list[int]
        beliefs_in_attention: list[int]

    retention_tier is left NULL — set by score_pending_snapshots() pass.
    Fire-and-forget. Logs errors, never raises.
    """
    try:
        s = substrate_state or {}
        writer.write(
            "INSERT OR IGNORE INTO substrate_snapshots "
            "(fountain_event_id, ts, coherence, voltage, drives_json, "
            "walk_state, walk_anchor_id, hot_branches_json, harmonic_pairs_json, "
            "gate_composition_json, groove_severity, recent_fires_ids_json, "
            "beliefs_in_attention_json, retention_tier, pinned) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 0)",
            (
                fountain_event_id,
                time.time(),
                s.get("coherence"),
                s.get("voltage"),
                json.dumps(s.get("drives") or {}),
                s.get("walk_state"),
                s.get("walk_anchor_id"),
                json.dumps(s.get("hot_branches") or {}),
                json.dumps(s.get("harmonic_pairs") or {}),
                json.dumps(s.get("gate_composition") or {}),
                s.get("groove_severity"),
                json.dumps(s.get("recent_fires_ids") or []),
                json.dumps(s.get("beliefs_in_attention") or []),
            ),
        )
        return True
    except Exception as exc:
        logger.warning("capture_snapshot failed for fire %d: %s",
                       fountain_event_id, exc)
        return False


# ── Scoring pass ────────────────────────────────────────────────────────────

def score_pending_snapshots(
    reader,
    writer,
    weights_path: Optional[Path] = None,
    limit: int = 1000,
) -> dict[str, int]:
    """Score snapshots that have retention_tier = NULL.

    Reads fountain_events.thought via FK, computes v2 score, assigns tier.
    Returns counts per tier.

    Reader must be over dynamic.db.
    """
    counts = {"genius": 0, "moment": 0, "ordinary": 0, "errors": 0}

    # Lazy import — avoid hard dep at module load
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from theory_x.genius.score_v2 import (
            compute_features,
            load_t6_beliefs,
        )
    except Exception as exc:
        logger.error("score_v2 import failed: %s", exc)
        counts["errors"] = -1
        return counts

    # Load v2 weights
    wp = weights_path or Path(__file__).resolve().parents[2] / "genius_score_weights.json"
    try:
        weights = json.loads(wp.read_text())
        w = weights["weights"]
        b = weights["bias"]
    except Exception as exc:
        logger.error("weights load failed: %s", exc)
        counts["errors"] = -1
        return counts

    # Pending snapshots joined to fountain content
    try:
        rows = reader.read(
            "SELECT s.id AS snapshot_id, s.fountain_event_id, "
            "       f.thought, f.ts AS fire_ts, f.hot_branch "
            "FROM substrate_snapshots s "
            "JOIN fountain_events f ON s.fountain_event_id = f.id "
            "WHERE s.retention_tier IS NULL "
            "ORDER BY s.id ASC LIMIT ?",
            (limit,),
        )
    except Exception as exc:
        logger.error("pending query failed: %s", exc)
        counts["errors"] = -1
        return counts

    if not rows:
        return counts

    t6 = load_t6_beliefs()

    # For prior_thoughts, batch-load surrounding fires per snapshot.
    for r in rows:
        try:
            sid = int(r["snapshot_id"])
            fire = {
                "id":         int(r["fountain_event_id"]),
                "ts":         float(r["fire_ts"]),
                "thought":    r["thought"],
                "hot_branch": r["hot_branch"],
            }
            # Prior 50 thoughts (substrate-wide, by ts)
            prior_rows = reader.read(
                "SELECT thought FROM fountain_events WHERE ts < ? "
                "ORDER BY ts DESC LIMIT 50",
                (fire["ts"],),
            )
            prior_thoughts = [pr["thought"] for pr in (prior_rows or [])]

            feats = compute_features(fire, prior_thoughts, t6)
            z = sum(w[j] * feats[j] for j in range(len(w))) + b
            # sigmoid
            import math
            score = 1.0 / (1.0 + math.exp(-z)) if z >= 0 else (
                math.exp(z) / (1.0 + math.exp(z)))

            if score >= _TIER_GENIUS:
                tier = "genius"
            elif score >= _TIER_MOMENT:
                tier = "moment"
            else:
                tier = "ordinary"

            writer.write(
                "UPDATE substrate_snapshots SET retention_tier = ? WHERE id = ?",
                (tier, sid),
            )
            counts[tier] += 1
        except Exception as exc:
            logger.warning("scoring snapshot %s failed: %s",
                           r.get("snapshot_id"), exc)
            counts["errors"] += 1

    return counts


# ── Pruning ─────────────────────────────────────────────────────────────────

def prune_snapshots(reader, writer, commit: bool = False) -> dict[str, int]:
    """Apply retention policy. Dry-run by default.

    Returns {tier: count_to_delete_or_deleted, 'pinned_skipped': N}.
    """
    now = time.time()
    result = {"genius": 0, "moment": 0, "ordinary": 0,
              "pending_unscored": 0, "pinned_skipped": 0}

    for tier, retention_s in _RETENTION_SECONDS.items():
        if retention_s is None:
            continue  # genius = forever
        cutoff = now - retention_s
        rows = reader.read(
            "SELECT id FROM substrate_snapshots "
            "WHERE retention_tier = ? AND ts < ? AND pinned = 0",
            (tier, cutoff),
        )
        ids = [int(r["id"]) for r in (rows or [])]
        result[tier] = len(ids)

        if commit and ids:
            placeholders = ",".join("?" * len(ids))
            writer.write(
                f"DELETE FROM substrate_snapshots WHERE id IN ({placeholders})",
                tuple(ids),
            )

    # Count unscored snapshots — informational
    rows = reader.read(
        "SELECT COUNT(*) AS n FROM substrate_snapshots "
        "WHERE retention_tier IS NULL", (),
    )
    if rows:
        result["pending_unscored"] = int(rows[0]["n"])

    # Count pinned that would otherwise be pruned
    rows = reader.read(
        "SELECT COUNT(*) AS n FROM substrate_snapshots WHERE pinned = 1", (),
    )
    if rows:
        result["pinned_skipped"] = int(rows[0]["n"])

    return result


# ── Manual controls ─────────────────────────────────────────────────────────

def pin_snapshot(fountain_event_id: int, writer) -> bool:
    try:
        writer.write(
            "UPDATE substrate_snapshots SET pinned = 1 "
            "WHERE fountain_event_id = ?", (fountain_event_id,),
        )
        return True
    except Exception as exc:
        logger.warning("pin failed: %s", exc)
        return False


def unpin_snapshot(fountain_event_id: int, writer) -> bool:
    try:
        writer.write(
            "UPDATE substrate_snapshots SET pinned = 0 "
            "WHERE fountain_event_id = ?", (fountain_event_id,),
        )
        return True
    except Exception as exc:
        logger.warning("unpin failed: %s", exc)
        return False


def delete_snapshot(fountain_event_id: int, writer) -> bool:
    """Manual delete — bypasses pin/tier checks. Use with care."""
    try:
        writer.write(
            "DELETE FROM substrate_snapshots WHERE fountain_event_id = ?",
            (fountain_event_id,),
        )
        return True
    except Exception as exc:
        logger.warning("delete failed: %s", exc)
        return False


def snapshot_stats(reader) -> dict[str, Any]:
    """Return stats: counts by tier, total, oldest, newest."""
    stats: dict[str, Any] = {
        "total": 0, "genius": 0, "moment": 0,
        "ordinary": 0, "unscored": 0, "pinned": 0,
        "oldest_ts": None, "newest_ts": None,
    }
    rows = reader.read(
        "SELECT retention_tier, COUNT(*) AS n FROM substrate_snapshots "
        "GROUP BY retention_tier", (),
    )
    for r in (rows or []):
        tier = r["retention_tier"]
        n = int(r["n"])
        stats["total"] += n
        if tier is None:
            stats["unscored"] = n
        elif tier in ("genius", "moment", "ordinary"):
            stats[tier] = n

    rows = reader.read(
        "SELECT MIN(ts) AS oldest, MAX(ts) AS newest "
        "FROM substrate_snapshots", (),
    )
    if rows:
        stats["oldest_ts"] = rows[0]["oldest"]
        stats["newest_ts"] = rows[0]["newest"]

    rows = reader.read(
        "SELECT COUNT(*) AS n FROM substrate_snapshots WHERE pinned = 1", (),
    )
    if rows:
        stats["pinned"] = int(rows[0]["n"])

    return stats
