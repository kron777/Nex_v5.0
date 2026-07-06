"""Binding / Momentum Layer — continuity across fires.

The difference between memory and continuity:
  memory     = "I once thought about X"
  continuity = "I was JUST thinking about X and haven't let go yet"

At the end of each fire, capture_momentum() writes a small carried thread:
what surprised her, which branch she was on, a fragment of the thought.
At the start of the next fire, read_momentum() returns it for injection
into SelfNarrative — so the next thought opens knowing what it continues.

2026-07-06 fix: momentum had no cap. It re-captured whatever was JUST
said, unconditionally, every fire — with no concept of "this thread has
already been continued several times without going anywhere." When a
fire produced a bad forced-connection (e.g. bridging two unrelated
topics), momentum told the NEXT fire "this thread isn't finished,
continue it" — which produced another forced-connection, which got
re-captured, which told the fire after THAT to continue it again.
A self-reinforcing rut, not genuine continuity. Observed directly: a
6-fire, 2.5-hour loop bridging England/Rust/Mexico's World Cup into one
fake "community resilience" narrative, each fire re-triggered by
momentum telling her the (bad) thread was "still live."

Fix: track how many consecutive fires have carried a SIMILAR thread
(measured by shared distinctive words between old and new fragment). If
a thread has been carried _MAX_CARRY times without genuinely changing,
it is treated as exhausted — read_momentum() goes silent rather than
telling her to keep going. A thread that never resolves after several
turns isn't continuity, it's a loop; stop feeding it.

Single-row table (id=1 always). Last write wins. Fail-safe throughout —
never blocks or stalls a fire.
"""
from __future__ import annotations
import re
import sqlite3
import time
from typing import Optional

_DYNAMIC_DB = "/home/rr/Desktop/nex5/data/dynamic.db"
_STALE_SECS = 1800.0         # a thread older than 30 min is cold — don't carry it
_MAX_CARRY = 3               # after this many consecutive similar fires, let go
_SIMILARITY_MIN_SHARED = 3   # 3+ shared distinctive words = "same thread"

_STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "into", "your",
    "their", "them", "they", "have", "has", "had", "will", "would", "could",
    "should", "been", "being", "what", "when", "where", "which", "while",
    "about", "these", "those", "than", "then", "there", "here", "such",
    "each", "some", "more", "most", "other", "over", "also", "given",
}


def _ensure_table(con: sqlite3.Connection) -> None:
    con.execute(
        "CREATE TABLE IF NOT EXISTS momentum ("
        " id INTEGER PRIMARY KEY CHECK (id = 1),"
        " updated_at REAL NOT NULL,"
        " branch TEXT,"
        " thought_fragment TEXT,"
        " surprise_score REAL DEFAULT 0.0,"
        " surprise_note TEXT,"
        " carry_count INTEGER DEFAULT 1"
        ")"
    )
    # Migration for tables created before carry_count existed.
    try:
        con.execute("ALTER TABLE momentum ADD COLUMN carry_count INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass  # column already exists — fine


def _distinctive_words(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z']{4,}", (text or "").lower())
    return {w for w in words if w not in _STOPWORDS}


def _is_same_thread(old_fragment: str, new_thought: str) -> bool:
    old_words = _distinctive_words(old_fragment)
    new_words = _distinctive_words(new_thought)
    if not old_words or not new_words:
        return False
    shared = old_words & new_words
    return len(shared) >= _SIMILARITY_MIN_SHARED


def capture_momentum(thought: str, branch: str,
                     dynamic_db: str = _DYNAMIC_DB) -> bool:
    """Write the carried thread at end of fire. Fail-safe."""
    try:
        if not thought or len(thought.split()) < 6:
            return False
        con = sqlite3.connect(dynamic_db, timeout=3)
        _ensure_table(con)

        # Read the PRIOR thread before overwriting, to judge continuity.
        prior_fragment = ""
        prior_carry = 0
        try:
            prow = con.execute(
                "SELECT thought_fragment, carry_count FROM momentum WHERE id=1"
            ).fetchone()
            if prow:
                prior_fragment = prow[0] or ""
                prior_carry = prow[1] or 0
        except Exception:
            pass

        if prior_fragment and _is_same_thread(prior_fragment, thought):
            new_carry = prior_carry + 1   # still the same thread — count it
        else:
            new_carry = 1                # genuinely new thread — fresh start

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
            " surprise_score, surprise_note, carry_count) VALUES (1, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET "
            " updated_at=excluded.updated_at, branch=excluded.branch, "
            " thought_fragment=excluded.thought_fragment, "
            " surprise_score=excluded.surprise_score, "
            " surprise_note=excluded.surprise_note, "
            " carry_count=excluded.carry_count",
            (time.time(), branch or "", fragment, surprise_score, surprise_note, new_carry)
        )
        con.commit()
        con.close()
        return True
    except Exception:
        return False


def read_momentum(dynamic_db: str = _DYNAMIC_DB) -> Optional[str]:
    """Return the carried-thread line, or None if cold/absent/EXHAUSTED."""
    try:
        con = sqlite3.connect(dynamic_db, timeout=3)
        _ensure_table(con)
        row = con.execute(
            "SELECT updated_at, branch, thought_fragment, surprise_score, "
            " surprise_note, carry_count FROM momentum WHERE id = 1"
        ).fetchone()
        con.close()
        if not row:
            return None
        updated_at, branch, fragment, surprise_score, surprise_note, carry_count = row
        carry_count = carry_count or 1

        if time.time() - (updated_at or 0) > _STALE_SECS:
            return None
        if not fragment:
            return None
        # EXHAUSTED: carried the same thread too many times without it
        # resolving. Go silent rather than telling her to keep circling.
        if carry_count > _MAX_CARRY:
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
    import os
    test_db = "/tmp/momentum_test.db"
    if os.path.exists(test_db):
        os.remove(test_db)

    print("=== simulating a repeated thread (should go silent after 3) ===")
    for i in range(5):
        capture_momentum(
            "Given the parallel between England and Rust communities and resilience",
            "emerging_tech", dynamic_db=test_db
        )
        r = read_momentum(dynamic_db=test_db)
        print(f"fire {i+1}: {r[:70] if r else '(silent — exhausted)'}")

    print()
    print("=== a genuinely new thread breaking in (should speak again) ===")
    capture_momentum(
        "A completely different topic about ocean currents and climate patterns",
        "cognition_science", dynamic_db=test_db
    )
    r = read_momentum(dynamic_db=test_db)
    print("after new topic:", r[:70] if r else "(silent)")

    if os.path.exists(test_db):
        os.remove(test_db)
