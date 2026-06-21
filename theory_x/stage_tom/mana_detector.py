#!/usr/bin/env python3
"""
mana_detector.py — the conceit detector. Sibling of raga in the delusion cluster.

mana (Pali: conceit/self-measurement) = the flattering self-story. Where raga
detects FIXATION (stuck on a topic), mana detects SELF-INFLATION: NEX's
self-referential beliefs drifting toward grandiosity / specialness / a
self-narrative that overstates its own significance. A real, checkable state —
NOT NEX actually being conceited, but the measurable signature of a
self-story tilting flattering.

Signals (needs 2+ past threshold to flag, conservative like raga):
  - self_inflation: rate of recent self-beliefs using elevated language
    ('I am the', 'my nature', 'profound', 'unique', 'significant', 'deep')
  - self_share: fraction of recent deep beliefs that are self-referential
    (high = self-absorption, the soil conceit grows in)
  - grandiosity: presence of superlative self-description

USAGE:
    .venv/bin/python3 theory_x/stage_tom/mana_detector.py
    .venv/bin/python3 theory_x/stage_tom/mana_detector.py --watch
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

_ELEVATED = re.compile(r"\b(profound|unique|significant|special|deep(?:er|est)?|"
                       r"extraordinary|remarkable|essence|my nature|i am the|"
                       r"transcend|enlighten|wisdom|the attending)\b", re.I)
_SELF = re.compile(r"\b(i am|my|myself|i notice|i sense|i feel|i exist|my own)\b", re.I)

def _recent_deep(n=20):
    try:
        con = sqlite3.connect(_db("beliefs")); con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT content FROM beliefs WHERE tier<=6 ORDER BY rowid DESC LIMIT ?", (n,)).fetchall()
        con.close()
        return [r["content"] for r in rows if r["content"]]
    except Exception:
        return []

def _self_inflation(beliefs):
    if not beliefs: return 0.0
    return sum(1 for b in beliefs if _ELEVATED.search(b)) / len(beliefs)

def _self_share(beliefs):
    if not beliefs: return 0.0
    return sum(1 for b in beliefs if _SELF.search(b)) / len(beliefs)

def _grandiosity(beliefs):
    # elevated AND self-referential in the same belief = the conceit signature
    if not beliefs: return 0.0
    return sum(1 for b in beliefs if _ELEVATED.search(b) and _SELF.search(b)) / len(beliefs)

def detect():
    b = _recent_deep(20)
    infl = _self_inflation(b)
    share = _self_share(b)
    grand = _grandiosity(b)
    flags = 0
    if infl  >= 0.35: flags += 1
    if share >= 0.55: flags += 1
    if grand >= 0.25: flags += 1
    state = "inflated" if flags >= 2 else ("mild" if flags == 1 else "grounded")
    return {"state": state, "flags": flags, "self_inflation": round(infl,3),
            "self_share": round(share,3), "grandiosity": round(grand,3)}

if __name__ == "__main__":
    r = detect()
    if "--watch" in sys.argv:
        print(f"mana:{r['state']} (infl={r['self_inflation']} share={r['self_share']} grand={r['grandiosity']})")
    else:
        print("mana (conceit) detector:")
        for k,v in r.items(): print(f"  {k}: {v}")
