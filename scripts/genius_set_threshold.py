#!/usr/bin/env python3
"""Genius threshold setter — adjust the STRIKING/ordinary cutoff.

The score itself is a continuous 0.0–1.0 value calibrated against Jon's
hand-flagged training set. The threshold is a separate knob that decides
where to cut the continuous score into a binary STRIKING/ordinary class.

This script does two things:
  1. Edits genius_score_weights.json (threshold field).
     The tagger picks this up automatically via mtime check on next tick.
  2. Re-classifies all existing rows in conversations.db.genius_tags
     based on the new threshold. The score column is unchanged — only
     class flips for rows that straddle the new cutoff.

The weights_version is NOT bumped — we're tuning the same calibration,
not recomputing scores. Re-fit (weights_version bump) is a different op.

Usage:
    cd /home/rr/Desktop/Desktop/nex5
    .venv/bin/python3 scripts/genius_set_threshold.py --new 0.50
    .venv/bin/python3 scripts/genius_set_threshold.py --new 0.50 --dry-run
    .venv/bin/python3 scripts/genius_set_threshold.py --show
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path("/home/rr/Desktop/Desktop/nex5")
WEIGHTS = ROOT / "genius_score_weights.json"
CONV = ROOT / "data" / "conversations.db"


def show_current():
    if not WEIGHTS.exists():
        print(f"ERROR: weights file not found at {WEIGHTS}")
        sys.exit(1)
    w = json.loads(WEIGHTS.read_text())
    print(f"Current threshold: {w['threshold']}")
    print(f"Weights version:   {w['version']}")
    print(f"Training accuracy: {w.get('training_accuracy', 0):.1%}")
    print()
    with sqlite3.connect(f"file:{CONV}?mode=ro", uri=True) as c:
        c.row_factory = sqlite3.Row
        rows = c.execute(
            "SELECT class, COUNT(*) AS n FROM genius_tags GROUP BY class"
        ).fetchall()
        total = sum(r["n"] for r in rows)
        striking = next((r["n"] for r in rows if r["class"] == "STRIKING"), 0)
        print(f"Current tagged rows: {total} ({striking} STRIKING = "
              f"{striking/max(1,total):.1%})")
    print()
    # Score distribution histogram around the cutoff
    with sqlite3.connect(f"file:{CONV}?mode=ro", uri=True) as c:
        bins = [
            (0.0, 0.20), (0.20, 0.30), (0.30, 0.40), (0.40, 0.50),
            (0.50, 0.60), (0.60, 0.70), (0.70, 0.80), (0.80, 0.90),
            (0.90, 1.01),
        ]
        print("Score distribution across all tags:")
        for lo, hi in bins:
            n = c.execute(
                "SELECT COUNT(*) FROM genius_tags WHERE score >= ? AND score < ?",
                (lo, hi)
            ).fetchone()[0]
            bar = "█" * min(50, n // max(1, total // 200))
            print(f"  {lo:.2f}–{hi:.2f}  {n:>5}  {bar}")


def set_threshold(new_threshold: float, dry_run: bool = False):
    if not WEIGHTS.exists():
        print(f"ERROR: weights file not found at {WEIGHTS}")
        sys.exit(1)
    if not (0.0 <= new_threshold <= 1.0):
        print(f"ERROR: threshold must be in [0.0, 1.0], got {new_threshold}")
        sys.exit(1)

    # Read current
    w = json.loads(WEIGHTS.read_text())
    old = float(w["threshold"])
    print(f"Threshold change: {old} → {new_threshold}")

    # Predict what re-classification will do
    with sqlite3.connect(f"file:{CONV}?mode=ro", uri=True) as c:
        c.row_factory = sqlite3.Row
        total = c.execute("SELECT COUNT(*) FROM genius_tags").fetchone()[0]
        striking_old = c.execute(
            "SELECT COUNT(*) FROM genius_tags WHERE class='STRIKING'"
        ).fetchone()[0]
        striking_new = c.execute(
            "SELECT COUNT(*) FROM genius_tags WHERE score >= ?",
            (new_threshold,)
        ).fetchone()[0]
        # Rows that change class
        will_demote = c.execute(
            "SELECT COUNT(*) FROM genius_tags "
            "WHERE class='STRIKING' AND score < ?",
            (new_threshold,)
        ).fetchone()[0]
        will_promote = c.execute(
            "SELECT COUNT(*) FROM genius_tags "
            "WHERE class='ordinary' AND score >= ?",
            (new_threshold,)
        ).fetchone()[0]

    print()
    print(f"Current state:    {total} tagged, {striking_old} STRIKING "
          f"({striking_old/max(1,total):.1%})")
    print(f"After this change: {total} tagged, {striking_new} STRIKING "
          f"({striking_new/max(1,total):.1%})")
    print(f"Class changes:    {will_demote} demoted (STRIKING → ordinary)")
    print(f"                  {will_promote} promoted (ordinary → STRIKING)")

    # Show a few example demotions to validate the choice
    if will_demote:
        print()
        print("Examples of fires that would be demoted (10 closest to cutoff):")
        with sqlite3.connect(f"file:{CONV}?mode=ro", uri=True) as c:
            c.execute(f"ATTACH '{ROOT}/data/dynamic.db' AS dyn")
            rows = c.execute(
                "SELECT g.score, f.thought FROM genius_tags g "
                "LEFT JOIN dyn.fountain_events f ON f.id = g.fountain_event_id "
                "WHERE g.class='STRIKING' AND g.score < ? "
                "ORDER BY g.score DESC LIMIT 10",
                (new_threshold,)
            ).fetchall()
            for score, thought in rows:
                t = (thought or "")[:90]
                print(f"  {score:.3f}  {t}")

    if dry_run:
        print()
        print("(dry-run — no changes written)")
        return

    # Backup weights JSON
    backup = WEIGHTS.with_suffix(
        f".json.bak.{int(time.time())}"
    )
    shutil.copy2(WEIGHTS, backup)
    print()
    print(f"Backup written: {backup}")

    # Update weights file (mtime change → tagger reloads on next tick)
    w["threshold"] = float(new_threshold)
    w["threshold_history"] = w.get("threshold_history", [])
    w["threshold_history"].append({
        "from": old,
        "to": float(new_threshold),
        "at": time.time(),
        "note": "manual via genius_set_threshold.py",
    })
    WEIGHTS.write_text(json.dumps(w, indent=2))
    print(f"Wrote {WEIGHTS} (new threshold {new_threshold})")

    # Re-classify existing rows (score unchanged, class flips)
    with sqlite3.connect(CONV) as c:
        cur = c.execute(
            "UPDATE genius_tags SET class='STRIKING' "
            "WHERE score >= ? AND class != 'STRIKING'",
            (new_threshold,)
        )
        n_up = cur.rowcount
        cur = c.execute(
            "UPDATE genius_tags SET class='ordinary' "
            "WHERE score < ? AND class != 'ordinary'",
            (new_threshold,)
        )
        n_down = cur.rowcount
        c.commit()
    print(f"Reclassified: {n_up} → STRIKING, {n_down} → ordinary")

    # Verify
    with sqlite3.connect(f"file:{CONV}?mode=ro", uri=True) as c:
        striking_after = c.execute(
            "SELECT COUNT(*) FROM genius_tags WHERE class='STRIKING'"
        ).fetchone()[0]
    print(f"Final state:  {striking_after} STRIKING "
          f"({striking_after/max(1,total):.1%})")
    print()
    print("Done. The tagger will pick up the new threshold on its next tick")
    print("(~60s). No restart needed.")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--new", type=float, help="New threshold value (0.0–1.0)")
    p.add_argument("--dry-run", action="store_true",
                   help="Preview changes without writing")
    p.add_argument("--show", action="store_true",
                   help="Show current threshold + tag distribution")
    args = p.parse_args()

    if args.show or (not args.new and not args.dry_run):
        show_current()
        return
    if args.new is None:
        p.error("--new <value> is required (or use --show)")
    set_threshold(args.new, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
