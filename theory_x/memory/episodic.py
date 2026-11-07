"""Episodic memory (SENTIENCE_PROGRAM Phase E).

Dark by default: NEX5_EPISODIC=1 to arm. An episode is "what happened" plus
"with what affect" -- distinct from a belief, which is "what I hold to be
true." Four existing, already-meaningful event sources feed it (nothing new
detected, no new judgement of what counts as notable -- each is a signal
some other faculty already decided was worth flagging):

  ghost_flag      ghost_flags      -- Jon's own "this mattered" marker
  meta_cognition  meta_cognition_events (conversations.db) -- a self-observed
                  pattern (groove, drift, ...)
  surprise        surprise_events (dynamic.db), score > 0.8 -- the same bar
                  Phase M1's reflective digest uses
  held_tension    held_tensions (dynamic.db) -- Phase D's "I hold X and
                  not-X" (only ever produces episodes once NEX5_HELD_TENSION
                  is armed and actually fires; empty source until then, not
                  a bug)

Each qualifying source row becomes one `episodes` row (dynamic.db),
UNIQUE(source_kind, source_id) so re-running record_episodes() never
duplicates one. "With what affect" is the nearest self_state_history row by
|bound_at - created_at|, within _AFFECT_MAX_GAP_S -- copied into the episode
at write time (affect_bound_at/affect_synthesis), not joined at read time,
so a later retention sweep of self_state_history can never retroactively
blank what an episode remembers feeling like.

reconstruct_episode() is the "reconstructive, not a verbatim log" read path:
given a time, it composes one short account (what + affect) rather than
returning raw rows -- the spec's own falsifier is that retrieval still can't
tell "what happened to me" from "what I believe," which a bare row dump
would not resolve either.

Not wired into gui/server.py, generator.py, or any live loop. Callable only
by hand (or a future, separately-decided scheduler) -- same posture as
tools/metacog_digest.py.
"""
from __future__ import annotations

import os
import time
from typing import Optional

_FLAG = "NEX5_EPISODIC"
_SURPRISE_THRESHOLD = 0.8
_DEFAULT_LOOKBACK_S = 24 * 3600
# PROVISIONAL (no live measurement yet): how far from an event's created_at
# a self_state_history row may be and still count as "the affect at the
# time." self_state_history is dense on the live corpus (~1 row every few
# minutes), so this is generous on purpose; re-derive if that density drops.
_AFFECT_MAX_GAP_S = 3600
# ghost_flags/held_tensions carry no numeric score of their own; these are
# PROVISIONAL fixed salience values, not measured.
_GHOST_FLAG_SALIENCE = 0.9
_HELD_TENSION_SALIENCE = 0.7


def _nearest_affect(dyn_reader, ts: float) -> tuple[Optional[float], Optional[str]]:
    try:
        row = dyn_reader.read_one(
            "SELECT bound_at, synthesis FROM self_state_history "
            "ORDER BY ABS(bound_at - ?) LIMIT 1",
            (ts,),
        )
    except Exception:
        return None, None
    if row is None or row["bound_at"] is None:
        return None, None
    if abs(row["bound_at"] - ts) > _AFFECT_MAX_GAP_S:
        return None, None
    return row["bound_at"], row["synthesis"]


def _clip(text: str, n: int = 200) -> str:
    text = (text or "").strip()
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0] + "…"


def _already_recorded(dyn_reader, source_kind: str, source_id: int) -> bool:
    row = dyn_reader.read_one(
        "SELECT 1 FROM episodes WHERE source_kind = ? AND source_id = ?",
        (source_kind, source_id),
    )
    return row is not None


def _candidates_ghost_flags(dyn_reader, window_start: float) -> list[dict]:
    try:
        rows = dyn_reader.read(
            "SELECT id, fountain_event_id, ts, reason FROM ghost_flags WHERE ts > ?",
            (window_start,),
        )
    except Exception:
        return []
    out = []
    for r in rows:
        reason = r["reason"] or f"flagged fire {r['fountain_event_id']}"
        out.append({
            "source_kind": "ghost_flag", "source_id": r["id"], "created_at": r["ts"],
            "what": f"Jon flagged this moment: {_clip(reason)}",
            "salience": _GHOST_FLAG_SALIENCE,
        })
    return out


def _candidates_meta_cognition(conv_reader, window_start: float) -> list[dict]:
    try:
        rows = conv_reader.read(
            "SELECT id, event_type, description, severity, created_at "
            "FROM meta_cognition_events WHERE created_at > ?",
            (window_start,),
        )
    except Exception:
        return []
    return [{
        "source_kind": "meta_cognition", "source_id": r["id"], "created_at": r["created_at"],
        "what": f"I noticed ({r['event_type']}): {_clip(r['description'])}",
        "salience": r["severity"],
    } for r in rows]


def _candidates_surprise(dyn_reader, window_start: float) -> list[dict]:
    try:
        rows = dyn_reader.read(
            "SELECT id, surprise_score, predicted_content, actual_content, triggered_at, "
            "prediction_type FROM surprise_events "
            "WHERE triggered_at > ? AND surprise_score > ?",
            (window_start, _SURPRISE_THRESHOLD),
        )
    except Exception:
        return []
    out = []
    for r in rows:
        text = r["actual_content"] or r["predicted_content"] or ""
        out.append({
            "source_kind": "surprise", "source_id": r["id"], "created_at": r["triggered_at"],
            "what": f"Something ({r['prediction_type']}) surprised me: {_clip(str(text))}",
            "salience": r["surprise_score"],
        })
    return out


def _candidates_held_tensions(dyn_reader, beliefs_reader, window_start: float) -> list[dict]:
    try:
        rows = dyn_reader.read(
            "SELECT id, belief_id_a, belief_id_b, created_at FROM held_tensions "
            "WHERE created_at > ?",
            (window_start,),
        )
    except Exception:
        return []
    out = []
    for r in rows:
        try:
            row_a = beliefs_reader.read_one("SELECT content FROM beliefs WHERE id = ?", (r["belief_id_a"],))
            row_b = beliefs_reader.read_one("SELECT content FROM beliefs WHERE id = ?", (r["belief_id_b"],))
        except Exception:
            row_a = row_b = None
        a_text = _clip(row_a["content"]) if row_a else "(a belief)"
        b_text = _clip(row_b["content"]) if row_b else "(another belief)"
        out.append({
            "source_kind": "held_tension", "source_id": r["id"], "created_at": r["created_at"],
            "what": f'I held both: "{a_text}" and "{b_text}".',
            "salience": _HELD_TENSION_SALIENCE,
        })
    return out


def record_episodes(
    conv_reader, dyn_reader, dyn_writer, beliefs_reader,
    lookback_s: float = _DEFAULT_LOOKBACK_S, now: Optional[float] = None,
) -> list[dict]:
    """Scan the four sources for events in the lookback window not yet
    recorded, attach the nearest affect snapshot, and write one episodes
    row each. Returns what was recorded. Flag unset -> no reads, no writes,
    returns []."""
    if os.environ.get(_FLAG) != "1":
        return []
    now = now if now is not None else time.time()
    window_start = now - lookback_s
    candidates = (
        _candidates_ghost_flags(dyn_reader, window_start)
        + _candidates_meta_cognition(conv_reader, window_start)
        + _candidates_surprise(dyn_reader, window_start)
        + _candidates_held_tensions(dyn_reader, beliefs_reader, window_start)
    )
    recorded = []
    for c in candidates:
        if _already_recorded(dyn_reader, c["source_kind"], c["source_id"]):
            continue
        affect_bound_at, affect_synthesis = _nearest_affect(dyn_reader, c["created_at"])
        try:
            dyn_writer.write(
                "INSERT INTO episodes "
                "(created_at, source_kind, source_id, what, salience, "
                "affect_bound_at, affect_synthesis, recorded_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (c["created_at"], c["source_kind"], c["source_id"], c["what"],
                 c["salience"], affect_bound_at, affect_synthesis, time.time()),
            )
        except Exception:
            continue
        c["affect_bound_at"] = affect_bound_at
        c["affect_synthesis"] = affect_synthesis
        recorded.append(c)
    return recorded


def query_episodes(
    dyn_reader, since: Optional[float] = None, until: Optional[float] = None,
    min_salience: float = 0.0, limit: int = 50,
) -> list[dict]:
    """Queryable by time and salience. Flag unset -> []: episodes may exist
    from before a disarm, but the faculty reads as off."""
    if os.environ.get(_FLAG) != "1":
        return []
    since = since if since is not None else 0.0
    until = until if until is not None else time.time()
    try:
        rows = dyn_reader.read(
            "SELECT * FROM episodes WHERE created_at >= ? AND created_at <= ? "
            "AND salience >= ? ORDER BY created_at DESC LIMIT ?",
            (since, until, min_salience, limit),
        )
    except Exception:
        return []
    return [dict(r) for r in rows]


def reconstruct_episode(dyn_reader, around_ts: float, window_s: float = 1800.0) -> Optional[dict]:
    """The single most salient episode within window_s of around_ts,
    composed into one short account -- what happened AND what it felt like,
    not a raw row. None if the flag is off or nothing is in range."""
    if os.environ.get(_FLAG) != "1":
        return None
    try:
        row = dyn_reader.read_one(
            "SELECT * FROM episodes WHERE created_at >= ? AND created_at <= ? "
            "ORDER BY salience DESC, ABS(created_at - ?) ASC LIMIT 1",
            (around_ts - window_s, around_ts + window_s, around_ts),
        )
    except Exception:
        return None
    if row is None:
        return None
    row = dict(row)
    when = time.strftime("%Y-%m-%d %H:%M", time.localtime(row["created_at"]))
    if row["affect_synthesis"]:
        account = f"Around {when}, {row['what']} At the time, {row['affect_synthesis']}"
    else:
        account = f"Around {when}, {row['what']} (no affect snapshot was close enough in time)"
    row["account"] = account
    return row
