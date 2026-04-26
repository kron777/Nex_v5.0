"""Family Trees — records and queries belief parent/child relationships."""
from __future__ import annotations

import time
from typing import Optional


def record_synergy(writer, child_id: int, parent_a_id: int, parent_b_id: int) -> None:
    now = time.time()
    for parent_id in (parent_a_id, parent_b_id):
        try:
            writer.write(
                "INSERT OR IGNORE INTO belief_lineage "
                "(child_id, parent_id, relationship, weight, created_at) "
                "VALUES (?, ?, 'synergy', 1.0, ?)",
                (child_id, parent_id, now),
            )
        except Exception:
            pass


def record_reference(writer, child_id: int, parent_id: int) -> None:
    try:
        writer.write(
            "INSERT OR IGNORE INTO belief_lineage "
            "(child_id, parent_id, relationship, weight, created_at) "
            "VALUES (?, ?, 'reference', 0.5, ?)",
            (child_id, parent_id, time.time()),
        )
    except Exception:
        pass


def descendants_of(reader, belief_id: int, depth: int = 3) -> list[dict]:
    results: list[dict] = []
    frontier = [belief_id]
    seen: set[int] = {belief_id}
    for _ in range(depth):
        if not frontier:
            break
        placeholders = ",".join("?" * len(frontier))
        rows = reader.read(
            f"SELECT child_id, relationship FROM belief_lineage "
            f"WHERE parent_id IN ({placeholders})",
            tuple(frontier),
        )
        frontier = []
        for r in rows:
            cid = r["child_id"]
            if cid not in seen:
                seen.add(cid)
                frontier.append(cid)
                results.append(dict(r))
    return results


def ancestors_of(reader, belief_id: int) -> list[dict]:
    rows = reader.read(
        "SELECT parent_id, relationship FROM belief_lineage WHERE child_id=?",
        (belief_id,),
    )
    return [dict(r) for r in rows]


def most_fertile(reader, top_n: int = 10) -> list[dict]:
    rows = reader.read(
        "SELECT parent_id, COUNT(*) AS descendant_count FROM belief_lineage "
        "GROUP BY parent_id ORDER BY descendant_count DESC LIMIT ?",
        (top_n,),
    )
    return [dict(r) for r in rows]
