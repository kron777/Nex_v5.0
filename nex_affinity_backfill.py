#!/usr/bin/env python3
"""Backfill affinity under the provenance scorer (D-A, PR B part 2).

Recomputes beliefs.affinity for already-scored rows using the provenance formula
in theory_x/life/affinity_loop.py, preserving the old value in affinity_legacy
and stamping affinity_model='prov_v1' so the migration is idempotent and
reversible.

SAFE BY DEFAULT. A bare invocation is a DRY RUN: it prints the plan (rows
matched, batch count, a 10-row old->new sample) and exits 0, touching nothing.
Writing requires BOTH:
    --apply   on the command line
    NEX5_AFFINITY_PROVENANCE=on   in the environment
so no one fires ~12k row updates by tab-completing a script. Run it only AFTER a
shadow soak has shown the provenance scores are right.

Rollback: set NEX5_AFFINITY_PROVENANCE=off and read
COALESCE(affinity_legacy, affinity).

Uses the single-source scoring functions from affinity_loop, so the backfill and
the live scorer can never drift.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

from substrate import connect
from substrate.paths import DbPath
from theory_x.life.affinity_loop import _provenance_affinity, _usage_score

_MODEL_TAG = "prov_v1"
_BATCH = 500


def plan(cx):
    """Return [(id, source, old_affinity, new_affinity), ...] for rows that have
    an affinity but have not yet been migrated (affinity_model IS NULL)."""
    now = time.time()
    rows = cx.execute(
        """
        SELECT b.id, b.source,
               COALESCE(b.use_count, 0) AS use_count,
               b.last_referenced_at, b.affinity,
               (SELECT COUNT(*) FROM belief_edges WHERE source_id = b.id) AS edges_out
        FROM beliefs b
        WHERE b.affinity IS NOT NULL AND b.affinity_model IS NULL
        """
    ).fetchall()
    out = []
    for r in rows:
        bid, source, use_count, last_ref, old_aff, edges_out = r
        hours_since = ((now - last_ref) / 3600) if last_ref else None
        usage = _usage_score(use_count, edges_out, hours_since)
        new_aff = _provenance_affinity(source, usage)
        out.append((bid, source, old_aff, new_aff))
    return out


def apply(cx, rows, batch=_BATCH):
    """Write the plan in batches: one BEGIN IMMEDIATE per batch, old value copied
    to affinity_legacy, new value to affinity, stamp affinity_model."""
    now = time.time()
    written = 0
    for i in range(0, len(rows), batch):
        chunk = rows[i:i + batch]
        cx.execute("BEGIN IMMEDIATE")
        try:
            for bid, _src, _old, new_aff in chunk:
                # In SQLite, SET RHS sees the pre-update row, so affinity_legacy
                # captures the old affinity while affinity takes the new value.
                cx.execute(
                    "UPDATE beliefs SET affinity_legacy = affinity, "
                    "affinity = ?, affinity_model = ?, affinity_updated_at = ? "
                    "WHERE id = ? AND affinity_model IS NULL",
                    (new_aff, _MODEL_TAG, now, bid),
                )
            cx.execute("COMMIT")
            written += len(chunk)
        except Exception:
            cx.execute("ROLLBACK")
            raise
    return written


def _print_plan(rows):
    n = len(rows)
    batches = (n + _BATCH - 1) // _BATCH
    print(f"[affinity backfill] DRY RUN — no changes written.")
    print(f"  rows to migrate (affinity set, affinity_model NULL): {n}")
    print(f"  batches of {_BATCH}: {batches}")
    if n:
        print("  sample (id: source  old -> new):")
        for bid, source, old_aff, new_aff in rows[:10]:
            old_s = f"{old_aff:.3f}" if old_aff is not None else "NULL"
            print(f"    {bid}: {source or '<null>':24s} {old_s} -> {new_aff:.3f}")
    print("  to execute: --apply AND NEX5_AFFINITY_PROVENANCE=on")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Backfill affinity under provenance scorer")
    ap.add_argument("--db", default=None, help="beliefs DB path (default: resolved)")
    ap.add_argument("--apply", action="store_true",
                    help="actually write (also requires NEX5_AFFINITY_PROVENANCE=on)")
    ap.add_argument("--batch", type=int, default=_BATCH)
    args = ap.parse_args(argv)

    db = args.db or str(DbPath("beliefs"))
    cx = connect(db, timeout=60)
    try:
        rows = plan(cx)
        if not args.apply:
            _print_plan(rows)
            return 0
        if os.environ.get("NEX5_AFFINITY_PROVENANCE", "off").strip().lower() != "on":
            print("REFUSING --apply: NEX5_AFFINITY_PROVENANCE is not 'on'.",
                  file=sys.stderr)
            return 2
        written = apply(cx, rows, batch=args.batch)
        print(f"[affinity backfill] migrated {written} rows (affinity_model={_MODEL_TAG}).")
        return 0
    finally:
        cx.close()


if __name__ == "__main__":
    raise SystemExit(main())
