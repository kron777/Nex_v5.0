"""Read access to tagged fountain outputs and their captured context.

Used by:
  - chat handler (on-demand keyword retrieval + always-in-prompt summary)
  - fountain generator (can sample from tagged thoughts)
  - identity_loop / pattern_loop (tag-aware metrics)

Feature flag: NEX_TAG_FEEDBACK_ON env var. When unset or '0', all functions
return empty results — substrate sees nothing, no behavior change. Switch on
with NEX_TAG_FEEDBACK_ON=1 in the run.py env.

All reads best-effort. Never raises — returns empty list/dict on any failure.
"""
from __future__ import annotations
import json
import os
import sqlite3
from typing import Any

DYN_DB = "/home/rr/Desktop/Desktop/nex5/data/dynamic.db"
FLAG_VAR = "NEX_TAG_FEEDBACK_ON"


def feedback_enabled() -> bool:
    """Kill switch: when false, all retrieval returns empty."""
    return os.environ.get(FLAG_VAR, "0") == "1"


def _connect() -> sqlite3.Connection | None:
    try:
        cx = sqlite3.connect(DYN_DB, timeout=5)
        cx.row_factory = sqlite3.Row
        return cx
    except Exception:
        return None


def _format_thought_plain(row: dict) -> str:
    """Format-1: quote tagged thought with its tag."""
    return f'"{row["thought"]}" [{row["tag"]}, fid={row["id"]}]'


def _format_thought_rich(row: dict, ctx: dict | None) -> str:
    """Format-3: thought with tag and substrate state at tag time."""
    base = _format_thought_plain(row)
    if not ctx:
        return base
    bits = []
    if ctx.get("aperture") is not None:
        bits.append(f"aperture={ctx['aperture']:.3f}")
    if ctx.get("hot_branch"):
        bits.append(f"branch={ctx['hot_branch']}")
    if ctx.get("belief_delta_1h") is not None:
        bits.append(f"fires_1h={ctx['belief_delta_1h']}")
    if bits:
        return base + " (" + ", ".join(bits) + ")"
    return base


def recent_tags(limit: int = 5, tag_filter: str | None = None,
                rich: bool = False) -> list[str]:
    """Return most recent N tagged thoughts as formatted strings.

    rich=True includes the substrate context (format-3). rich=False is plain.
    tag_filter='coin' | 'maybe' | 'non' | None (all tags).
    """
    if not feedback_enabled():
        return []
    cx = _connect()
    if cx is None:
        return []
    try:
        sql = ("SELECT id, ts, thought, tag FROM fountain_events "
               "WHERE tag IS NOT NULL")
        params: list[Any] = []
        if tag_filter in ("coin", "maybe", "non"):
            sql += " AND tag = ?"
            params.append(tag_filter)
        sql += " ORDER BY ts DESC LIMIT ?"
        params.append(limit)
        rows = cx.execute(sql, params).fetchall()
        if not rows:
            return []
        if not rich:
            return [_format_thought_plain(dict(r)) for r in rows]
        # Rich format: also fetch context for each
        out = []
        for r in rows:
            ctx_row = cx.execute(
                "SELECT aperture, hot_branch, belief_delta_1h "
                "FROM coincidence_context WHERE fountain_event_id = ?",
                (r["id"],),
            ).fetchone()
            ctx = dict(ctx_row) if ctx_row else None
            out.append(_format_thought_rich(dict(r), ctx))
        return out
    except Exception:
        return []
    finally:
        cx.close()


def tags_matching(query: str, limit: int = 5, rich: bool = False) -> list[str]:
    """Keyword search across tagged thoughts. Case-insensitive LIKE match.
    Returns most recent matches, formatted.
    """
    if not feedback_enabled() or not query or not query.strip():
        return []
    cx = _connect()
    if cx is None:
        return []
    try:
        pattern = f"%{query.strip().lower()}%"
        rows = cx.execute(
            "SELECT id, ts, thought, tag FROM fountain_events "
            "WHERE tag IS NOT NULL AND LOWER(thought) LIKE ? "
            "ORDER BY ts DESC LIMIT ?",
            (pattern, limit),
        ).fetchall()
        if not rows:
            return []
        if not rich:
            return [_format_thought_plain(dict(r)) for r in rows]
        out = []
        for r in rows:
            ctx_row = cx.execute(
                "SELECT aperture, hot_branch, belief_delta_1h "
                "FROM coincidence_context WHERE fountain_event_id = ?",
                (r["id"],),
            ).fetchone()
            ctx = dict(ctx_row) if ctx_row else None
            out.append(_format_thought_rich(dict(r), ctx))
        return out
    except Exception:
        return []
    finally:
        cx.close()


def tag_summary() -> dict[str, Any]:
    """Compact counts + 2 most-recent coin examples for always-in-prompt block.
    Returns {'enabled': bool, 'counts': {coin,maybe,non}, 'recent_coins': [...]}
    """
    if not feedback_enabled():
        return {"enabled": False, "counts": {}, "recent_coins": []}
    cx = _connect()
    if cx is None:
        return {"enabled": True, "counts": {}, "recent_coins": []}
    try:
        counts_rows = cx.execute(
            "SELECT tag, COUNT(*) AS n FROM fountain_events "
            "WHERE tag IS NOT NULL GROUP BY tag"
        ).fetchall()
        counts = {r["tag"]: r["n"] for r in counts_rows}
        recent_coins_rows = cx.execute(
            "SELECT id, thought FROM fountain_events "
            "WHERE tag = 'coin' ORDER BY ts DESC LIMIT 2"
        ).fetchall()
        recent_coins = [r["thought"] for r in recent_coins_rows]
        return {
            "enabled": True,
            "counts": counts,
            "total_tagged": sum(counts.values()),
            "recent_coins": recent_coins,
        }
    except Exception:
        return {"enabled": True, "counts": {}, "recent_coins": []}
    finally:
        cx.close()


def format_prompt_block(rich: bool = False, max_recent: int = 3) -> str:
    """Render a compact block for injection into prompts.
    Empty string if feedback disabled or no tags exist.
    Output looks like:

      [Jon's tags on your recent fountain thoughts]
      coin (3): "The sun casts long shadows today."
                "The coffee pot starts to whistle in the kitchen."
      maybe (1): "The afternoon light shifts again."
      non (4): "The library's AC feels too cool today."
    """
    if not feedback_enabled():
        return ""
    summary = tag_summary()
    counts = summary.get("counts", {})
    if not counts:
        return ""
    lines = ["[Jon's tags on your recent fountain thoughts]"]
    for tag in ("coin", "maybe", "non"):
        n = counts.get(tag, 0)
        if n == 0:
            continue
        examples = recent_tags(limit=max_recent, tag_filter=tag, rich=rich)
        if not examples:
            lines.append(f"  {tag} ({n}): (no examples)")
        else:
            lines.append(f"  {tag} ({n}):")
            for ex in examples:
                lines.append(f"    {ex}")
    return "\n".join(lines)
