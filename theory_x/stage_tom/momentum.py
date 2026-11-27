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
import logging
import os
import re
from substrate import Reader, Writer, OperationalError
import time
from typing import Optional

log = logging.getLogger("theory_x.stage_tom.momentum")

try:
    from substrate.paths import DbPath  # resolves NEX5_DATA_DIR at use time (test hygiene)
except ImportError:  # run as a script: put the repo root on sys.path
    import sys as _sys
    from pathlib import Path as _P
    _sys.path.insert(0, str(_P(__file__).resolve().parents[2]))
    from substrate.paths import DbPath
_DYNAMIC_DB = DbPath("dynamic")
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


def _ensure_table(writer: Writer) -> None:
    writer.write(
        "CREATE TABLE IF NOT EXISTS momentum ("
        " id INTEGER PRIMARY KEY CHECK (id = 1),"
        " updated_at REAL NOT NULL,"
        " branch TEXT,"
        " thought_fragment TEXT,"
        " surprise_score REAL DEFAULT 0.0,"
        " surprise_note TEXT,"
        " carry_count INTEGER DEFAULT 1,"
        " resolved INTEGER"
        ")"
    )
    # Additive migrations remain idempotent and run through the same Writer.
    try:
        writer.write("ALTER TABLE momentum ADD COLUMN carry_count INTEGER DEFAULT 1")
    except OperationalError:
        pass  # column already exists — fine
    try:
        writer.write("ALTER TABLE momentum ADD COLUMN resolved INTEGER")
    except OperationalError:
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


def capture_momentum(
    thought: str,
    branch: str,
    dynamic_db: str = _DYNAMIC_DB,
    trace=None,
    *,
    dynamic_reader: Optional[Reader] = None,
    dynamic_writer: Optional[Writer] = None,
) -> bool:
    """Write the carried thread through the shared dynamic.db Writer. Fail-safe."""
    own_reader = dynamic_reader is None
    own_writer = dynamic_writer is None
    reader = dynamic_reader or Reader(dynamic_db)
    writer = dynamic_writer or Writer(dynamic_db, name="momentum")
    try:
        if not thought or len(thought.split()) < 6:
            return False
        _ensure_table(writer)

        # Read the PRIOR thread before overwriting, to judge continuity.
        prior_fragment = ""
        prior_carry = 0
        try:
            prow = reader.read_one(
                "SELECT thought_fragment, carry_count FROM momentum WHERE id=1"
            )
            if prow:
                prior_fragment = prow["thought_fragment"] or ""
                prior_carry = prow["carry_count"] or 0
        except Exception:
            pass

        if prior_fragment and _is_same_thread(prior_fragment, thought):
            new_carry = prior_carry + 1
        else:
            new_carry = 1

        surprise_score = 0.0
        surprise_note = ""
        try:
            row = reader.read_one(
                "SELECT surprise_score, actual_content FROM surprise_events "
                "WHERE triggered_at > ? AND surprise_score > 0.3 "
                "ORDER BY triggered_at DESC LIMIT 1",
                (time.time() - 60,),
            )
            if row:
                surprise_score = float(row["surprise_score"])
                surprise_note = (row["actual_content"] or "")[:80]
        except Exception:
            pass

        fragment = thought[:120].rstrip(".,;: ")
        writer.write(
            "INSERT INTO momentum (id, updated_at, branch, thought_fragment, "
            " surprise_score, surprise_note, carry_count) VALUES (1, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET "
            " updated_at=excluded.updated_at, branch=excluded.branch, "
            " thought_fragment=excluded.thought_fragment, "
            " surprise_score=excluded.surprise_score, "
            " surprise_note=excluded.surprise_note, "
            " carry_count=excluded.carry_count",
            (time.time(), branch or "", fragment, surprise_score, surprise_note, new_carry),
        )
        if trace is not None:
            trace.writer_delta(
                database="dynamic",
                table="momentum",
                operation="INSERT_OR_UPDATE",
                row_id=1,
                metadata={"branch_id": branch, "carry_count": new_carry},
                parent_ids=[
                    rid for rid in (
                        trace.reference("fountain_output_candidate"),
                        trace.reference("fountain_hot_branch_selection"),
                    ) if rid
                ],
            )
        return True
    except Exception:
        return False
    finally:
        if own_writer:
            writer.close()
        if own_reader:
            try:
                reader.close()
            except Exception:
                pass


def stamp_resolution(
    resolved: bool,
    dynamic_db: str = _DYNAMIC_DB,
    trace=None,
    *,
    dynamic_reader: Optional[Reader] = None,
    dynamic_writer: Optional[Writer] = None,
) -> bool:
    """Stamp the current thread's outcome through the shared dynamic Writer."""
    own_reader = dynamic_reader is None
    own_writer = dynamic_writer is None
    reader = dynamic_reader or Reader(dynamic_db)
    writer = dynamic_writer or Writer(dynamic_db, name="momentum")
    try:
        _ensure_table(writer)
        row = reader.read_one(
            "SELECT carry_count FROM momentum WHERE id = 1"
        )
        if not row:
            return False
        if (row["carry_count"] or 0) > _MAX_CARRY:
            return False
        writer.write(
            "UPDATE momentum SET resolved = ? WHERE id = 1",
            (1 if resolved else 0,),
        )
        if trace is not None:
            trace.writer_delta(
                database="dynamic",
                table="momentum",
                operation="UPDATE",
                row_id=1,
                metadata={"resolved": bool(resolved)},
                parent_ids=[
                    rid for rid in (
                        trace.reference("fountain_belief_write") if resolved
                        else trace.reference("fountain_crystallizer_terminal"),
                        trace.reference("fountain_crystallization_link") if resolved else None,
                        trace.reference("fountain_quality_gate") if not resolved else None,
                    ) if rid
                ],
            )
        return True
    except Exception:
        return False
    finally:
        if own_writer:
            writer.close()
        if own_reader:
            try:
                reader.close()
            except Exception:
                pass


def read_momentum(
    dynamic_db: str = _DYNAMIC_DB,
    *,
    dynamic_reader: Optional[Reader] = None,
) -> Optional[str]:
    """Read the carried thread without creating or mutating its table."""
    own_reader = dynamic_reader is None
    reader = dynamic_reader or Reader(dynamic_db)
    try:
        row = reader.read_one(
            "SELECT updated_at, branch, thought_fragment, surprise_score, "
            " surprise_note, carry_count, resolved FROM momentum WHERE id = 1"
        )
        if not row:
            return None
        updated_at = row["updated_at"]
        branch = row["branch"]
        fragment = row["thought_fragment"]
        surprise_score = row["surprise_score"]
        surprise_note = row["surprise_note"]
        carry_count = row["carry_count"] or 1
        resolved = row["resolved"]

        if time.time() - (updated_at or 0) > _STALE_SECS:
            return None
        if not fragment or carry_count > _MAX_CARRY:
            return None

        line = "Carried forward from my last thought"
        if branch:
            line += f" (I was on {branch})"
        line += f": '{fragment}...' — this thread isn't finished."
        if surprise_score and surprise_score > 0.3 and surprise_note:
            line += (f" What surprised me: '{surprise_note}...' "
                     f"still sits unresolved.")
        if os.environ.get("NEX5_CARRYOVER") == "1" and resolved is not None:
            line += (" — and last cycle it settled into a belief." if resolved
                     else " — and last cycle it stalled; nothing settled.")
            try:
                log.info("carryover: rendered %s clause, branch=%s",
                         "settled" if resolved else "stalled", branch or "?")
            except Exception:
                pass
        return line
    except Exception:
        return None
    finally:
        if own_reader:
            try:
                reader.close()
            except Exception:
                pass


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
