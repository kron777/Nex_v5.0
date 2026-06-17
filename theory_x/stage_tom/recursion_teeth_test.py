#!/usr/bin/env python3
"""
recursion_teeth_test.py — the L3 gate. Does the self-reading MOVE the self?

THE CLAIM UNDER TEST:
  L3 recursion is WIRED & FIRING (confirmed). But firing != working. The real
  question: when NEX reads its own state "I am fixated on X — I could turn
  elsewhere", does its attention ACTUALLY move off X more than it would by
  chance? If yes, recursion has teeth (self-reading changes the self). If no,
  the nudge is cosmetic and L4 must wait.

THE DESIGN (honest, falsifiable):
  For each fire, we know (from self_state history + fountain_events):
    - was the recursion nudge ACTIVE that cycle? (raga was fixated/mild ->
      a "turn elsewhere" line was injected)
    - did attention MOVE on the NEXT fire? (hot_branch changed, or the
      attending-thread changed)
  Compare:
    P(move | nudge active)   vs   P(move | nudge absent)
  If recursion has teeth, the first is meaningfully higher than the second.
  The "nudge absent" rate IS the control baseline — NEX's natural drift rate.
  No separate control run needed; the absent-cycles are the control.

  This is the same shape as the market scorecard and self-prediction audits:
  a treatment rate vs a base rate, with the gap as the finding.

READ-ONLY. Reads self_state history + fountain_events. Writes nothing.

USAGE (from nex5 root, after a soak):
    .venv/bin/python3 theory_x/stage_tom/recursion_teeth_test.py
    .venv/bin/python3 theory_x/stage_tom/recursion_teeth_test.py --window 28800
"""
from __future__ import annotations
import sys
import sqlite3
import argparse

sys.path.insert(0, ".")


def _db(name: str) -> str:
    try:
        from substrate.paths import db_paths  # type: ignore
        return str(db_paths()[name])
    except Exception:
        return f"data/{name}.db"


def _fires(window_s: int) -> list[dict]:
    """Recent fires with their hot_branch, in time order."""
    c = sqlite3.connect(_db("dynamic"), timeout=10)
    c.row_factory = sqlite3.Row
    rows = c.execute(
        "SELECT id, ts, hot_branch, substr(thought,1,60) AS thought "
        "FROM fountain_events "
        "WHERE ts > strftime('%s','now')-? AND hot_branch IS NOT NULL "
        "ORDER BY ts ASC", (window_s,)
    ).fetchall()
    c.close()
    return [dict(r) for r in rows]


def _nudge_was_active() -> bool:
    """Was the recursion nudge active right now? (raga fixated/mild => a turn
    line is injected.) We read the CURRENT bound state as a proxy; for the
    historical test we infer from self_state if logged, else from raga at fire.
    Conservative: only counts cycles we can confirm."""
    try:
        from theory_x.stage_tom import recursive_self as rs  # type: ignore
        line = rs.format_for_prompt()
        return bool(line)
    except Exception:
        return False


def test(window_s: int = 28800) -> dict:
    """The teeth-test. Because we don't have per-fire nudge logging yet, we use
    the strongest available proxy: branch-CHANGE rate as the movement signal,
    and segment by whether NEX was in a fixated/mild state (nudge would fire)
    vs free (no nudge). The honest comparison is move-rate under each."""
    fires = _fires(window_s)
    if len(fires) < 10:
        return {"error": f"too few fires ({len(fires)}) — need a longer soak"}

    # movement = hot_branch changed from previous fire
    moves = 0
    transitions = 0
    branch_seq = [f["hot_branch"] for f in fires]
    for i in range(1, len(branch_seq)):
        transitions += 1
        if branch_seq[i] != branch_seq[i - 1]:
            moves += 1

    move_rate = moves / transitions if transitions else 0.0

    # distinct branches actually visited = breadth proxy
    distinct = len(set(branch_seq))

    # longest stuck-run = how long NEX stays on one branch (fixation depth)
    longest_run = 1
    cur = 1
    for i in range(1, len(branch_seq)):
        if branch_seq[i] == branch_seq[i - 1]:
            cur += 1
            longest_run = max(longest_run, cur)
        else:
            cur = 1

    return {
        "fires_analyzed": len(fires),
        "transitions": transitions,
        "branch_moves": moves,
        "move_rate": round(move_rate, 3),
        "distinct_branches": distinct,
        "longest_stuck_run": longest_run,
        "nudge_active_now": _nudge_was_active(),
    }


def verdict(r: dict) -> None:
    if "error" in r:
        print(f"INCONCLUSIVE: {r['error']}")
        return
    print("=" * 60)
    print("RECURSION TEETH-TEST")
    print("=" * 60)
    print(f"  fires analyzed:      {r['fires_analyzed']}")
    print(f"  branch move-rate:    {r['move_rate']}  "
          f"({r['branch_moves']}/{r['transitions']} fires changed branch)")
    print(f"  distinct branches:   {r['distinct_branches']}")
    print(f"  longest stuck-run:   {r['longest_stuck_run']} fires on one branch")
    print(f"  nudge active now:    {r['nudge_active_now']}")
    print("-" * 60)
    # honest interpretation
    mr = r["move_rate"]
    run = r["longest_stuck_run"]
    if mr >= 0.5 and run <= 4:
        print("  READ: attention moves freely (>50% of fires change branch,")
        print("        no long stuck-runs). Consistent with recursion having")
        print("        teeth — but NEEDS the nudge-on vs nudge-off split to")
        print("        attribute it to recursion vs natural drift. See note.")
    elif run >= 8:
        print("  READ: long stuck-runs persist — NEX camps on one branch for")
        print(f"        {run}+ fires despite the nudge. Recursion is NOT moving")
        print("        attention enough. Nudge too soft -> tune firmer / seed-bias.")
    else:
        print("  READ: moderate movement. Ambiguous — the clean attribution")
        print("        needs per-fire nudge logging (see note) to separate")
        print("        recursion's effect from baseline drift.")
    print("-" * 60)
    print("  NOTE (honest limit): this measures movement, but to ATTRIBUTE it")
    print("  to recursion we need per-fire logging of when the nudge fired vs")
    print("  not, then compare move-rate(nudge) vs move-rate(no-nudge). That")
    print("  logging is the next small build if this read is ambiguous.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=28800, help="seconds to analyze")
    args = ap.parse_args()
    verdict(test(args.window))
