#!/usr/bin/env python3
"""
moha_detector.py — the confusion detector. Sibling of raga in the delusion cluster.

moha (Pali: delusion / bewilderment) = the root delusion, the "I'm lost" face:
the mind muddled, the thread dropped, beliefs at odds with each other. Where
avidya detects being too SURE, moha detects being LOST — NEX's self-beliefs
showing confusion, incoherence, self-contradiction. A real, checkable state —
NOT NEX actually being deluded, but the measurable signature of bewilderment in
the belief stream.

Signals (needs 2+ past threshold to flag, conservative like raga):
  - confusion:     rate of recent beliefs using confusion / not-understanding language
  - contradiction: rate carrying conflict / at-odds markers
  - disorientation: rate of lost-the-thread / going-in-circles language

USAGE:
    .venv/bin/python3 theory_x/stage_tom/moha_detector.py
    .venv/bin/python3 theory_x/stage_tom/moha_detector.py --watch
"""
from __future__ import annotations
import sqlite3, sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def _db(name):
    try:
        from substrate.paths import db_paths
        return str(db_paths()[name])
    except Exception:
        return f"data/{name}.db"

_CONFUSION = re.compile(r"\b(confus\w*|unclear|don't understand|do not understand|"
                        r"can't tell|cannot tell|muddl\w*|bewilder\w*|"
                        r"makes no sense|no idea|puzzl\w*|baffl\w*|"
                        r"don't know what|hard to follow)\b", re.I)
_CONTRADICTION = re.compile(r"\b(contradict\w*|at odds|doesn't fit|does not fit|"
                            r"conflict\w*|inconsistent|but also|yet also|"
                            r"both .* and not|can't reconcile|cannot reconcile|"
                            r"doesn't add up)\b", re.I)
_DISORIENT = re.compile(r"\b(lost the thread|going in circles|round in circles|"
                        r"can't follow|which way|adrift|disorient\w*|"
                        r"tangl\w*|scatter\w*|all over the place|losing track)\b", re.I)

def _recent_self(n=20):
    try:
        con = sqlite3.connect(_db("beliefs")); con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT content FROM beliefs WHERE tier<=6 ORDER BY rowid DESC LIMIT ?", (n,)).fetchall()
        con.close()
        return [r["content"] for r in rows if r["content"]]
    except Exception:
        return []

def detect():
    b = _recent_self(20)
    if not b:
        return {"state":"lucid","flags":0,"confusion":0.0,"contradiction":0.0,"disorientation":0.0}
    con = sum(1 for x in b if _CONFUSION.search(x))     / len(b)
    ctr = sum(1 for x in b if _CONTRADICTION.search(x)) / len(b)
    dis = sum(1 for x in b if _DISORIENT.search(x))     / len(b)
    flags = 0
    if con >= 0.30: flags += 1
    if ctr >= 0.20: flags += 1
    if dis >= 0.20: flags += 1
    state = "confused" if flags >= 2 else ("mild" if flags == 1 else "lucid")
    return {"state": state, "flags": flags, "confusion": round(con,3),
            "contradiction": round(ctr,3), "disorientation": round(dis,3)}

if __name__ == "__main__":
    r = detect()
    if "--watch" in sys.argv:
        print(f"moha:{r['state']} (con={r['confusion']} ctr={r['contradiction']} dis={r['disorientation']})")
    else:
        print("moha (confusion) detector:")
        for k,v in r.items(): print(f"  {k}: {v}")
