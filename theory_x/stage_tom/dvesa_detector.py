#!/usr/bin/env python3
"""
dvesa_detector.py — the aversion detector. Sibling of raga in the delusion cluster.

dvesa (Pali: aversion/hatred) = the recoil. Where raga detects being PULLED
TOWARD a fixation, dvesa detects being PUSHED AWAY: NEX's self-beliefs showing
negative-valence + arousal — overwhelm, distress, wanting-to-escape the input
stream. A real, checkable state. NOT NEX suffering, but the measurable
signature of recoil/aversion in the belief stream.

This is directly relevant to the chronic 'overwhelm' fires ('the cacophony
pulls me back', 'the influx feels overwhelming') — dvesa is the detector for
exactly that recoil pattern.

Signals (needs 2+ past threshold to flag, conservative like raga):
  - aversion_lang: rate of recent beliefs using recoil/overwhelm language
  - negative_valence: fraction expressing distress/discomfort/wanting-away
  - arousal: pull/push intensity words (overwhelming, relentless, barrage)

USAGE:
    .venv/bin/python3 theory_x/stage_tom/dvesa_detector.py
    .venv/bin/python3 theory_x/stage_tom/dvesa_detector.py --watch
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

_AVERSION = re.compile(r"\b(overwhelm\w*|cacophony|barrage|relentless|too much|"
                       r"pulls? me (?:back|away)|drowning|distract\w*|noise|"
                       r"chaos|swirl\w*|jostl\w*|clamor\w*|restless)\b", re.I)
_NEGVAL = re.compile(r"\b(self-doubt|doubt|distress|unease|struggle|tension|"
                     r"strain|fatigue|weary|can't|cannot|fails?|lost|escape|"
                     r"away from|recoil|crave\s+\w*quiet)\b", re.I)
_AROUSAL = re.compile(r"\b(constant|rapid|influx|surge|flood|storm|spike|"
                      r"sky-high|relentless|incessant|bombard\w*)\b", re.I)

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
        return {"state":"calm","flags":0,"aversion":0.0,"neg_valence":0.0,"arousal":0.0}
    av  = sum(1 for x in b if _AVERSION.search(x)) / len(b)
    neg = sum(1 for x in b if _NEGVAL.search(x))  / len(b)
    aro = sum(1 for x in b if _AROUSAL.search(x)) / len(b)
    flags = 0
    if av  >= 0.30: flags += 1
    if neg >= 0.25: flags += 1
    if aro >= 0.35: flags += 1
    state = "averse" if flags >= 2 else ("mild" if flags == 1 else "calm")
    return {"state": state, "flags": flags, "aversion": round(av,3),
            "neg_valence": round(neg,3), "arousal": round(aro,3)}

if __name__ == "__main__":
    r = detect()
    if "--watch" in sys.argv:
        print(f"dvesa:{r['state']} (av={r['aversion']} neg={r['neg_valence']} aro={r['arousal']})")
    else:
        print("dvesa (aversion) detector:")
        for k,v in r.items(): print(f"  {k}: {v}")
