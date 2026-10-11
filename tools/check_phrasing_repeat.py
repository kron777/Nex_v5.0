#!/usr/bin/env python3
"""check_phrasing_repeat.py — READ-ONLY measure of the PHRASING groove.

The grooving that survives every retrieval/readiness lever is phrasing-level: a
template opener frame ("this item is about ...", "this item reminds me ...")
applied across varied content and branches (s=0.878 branch switching, yet the
opener repeats). This reports that, winner-blind and content-independent:

  * opener_repeat   — fraction of substantive fires whose first-N-word opener is
                      shared by >= 1 other fire in the window (the template-frame rate).
  * opener_hhi      — concentration of openers (low HHI + high repeat = a STRUCTURAL
                      frame over varied content, which is the groove's signature).
  * consec_jaccard  — fraction of consecutive fires whose first-sentence 5-gram
                      Jaccard >= 0.5 (genuine adjacent phrasing repeats; it bursts).
  * is_template     — stakes_monitor._is_template per-fire rate (the narrow 46-regex
                      phrasing-decay detector, for cross-reference).

READ-ONLY: opens dynamic DB mode=ro; writes nothing (except --freeze -> a JSON
baseline file). House style of check_cadence/check_template_repetition.
Usage:
  python3 tools/check_phrasing_repeat.py [--window N] [--days D]
  python3 tools/check_phrasing_repeat.py --freeze observation_reports/r83_baselines/phrasing.json
  python3 tools/check_phrasing_repeat.py --baseline observation_reports/r83_baselines/phrasing.json
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sqlite3
import statistics as st
import sys
import time

sys.path.insert(0, __file__.rsplit("/tools/", 1)[0])

from substrate.paths import db_paths  # noqa: E402
from theory_x.stage_tom import stakes_monitor as sm  # noqa: E402

_OPENER_WORDS = 8
_JACCARD_K = 5
_JACCARD_HIT = 0.5


def _tok(text: str) -> list:
    return re.findall(r"[a-z']+", (text or "").lower())


def _opener(t: str) -> str:
    return " ".join(_tok(t)[:_OPENER_WORDS])


def _first_sentence_grams(t: str, k: int = _JACCARD_K) -> set:
    s = re.split(r"[.!?]", t or "")[0]
    w = _tok(s)
    return {tuple(w[i:i + k]) for i in range(max(0, len(w) - k + 1))}


def measure(window: int = 2000, days: float | None = None) -> dict:
    db = str(db_paths()["dynamic"])
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5)
    try:
        if days is not None:
            rows = con.execute(
                "SELECT thought FROM fountain_events WHERE ts > ? AND thought IS NOT NULL "
                "ORDER BY ts DESC", (time.time() - days * 86400,)).fetchall()
        else:
            rows = con.execute(
                "SELECT thought FROM fountain_events WHERE thought IS NOT NULL "
                "ORDER BY ts DESC LIMIT ?", (window,)).fetchall()
    finally:
        con.close()
    subst = [r[0] for r in rows
             if r[0] and len(r[0].split()) >= sm._MIN_WORDS and not r[0].startswith("[")]
    subst.reverse()  # chronological, for the consecutive measure
    n = len(subst)
    if n < 10:
        return {"n": n, "error": "insufficient substantive fires"}

    openers = [_opener(t) for t in subst]
    oc = collections.Counter(openers)
    repeat = sum(c for c in oc.values() if c >= 2) / n
    hhi = sum((c / n) ** 2 for c in oc.values())

    grams = [_first_sentence_grams(t) for t in subst]
    sims = []
    for i in range(1, n):
        a, b = grams[i], grams[i - 1]
        if a and b:
            sims.append(len(a & b) / len(a | b))
    consec = (sum(1 for s in sims if s >= _JACCARD_HIT) / len(sims)) if sims else 0.0

    tmpl = sum(1 for t in subst if sm._is_template(t)) / n

    return {
        "n": n,
        "opener_repeat": round(repeat, 4),
        "opener_distinct": len(oc),
        "opener_hhi": round(hhi, 5),
        "consec_jaccard_ge_0.5": round(consec, 4),
        "is_template_rate": round(tmpl, 4),
        "top_openers": oc.most_common(5),
    }


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=2000)
    ap.add_argument("--days", type=float, default=None)
    ap.add_argument("--freeze", metavar="PATH")
    ap.add_argument("--baseline", metavar="PATH")
    args = ap.parse_args(argv[1:])

    m = measure(window=args.window, days=args.days)
    print("=" * 68)
    print(f"PHRASING-REPEAT  {time.strftime('%Y-%m-%d %H:%M:%S')}  (n={m.get('n')})")
    print("=" * 68)
    if "error" in m:
        print("  " + m["error"]); return 1
    print(f"  opener_repeat (8-word opener shared)   : {m['opener_repeat']:.3f}  "
          f"(distinct {m['opener_distinct']}, HHI {m['opener_hhi']})")
    print(f"  consec first-sentence 5-gram J>=0.5    : {m['consec_jaccard_ge_0.5']:.3f}")
    print(f"  _is_template per-fire rate             : {m['is_template_rate']:.3f}")
    print("  top openers:")
    for o, c in m["top_openers"]:
        print(f"    {c:>4}  {o[:64]}")

    if args.freeze:
        import os
        os.makedirs(os.path.dirname(args.freeze) or ".", exist_ok=True)
        with open(args.freeze, "w") as f:
            json.dump({**m, "frozen_at": time.strftime("%Y-%m-%d")}, f, indent=2)
        print(f"\n  frozen -> {args.freeze}")
    if args.baseline:
        with open(args.baseline) as f:
            base = json.load(f)
        print("\n  vs baseline (frozen {}):".format(base.get("frozen_at", "?")))
        for key in ("opener_repeat", "consec_jaccard_ge_0.5", "is_template_rate"):
            b, c = base.get(key), m.get(key)
            if b is not None:
                print(f"    {key:<28}: {c:.3f}  (baseline {b:.3f}, delta {c - b:+.3f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
