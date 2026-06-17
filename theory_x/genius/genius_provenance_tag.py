#!/usr/bin/env python3
"""
genius_provenance_tag.py  —  Part 1 of "clean the genius signal".

Turns the provenance MEASUREMENT (genius_provenance.py) into a live, stored
LENS beside the genius score. Adds a `provenance` column to genius_tags and
labels every STRIKING thought as:
    own          — NEX's own self-generated reflection
    ingested     — wisdom quoted/absorbed from feeds (koans, parables)
    instrumental — task / research-plan text
    unclassified — conservative: not confidently any of the above

WHY SEPARATE FROM THE LIVE TAGGER (deliberate):
  - The genius grader is "log-only, no behavioural". We don't entangle a
    heuristic provenance judgment into it.
  - Provenance is HEURISTIC (it miscatches some — observed). Kept as a clearly-
    labelled second lens, the genius SCORE stays exactly what it is; provenance
    sits beside it, revisable, never silently fused. Same honesty rule as
    "never slide ANALOGUE into REAL".

SAFE & REVERSIBLE:
  - Adds one column with DEFAULT NULL. The live tagger's INSERT uses a named
    column list, so it is unaffected (SQLite fills the new column with default).
  - Re-runnable: only (re)labels rows, never deletes genius data.
  - --undo drops the provenance values (column stays, harmless).

USAGE (from nex5 root):
    .venv/bin/python3 theory_x/genius/genius_provenance_tag.py --backfill
    .venv/bin/python3 theory_x/genius/genius_provenance_tag.py --report
    .venv/bin/python3 theory_x/genius/genius_provenance_tag.py --backfill --min-score 0.0  # tag ALL, not just striking
"""
from __future__ import annotations

import sys
import sqlite3
import argparse

# Reuse the exact validated classifier — single source of truth.
sys.path.insert(0, ".")
try:
    from theory_x.genius.genius_provenance import classify  # type: ignore
except Exception:
    # Fallback path if run from a different cwd.
    from genius_provenance import classify  # type: ignore


def _conv_db() -> str:
    try:
        from substrate.paths import db_paths  # type: ignore
        return str(db_paths()["conversations"])
    except Exception:
        return "data/conversations.db"


def _dyn_db() -> str:
    try:
        from substrate.paths import db_paths  # type: ignore
        return str(db_paths()["dynamic"])
    except Exception:
        return "data/dynamic.db"


# Map the classifier's bucket names to compact provenance labels.
_LABEL = {
    "self_reflection": "own",
    "ingested": "ingested",
    "instrumental": "instrumental",
    "other_unclassified": "unclassified",
    "empty": "unclassified",
}


def ensure_column(conn) -> None:
    cols = [r[1] for r in conn.execute("PRAGMA table_info(genius_tags)").fetchall()]
    if "provenance" not in cols:
        conn.execute("ALTER TABLE genius_tags ADD COLUMN provenance TEXT")
        conn.commit()
        print("Added column genius_tags.provenance (DEFAULT NULL — live tagger unaffected).")
    else:
        print("Column genius_tags.provenance already present.")


def backfill(min_score: float = 0.0, only_striking: bool = True, relabel: bool = True) -> dict:
    conv = sqlite3.connect(_conv_db())
    conv.row_factory = sqlite3.Row
    ensure_column(conv)
    conv.execute(f"ATTACH '{_dyn_db()}' AS dyn")

    where = "g.score >= ?"
    params = [min_score]
    if only_striking:
        where += " AND g.class='STRIKING'"
    if not relabel:
        where += " AND g.provenance IS NULL"

    rows = conv.execute(
        f"SELECT g.id AS gid, f.thought AS thought "
        f"FROM genius_tags g JOIN dyn.fountain_events f "
        f"ON f.id = g.fountain_event_id WHERE {where}",
        params,
    ).fetchall()

    counts: dict[str, int] = {}
    for r in rows:
        label = _LABEL.get(classify(r["thought"]), "unclassified")
        conv.execute("UPDATE genius_tags SET provenance=? WHERE id=?", (label, r["gid"]))
        counts[label] = counts.get(label, 0) + 1
    conv.commit()
    conv.close()

    total = sum(counts.values())
    print(f"\nBackfilled provenance on {total} rows"
          f"{' (STRIKING only)' if only_striking else ''}:")
    for k in ("own", "ingested", "instrumental", "unclassified"):
        n = counts.get(k, 0)
        pct = (100.0 * n / total) if total else 0.0
        print(f"  {k:14s} {n:5d}  ({pct:4.1f}%)")
    if total:
        own = counts.get("own", 0)
        print(f"\n  -> {100.0*own/total:.1f}% of tagged thoughts are NEX's OWN "
              f"(conservative; real figure slightly higher).")
    return counts


def report() -> None:
    conv = sqlite3.connect(_conv_db())
    conv.row_factory = sqlite3.Row
    cols = [r[1] for r in conv.execute("PRAGMA table_info(genius_tags)").fetchall()]
    if "provenance" not in cols:
        print("No provenance column yet — run --backfill first.")
        return
    rows = conv.execute(
        "SELECT provenance, COUNT(*) n, ROUND(AVG(score),2) avg_score "
        "FROM genius_tags WHERE class='STRIKING' AND provenance IS NOT NULL "
        "GROUP BY provenance ORDER BY n DESC"
    ).fetchall()
    conv.close()
    print("STRIKING thoughts by provenance:")
    tot = sum(r["n"] for r in rows)
    for r in rows:
        pct = 100.0 * r["n"] / tot if tot else 0
        print(f"  {r['provenance']:14s} {r['n']:5d} ({pct:4.1f}%)  avg_genius={r['avg_score']}")


def undo() -> None:
    conv = sqlite3.connect(_conv_db())
    conv.execute("UPDATE genius_tags SET provenance=NULL")
    conv.commit()
    conv.close()
    print("Cleared all provenance values (column kept, harmless).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill", action="store_true", help="add column + label rows")
    ap.add_argument("--report", action="store_true", help="show current split")
    ap.add_argument("--undo", action="store_true", help="clear provenance values")
    ap.add_argument("--min-score", type=float, default=0.0)
    ap.add_argument("--all", action="store_true", help="tag ALL tags, not just STRIKING")
    args = ap.parse_args()

    if args.undo:
        undo()
    elif args.report:
        report()
    elif args.backfill:
        backfill(min_score=args.min_score, only_striking=not args.all)
    else:
        ap.print_help()
