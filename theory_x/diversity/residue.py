"""Save Half-Thoughts — captures pre-propositional residue across fountain cycles."""
from __future__ import annotations

import logging
import time
from typing import Optional

log = logging.getLogger("theory_x.diversity.residue")

_REAP_AFTER_SECONDS = 7 * 86400   # consumed rows older than this are deleted
_REAP_INTERVAL = 3600.0           # at most one reap pass per hour
_last_reap = 0.0


def save_residue(writer, cycle_id: str, belief_id: int, activation_strength: float) -> None:
    writer.write(
        "INSERT INTO residue (cycle_id, belief_id, activation_strength, created_at) "
        "VALUES (?, ?, ?, ?)",
        (cycle_id, belief_id, activation_strength, time.time()),
    )


def _reap(writer, now: float) -> None:
    """Delete consumed residue older than _REAP_AFTER_SECONDS. Throttled,
    fire-and-forget: this runs on the fire path, so it must never raise."""
    global _last_reap
    if now - _last_reap < _REAP_INTERVAL:
        return
    _last_reap = now
    try:
        writer.write(
            "DELETE FROM residue WHERE consumed_at IS NOT NULL AND consumed_at < ?",
            (now - _REAP_AFTER_SECONDS,),
        )
    except Exception as exc:
        log.warning("residue reap failed (non-fatal): %s", exc)


def pop_residue(reader, writer, limit: int = 2) -> list[dict]:
    """Retrieve unconsumed residue from the previous cycle, mark consumed.

    2026-08-03 (round 27): ordered by created_at DESC, not
    activation_strength DESC. Every unconsumed row carries
    activation_strength exactly 1.0 (393,838/393,838 measured), so that
    ORDER BY was a total tie and SQLite returned rowid order -- i.e. the
    OLDEST unconsumed row first. The head of the queue was 73.3 days old,
    and since the table gains ~4,600 rows/day while popping only ~1,056,
    the backlog could never drain: this docstring's "from the previous
    cycle" had been false since roughly May. created_at DESC makes it true.

    Note (not fixed here): the ~394k pre-existing unconsumed rows become
    permanently unreachable under DESC ordering. They are inert, but they
    are dead weight and want their own decision -- the reaper below only
    removes CONSUMED rows.
    """
    now = time.time()
    _reap(writer, now)
    rows = reader.read(
        "SELECT id, belief_id FROM residue "
        "WHERE consumed_at IS NULL "
        "ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    if not rows:
        return []

    ids = [r["id"] for r in rows]
    placeholders = ",".join("?" * len(ids))
    writer.write(
        f"UPDATE residue SET consumed_at=? WHERE id IN ({placeholders})",
        (now, *ids),
    )

    belief_ids = [r["belief_id"] for r in rows]
    return [{"belief_id": bid} for bid in belief_ids]


def fetch_residue_beliefs(reader, belief_ids: list[int]) -> list[dict]:
    """Look up full belief rows for a list of belief_ids.

    2026-07-26: tier < 8 added. Residue is saved from generator.py's
    own_rows oversample pool and can sit unconsumed for many cycles
    (activation_strength-ordered popping is not FIFO); a belief tombstoned
    (tier=8) after being saved as residue but before being popped would
    otherwise still surface here, since this lookup is by raw id with no
    other filter -- own_rows now excludes tier=8 at the source too, but
    this guards the pre-existing backlog and any future case of the same
    shape.
    """
    if not belief_ids:
        return []
    placeholders = ",".join("?" * len(belief_ids))
    rows = reader.read(
        f"SELECT id, content, source, tier, confidence, created_at FROM beliefs "
        f"WHERE id IN ({placeholders}) AND tier < 8",
        tuple(belief_ids),
    )
    return [dict(r) for r in rows]
