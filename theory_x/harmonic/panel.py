"""HARMONIC METRIC panel data preparation.

CHORD §4 deliverable C, session 2.

Mirrors the diversity/panel.py pattern: a single `overview()` function
that the /api/harmonic/overview route calls. Returns a JSON-ready dict
with the data the HUD HARMONIC METRIC sub-panel needs to render.

Reads (all read-only, no writes):
  - substrate_coherence (conversations.db): last 144 rows for trajectory
    (12h at 5-min tick) + most recent total + per-pair scores
  - fountain_events (dynamic.db): most recent substrate_voice fire +
    anchor_belief_id
  - beliefs (beliefs.db): content + tier + source for the most recent
    anchor

Returns dict with keys:
  current        — latest substrate_coherence row dict, or None if empty
  recent         — list of {ts, total} for trajectory (sparkline data)
  pair_scores    — flat dict of pair_name -> latest score
  walk           — {anchor_id, content, tier, source, last_ts, track_label}
                   or None if no anchor has been voiced
  meta           — {total_rows, last_tick_age_seconds}
"""
from __future__ import annotations

import json
import time
from typing import Optional


_TRACK_1 = (4442, 4541)
_TRACK_2 = (4803, 4902)
_PRACTICE = (3609, 3614)


def _track_label_for(anchor_id: Optional[int]) -> str:
    if anchor_id is None:
        return "unknown"
    if _TRACK_1[0] <= anchor_id <= _TRACK_1[1]:
        return f"Track 1 ({anchor_id - _TRACK_1[0] + 1}/100)"
    if _TRACK_2[0] <= anchor_id <= _TRACK_2[1]:
        return f"Track 2 ({anchor_id - _TRACK_2[0] + 1}/100)"
    if _PRACTICE[0] <= anchor_id <= _PRACTICE[1]:
        return f"Practice ({anchor_id - _PRACTICE[0] + 1}/6)"
    return f"Other (id {anchor_id})"


def overview(
    conversations_reader,
    dynamic_reader=None,
    beliefs_reader=None,
) -> dict:
    """Return data for the HARMONIC METRIC HUD panel.

    conversations_reader is required (substrate_coherence lives there).
    dynamic_reader and beliefs_reader are optional — if absent, the
    walk-anchor section returns None gracefully.
    """
    out: dict = {
        "current": None,
        "recent": [],
        "pair_scores": {},
        "walk": None,
        "meta": {"total_rows": 0, "last_tick_age_seconds": None},
    }

    # ── current + recent trajectory ──────────────────────────────────────────
    try:
        rows = conversations_reader.read(
            "SELECT id, ts, total, pair_scores, walk_state, walk_anchor_id, "
            "drive_conflict FROM substrate_coherence "
            "ORDER BY ts DESC LIMIT 144"
        )
        rows = list(rows or [])
        if rows:
            latest = rows[0]
            out["current"] = {
                "id": int(latest["id"]),
                "ts": float(latest["ts"]),
                "total": round(float(latest["total"]), 3),
                "walk_state": latest["walk_state"],
                "walk_anchor_id": (
                    int(latest["walk_anchor_id"])
                    if latest["walk_anchor_id"] is not None else None
                ),
                "drive_conflict": latest["drive_conflict"],
            }
            try:
                out["pair_scores"] = {
                    k: round(float(v), 3)
                    for k, v in json.loads(latest["pair_scores"]).items()
                }
            except Exception:
                out["pair_scores"] = {}

            # Trajectory: oldest first for sparkline rendering
            out["recent"] = [
                {"ts": float(r["ts"]), "total": round(float(r["total"]), 3)}
                for r in reversed(rows)
            ]
            out["meta"]["total_rows"] = len(rows)
            out["meta"]["last_tick_age_seconds"] = round(
                time.time() - float(latest["ts"]), 1
            )
    except Exception:
        pass  # Empty table on first boot; return defaults

    # ── walk anchor (most recent substrate_voice fire) ───────────────────────
    if dynamic_reader is not None and beliefs_reader is not None:
        try:
            sv_rows = dynamic_reader.read(
                "SELECT ts, anchor_belief_id FROM fountain_events "
                "WHERE hot_branch='substrate_voice' "
                "ORDER BY ts DESC LIMIT 1"
            )
            sv_rows = list(sv_rows or [])
            if sv_rows and sv_rows[0]["anchor_belief_id"]:
                anchor_id = int(sv_rows[0]["anchor_belief_id"])
                sv_ts = float(sv_rows[0]["ts"])
                belief_rows = beliefs_reader.read(
                    "SELECT content, tier, source FROM beliefs WHERE id = ?",
                    (anchor_id,),
                )
                belief_rows = list(belief_rows or [])
                if belief_rows:
                    b = belief_rows[0]
                    out["walk"] = {
                        "anchor_id": anchor_id,
                        "content": (b["content"] or "")[:280],
                        "tier": int(b["tier"]) if b["tier"] is not None else None,
                        "source": b["source"],
                        "last_ts": sv_ts,
                        "age_seconds": round(time.time() - sv_ts, 1),
                        "track_label": _track_label_for(anchor_id),
                    }
        except Exception:
            pass  # Walk section optional; graceful degrade

    return out
