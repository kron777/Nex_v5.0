"""Ledger primitives for Phase D — refuse() / consolidate() / recall().

DEPENDS ON SHADOW BUDGET — NOT IN THE LIVE PATH.
Budget: theory_x/stage_finitude/budget_shadow.py @ commit d9bc326.
Nothing in gui/server.py or selector.py imports this file.
Wiring target: 2026-11-21 (r77 close). See MIND_MAP.yaml p13_finitude.

Governing constraint: descriptive, never verdict. refuse() prices a
held contradiction; it never deletes, disables, downweights, or
annotates an option, and it never returns a boolean a caller could
veto on (it returns an entry id).

Entry shape (held_tensions, the SAME table harmonizer.py's
_hold_as_tension() already writes to — see substrate/schema/dynamic.sql
and init_db.py's _MIGRATIONS["dynamic"] for the kind/cost/irreversibility/
seq/provenance columns this module adds):

    kind             'tension_held' (never 'refused' — see module docstring
                     rationale below)
    refs             belief_id_a / belief_id_b, reused, not duplicated —
                     already an unordered (min, max) pair at write time
    cost             cumulative cost paid across every facing of this pair
    irreversibility  always 1 for kind='tension_held'
    seq              number of times this exact pair has been faced
    provenance       comma-joined, de-duplicated set of writers that have
                     ever faced this pair ('shadow', or a live writer's
                     identifier once the swap happens)

Why "refuse" but never a row named "refused": "fires" means "costs," not
"blocks." A row named after the verdict this module is forbidden from
reaching ("refused") would invite a future reader to hear "it decided not
to." tension_held is a record that a specific cost was paid at a specific
moment — immutable, unconditional, and not retroactively a verdict.

Why no `dark` column on the row itself: `dark` is a MIND_MAP.yaml node
status — a statement about whether the live loop calls a mechanism. It is
not a property of a ledger record. A row that paid a real cost does not
become a conditional fact because the caller that paid it was a shadow.
provenance carries that distinction instead (map carries the status;
ledger carries the fact).

CONFLICT, reported per the spec's own instruction rather than silently
reconciled: consolidate()'s per-kind dispatch table names an 'episode'
branch that is supposed to call "E's existing lossy compression,
unchanged." No such function exists anywhere in this codebase — grepped
`def consolidate` repo-wide (2026-11-10): zero hits, including inside
theory_x/memory/episodic.py. E has record_episodes/query_episodes/
reconstruct_episode; none of them compress or merge anything. consolidate()
below therefore treats kind='episode' as an explicit, documented no-op
pass-through (the only way to dispatch to "unchanged" behaviour that
doesn't exist is to touch nothing), not a call into a real function.
"""
from __future__ import annotations

import time
from typing import Any, Optional

from theory_x.stage_finitude.budget_shadow import Budget, InsufficientBudget

__all__ = ["refuse", "consolidate", "recall", "InsufficientBudget"]

UNRESOLVED_MARKER = "unresolved"


def _pair(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a <= b else (b, a)


def refuse(writer: Any, reader: Any, budget: Budget,
           pole_a: int, pole_b: int, cost: int,
           provenance: str = "shadow") -> int:
    """A write, not a block. Commits exactly one tension_held row for the
    unordered pair (pole_a, pole_b) and spends `cost` from `budget` in the
    SAME transaction as that commit — here, literally the same INSERT (or
    UPDATE on re-facing): there is one row, and it carries the cost, so
    there is nothing for a second write to get out of sync with.

    `budget.check_capacity(cost)` raises InsufficientBudget BEFORE any
    write is attempted — a caller that cannot afford the cost gets no row
    and no partial state, same ordering discipline as Budget.spend()
    (check first, write second, only then advance the in-memory balance).

    Re-facing the same pair (a second refuse() call for a pair already
    open): the existing row is UPDATED, not duplicated — seq increments,
    cost accrues (you paid twice), provenance unions. The pair stays one
    row; "I faced this twice" is a fact about that one row, not two rows.

    Returns the entry id only — never a boolean a caller could gate on.
    """
    budget.check_capacity(cost)  # raises InsufficientBudget; writes nothing on failure
    key_a, key_b = _pair(pole_a, pole_b)
    now = time.time()

    existing = reader.read_one(
        "SELECT id, cost, seq, provenance FROM held_tensions "
        "WHERE kind = 'tension_held' AND belief_id_a = ? AND belief_id_b = ? "
        "AND resolved_at IS NULL",
        (key_a, key_b),
    )
    if existing is not None:
        new_cost = (existing["cost"] or 0) + cost
        new_seq = (existing["seq"] or 1) + 1
        provs = set(p for p in (existing["provenance"] or "").split(",") if p)
        provs.add(provenance)
        writer.write(
            "UPDATE held_tensions SET cost = ?, seq = ?, provenance = ? WHERE id = ?",
            (new_cost, new_seq, ",".join(sorted(provs)), existing["id"]),
        )
        entry_id = existing["id"]
    else:
        entry_id = writer.write(
            "INSERT INTO held_tensions "
            "(belief_id_a, belief_id_b, created_at, kind, cost, "
            " irreversibility, seq, provenance) "
            "VALUES (?, ?, ?, 'tension_held', ?, 1, 1, ?)",
            (key_a, key_b, now, cost, provenance),
        )

    budget._spent += cost  # advance in-memory balance only after the write succeeded
    return entry_id


def consolidate(reader: Any, writer: Any, kind: str = "tension_held") -> dict:
    """Shared ledger operation with per-kind dispatch.

    kind='episode': explicit no-op pass-through — see module docstring
    CONFLICT note; there is no real E-side consolidate() to dispatch to,
    so dispatching to "unchanged" means touching nothing.

    kind='tension_held': dedupe by unordered ref-pair ONLY. Different
    ref-pairs are never combined, at any call volume — the invariant this
    function exists to hold is that consolidation may reduce the COST of
    holding a tension, it may never reduce the NUMBER of distinct tensions.
    Same-pair duplicate rows (possible under a read-then-write race between
    two concurrent refuse() calls for the same pair — refuse() itself
    prevents duplication in the common case, this is the race-cleanup
    pass) collapse to one row: seq sums, provenance unions, cost becomes
    the single highest facing cost paid (the duplication gets cheaper to
    hold; the tension itself does not vanish or get cheaper to have faced
    at all).
    """
    if kind == "episode":
        return {"kind": "episode", "merged_rows": 0, "distinct_pairs": None,
                "note": "no-op pass-through -- no real consolidate() exists "
                        "for episodes to dispatch to; see module docstring CONFLICT"}
    if kind != "tension_held":
        return {"kind": kind, "merged_rows": 0, "distinct_pairs": None,
                "note": "no dedupe policy defined for this kind"}

    rows = reader.read(
        "SELECT id, belief_id_a, belief_id_b, cost, seq, provenance, created_at "
        "FROM held_tensions WHERE kind = 'tension_held' AND resolved_at IS NULL"
    )
    groups: dict[tuple[int, int], list] = {}
    for r in rows:
        groups.setdefault(_pair(r["belief_id_a"], r["belief_id_b"]), []).append(r)

    merged = 0
    cost_delta = 0
    for group in groups.values():
        if len(group) <= 1:
            continue
        ordered = sorted(group, key=lambda r: r["created_at"])
        keep, dupes = ordered[0], ordered[1:]
        total_seq = sum(r["seq"] or 1 for r in ordered)
        total_cost_before = sum(r["cost"] or 0 for r in ordered)
        consolidated_cost = max(r["cost"] or 0 for r in ordered)
        provs = sorted(set(p for r in ordered for p in (r["provenance"] or "").split(",") if p))
        writer.write(
            "UPDATE held_tensions SET seq = ?, cost = ?, provenance = ? WHERE id = ?",
            (total_seq, consolidated_cost, ",".join(provs), keep["id"]),
        )
        for d in dupes:
            writer.write("DELETE FROM held_tensions WHERE id = ?", (d["id"],))
        merged += len(dupes)
        cost_delta += total_cost_before - consolidated_cost

    return {"kind": "tension_held", "merged_rows": merged,
            "distinct_pairs": len(groups), "cost_delta": cost_delta}


def recall(reader: Any, pole_a: int, pole_b: int) -> dict:
    """Returns the tension_held record for (pole_a, pole_b): both poles,
    cost, count (seq), and an explicit `unresolved` marker. Never
    fabricates a resolution, never picks a winner, never summarizes —
    there is no code path here that reads or returns anything named
    'winner', 'decision', or 'resolution'; the return shape has no field
    for one. A query against a pair with no open record returns
    found=False with the same explicit unresolved=True marker rather than
    an empty/ambiguous result (silence is ambiguous between "no answer
    exists" and "the store lost it" — this module prefers the marker).
    """
    key_a, key_b = _pair(pole_a, pole_b)
    row = reader.read_one(
        "SELECT belief_id_a, belief_id_b, cost, seq FROM held_tensions "
        "WHERE kind = 'tension_held' AND belief_id_a = ? AND belief_id_b = ? "
        "AND resolved_at IS NULL",
        (key_a, key_b),
    )
    if row is None:
        return {"found": False, "refs": [key_a, key_b],
                "unresolved": True, "cost": None, "count": 0}
    return {"found": True, "refs": [row["belief_id_a"], row["belief_id_b"]],
            "unresolved": True, "cost": row["cost"], "count": row["seq"]}
