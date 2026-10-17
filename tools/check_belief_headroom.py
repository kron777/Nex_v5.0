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

# Mirror of generator constants (kept local so the tool stays light; a test asserts they match the
# generator so drift is caught). The fetch applies BOTH caps, in recency order, until own_n is filled.
_OWN_CONTENT_SOURCES = (
    "fountain_insight", "synergized", "precipitated_from_dynamic",
    "precipitated_from_sense", "behavioural_observation", "auto_probe",
)
_SENSE_SOURCE = "precipitated_from_sense"
_OWN_PER_SOURCE_MAX = 3
_OWN_PER_SOURCE_OVERRIDES = {"precipitated_from_sense": 5}
_PER_BRANCH_CAP = 2                 # generator uses a function-local literal; mirrored here
_DAY = 86400.0


def _source_cap(src: str) -> int:
    return _OWN_PER_SOURCE_OVERRIDES.get(src, _OWN_PER_SOURCE_MAX)


def _capped_fetch(pool: list, own_n: int) -> set:
    """Replicate the real fetch admission: iterate by effective recency desc, skipping a belief whose
    SOURCE cap (3, or 5 for sense) or BRANCH cap (2) is already full, until own_n are picked. Returns
    the set of admitted belief indices (`i`). This is what makes the pre-screen cap-aware: a belief can
    clear the rank cutoff yet be locked out because its branch/source is full."""
    picked = set()
    per_src: dict = {}
    per_br: dict = {}
    for b in sorted(pool, key=lambda x: x["eff"], reverse=True):
        src, br = b["source"], b["branch_id"]
        if per_src.get(src, 0) >= _source_cap(src):
            continue
        if br and per_br.get(br, 0) >= _PER_BRANCH_CAP:
            continue
        picked.add(b["i"])
        per_src[src] = per_src.get(src, 0) + 1
        if br:
            per_br[br] = per_br.get(br, 0) + 1
        if len(picked) >= own_n:
            break
    return picked


def _fetch_pool(db: str, days: float | None) -> list:
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5)
    except sqlite3.OperationalError:
        return []                                   # beliefs.db absent / unreadable -> empty pool
    try:
        ph = ",".join("?" * len(_OWN_CONTENT_SOURCES))
        q = (f"SELECT b.source, b.created_at, b.branch_id, COALESCE(bb.boost_value, 1.0) AS bv "
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
    return [{"i": i, "source": s, "created_at": float(ca), "branch_id": br, "bv": float(bv)}
            for i, (s, ca, br, bv) in enumerate(rows) if ca is not None]


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

    fetched = _capped_fetch(pool, own_n)                         # the REAL fetched set (both caps applied)
    fetched_beliefs = [b for b in pool if b["i"] in fetched]
    cutoff_eff = min(b["eff"] for b in fetched_beliefs)          # weakest admitted belief's eff
    below = [b for b in pool if b["i"] not in fetched]

    def _clears_cutoff(bs):          # pre-cap test: would a max boost raise eff above the rank cutoff?
        return [b for b in bs if (b["created_at"] + max_bonus) > cutoff_eff]

    def _promotable_effective(bs):   # cap-AWARE: re-run the capped fetch with b boosted; is it admitted?
        out = []
        for b in bs:
            saved = b["eff"]
            b["eff"] = b["created_at"] + max_bonus
            if b["i"] in _capped_fetch(pool, own_n):
                out.append(b)
            b["eff"] = saved
        return out

    # promotable_effective ⊆ clears (a belief that can't clear the rank cutoff can't be admitted under
    # caps either), so only re-simulate the clears set — keeps this O(clears·N), not O(below·N).
    clears = _clears_cutoff(below)
    prom_eff = _promotable_effective(clears)
    sense_below = [b for b in below if b["source"] == _SENSE_SOURCE]
    sense_clears = _clears_cutoff(sense_below)
    sense_prom_eff = _promotable_effective(sense_clears)
    sense_in_fetch = sum(1 for b in fetched_beliefs if b["source"] == _SENSE_SOURCE)

    top_below = max(below, key=lambda b: b["created_at"])
    grade_marginal = max(0.0, (cutoff_eff - top_below["created_at"]) / BOOST_TIME_BONUS_SECONDS)

    # effect-size WINDOW (Q2, a read not a gate): decay clock is static; the binding RACE clock needs the
    # live inter-fire cadence (fountain_events), so we report the pool's own-write rate as a proxy and flag it.
    span_days = max(1e-6, (now - min(b["created_at"] for b in pool)) / _DAY)
    b_val = 1.0 + max_grade
    decay_window_days = round(max(0.0, (b_val - 1.05) / 0.02), 2)   # DECAY_RATE_PER_DAY = 0.02
    src_pool = collections.Counter(b["source"] for b in pool)
    return {
        "n": n,
        "own_n": own_n,
        "max_grade": max_grade,
        "max_bonus_days": round(max_bonus / _DAY, 3),
        "cutoff_age_days": round((now - cutoff_eff) / _DAY, 3),
        "grade_to_promote_marginal": round(grade_marginal, 3),
        "promotable_clears_cutoff": len(clears),        # pre-cap (diagnostic)
        "promotable_effective": len(prom_eff),          # cap-aware (the honest generic count)
        "cap_blocked": len(clears) - len(prom_eff),     # clear the cutoff but locked out by a cap
        "sense": {
            "in_pool": src_pool.get(_SENSE_SOURCE, 0),
            "in_fetch": sense_in_fetch,
            "cap": _source_cap(_SENSE_SOURCE),
            "cap_saturated": sense_in_fetch >= _source_cap(_SENSE_SOURCE),  # => reorder-only, net adds 0
            "below_cutoff": len(sense_below),
            "promotable_clears_cutoff": len(sense_clears),
            "promotable_effective": len(sense_prom_eff),   # the GO gate (reorder pool when saturated)
            "cap_blocked": len(sense_clears) - len(sense_prom_eff),
        },
        "effect_window": {
            "decay_window_days": decay_window_days,         # not the binding clock
            "pool_own_writes_per_day": round(n / span_days, 2),
            "race_clock": "needs live fountain_events inter-fire cadence (binding; not computable offline)",
        },
        "source_distribution": dict(src_pool.most_common()),
    }


def _verdict(m: dict) -> str:
    # GO gates on the SENSE cap-aware count (the lever acts on sense beliefs). Generic promotable is a
    # substrate diagnostic, never the gate (gating on it is the readiness-gate mistake — measuring the
    # room, not the lever). in_fetch>0 is a ceiling REDUCER (less marginal room), not a GO signal.
    s = m["sense"]
    spe = s["promotable_effective"]
    if s["in_pool"] == 0:
        return ("NO-GO / SENSE PATH DEAD: no precipitated_from_sense beliefs in the pool — upstream "
                "EXPOSURE problem (fix the sense→belief precipitation, not the boost).")
    if spe == 0:
        reason = ("all sense beliefs are already in-fetch (no marginal room)" if s["below_cutoff"] == 0
                  else f"{s['cap_blocked']} clear the rank cutoff but are locked out by a source/branch cap"
                       if s["cap_blocked"] > 0 else "the cutoff gap exceeds any feasible boost")
        return (f"NO-GO / HEADROOM ABSENT for sense: 0 sense beliefs cap-aware-promotable ({reason}). "
                f"belief_boost is decision-INERT for the sense path — do NOT build.")
    strong = spe >= 3
    if s.get("cap_saturated"):
        # the sense slot is full (in_fetch == cap), so a boost cannot ADD sense — only REORDER within
        # the allocation: each promotable belief enters by EVICTING an incumbent. Relabel honestly
        # (Beam QC): headroom != deficiency; whether recency is a bad selector is a separate read.
        tag = (f"GO / REORDER HEADROOM PRESENT: {spe} sense beliefs cap-aware-promotable" if strong
               else f"THIN REORDER HEADROOM: only {spe} promotable")
        tag += (f" — sense fills its source cap ({s['in_fetch']}/{s['cap']}), so NET additions = 0: each "
                f"entrant EVICTS an incumbent sense belief. Headroom != deficiency — whether recency is a "
                f"worse selector than a boost grade (DRIVER DIVERGENCE) is UNMEASURED; arm on the Stage-A "
                f"channel-liveness/divergence read, not on this.")
    else:
        tag = (f"GO / HEADROOM PRESENT: {spe} sense beliefs cap-aware-promotable" if strong
               else f"THIN: only {spe} sense belief(s) cap-aware-promotable — design with caution")
        if s["in_fetch"] > 0:
            tag += (f" | NB sense already in-fetch ({s['in_fetch']}/{s['cap']}): a ceiling REDUCER, not "
                    f"extra headroom")
    if s["cap_blocked"] > 0:
        tag += f" | {s['cap_blocked']} sense cap-blocked (rank-clear but source/branch full)"
    return tag + f". (generic promotable_effective={m['promotable_effective']}, diagnostic only.)"


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
    s, ew = m["sense"], m["effect_window"]
    print(f"  own_n / max_grade        : {m['own_n']} / {m['max_grade']}  "
          f"(max boost lift {m['max_bonus_days']} days)  cap: source 3 / sense 5 / branch 2")
    print(f"  fetch cutoff age         : {m['cutoff_age_days']} days   "
          f"grade to promote marginal {m['grade_to_promote_marginal']} (vs max {m['max_grade']})")
    print(f"  generic promotable       : clears-cutoff {m['promotable_clears_cutoff']}  "
          f"cap-aware {m['promotable_effective']}  cap-blocked {m['cap_blocked']}   (diagnostic)")
    print(f"  SENSE (the gate)         : in-pool {s['in_pool']}  in-fetch {s['in_fetch']}  below {s['below_cutoff']}  "
          f"clears {s['promotable_clears_cutoff']}  CAP-AWARE {s['promotable_effective']}  cap-blocked {s['cap_blocked']}")
    print(f"  effect window            : decay {ew['decay_window_days']}d  "
          f"pool-writes/day {ew['pool_own_writes_per_day']}  race-clock: {ew['race_clock']}")
    print(f"  source distribution      : {m['source_distribution']}")
    print(f"  VERDICT                  : {_verdict(m)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
