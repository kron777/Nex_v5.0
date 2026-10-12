#!/usr/bin/env python3
"""check_belief_headroom.py — READ-ONLY E4 HEADROOM pre-screen for the belief_boost content lever.

The only reorder-free way a sense/surprise-derived signal could reach the fountain's fetched CONTENT
is the belief pool: the fetch (_retrieve_context_beliefs) orders own-content beliefs by EFFECTIVE
RECENCY and takes the top own_n, where

    eff = created_at + (boost_value - 1.0) * BOOST_TIME_BONUS_SECONDS     (3.5 days)

so a boost makes a belief look up to (max_grade * 3.5) days newer. Boost REPLACES (ON CONFLICT UPDATE),
it does not stack, so a belief's MAX reachable recency is created_at + max_grade*3.5d, regardless of any
current boost. Empirical max grade ~0.42 => ~1.47 days of lift.

HEADROOM (the binding E4 predicate, the saturated-readiness analogue): can a within-range boost actually
change WHICH beliefs are fetched? If the time gap at the fetch cutoff exceeds the max lift, no boost can
promote a below-cutoff belief across it — the lever is decision-INERT by construction, exactly like the
readiness gate saturated at fire. If several below-cutoff beliefs sit within the lift, a boost genuinely
swaps content in — the lever is live, and worth designing.

Two reads, because the lever's PURPOSE is sense->content, not any content:
  - GENERIC headroom: of all own-content beliefs below the cutoff, how many a max boost could promote.
  - SENSE headroom: the same restricted to precipitated_from_sense beliefs (a distinct `source`, so the
    pool is not blended) — if zero sense beliefs are promotable, the sense->content path is inert even
    when generic headroom exists.

READ-ONLY: opens beliefs DB mode=ro; writes nothing. ANALOGUE. No flag, no fire-path change.
Usage:
  python3 tools/check_belief_headroom.py [--own-n 12] [--max-grade 0.42] [--days D]
"""
from __future__ import annotations

import argparse
import collections
import sqlite3
import sys
import time

sys.path.insert(0, __file__.rsplit("/tools/", 1)[0])

from substrate.paths import db_paths  # noqa: E402
from theory_x.diversity.boost import BOOST_TIME_BONUS_SECONDS  # noqa: E402

# Mirror of generator._OWN_CONTENT_SOURCES (kept local so the tool stays light; a test asserts it
# matches the generator's tuple so drift is caught).
_OWN_CONTENT_SOURCES = (
    "fountain_insight", "synergized", "precipitated_from_dynamic",
    "precipitated_from_sense", "behavioural_observation", "auto_probe",
)
_SENSE_SOURCE = "precipitated_from_sense"
_DAY = 86400.0


def _fetch_pool(db: str, days: float | None) -> list:
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5)
    except sqlite3.OperationalError:
        return []                                   # beliefs.db absent / unreadable -> empty pool
    try:
        ph = ",".join("?" * len(_OWN_CONTENT_SOURCES))
        q = (f"SELECT b.source, b.created_at, COALESCE(bb.boost_value, 1.0) AS bv "
             f"FROM beliefs b LEFT JOIN belief_boost bb ON b.id = bb.belief_id "
             f"WHERE b.source IN ({ph}) AND b.tier < 8")
        args = list(_OWN_CONTENT_SOURCES)
        if days is not None:
            q += " AND b.created_at > ?"
            args.append(time.time() - days * _DAY)
        rows = con.execute(q, args).fetchall()
    except sqlite3.OperationalError:
        return []                                   # schema missing (no beliefs table yet)
    finally:
        con.close()
    return [{"source": s, "created_at": float(ca), "bv": float(bv)} for s, ca, bv in rows
            if ca is not None]


def measure(db: str, own_n: int = 12, max_grade: float = 0.42, days: float | None = None) -> dict:
    pool = _fetch_pool(db, days)
    n = len(pool)
    if n < own_n + 1:
        return {"n": n, "error": f"pool too small for own_n={own_n} (need > {own_n}); "
                                 f"is beliefs.db populated? {db}"}
    now = time.time()
    max_bonus = max_grade * BOOST_TIME_BONUS_SECONDS
    for b in pool:
        b["eff"] = b["created_at"] + (b["bv"] - 1.0) * BOOST_TIME_BONUS_SECONDS
    pool.sort(key=lambda b: b["eff"], reverse=True)
    cutoff_eff = pool[own_n - 1]["eff"]          # the N-th (last admitted) belief's effective recency
    below = pool[own_n:]                         # everything the fetch currently drops

    def _promotable(bs):
        # boost REPLACES, so max reachable eff = created_at + max_bonus; promotable iff that clears cutoff
        return [b for b in bs if (b["created_at"] + max_bonus) > cutoff_eff]

    prom = _promotable(below)
    sense_below = [b for b in below if b["source"] == _SENSE_SOURCE]
    sense_prom = _promotable(sense_below)
    sense_in_fetch = sum(1 for b in pool[:own_n] if b["source"] == _SENSE_SOURCE)
    # grade the single most-recent below-cutoff belief would need (0 if already promotable at grade 0)
    top_below = below[0]
    grade_marginal = max(0.0, (cutoff_eff - top_below["created_at"]) / BOOST_TIME_BONUS_SECONDS)
    # recency spread of the swap zone (beliefs whose created_at is within max_bonus of the cutoff)
    swap_zone = [b for b in pool if abs(b["created_at"] - cutoff_eff) < max_bonus]

    src_pool = collections.Counter(b["source"] for b in pool)
    return {
        "n": n,
        "own_n": own_n,
        "max_grade": max_grade,
        "max_bonus_days": round(max_bonus / _DAY, 3),
        "cutoff_age_days": round((now - cutoff_eff) / _DAY, 3),
        "grade_to_promote_marginal": round(grade_marginal, 3),   # vs max_grade
        "promotable_count": len(prom),                           # below-cutoff beliefs a max boost lifts in
        "swap_zone_count": len(swap_zone),                       # density of the realistic swap window
        "sense": {
            "in_pool": src_pool.get(_SENSE_SOURCE, 0),
            "in_fetch": sense_in_fetch,
            "below_cutoff": len(sense_below),
            "promotable": len(sense_prom),
        },
        "source_distribution": dict(src_pool.most_common()),
    }


def _verdict(m: dict) -> str:
    pc, mg, gm = m["promotable_count"], m["max_grade"], m["grade_to_promote_marginal"]
    sense = m["sense"]
    if pc == 0 or gm > mg:
        g = (f"HEADROOM ABSENT (no below-cutoff belief is promotable within max grade {mg}; the marginal "
             f"belief needs grade {gm} > {mg}). A boost cannot change the fetched set — belief_boost is "
             f"decision-INERT here, the saturated-gate analogue. DO NOT build the lever.")
    elif pc < 3:
        g = (f"HEADROOM THIN (only {pc} below-cutoff belief(s) promotable; the lever could swap very "
             f"little in). Design with caution — re-measure before arming.")
    else:
        g = (f"HEADROOM PRESENT ({pc} below-cutoff beliefs promotable within grade {mg}; a boost genuinely "
             f"re-orders the fetch). The lever has range; proceed to design.")
    # sense-specific gate: even with generic headroom, the sense->content PURPOSE needs sense material
    if sense["in_pool"] == 0:
        g += " | SENSE PATH DEAD: no precipitated_from_sense beliefs in the pool to boost."
    elif sense["promotable"] == 0 and sense["in_fetch"] == 0:
        g += (" | SENSE PATH INERT: sense beliefs exist but none are in the fetch or promotable — a "
              "sense-driven boost could not surface them.")
    return g


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--own-n", type=int, default=12, help="fetch own-slot size (modes.py default 12)")
    ap.add_argument("--max-grade", type=float, default=0.42, help="max boost grade (empirical ~0.42)")
    ap.add_argument("--days", type=float, default=None, help="restrict pool to beliefs newer than D days")
    ap.add_argument("--db", default=None)
    args = ap.parse_args(argv[1:])

    db = args.db or str(db_paths()["beliefs"])
    m = measure(db, own_n=args.own_n, max_grade=args.max_grade, days=args.days)
    print("=" * 72)
    print(f"BELIEF-HEADROOM  {time.strftime('%Y-%m-%d %H:%M:%S')}  (own-content pool n={m.get('n')})")
    print("=" * 72)
    if "error" in m:
        print("  " + m["error"])
        return 1
    s = m["sense"]
    print(f"  own_n / max_grade        : {m['own_n']} / {m['max_grade']}  "
          f"(max boost lift {m['max_bonus_days']} days)")
    print(f"  fetch cutoff age         : {m['cutoff_age_days']} days")
    print(f"  grade to promote marginal: {m['grade_to_promote_marginal']}  (vs max {m['max_grade']})")
    print(f"  promotable below cutoff  : {m['promotable_count']}   swap-zone density {m['swap_zone_count']}")
    print(f"  sense (precip_from_sense): in-pool {s['in_pool']}  in-fetch {s['in_fetch']}  "
          f"below {s['below_cutoff']}  promotable {s['promotable']}")
    print(f"  source distribution      : {m['source_distribution']}")
    print(f"  VERDICT                  : {_verdict(m)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
