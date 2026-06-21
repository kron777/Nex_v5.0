#!/usr/bin/env python3
"""
recursion_attribution.py — the proper control for the L3 teeth-test.

The original recursion_teeth_test.py admits it uses a PROXY: it segments
branch-change rate by current raga-state, not by whether the recursion nudge
ACTUALLY fired that cycle. That conflation is why the verdict came back
ambiguous (move-rate 0.469, can't attribute to recursion vs natural drift).

This sidecar logs, per fire:
    ts, nudge_active (did perturbation() return perturb=True?),
    branch_at_fire, branch_prev  -> move = (branch != branch_prev)

Then split:  P(move | nudge_active)  vs  P(move | nudge_absent)
The nudge-absent rate is the TRUE baseline (natural drift). If recursion has
teeth, P(move|active) >> P(move|absent). If they're equal, the nudge is
cosmetic and L4 stays gated.

USAGE:
    # sampler: call sample() once per fire from the fountain loop, OR run the
    # standalone watcher that polls recent fires and records nudge-state.
    .venv/bin/python3 theory_x/stage_tom/recursion_attribution.py --watch &   # gather
    .venv/bin/python3 theory_x/stage_tom/recursion_attribution.py --verdict   # read result
"""
from __future__ import annotations
import sqlite3, time, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def _db(name):
    try:
        from substrate.paths import db_paths
        return str(db_paths()[name])
    except Exception:
        return f"data/{name}.db"

def _ensure_table():
    con = sqlite3.connect(_db("dynamic"))
    con.execute("""CREATE TABLE IF NOT EXISTS recursion_attrib (
        ts REAL PRIMARY KEY, nudge_active INTEGER, branch TEXT, branch_prev TEXT, moved INTEGER)""")
    con.commit(); con.close()

def _nudge_active() -> bool:
    """Did the recursion perturbation actually fire? Source of truth: recursive_self.perturbation()."""
    try:
        from theory_x.stage_tom.recursive_self import perturbation
        return bool(perturbation().get("perturb", False))
    except Exception:
        return False

def _current_branch() -> str:
    """Hot branch right now, from fountain fires (same signal the teeth-test uses)."""
    try:
        con = sqlite3.connect(_db("dynamic")); con.row_factory = sqlite3.Row
        row = con.execute("SELECT hot_branch FROM fountain_events ORDER BY ts DESC LIMIT 1").fetchone()
        con.close()
        return str(row["hot_branch"]) if row and row["hot_branch"] else ""
    except Exception:
        return ""

def sample():
    """Record one observation: was the nudge active, and did the branch move?"""
    _ensure_table()
    con = sqlite3.connect(_db("dynamic")); con.row_factory = sqlite3.Row
    prev = con.execute("SELECT branch FROM recursion_attrib ORDER BY ts DESC LIMIT 1").fetchone()
    branch_prev = prev["branch"] if prev else ""
    branch = _current_branch()
    if branch and branch == branch_prev:
        # no new fire since last sample — skip dup
        con.close(); return
    active = 1 if _nudge_active() else 0
    moved = 1 if (branch_prev and branch != branch_prev) else 0
    con.execute("INSERT OR REPLACE INTO recursion_attrib VALUES (?,?,?,?,?)",
                (time.time(), active, branch, branch_prev, moved))
    con.commit(); con.close()

def verdict():
    _ensure_table()
    con = sqlite3.connect(_db("dynamic")); con.row_factory = sqlite3.Row
    rows = con.execute("SELECT nudge_active, moved FROM recursion_attrib WHERE branch_prev != ''").fetchall()
    con.close()
    act = [r["moved"] for r in rows if r["nudge_active"] == 1]
    inact = [r["moved"] for r in rows if r["nudge_active"] == 0]
    pa = sum(act)/len(act) if act else 0.0
    pi = sum(inact)/len(inact) if inact else 0.0
    print("="*56)
    print("L3 RECURSION TEETH — attribution verdict")
    print("="*56)
    print(f"  samples: {len(rows)}  (nudge-active={len(act)}, nudge-absent={len(inact)})")
    print(f"  P(move | nudge ACTIVE):  {pa:.3f}  ({sum(act)}/{len(act)})")
    print(f"  P(move | nudge ABSENT):  {pi:.3f}  ({sum(inact)}/{len(inact)})  <- baseline drift")
    print("-"*56)
    if len(act) < 20 or len(inact) < 20:
        print("  VERDICT: INSUFFICIENT DATA — need >=20 of each. Let the soak gather.")
    elif pa > pi + 0.10:
        print(f"  VERDICT: TEETH CONFIRMED — nudge moves attention +{pa-pi:.3f} over baseline.")
        print("           L3_recursion has teeth. L4_stakes unblocked.")
    elif abs(pa - pi) <= 0.10:
        print("  VERDICT: COSMETIC — nudge ~= baseline drift. Recursion does NOT move")
        print("           attention. L4 stays gated; recursion needs real teeth first.")
    else:
        print(f"  VERDICT: NEGATIVE — nudge moves LESS than baseline ({pa-pi:+.3f}). Investigate.")
    print("="*56)

if __name__ == "__main__":
    if "--verdict" in sys.argv:
        verdict()
    elif "--watch" in sys.argv:
        print("[attrib] sampling every 20s — Ctrl-C to stop")
        while True:
            try: sample(); time.sleep(20)
            except KeyboardInterrupt: print("\n[attrib] stopped"); break
            except Exception as e: print(f"[attrib] err: {e!r}"); time.sleep(20)
    else:
        sample(); print("one sample recorded. --watch to gather, --verdict to read.")
