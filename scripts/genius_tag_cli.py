#!/usr/bin/env python3
"""Genius tagger — manual backfill / inspect CLI.

Use this when you want to score historical fountain_events without
booting nex5, or to inspect what the tagger has written so far.

Commands:
  backfill [--hours N]     Score recent fires (default 14 days)
                           that have no row for current weights version.
                           Idempotent.
  show     [--limit N]     Show last N tagged fires sorted by tag time
                           (default 30). Use --striking for STRIKING only.
  top      [--limit N]     Top N STRIKING by score across all tags.
  rate                     Overall striking rate by branch.
  reset    --version V     Delete all tags for weights_version V
                           (use before re-scoring with bumped weights).

Run with the project venv:
  cd /home/rr/Desktop/nex5
  .venv/bin/python3 scripts/genius_tag_cli.py backfill
  .venv/bin/python3 scripts/genius_tag_cli.py show --striking
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

# Repo root on Jon's machine
ROOT = Path("/home/rr/Desktop/nex5")
DATA = ROOT / "data"
DYN = DATA / "dynamic.db"
BEL = DATA / "beliefs.db"
CONV = DATA / "conversations.db"
WEIGHTS = ROOT / "genius_score_weights.json"

sys.path.insert(0, str(ROOT))


def _load_weights():
    if not WEIGHTS.exists():
        print(f"ERROR: weights file not found at {WEIGHTS}")
        print("Run: .venv/bin/python3 -m theory_x.genius.score_v2")
        sys.exit(1)
    return json.loads(WEIGHTS.read_text())


def _open_ro(p):
    c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


def _open_rw(p):
    c = sqlite3.connect(p)
    c.row_factory = sqlite3.Row
    return c


# ── commands ─────────────────────────────────────────────────────────────────

def cmd_backfill(args):
    from theory_x.genius import score_v2
    weights = _load_weights()
    version = str(weights["version"])
    threshold = float(weights["threshold"])
    cutoff = time.time() - args.hours * 3600
    ts_now = time.time()

    with _open_ro(DYN) as d:
        fires = [dict(r) for r in d.execute(
            "SELECT id, ts, thought, hot_branch FROM fountain_events "
            "WHERE ts > ? ORDER BY ts ASC", (cutoff,)
        ).fetchall()]
    print(f"Loaded {len(fires)} fountain_events from last {args.hours}h")

    with _open_ro(BEL) as b:
        t6 = [dict(r) for r in b.execute(
            "SELECT id, content, tier, created_at FROM beliefs "
            "WHERE tier = 6 AND created_at > ?", (ts_now - 14 * 86400,)
        ).fetchall()]
    print(f"Loaded {len(t6)} T6 beliefs (F3 context)")

    with _open_ro(CONV) as c:
        already = {int(r["fountain_event_id"]) for r in c.execute(
            "SELECT fountain_event_id FROM genius_tags WHERE weights_version=?",
            (version,)
        ).fetchall()}
    print(f"{len(already)} fires already tagged under version '{version}'")

    to_tag = [f for f in fires if int(f["id"]) not in already]
    print(f"{len(to_tag)} fires to score")
    if not to_tag:
        return

    thoughts_in_order = [f["thought"] for f in fires]
    to_tag_set = {int(f["id"]) for f in to_tag}
    wbias = float(weights["bias"])
    wvec = list(map(float, weights["weights"]))

    striking = 0
    rows = []
    for i, fire in enumerate(fires):
        if int(fire["id"]) not in to_tag_set:
            continue
        prior = thoughts_in_order[max(0, i - 50):i]
        feats = score_v2.compute_features(fire, prior, t6)
        z = sum(wvec[j] * feats[j] for j in range(5)) + wbias
        score = score_v2.sigmoid(z)
        cls = "STRIKING" if score >= threshold else "ordinary"
        rows.append((int(fire["id"]), score, cls, version, ts_now))
        if cls == "STRIKING":
            striking += 1

    print(f"Writing {len(rows)} rows ({striking} STRIKING, "
          f"{striking/max(1,len(rows)):.1%})...")
    with _open_rw(CONV) as c:
        c.executemany(
            "INSERT OR IGNORE INTO genius_tags "
            "(fountain_event_id, score, class, weights_version, tagged_at) "
            "VALUES (?, ?, ?, ?, ?)", rows,
        )
        c.commit()
    print("Done.")


def cmd_show(args):
    where = "WHERE g.class = 'STRIKING'" if args.striking else ""
    with _open_ro(CONV) as c:
        c.execute(f"ATTACH '{DYN}' AS dyn")
        rows = c.execute(
            f"SELECT g.fountain_event_id, g.score, g.class, g.weights_version, "
            f"g.tagged_at, f.thought, f.hot_branch "
            f"FROM genius_tags g LEFT JOIN dyn.fountain_events f "
            f"ON f.id = g.fountain_event_id "
            f"{where} ORDER BY g.tagged_at DESC LIMIT ?",
            (args.limit,),
        ).fetchall()

    if not rows:
        print("No tags found.")
        return

    for r in rows:
        marker = "★" if r["class"] == "STRIKING" else " "
        thought = (r["thought"] or "")[:110]
        branch = r["hot_branch"] or "?"
        print(f"{marker} {r['score']:.3f}  [{r['class']:8s}]  "
              f"#{r['fountain_event_id']}  ({branch})  {thought}")


def cmd_top(args):
    with _open_ro(CONV) as c:
        c.execute(f"ATTACH '{DYN}' AS dyn")
        rows = c.execute(
            "SELECT g.fountain_event_id, g.score, g.class, "
            "f.thought, f.hot_branch "
            "FROM genius_tags g LEFT JOIN dyn.fountain_events f "
            "ON f.id = g.fountain_event_id "
            "WHERE g.class = 'STRIKING' "
            "ORDER BY g.score DESC LIMIT ?",
            (args.limit,),
        ).fetchall()
    for r in rows:
        thought = (r["thought"] or "")[:110]
        branch = r["hot_branch"] or "?"
        print(f"★ {r['score']:.3f}  #{r['fountain_event_id']}  "
              f"({branch})  {thought}")


def cmd_rate(args):
    with _open_ro(CONV) as c:
        c.execute(f"ATTACH '{DYN}' AS dyn")
        rows = c.execute(
            "SELECT f.hot_branch, g.class, COUNT(*) AS n "
            "FROM genius_tags g LEFT JOIN dyn.fountain_events f "
            "ON f.id = g.fountain_event_id "
            "GROUP BY f.hot_branch, g.class "
            "ORDER BY f.hot_branch, g.class"
        ).fetchall()
    by_branch = {}
    for r in rows:
        b = r["hot_branch"] or "?"
        by_branch.setdefault(b, {"STRIKING": 0, "ordinary": 0})
        by_branch[b][r["class"]] = int(r["n"])
    print(f"{'branch':<25s} {'striking':>10s} {'ordinary':>10s} "
          f"{'total':>8s} {'rate':>8s}")
    for b, d in sorted(by_branch.items(), key=lambda x: -sum(x[1].values())):
        total = d["STRIKING"] + d["ordinary"]
        rate = d["STRIKING"] / max(1, total)
        print(f"{b:<25s} {d['STRIKING']:>10d} {d['ordinary']:>10d} "
              f"{total:>8d} {rate:>7.1%}")


def cmd_reset(args):
    with _open_rw(CONV) as c:
        cur = c.execute(
            "DELETE FROM genius_tags WHERE weights_version = ?",
            (args.version,),
        )
        c.commit()
        print(f"Deleted {cur.rowcount} rows for version '{args.version}'")


def main():
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest="cmd", required=True)

    bf = sp.add_parser("backfill")
    bf.add_argument("--hours", type=int, default=14 * 24)
    bf.set_defaults(func=cmd_backfill)

    sh = sp.add_parser("show")
    sh.add_argument("--limit", type=int, default=30)
    sh.add_argument("--striking", action="store_true")
    sh.set_defaults(func=cmd_show)

    tp = sp.add_parser("top")
    tp.add_argument("--limit", type=int, default=20)
    tp.set_defaults(func=cmd_top)

    rt = sp.add_parser("rate")
    rt.set_defaults(func=cmd_rate)

    rs = sp.add_parser("reset")
    rs.add_argument("--version", required=True)
    rs.set_defaults(func=cmd_reset)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
