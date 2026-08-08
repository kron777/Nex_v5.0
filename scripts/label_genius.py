#!/usr/bin/env python3
"""Terminal labelling tool for the genius scorer refit (round 39).

Smallest thing that works. One fire at a time, its focal item beside it, two
keys, writes to a table. Resumable -- the sample is drawn ONCE and frozen, so
the set cannot shift between sessions.

    Draw the sample (once):   python3 scripts/label_genius.py --draw
    Label:                    python3 scripts/label_genius.py
    Progress:                 python3 scripts/label_genius.py --status

Sampling rule (round 38 C1): 80 from the decision band [0.3, 0.7) where a
weight change can actually flip a decision, plus 40 anchors -- 20 from
[0.8, 1.0) and 20 from [0.0, 0.2) -- to catch gross miscalibration.
Stratified across days so one day's topic cannot dominate. Uniform sampling
was rejected: 57% of fires sit in [0.0, 0.2) where nothing can flip.
"""
from __future__ import annotations

import argparse
import os
import random
import sqlite3
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONV = os.path.join(ROOT, "data", "conversations.db")
DYN = os.path.join(ROOT, "data", "dynamic.db")

BANDS = [("decision", 0.3, 0.7, 80), ("high", 0.8, 1.01, 20), ("low", 0.0, 0.2, 20)]
WINDOW_DAYS = 14
SEED = 39  # frozen; changing it would redraw the sample


def _connect_rw():
    c = sqlite3.connect(CONV, timeout=30)
    c.execute(
        "CREATE TABLE IF NOT EXISTS genius_labels ("
        "  fountain_event_id INTEGER PRIMARY KEY,"
        "  band TEXT NOT NULL,"
        "  score REAL,"
        "  label INTEGER,"          # 1 striking, 0 ordinary, NULL = drawn not yet labelled
        "  labelled_at REAL,"
        "  drawn_at REAL NOT NULL"
        ")"
    )
    c.commit()
    return c


def draw(force: bool = False) -> int:
    c = _connect_rw()
    n = c.execute("SELECT COUNT(*) FROM genius_labels").fetchone()[0]
    if n and not force:
        print(f"Sample already drawn ({n} rows). It is FROZEN on purpose so the set "
              f"cannot shift under you between sessions.\nUse --draw --force only if "
              f"you intend to discard it and start over.")
        return 1
    if force:
        c.execute("DELETE FROM genius_labels")

    cutoff = time.time() - WINDOW_DAYS * 86400
    rows = c.execute(
        "SELECT fountain_event_id, score, tagged_at FROM genius_tags "
        "WHERE tagged_at > ? AND score IS NOT NULL", (cutoff,)
    ).fetchall()
    # Stratify across days: bucket by day, then round-robin so no single day
    # can dominate a band.
    rng = random.Random(SEED)
    total = 0
    for band, lo, hi, want in BANDS:
        pool = [r for r in rows if lo <= r[1] < hi]
        byday: dict = {}
        for r in pool:
            byday.setdefault(time.strftime("%Y-%m-%d", time.gmtime(r[2])), []).append(r)
        for v in byday.values():
            rng.shuffle(v)
        picked, days = [], sorted(byday)
        while len(picked) < want and any(byday[d] for d in days):
            for d in days:
                if byday[d] and len(picked) < want:
                    picked.append(byday[d].pop())
        now = time.time()
        c.executemany(
            "INSERT OR IGNORE INTO genius_labels "
            "(fountain_event_id, band, score, label, labelled_at, drawn_at) "
            "VALUES (?,?,?,NULL,NULL,?)",
            [(r[0], band, r[1], now) for r in picked],
        )
        print(f"  {band:<9} band [{lo:.1f},{hi:.2f})  wanted {want:>3}  drew {len(picked):>3}"
              f"  from {len(pool)} available across {len(byday)} days")
        total += len(picked)
    c.commit()
    print(f"\nDrew {total} fires. FROZEN. Now run:  python3 scripts/label_genius.py")
    return 0


def status() -> int:
    c = _connect_rw()
    print(f"{'band':<10}{'done':>6}{'total':>7}")
    for band, _lo, _hi, _w in BANDS:
        d = c.execute("SELECT COUNT(*) FROM genius_labels WHERE band=? AND label IS NOT NULL",
                      (band,)).fetchone()[0]
        t = c.execute("SELECT COUNT(*) FROM genius_labels WHERE band=?", (band,)).fetchone()[0]
        print(f"{band:<10}{d:>6}{t:>7}")
    d = c.execute("SELECT COUNT(*) FROM genius_labels WHERE label IS NOT NULL").fetchone()[0]
    t = c.execute("SELECT COUNT(*) FROM genius_labels").fetchone()[0]
    print(f"{'TOTAL':<10}{d:>6}{t:>7}")
    return 0


def label() -> int:
    c = _connect_rw()
    dyn = sqlite3.connect(f"file:{DYN}?mode=ro", uri=True)
    dyn.row_factory = sqlite3.Row
    todo = c.execute(
        "SELECT fountain_event_id, band, score FROM genius_labels "
        "WHERE label IS NULL ORDER BY RANDOM()"
    ).fetchall()
    if not todo:
        print("Nothing left to label. Run --status, or --draw to start a new set.")
        return 0
    done = c.execute("SELECT COUNT(*) FROM genius_labels WHERE label IS NOT NULL").fetchone()[0]
    total = done + len(todo)
    print("=" * 74)
    print("  s = STRIKING    o = ordinary    u = undo last    q = quit (progress saved)")
    print("  The SCORE IS HIDDEN until you answer, so it cannot anchor you.")
    print("=" * 74)
    last = None
    for fid, band, score in todo:
        r = dyn.execute(
            "SELECT thought, focal_item, mode, hot_branch FROM fountain_events WHERE id=?",
            (fid,)).fetchone()
        if r is None or not (r["thought"] or "").strip():
            c.execute("UPDATE genius_labels SET label=-1, labelled_at=? "
                      "WHERE fountain_event_id=?", (time.time(), fid))
            c.commit()
            continue
        done += 1
        print(f"\n[{done}/{total}]  mode={r['mode']}  branch={r['hot_branch']}")
        if r["focal_item"]:
            print(f"  ITEM : {r['focal_item'][:200]}")
        print(f"  FIRE : {(r['thought'] or '').strip()[:900]}")
        while True:
            try:
                k = input("  > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nsaved.")
                return 0
            if k == "q":
                print(f"saved. {done - 1} labelled so far.")
                return 0
            if k == "u" and last is not None:
                c.execute("UPDATE genius_labels SET label=NULL, labelled_at=NULL "
                          "WHERE fountain_event_id=?", (last,))
                c.commit()
                print(f"  undone {last} — it will come round again.")
                done -= 2
                break
            if k in ("s", "o"):
                c.execute("UPDATE genius_labels SET label=?, labelled_at=? "
                          "WHERE fountain_event_id=?", (1 if k == "s" else 0, time.time(), fid))
                c.commit()
                last = fid
                print(f"  recorded {'STRIKING' if k=='s' else 'ordinary'}   "
                      f"(scorer said {score:.3f} — {'agrees' if (k=='s')==(score>=0.5) else 'DISAGREES'})")
                break
            print("  s / o / u / q")
    print("\nAll done. Run --status to confirm.")
    return 0


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="genius scorer labelling tool")
    ap.add_argument("--draw", action="store_true", help="draw and freeze the sample (once)")
    ap.add_argument("--force", action="store_true", help="with --draw: discard an existing set")
    ap.add_argument("--status", action="store_true", help="show progress")
    a = ap.parse_args(argv)
    if a.draw:
        return draw(force=a.force)
    if a.status:
        return status()
    return label()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
