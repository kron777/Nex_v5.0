"""Subject fidelity: does a fire actually engage the item it was given?

Round 33 found that ~half of all item-bearing fires reference nothing from
their focal item. That sits UPSTREAM of every feedback carrier chased in
rounds 29-32 (the exemplar block, the momentum carry, the narrative's recent
fires, the sense/seed blocks): a fire with no grip on its assigned subject
falls back on whatever opening is most available, and for the last two weeks
that has been a confabulated preamble.

This module is READ-ONLY INSTRUMENTATION, in the shape of
corpus_convergence.py. It gates nothing, it is imported by nothing on the
fire path, and shipping it requires no restart. Round 34 ships the metric
deliberately WITHOUT the reject-or-regenerate gate: the gate could suppress
up to ~47% of fires and starve the crystallizer, so it waits on a baseline.

TWO READINGS, and they are not interchangeable:

  on_subject  -- binary, ">= 1 shared content token". This is exactly the
                 predicate crystallizer._is_on_subject already applies on the
                 fire path to choose the 600-char vs 300-char ceiling (round
                 29). Reported here so the metric is commensurable with the
                 gate that already exists.

  recall      -- continuous, |focal tokens present in fire| / |focal tokens|.
                 Strictly more informative: a fire can share one incidental
                 token and still be about something else entirely. The 20%
                 threshold is the round-33 reporting convention, not a gate.

Tokenizer is crystallizer._fidelity_tokens, the house standard
(GENIUS_FIDELITY_BASELINE.md section 1), so readings here are comparable with
maxDF* and with the R29 ceiling. Fires with no focal_item (DRIFT, substrate
voice) bind no subject by design and are EXCLUDED from the denominator --
counting them would make the metric a measure of mode mix, not of fidelity.
"""
from __future__ import annotations

import math
import sqlite3
from typing import Optional

from theory_x.stage6_fountain.crystallizer import _fidelity_tokens

_DEFAULT_DB = "/home/rr/Desktop/Desktop/nex5/data/dynamic.db"

# Rolling window, in fires, matched to corpus_convergence.WINDOW so the two
# instruments describe comparable stretches of history.
WINDOW = 200

# Reporting convention from round 33, NOT a gate.
RECALL_THRESHOLD = 0.20

# FROZEN BASELINE -- see observation_reports/r34.md section 3.
#
# Window is the 7 days ENDING AT THE R32 RESTART (2026-07-31T16:10:54Z ->
# 2026-08-07T16:10:54Z), deliberately not "the last 7 days": it must not
# contain R32, so that R32 and any later fidelity intervention are both
# measured against ground that predates them. Fitted data -- refit ONLY on a
# window with no active intervention in it, and say so when you do.
#
# ---------------------------------------------------------------------------
# READ THIS BEFORE COMPARING ANYTHING AGAINST IT. THE SERIES IS NOT
# STATIONARY. Day-by-day on-subject over the four days into the R32 restart:
#
#     T-4d..T-3d   n=291   0.454  [0.397, 0.511]
#     T-3d..T-2d   n=325   0.523  [0.469, 0.577]
#     T-2d..T-1d   n=306   0.588  [0.532, 0.642]
#     T-1d..T      n=312   0.567  [0.512, 0.621]
#     T..T+1d      n=155   0.639  [0.561, 0.710]   <- post-R32
#
# The metric was already climbing ~4 points/day before any round-34 work, from
# a cause not yet identified. The post-R32 reading continues that trend and its
# CI overlaps the adjacent pre-restart day heavily; R32 CANNOT be credited with
# it. A single-point comparison against the pooled 7-day figure below WILL
# manufacture a false positive, because the pool averages in the low early
# days. Judge an intervention against the ADJACENT pre-window, or against a
# fitted trend -- never against this pooled number alone.
# ---------------------------------------------------------------------------
BASELINE = {
    "fitted_on": "2026-08-08",
    "fitted_by": "round 34",
    "window_utc": ["2026-07-31T16:10:54Z", "2026-08-07T16:10:54Z"],
    "window_days": 7,
    "n": 1586,
    "mean_recall": 0.3612,
    "p_on_subject": 0.5290,        # 95% CI [0.5044, 0.5535]
    "p_on_subject_ci": [0.5044, 0.5535],
    "p_recall_ge_20": 0.4874,      # 95% CI [0.4628, 0.5120]
    "p_recall_ge_20_ci": [0.4628, 0.5120],
    "p_zero": 0.4710,              # 95% CI [0.4465, 0.4956]
    "p_zero_ci": [0.4465, 0.4956],
    "by_mode": {
        "ARGUE":   {"n": 794, "p_on_subject": 0.4156, "p_recall_ge_20": 0.3652,
                    "mean_recall": 0.2461},
        "EXPLAIN": {"n": 792, "p_on_subject": 0.6427, "p_recall_ge_20": 0.6098,
                    "mean_recall": 0.4765},
    },
}


def _wilson(k: int, n: int, z: float = 1.96) -> tuple:
    """Wilson score interval. Normal-approximation CIs are unusable in the
    tails here (post-intervention windows run n<50 and rates near 0)."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - m) / d), min(1.0, (c + m) / d))


def token_recall(fire: Optional[str], focal_item: Optional[str]) -> Optional[float]:
    """Share of the focal item's distinct content tokens present in the fire.

    Returns None -- not 0.0 -- when there is no subject to be faithful to, so
    callers cannot silently average unanswerable cases into the rate.
    """
    if not fire or not focal_item:
        return None
    focal = list(dict.fromkeys(_fidelity_tokens(focal_item)))
    if not focal:
        return None
    body = set(_fidelity_tokens(fire))
    return sum(1 for t in focal if t in body) / len(focal)


def recent_fires(db_path: str = _DEFAULT_DB, window: int = WINDOW,
                 days: Optional[float] = None) -> list:
    """The most recent item-bearing fires, oldest first.

    `days` overrides `window` for a wall-clock window instead of a fire count.
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10)
    try:
        if days is not None:
            import time
            rows = conn.execute(
                "SELECT ts, mode, thought, focal_item FROM fountain_events "
                "WHERE thought IS NOT NULL AND focal_item IS NOT NULL "
                "AND ts > ? ORDER BY ts",
                (time.time() - days * 86400,),
            ).fetchall()
            return list(rows)
        rows = conn.execute(
            "SELECT ts, mode, thought, focal_item FROM fountain_events "
            "WHERE thought IS NOT NULL AND focal_item IS NOT NULL "
            "ORDER BY ts DESC LIMIT ?",
            (window,),
        ).fetchall()
    finally:
        conn.close()
    return list(reversed(rows))


def subject_fidelity(fires: Optional[list] = None, db_path: str = _DEFAULT_DB,
                     window: int = WINDOW, days: Optional[float] = None) -> dict:
    """Compute the reading over `fires` (default: the live rolling window).

    `fires` may be rows of (ts, mode, thought, focal_item) so a caller
    replaying history can pass DB rows straight through.
    """
    if fires is None:
        fires = recent_fires(db_path, window, days)

    recalls = []
    modes: dict = {}
    for r in fires:
        mode, thought, focal = r[-3], r[-2], r[-1]
        v = token_recall(thought, focal)
        if v is None:
            continue
        recalls.append(v)
        m = modes.setdefault(str(mode), [])
        m.append(v)

    n = len(recalls)
    if n == 0:
        return {"n": 0, "mean_recall": None, "p_on_subject": None,
                "p_recall_ge_20": None, "p_zero": None, "by_mode": {},
                "baseline": BASELINE}

    k_on = sum(1 for v in recalls if v > 0)
    k_ge = sum(1 for v in recalls if v >= RECALL_THRESHOLD)
    k_zero = n - k_on

    by_mode = {}
    for m, vs in sorted(modes.items(), key=lambda kv: -len(kv[1])):
        by_mode[m] = {
            "n": len(vs),
            "mean_recall": sum(vs) / len(vs),
            "p_on_subject": sum(1 for v in vs if v > 0) / len(vs),
            "p_recall_ge_20": sum(1 for v in vs if v >= RECALL_THRESHOLD) / len(vs),
        }

    return {
        "n": n,
        "mean_recall": sum(recalls) / n,
        "p_on_subject": k_on / n,
        "p_on_subject_ci": _wilson(k_on, n),
        "p_recall_ge_20": k_ge / n,
        "p_recall_ge_20_ci": _wilson(k_ge, n),
        "p_zero": k_zero / n,
        "p_zero_ci": _wilson(k_zero, n),
        "by_mode": by_mode,
        "baseline": BASELINE,
    }


def _main(argv: list) -> int:
    import argparse
    import time

    ap = argparse.ArgumentParser(description="subject-fidelity reading")
    ap.add_argument("--window", type=int, default=WINDOW)
    ap.add_argument("--days", type=float, default=None,
                    help="use a wall-clock window instead of a fire count")
    ap.add_argument("--db", default=_DEFAULT_DB)
    ap.add_argument("--since", type=float, default=None,
                    help="only fires with ts > this epoch (e.g. a restart)")
    ap.add_argument("--history", type=int, default=0,
                    help="also print the last N rolling readings")
    args = ap.parse_args(argv)

    fires = recent_fires(args.db, args.window, args.days)
    if args.since is not None:
        fires = [f for f in fires if f[0] > args.since]
    r = subject_fidelity(fires=fires)

    span = f"{args.days}d" if args.days else f"{r['n']} fires"
    print(f"subject fidelity  window={span}  (item-bearing fires only)")
    if not r["n"]:
        print("  no data")
        return 0
    b = r["baseline"]
    print(f"baseline: fitted {b['fitted_on']} on n={b['n']} over "
          f"{b['window_days']}d, pre-intervention")
    print(f"  n = {r['n']}")
    print(f"  mean token recall of focal item : {r['mean_recall']:.3f}"
          f"   (baseline {b['mean_recall']:.3f})")
    lo, hi = r["p_on_subject_ci"]
    print(f"  P(on-subject, >=1 token)        : {r['p_on_subject']:.3f}"
          f"  [{lo:.3f}, {hi:.3f}]   (baseline {b['p_on_subject']:.3f})")
    lo, hi = r["p_recall_ge_20_ci"]
    print(f"  P(recall >= {RECALL_THRESHOLD:.0%})                : "
          f"{r['p_recall_ge_20']:.3f}  [{lo:.3f}, {hi:.3f}]"
          f"   (baseline {b['p_recall_ge_20']:.3f})")
    lo, hi = r["p_zero_ci"]
    print(f"  P(ZERO overlap with its item)   : {r['p_zero']:.3f}"
          f"  [{lo:.3f}, {hi:.3f}]   (baseline {b['p_zero']:.3f})")
    print("\n  by mode:")
    for m, d in r["by_mode"].items():
        print(f"    {m:<10} n={d['n']:<5} on-subject={d['p_on_subject']:.3f}"
              f"  recall>=20%={d['p_recall_ge_20']:.3f}"
              f"  mean={d['mean_recall']:.3f}")

    if args.history > 0:
        conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True, timeout=10)
        try:
            rows = conn.execute(
                "SELECT ts, mode, thought, focal_item FROM fountain_events "
                "WHERE thought IS NOT NULL AND focal_item IS NOT NULL "
                "ORDER BY ts DESC LIMIT ?",
                (args.window + args.history,),
            ).fetchall()
        finally:
            conn.close()
        rows = list(reversed(rows))
        print(f"\nlast {args.history} rolling readings (window={args.window}):")
        for i in range(args.window, len(rows) + 1):
            h = subject_fidelity(fires=rows[i - args.window:i])
            ts = time.strftime("%m-%d %H:%M", time.gmtime(rows[i - 1][0]))
            print(f"  {ts}  on-subject {h['p_on_subject']*100:5.1f}%"
                  f"   recall>=20% {h['p_recall_ge_20']*100:5.1f}%"
                  f"   mean {h['mean_recall']:.3f}")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv[1:]))
