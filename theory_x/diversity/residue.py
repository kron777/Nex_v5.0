"""Save Half-Thoughts — captures pre-propositional residue across fountain cycles."""
from __future__ import annotations

import logging
import time
from typing import Optional

log = logging.getLogger("theory_x.diversity.residue")


def save_residue(writer, cycle_id: str, belief_id: int, activation_strength: float) -> None:
    writer.write(
        "INSERT INTO residue (cycle_id, belief_id, activation_strength, created_at) "
        "VALUES (?, ?, ?, ?)",
        (cycle_id, belief_id, activation_strength, time.time()),
    )


def pop_residue(reader, writer, limit: int = 2) -> list[dict]:
    """Retrieve unconsumed residue from the previous cycle, mark consumed."""
    rows = reader.read(
        "SELECT id, belief_id FROM residue "
        "WHERE consumed_at IS NULL "
        "ORDER BY activation_strength DESC LIMIT ?",
        (limit,),
    )
    if not rows:
        return []

    now = time.time()
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
