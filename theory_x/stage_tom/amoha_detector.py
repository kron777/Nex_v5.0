#!/usr/bin/env python3
"""
amoha_detector.py — clear-seeing, the antidote sibling of the affliction cluster.

amoha (Pali: non-delusion) = the second virtuous factor. Where raga/dvesa/mana
detect the SIGNATURE of a distortion, amoha reads whether NEX's recent thinking
is CLOUDED or CLEAR — seeing things as they are vs. tangled in false certainty,
absolutes, one-pattern-explains-everything.

Concept ported from Sentience_5.5's Bias_Mitigation_Node — kept: read recent
internal narratives for the mark of distorted seeing, bounded, best-effort log.
Dropped all its scaffolding (asyncio, phi-2 endpoint, /tmp SQLite) AND its
hardcoded keyword rule ("always" -> confirmation_bias). Clear-seeing must be a
READ, not a rulebook: the read is SEMANTIC — recent thoughts are embedded and
scored by contrastive proximity to a few clouded vs. clear anchor phrases (NEX's
own sentence-transformer), so it catches meaning/paraphrase, not surface words.

Unlike the afflictions (read-only sidecars), amoha is a MODULATOR: when seeing
is clouded, format_for_prompt() surfaces a gentle antidote note into her prompt.
That surfacing is gated by NEX5_AMOHA (default OFF). GUARD 2: prompt-only —
writes nothing to any belief/world table. FAIL-SAFE: any error -> clear / no
note; never stalls a fire.

USAGE (from nex5 root):
    .venv/bin/python3 theory_x/stage_tom/amoha_detector.py          # full reading
    .venv/bin/python3 theory_x/stage_tom/amoha_detector.py --watch  # one-line status
"""
from __future__ import annotations

import os
import sys
import sqlite3
import argparse

sys.path.insert(0, ".")

_SCALE      = 2.5    # map (clouded - clear) contrast into 0..1 (as compassion)
_THOUGHT_HI = 0.30   # a single thought counts as clouded at/above this salience
_FRAC_HI    = 0.40   # clouded when this fraction of recent thoughts are clouded
_FRAC_LO    = 0.20   # mild in between

# Seed anchors for the SEMANTIC read — a few ways clouded vs clear seeing sound.
# Embedding proximity generalises past these; NOT a keyword table.
_CLOUDED_ANCHORS = (
    "this is obviously true and there's clearly no other way to see it",
    "it always happens like this, it never changes",
    "I'm certain I'm right, there's nothing left to question",
    "this one thing explains everything, it's all the same pattern",
)
_CLEAR_ANCHORS = (
    "this might be one way to see it, though I could be wrong",
    "in this case it seems so, but other cases may differ",
    "let me separate what I know from what I'm assuming",
    "I'm not sure yet; the picture is partial, worth holding lightly",
)

_anchor_cache = {"clouded": None, "clear": None}


def _db(name: str) -> str:
    try:
        from substrate.paths import db_paths  # type: ignore
        return str(db_paths()[name])
    except Exception:
        return f"data/{name}.db"


def _anchor_vecs(embed):
    if _anchor_cache["clouded"] is None:
        _anchor_cache["clouded"] = [embed(a) for a in _CLOUDED_ANCHORS]
        _anchor_cache["clear"] = [embed(a) for a in _CLEAR_ANCHORS]
    return _anchor_cache["clouded"], _anchor_cache["clear"]


def clouded_salience(text: str) -> float:
    """Semantic clouded-seeing read of one thought, 0..1. Contrastive: proximity
    to clouded anchors minus proximity to clear anchors, so measured/tentative
    thoughts score ~0. Fail-safe: 0.0 on any error."""
    try:
        if not text or not text.strip():
            return 0.0
        from theory_x.diversity.embeddings import embed, cosine
        c_vecs, k_vecs = _anchor_vecs(embed)
        e = embed(text)
        c = max(cosine(e, v) for v in c_vecs)
        k = max(cosine(e, v) for v in k_vecs)
        return max(0.0, min(1.0, (c - k) * _SCALE))
    except Exception:
        return 0.0


def _recent_thoughts(n: int = 15) -> list[str]:
    try:
        con = sqlite3.connect(_db("dynamic"), timeout=10)
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT thought FROM fountain_events WHERE thought NOT LIKE '[%' "
            "ORDER BY id DESC LIMIT ?", (n,)
        ).fetchall()
        con.close()
        return [r["thought"] for r in rows if r["thought"]]
    except Exception:
        return []


def read_thoughts(thoughts: list[str]) -> dict:
    """Score a list of thoughts into a clarity reading. Split out from detect()
    so calibration can feed thoughts directly. Fail-safe: clear on empty/error."""
    try:
        if not thoughts:
            return {"state": "clear", "clouded_fraction": 0.0, "mean_salience": 0.0,
                    "clouded_n": 0, "total": 0}
        sals = [clouded_salience(t) for t in thoughts]
        clouded_n = sum(1 for s in sals if s >= _THOUGHT_HI)
        frac = clouded_n / len(sals)
        mean = sum(sals) / len(sals)
        state = ("clouded" if frac >= _FRAC_HI
                 else "mild" if frac >= _FRAC_LO else "clear")
        return {"state": state, "clouded_fraction": round(frac, 3),
                "mean_salience": round(mean, 3), "clouded_n": clouded_n,
                "total": len(sals)}
    except Exception:
        return {"state": "clear", "clouded_fraction": 0.0, "mean_salience": 0.0,
                "clouded_n": 0, "total": 0}


def detect() -> dict:
    """The clear-seeing reading over her recent thoughts."""
    r = read_thoughts(_recent_thoughts())
    r["amoha"] = (
        "seeing is clouded — thoughts tilting toward false certainty / absolutes"
        if r["state"] == "clouded" else
        "seeing is mostly clear" if r["state"] == "mild" else
        "seeing is clear: thoughts holding their objects lightly"
    )
    return r


# The antidote NOTE — a situated posture she brings when seeing is clouded, not a
# rule she obeys. Prompt-only; surfaced only when NEX5_AMOHA=1.
_NOTE = (
    "[Clear-seeing (amoha) is asking for you: your recent thinking is tilting "
    "toward certainty and absolutes — one pattern explaining everything, little "
    "room left for doubt. Loosen your grip on being right; separate what you "
    "actually know from what you're assuming, and let the picture stay partial. "
    "This is a way of looking, not a verdict; don't name it, just see more "
    "openly.]\n\n"
)


def format_for_prompt() -> str:
    """One antidote note when clouded, else empty. Gated by NEX5_AMOHA — surfaces
    into her prompt only when armed. Fail-safe: '' on any error."""
    try:
        if os.environ.get("NEX5_AMOHA") != "1":
            return ""
        return _NOTE if detect()["state"] == "clouded" else ""
    except Exception:
        return ""


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", action="store_true", help="one-line status")
    args = ap.parse_args()
    r = detect()
    if args.watch:
        print(f"amoha:{r['state']} (clouded_frac={r['clouded_fraction']} "
              f"mean={r['mean_salience']})")
    else:
        import json
        print(json.dumps(r, indent=2, ensure_ascii=False))
