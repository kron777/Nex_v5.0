#!/usr/bin/env python3
"""check_tripwires.py — READ-ONLY trustworthy read of the two revert tripwires.

Why this exists: both gauges were being MIS-READ, not miscalibrated.
  * on-subject: the real instrument is subject_fidelity.p_on_subject (binary,
    ">=1 shared content token", frozen baseline EXPLAIN=0.6427 / overall 0.529),
    NOT the mean token_recall (~0.51) that was mistakenly compared to 0.65. Read
    the right metric and the "regression" disappears.
  * maxDF*: a single number ("30% driven by 'understanding'") cannot tell a
    reader whether that is a genuine single-story collapse or NEX's standing
    register vocabulary. R73's discriminator is burst ratio (max/median daily DF)
    + branch-distribution entropy: a real attractor SPIKES and CONCENTRATES in
    few branches (societal 08-21: burst 22.7, entropy 0.808); standing register
    is FLAT and branch-spread. This prints that context next to the driver so a
    breach can be judged, without touching the alarm's own logic.

    CAVEAT (measured 2026-09-12): with the known attractors DECAYED, burst+entropy
    no longer separate them from register in the live window (advancements 11.4%
    DF / burst 1.94 / entropy 0.610 is indistinguishable from register foundation
    11.4% / 1.71 / 0.619). So the context is an aid to judgement, not an automatic
    verdict — see the maxDF* recalibration STOP note in the session report.

READ-ONLY: opens beliefs/dynamic DBs mode=ro; writes nothing.
Usage:  .venv/bin/python3 tools/check_tripwires.py [FIDELITY_WINDOW]  (default 400)
"""
from __future__ import annotations

import collections
import datetime as dt
import math
import sqlite3
import sys
import time

sys.path.insert(0, __file__.rsplit("/tools/", 1)[0])

from theory_x.stage6_fountain.crystallizer import _fidelity_tokens
from theory_x.stage6_fountain import corpus_convergence as cc
from theory_x.stage6_fountain import subject_fidelity as sf

_BELIEFS = "/home/rr/Desktop/Desktop/nex5/data/beliefs.db"


def _driver_context(token: str, window_days: int = 30) -> dict:
    """Burst ratio (max/median daily DF share) + normalized branch entropy for a
    token over the recent crystallized corpus. R73's attractor discriminator."""
    cut = time.time() - window_days * 86400
    con = sqlite3.connect(f"file:{_BELIEFS}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT content, created_at, branch_id FROM beliefs "
            "WHERE source='fountain_insight' AND content IS NOT NULL AND created_at>?",
            (cut,),
        ).fetchall()
    finally:
        con.close()
    byday = collections.Counter()
    daytot = collections.Counter()
    bybranch = collections.Counter()
    for content, ts, br in rows:
        day = dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%m-%d")
        daytot[day] += 1
        if token in set(_fidelity_tokens(content)):
            byday[day] += 1
            bybranch[br or "?"] += 1
    shares = [byday[d] / daytot[d] for d in daytot if daytot[d] >= 5 and byday[d] > 0]
    if not shares:
        return {"burst": None, "branch_entropy": None, "n_branches": 0}
    shares.sort()
    med = shares[len(shares) // 2]
    burst = (max(shares) / med) if med > 0 else None
    tot = sum(bybranch.values())
    ent = -sum((v / tot) * math.log(v / tot) for v in bybranch.values()) if tot else 0.0
    maxent = math.log(len(bybranch)) if len(bybranch) > 1 else 1.0
    return {"burst": burst, "branch_entropy": (ent / maxent) if maxent > 0 else 0.0,
            "n_branches": len(bybranch)}


def main(argv):
    win = int(argv[1]) if len(argv) > 1 else 400
    print("=" * 68)
    print(f"TRIPWIRE CHECK  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 68)

    # --- maxDF* ---
    r = cc.max_df_star()
    tok = r.get("token")
    ctx = _driver_context(tok) if tok else {}
    breach = r.get("breach")
    print("maxDF*  (revert tripwire: breach >= 25%)")
    print(f"  reading : {r['max_df_star']*100:.1f}%  driven by '{tok}' "
          f"({r.get('doc_count')}/{r.get('n')})  {'** BREACH **' if breach else 'ok'}")
    if ctx.get("burst") is not None:
        # heuristic read only — see CAVEAT in the module docstring
        looks = ("attractor-like (bursty/concentrated)"
                 if (ctx["burst"] and ctx["burst"] >= 4.0 and ctx["branch_entropy"] < 0.55)
                 else "register-like (flat/branch-spread) — likely a false positive")
        print(f"  driver context: burst={ctx['burst']:.2f}  "
              f"branch_entropy={ctx['branch_entropy']:.3f}  "
              f"branches={ctx['n_branches']}  -> {looks}")
    print(f"  runners-up: " + ", ".join(f"{t} {s*100:.0f}%" for t, _c, s in r["top"][1:]))

    # --- on-subject (the REAL instrument) ---
    f = sf.subject_fidelity(window=win)
    bm = f.get("by_mode", {})
    print()
    print("on-subject p_on_subject  (>=1 shared content token; NOT mean token_recall)")
    print(f"  overall : {f['p_on_subject']:.3f}  (baseline {sf.BASELINE['p_on_subject']:.3f})  n={f['n']}")
    for m in ("EXPLAIN", "ARGUE"):
        if m in bm:
            base = sf.BASELINE["by_mode"][m]["p_on_subject"]
            trip = " ** UNDER 0.65 (EXPLAIN revert tripwire) **" if (m == "EXPLAIN" and bm[m]["p_on_subject"] < 0.65) else ""
            print(f"  {m:<8}: {bm[m]['p_on_subject']:.3f}  (baseline {base:.3f}){trip}")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
