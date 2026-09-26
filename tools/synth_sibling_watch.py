#!/usr/bin/env python3
"""READ-ONLY live watch for NEX5_SYNTH_FRESH_SIBLING (armed ac26611,
2026-09-26 22:43 SAST). Reads synergizer_log since the arm and reports:
chain generation g of each pick's fresh side (as of the pick), fresh-side
source mix + age, token concentration of the new syntheses vs the pre-arm
window, picks/day vs the 7 days before SYNTH_FRESH, and recorder health.

  .venv/bin/python3 tools/synth_sibling_watch.py [--since EPOCH]
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import statistics as st
import subprocess
import sys
import time
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from theory_x.stage3_world_model.synergizer import BeliefSynergizer as _BS  # noqa: E402

SIB_ARM = 1790455403        # 2026-09-26 22:43:23 SAST, ac26611
FRESH_ARM = 1790450100      # 2026-09-26 21:15 SAST, 0df1e16 (SYNTH_FRESH only until SIB_ARM)
D = 86400.0


def _ro(name):
    c = sqlite3.connect(f"file:{os.path.join(ROOT, 'data', name)}?mode=ro", uri=True, timeout=10)
    c.row_factory = sqlite3.Row
    return c


def generation(db, parents, bid, ts):
    """g of belief `bid` as of `ts` — the same rule as _synth_generations."""
    lo = ts - _BS._SIB_WINDOW_S
    memo = {}

    def gen(b, depth):
        if b in memo:
            return memo[b]
        r = db.execute("SELECT source, created_at FROM beliefs WHERE id=?", (b,)).fetchone()
        if not r or r["source"] != "synergized" or not (lo <= r["created_at"] < ts):
            return 0
        g = 1
        if depth < _BS._SIB_MAX_GEN:
            g += max((gen(p, depth + 1) for p in parents.get(b, ())), default=0)
        memo[b] = g
        return g
    return gen(bid, 1)


def window(db, parents, lo, hi):
    picks = db.execute(
        "SELECT s.ts, s.belief_id_a a, s.belief_id_b b, s.result_belief_id rid, b.source, "
        "b.created_at bc FROM synergizer_log s JOIN beliefs b ON b.id = s.belief_id_b "
        "WHERE s.ts >= ? AND s.ts < ? ORDER BY s.ts", (lo, hi)).fetchall()
    return [dict(p, g=generation(db, parents, p["b"], p["ts"]), age_d=(p["ts"] - p["bc"]) / D)
            for p in picks]


def summarise(name, picks, span_d):
    if not picks:
        print(f"{name}: no picks"); return
    n = len(picks)
    ages = sorted(p["age_d"] for p in picks)
    p90 = ages[min(n - 1, int(0.9 * n))]
    src = Counter(p["source"] for p in picks)
    own = sum(p["source"] == "synergized" and p["age_d"] < 2 for p in picks)
    print(f"{name}: n={n} ({n / span_d:.1f}/day over {span_d:.2f}d)")
    print(f"   chain g>=2 {sum(p['g'] >= 2 for p in picks) / n:.0%}  g>=3 {sum(p['g'] >= 3 for p in picks) / n:.0%}"
          f"  max g {max(p['g'] for p in picks)}   g dist {dict(sorted(Counter(p['g'] for p in picks).items()))}")
    print(f"   fresh source {dict(src.most_common())}; own <48h synthesis {own / n:.0%}")
    print(f"   fresh age median {st.median(ages):.2f}d  p90 {p90:.2f}d  (pre-arm 7d: 49.2d / 124.8d)")


def tokens(db, lo, hi, label):
    from theory_x.stage6_fountain.corpus_convergence import load_register_exclusion
    from theory_x.stage6_fountain.crystallizer import _fidelity_tokens
    ex = set(load_register_exclusion()["terms"])
    docs = [r[0] for r in db.execute(
        "SELECT content FROM beliefs WHERE source='synergized' AND created_at >= ? AND created_at < ?",
        (lo, hi))]
    if not docs:
        print(f"{label}: no syntheses"); return docs
    df = Counter()
    for d in docs:
        df.update({t for t in _fidelity_tokens(d or "") if t not in ex})
    top = df.most_common(8)
    theme = sum(1 for d in docs if any(k in (d or "").lower() for k in ("zen", "not knowing", "not-knowing",
                                                                           "don't know", "dont know")))
    print(f"{label}: n={len(docs)} maxDF {top[0][1] / len(docs):.0%} ('{top[0][0]}'); "
          f"'zen/not-knowing' theme {theme / len(docs):.0%}; top {[(t, round(c / len(docs), 2)) for t, c in top]}")
    return docs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=float, default=SIB_ARM)
    ap.add_argument("--show", type=int, default=8, help="print the last N synthesis texts")
    a = ap.parse_args()
    now = time.time()
    db = _ro("beliefs.db")
    parents = {}
    for r in db.execute("SELECT child_id, parent_id FROM belief_lineage"):
        parents.setdefault(r["child_id"], set()).add(r["parent_id"])

    print(f"now {time.strftime('%F %T', time.localtime(now))}; window since "
          f"{time.strftime('%F %T', time.localtime(a.since))} = {(now - a.since) / 3600:.1f}h")
    try:
        boots = subprocess.run(["journalctl", "--list-boots", "--no-pager", "-q"], capture_output=True,
                               text=True, timeout=10).stdout.strip().splitlines()
        since_boots = [b for b in boots if b.split()[3:5] and
                       time.mktime(time.strptime(" ".join(b.split()[3:5]), "%Y-%m-%d %H:%M:%S")) > a.since]
        print(f"boots since window start: {len(since_boots)} (0 = clean uptime)")
    except Exception as e:
        print(f"boot check skipped: {e}")

    pre7 = db.execute("SELECT COUNT(*) FROM synergizer_log WHERE ts BETWEEN ? AND ?",
                      (FRESH_ARM - 7 * D, FRESH_ARM)).fetchone()[0]
    print(f"baseline volume: {pre7 / 7:.1f} picks/day (7d before SYNTH_FRESH)\n")
    summarise("SYNTH_FRESH only (pre-SIBLING soak)", window(db, parents, FRESH_ARM, SIB_ARM),
              (SIB_ARM - FRESH_ARM) / D)
    post = window(db, parents, a.since, now + 1)
    summarise("SYNTH_FRESH + SIBLING (since arm)", post, (now - a.since) / D)
    print()
    tokens(db, FRESH_ARM - 7 * D, FRESH_ARM, "syntheses 7d pre-SYNTH_FRESH")
    tokens(db, FRESH_ARM, SIB_ARM, "syntheses SYNTH_FRESH-only soak")
    docs = tokens(db, a.since, now + 1, "syntheses since SIBLING arm")
    for d in docs[-a.show:]:
        print("    >", (d or "")[:150])

    dyn = _ro("dynamic.db")
    mx, last = dyn.execute("SELECT MAX(id), MAX(ts) FROM fountain_retrieval_log").fetchone()
    surv = db.execute("SELECT COUNT(*), MAX(ts) FROM belief_survival").fetchone()
    used = db.execute("SELECT COUNT(*), MAX(updated_at) FROM belief_use_days").fetchone()
    fmt = lambda t: time.strftime('%F %T', time.localtime(t)) if t else "-"  # noqa: E731
    print(f"\nrecorders: fountain_retrieval_log max(id)={mx} last {fmt(last)}; "
          f"belief_survival {surv[0]} rows last {fmt(surv[1])}; belief_use_days {used[0]} rows last {fmt(used[1])}")


if __name__ == "__main__":
    main()
