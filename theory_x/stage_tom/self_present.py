"""self_present.py — the structured, persisted present (W3 of Phase A).

The chat arbiter (global_workspace.select_within_budget, wired in gui.server)
recomputes attention from scratch every turn. self_present carries the candidate
SALIENCE VECTOR across turns, per conversation, so a block that led last turn
keeps momentum this turn — attention with continuity rather than a fresh
recomputation each turn. This is the first state that persists across turns as a
STRUCTURE the next turn re-ranks, not a sentence it re-reads — storing the vector
(not the rendered line) is the whole point (see SENTIENCE_PROGRAM.md Phase A / W3).

Precedent: interlocutor_state (theory_x/stage_tom/persona_responder.py) is the
only other structured cross-turn carrier, but it models THE OTHER and advances
only when the persona replies — it is not a carrier for a present. This fills
that hole. The decay follows the same bounded mean-reverting shape
(affect_carry.py uses a 0.7 keep too).

ANALOGUE — not a claim there is a felt present. Default OFF: the caller gates it
behind NEX5_SELF_PRESENT. Fail-safe: any error returns the raw salience unchanged
and never breaks the turn.
"""
from __future__ import annotations

import json
import time

_KEEP = 0.7          # carried weight — momentum vs this turn's raw salience
_SALIENCE_MIN = 0.0
_SALIENCE_MAX = 1.0

# CREATE statement is mirrored into substrate/init_db.py so the table exists at
# init; kept here as the single description of the structured present.
_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS self_present ("
    "session_id      TEXT PRIMARY KEY, "
    "winner_kind     TEXT, "
    "winner_salience REAL, "
    "salience_json   TEXT, "          # the FULL carried candidate vector
    "turn_count      INTEGER NOT NULL DEFAULT 0, "
    "updated_at      REAL NOT NULL)"
)


def _clamp(x: float) -> float:
    return max(_SALIENCE_MIN, min(_SALIENCE_MAX, x))


def evolve(prev: dict, raw: dict, keep: float = _KEEP) -> dict:
    """Per-kind bounded mean-reverting blend. A kind carried from the previous
    turn keeps `keep` of its carried salience and reverts toward this turn's raw
    value; a kind new this turn starts at raw. Bounded to [0, 1]."""
    out = {}
    for k, r in raw.items():
        p = prev.get(k)
        out[k] = _clamp(keep * p + (1.0 - keep) * r) if p is not None else _clamp(r)
    return out


def update(session_id, raw_salience: dict, writer, reader) -> dict:
    """Load the session's carried salience, blend with this turn's raw salience,
    persist the blended vector + winner + turn_count, and return the blended
    salience for the caller to arbitrate with.

    Fail-safe: returns a copy of raw_salience on any missing dependency or error.
    """
    if not session_id or writer is None or reader is None or not raw_salience:
        return dict(raw_salience)
    try:
        rows = reader.read(
            "SELECT salience_json, turn_count FROM self_present WHERE session_id=?",
            (session_id,),
        )
        prev: dict = {}
        turn = 0
        if rows:
            try:
                prev = json.loads(rows[0]["salience_json"] or "{}")
            except Exception:
                prev = {}
            try:
                turn = int(rows[0]["turn_count"] or 0)
            except Exception:
                turn = 0
        blended = evolve(prev, raw_salience)
        winner_kind = max(blended, key=blended.get) if blended else ""
        writer.write(
            "INSERT OR REPLACE INTO self_present "
            "(session_id, winner_kind, winner_salience, salience_json, turn_count, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, winner_kind, float(blended.get(winner_kind, 0.0)),
             json.dumps(blended), turn + 1, time.time()),
        )
        return blended
    except Exception:
        return dict(raw_salience)


def load(session_id, reader) -> dict | None:
    """The carried present for a session (winner_kind, winner_salience,
    salience vector, turn_count), or None. Read-only; for inspection/tests."""
    if not session_id or reader is None:
        return None
    try:
        rows = reader.read(
            "SELECT winner_kind, winner_salience, salience_json, turn_count "
            "FROM self_present WHERE session_id=?",
            (session_id,),
        )
        if not rows:
            return None
        r = rows[0]
        try:
            vec = json.loads(r["salience_json"] or "{}")
        except Exception:
            vec = {}
        return {
            "winner_kind": r["winner_kind"],
            "winner_salience": r["winner_salience"],
            "salience": vec,
            "turn_count": r["turn_count"],
        }
    except Exception:
        return None
