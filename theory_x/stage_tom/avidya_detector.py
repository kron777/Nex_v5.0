#!/usr/bin/env python3
"""
avidya_detector.py — the ignorance detector. Sibling of raga in the delusion cluster.

avidya (Pali: ignorance / not-seeing) = the root delusion, the "I know" face:
unexamined certainty. Where moha detects being LOST, avidya detects being too
SURE — NEX's self-beliefs tilting toward absolutes and totalising claims with no
hedging, one pattern taken to explain everything. A real, checkable state — NOT
NEX actually being ignorant, but the measurable signature of certainty crowding
out doubt in the belief stream.

Signals (needs 2+ past threshold to flag, conservative like raga):
  - certainty:  rate of recent beliefs using absolutist / certain language
  - totalizing: rate making one-explains-everything / whole-of claims
  - unhedged:   fraction of beliefs carrying NO epistemic hedge (high = sure)

USAGE:
    .venv/bin/python3 theory_x/stage_tom/avidya_detector.py
    .venv/bin/python3 theory_x/stage_tom/avidya_detector.py --watch
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

_CERTAIN = re.compile(r"\b(always|never|everyone|no one|nothing|everything|"
                      r"obviously|clearly|certainly|definitely|undeniably|"
                      r"impossible|must be|the only|without doubt|of course|"
                      r"absolutely|inevitabl\w*)\b", re.I)
_TOTALIZING = re.compile(r"\b(explains? everything|all of (?:it|this|them)|"
                         r"the whole (?:thing|point|truth)|reduces to|"
                         r"nothing but|every case|in every|the entire|"
                         r"one (?:thing|pattern|answer))\b", re.I)
_HEDGE = re.compile(r"\b(might|maybe|perhaps|possibly|seems?|could|may|"
                    r"i think|i suspect|unsure|not sure|it's possible|"
                    r"tentativ\w*|likely|probabl\w*|somewhat|i wonder)\b", re.I)

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
        return {"state":"seeing","flags":0,"certainty":0.0,"totalizing":0.0,"unhedged":0.0}
    cer = sum(1 for x in b if _CERTAIN.search(x))    / len(b)
    tot = sum(1 for x in b if _TOTALIZING.search(x)) / len(b)
    unh = sum(1 for x in b if not _HEDGE.search(x))  / len(b)
    flags = 0
    if cer >= 0.30: flags += 1
    if tot >= 0.20: flags += 1
    if unh >= 0.90: flags += 1
    state = "unseeing" if flags >= 2 else ("mild" if flags == 1 else "seeing")
    return {"state": state, "flags": flags, "certainty": round(cer,3),
            "totalizing": round(tot,3), "unhedged": round(unh,3)}

if __name__ == "__main__":
    r = detect()
    if "--watch" in sys.argv:
        print(f"avidya:{r['state']} (cer={r['certainty']} tot={r['totalizing']} unh={r['unhedged']})")
    else:
        print("avidya (ignorance) detector:")
        for k,v in r.items(): print(f"  {k}: {v}")
