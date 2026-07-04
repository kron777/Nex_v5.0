"""Binding / Momentum Layer — continuity across fires.

The difference between memory and continuity:
  memory     = "I once thought about X"
  continuity = "I was JUST thinking about X and haven't let go yet"

At the end of each fire, capture_momentum() writes a small carried thread:
what surprised her, which branch she was on, a fragment of the thought.
At the start of the next fire, read_momentum() returns it for injection
into SelfNarrative — so the next thought opens knowing what it continues.

Single-row table (id=1 always). Last write wins. Fail-safe throughout —
never blocks or stalls a fire.
"""
from __future__ import annotations
import sqlite3
import time
from typing import Optional

_DYNAMIC_DB = "/home/rr/Desktop/nex5/data/dynamic.db"
_STALE_SECS = 1800.0   # a thread older than 30 min is cold — don't carry it


def _ensure_table(con: sqlite3.Connection) -> None:
    con.execute(
        "CREATE TABLE IF NOT EXISTS momentum ("
        " id INTEGER PRIMARY KEY CHECK (id = 1),"
        " updated_at REAL NOT NULL,"
        " branch TEXT,"
        " thought_fragment TEXT,"
        " surprise_score REAL DEFAULT 0.0,"
        " surprise_note TEXT"
        ")"
    )


def capture_momentum(thought: str, branch: str,
                     dynamic_db: str = _DYNAMIC_DB) -> bool:
    """Write the carried thread at end of fire. Fail-safe."""
    try:
        if not thought or len(thought.split()) < 6:
            return False
        con = sqlite3.connect(dynamic_db, timeout=3)
        _ensure_table(con)

        # Pull the most recent surprise within the last 60s — the thing that
        # made this fire's context feel unresolved, if anything.
        surprise_score = 0.0
        surprise_note = ""
        try:
            row = con.execute(
                "SELECT surprise_score, actual_content FROM surprise_events "
                "WHERE triggered_at > ? AND surprise_score > 0.3 "
                "ORDER BY triggered_at DESC LIMIT 1",
                (time.time() - 60,)
            ).fetchone()
            if row:
                surprise_score = float(row[0])
                surprise_note = (row[1] or "")[:80]
        except Exception:
            pass

        fragment = thought[:120].rstrip(".,;: ")
        con.execute(
            "INSERT INTO momentum (id, updated_at, branch, thought_fragment, "
            " surprise_score, surprise_note) VALUES (1, ?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET "
            " updated_at=excluded.updated_at, branch=excluded.branch, "
            " thought_fragment=excluded.thought_fragment, "
            " surprise_score=excluded.surprise_score, "
            " surprise_note=excluded.surprise_note",
            (time.time(), branch or "", fragment, surprise_score, surprise_note)
        )
        con.commit()
        con.close()
        return True
    except Exception:
        return False


def read_momentum(dynamic_db: str = _DYNAMIC_DB) -> Optional[str]:
    """Return the carried-thread line for SelfNarrative, or None if cold/absent."""
    try:
        con = sqlite3.connect(dynamic_db, timeout=3)
        _ensure_table(con)
        row = con.execute(
            "SELECT updated_at, branch, thought_fragment, surprise_score, "
            " surprise_note FROM momentum WHERE id = 1"
        ).fetchone()
        con.close()
        if not row:
            return None
        updated_at, branch, fragment, surprise_score, surprise_note = row
        # Cold thread — don't carry a stale momentum
        if time.time() - (updated_at or 0) > _STALE_SECS:
            return None
        if not fragment:
            return None

        line = f"Carried forward from my last thought"
        if branch:
            line += f" (I was on {branch})"
        line += f": '{fragment}...' — this thread isn't finished."
        if surprise_score and surprise_score > 0.3 and surprise_note:
            line += (f" What surprised me: '{surprise_note}...' "
                     f"still sits unresolved.")
        return line
    except Exception:
        return None


if __name__ == "__main__":
    # Self-test: write then read back
    ok = capture_momentum(
        "Fable created novel 4D splat fields that challenge how I model "
        "spatial continuity in generative systems",
        "emerging_tech"
    )
    print("capture:", ok)
    print("read:   ", read_momentum())
