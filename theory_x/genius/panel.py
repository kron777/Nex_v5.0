"""GENIUS panel data preparation.

GENIUS_SCORE_v2.md §7d. Mirrors theory_x/harmonic/panel.py pattern:
a single `overview()` function the /api/genius/recent route calls.
Returns a JSON-ready dict with the data the HUD needs to render.

Reads (all read-only, no writes):
  - genius_tags (conversations.db): last N tagged fires
  - fountain_events (dynamic.db): joined for thought + branch
"""
from __future__ import annotations

import time
from typing import Optional


_DEFAULT_LIMIT = 20


def overview(
    conversations_reader,
    dynamic_reader,
    limit: int = _DEFAULT_LIMIT,
    only_striking: bool = False,
) -> dict:
    """Return data for the GENIUS HUD panel.

    conversations_reader is required (genius_tags lives there).
    dynamic_reader is required (fountain_events lives there).

    Returns dict with keys:
      tags          — list of {fire_id, score, class, weights_version,
                       tagged_at, age_seconds, thought, hot_branch,
                       fire_ts}; ordered most-recent first
      stats         — {total, striking, striking_rate, current_version,
                       current_threshold}
      meta          — {last_tag_age_seconds, last_tagged_at}
    """
    out: dict = {
        "tags": [],
        "stats": {
            "total": 0,
            "striking": 0,
            "striking_rate": 0.0,
            "current_version": None,
            "current_threshold": None,
        },
        "meta": {
            "last_tag_age_seconds": None,
            "last_tagged_at": None,
        },
    }

    # ── recent tag rows ──────────────────────────────────────────────────────
    try:
        if only_striking:
            tag_rows = conversations_reader.read(
                "SELECT fountain_event_id, score, class, weights_version, "
                "tagged_at FROM genius_tags WHERE class = 'STRIKING' "
                "ORDER BY tagged_at DESC LIMIT ?",
                (int(limit),),
            )
        else:
            tag_rows = conversations_reader.read(
                "SELECT fountain_event_id, score, class, weights_version, "
                "tagged_at FROM genius_tags "
                "ORDER BY tagged_at DESC LIMIT ?",
                (int(limit),),
            )
    except Exception:
        return out
    tag_rows = list(tag_rows or [])
    if not tag_rows:
        return out

    # ── join with fountain_events for thought + branch ───────────────────────
    fire_ids = [int(r["fountain_event_id"]) for r in tag_rows]
    fires_by_id: dict[int, dict] = {}
    try:
        placeholders = ",".join("?" * len(fire_ids))
        fire_rows = dynamic_reader.read(
            f"SELECT id, ts, thought, hot_branch FROM fountain_events "
            f"WHERE id IN ({placeholders})",
            tuple(fire_ids),
        )
        for fr in (fire_rows or []):
            fires_by_id[int(fr["id"])] = {
                "ts": float(fr["ts"]),
                "thought": fr["thought"] or "",
                "hot_branch": fr["hot_branch"],
            }
    except Exception:
        pass  # tags without fire context still render

    now = time.time()
    tags_out = []
    for r in tag_rows:
        fid = int(r["fountain_event_id"])
        fire = fires_by_id.get(fid, {})
        tagged_at = float(r["tagged_at"])
        tags_out.append({
            "fire_id": fid,
            "score": round(float(r["score"]), 4),
            "class": r["class"],
            "weights_version": r["weights_version"],
            "tagged_at": tagged_at,
            "age_seconds": round(now - tagged_at, 1),
            "thought": (fire.get("thought") or "")[:400],
            "hot_branch": fire.get("hot_branch"),
            "fire_ts": fire.get("ts"),
        })
    out["tags"] = tags_out

    # ── stats: totals + current version/threshold ────────────────────────────
    try:
        stat_rows = conversations_reader.read(
            "SELECT class, COUNT(*) AS n FROM genius_tags GROUP BY class"
        )
        total = 0
        striking = 0
        for sr in (stat_rows or []):
            n = int(sr["n"])
            total += n
            if sr["class"] == "STRIKING":
                striking = n
        out["stats"]["total"] = total
        out["stats"]["striking"] = striking
        out["stats"]["striking_rate"] = (
            round(striking / max(1, total), 4) if total else 0.0
        )
    except Exception:
        pass

    # Current version = the one in the most recent tag row
    try:
        latest = tag_rows[0]
        out["stats"]["current_version"] = latest["weights_version"]
        out["meta"]["last_tagged_at"] = float(latest["tagged_at"])
        out["meta"]["last_tag_age_seconds"] = round(
            now - float(latest["tagged_at"]), 1
        )
    except Exception:
        pass

    return out
