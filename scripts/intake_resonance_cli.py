#!/usr/bin/env python3
"""Intake resonance — inspect what newly-crystallized beliefs are resonating
against in the standing-point library.

Same shape as scripts/genius_tag_cli.py. Carryx §8 Step 1 surfacer.

Commands:
  show              Distribution of resonance scores across all logged rows.
  recent [--limit]  Most recent intake events with their resonance + match.
  top   [--limit]   Highest-resonance intake events.
  bottom [--limit]  Lowest-resonance intake events (peripheral / noise).
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path("/home/rr/Desktop/Desktop/nex5")
BELIEFS = ROOT / "data" / "beliefs.db"


def _open_ro():
    c = sqlite3.connect(f"file:{BELIEFS}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


def cmd_show(args):
    with _open_ro() as c:
        total = c.execute("SELECT COUNT(*) FROM intake_resonance_log").fetchone()[0]
        if total == 0:
            print("No intake_resonance_log rows yet — let nex run a bit first.")
            return
        print(f"Total intake events logged: {total}")
        print()
        print("Distribution of resonance scores:")
        bins = [
            (0.00, 0.20), (0.20, 0.30), (0.30, 0.40), (0.40, 0.50),
            (0.50, 0.60), (0.60, 0.70), (0.70, 0.80), (0.80, 0.90),
            (0.90, 1.01),
        ]
        max_n = 0
        counts = []
        for lo, hi in bins:
            n = c.execute(
                "SELECT COUNT(*) FROM intake_resonance_log "
                "WHERE resonance >= ? AND resonance < ?", (lo, hi)
            ).fetchone()[0]
            counts.append(n)
            max_n = max(max_n, n)
        for (lo, hi), n in zip(bins, counts):
            bar_len = int(50 * n / max(1, max_n))
            bar = "█" * bar_len
            print(f"  {lo:.2f}–{hi:.2f}  {n:>6}  {bar}")
        print()
        avg = c.execute("SELECT AVG(resonance) FROM intake_resonance_log").fetchone()[0]
        print(f"Mean resonance: {avg:.3f}")


def cmd_recent(args):
    with _open_ro() as c:
        rows = c.execute(
            "SELECT i.content, i.resonance, i.top_match_belief_id, i.ts, "
            "       b.content AS match_content "
            "FROM intake_resonance_log i "
            "LEFT JOIN beliefs b ON b.id = i.top_match_belief_id "
            "ORDER BY i.ts DESC LIMIT ?",
            (args.limit,)
        ).fetchall()
        for r in rows:
            print(f"{r['resonance']:.3f}  {(r['content'] or '')[:80]}")
            if r["match_content"]:
                print(f"        ↳ #{r['top_match_belief_id']}: "
                      f"{(r['match_content'] or '')[:80]}")
            print()


def cmd_top(args):
    with _open_ro() as c:
        rows = c.execute(
            "SELECT i.content, i.resonance, i.top_match_belief_id, "
            "       b.content AS match_content "
            "FROM intake_resonance_log i "
            "LEFT JOIN beliefs b ON b.id = i.top_match_belief_id "
            "ORDER BY i.resonance DESC LIMIT ?",
            (args.limit,)
        ).fetchall()
        for r in rows:
            print(f"★ {r['resonance']:.3f}  {(r['content'] or '')[:80]}")
            if r["match_content"]:
                print(f"        ↳ #{r['top_match_belief_id']}: "
                      f"{(r['match_content'] or '')[:80]}")
            print()


def cmd_bottom(args):
    with _open_ro() as c:
        rows = c.execute(
            "SELECT content, resonance FROM intake_resonance_log "
            "ORDER BY resonance ASC LIMIT ?",
            (args.limit,)
        ).fetchall()
        for r in rows:
            print(f"  {r['resonance']:.3f}  {(r['content'] or '')[:80]}")


def main():
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("show").set_defaults(func=cmd_show)
    rc = sp.add_parser("recent"); rc.add_argument("--limit", type=int, default=20); rc.set_defaults(func=cmd_recent)
    tp = sp.add_parser("top"); tp.add_argument("--limit", type=int, default=20); tp.set_defaults(func=cmd_top)
    bt = sp.add_parser("bottom"); bt.add_argument("--limit", type=int, default=20); bt.set_defaults(func=cmd_bottom)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
