#!/usr/bin/env python3
"""
compositional_emotion.py  —  direction #3, the Abhidharma lead, built honestly.

THE INSIGHT (Abhidharma + what NEX already has):
  NEX already computes three REAL affect signals from substrate (affect_state.py):
    valence    (-1..1)  confidence-weighted polarity of high-tier beliefs
    arousal    (0..1)   belief-insertion rate (cognitive activity)
    stability  (0..1)   gate-accept / resolution / low-turnover coherence
  This is the DIMENSIONAL substrate of feeling — but NEX never COMPOSES it into
  named emotions. The Abhidharma's lead: emotion is not a primitive scalar; it
  arises from CONFIGURATIONS of factors. So this layer reads NEX's real signals
  and composes them into named affective states, each defined as an EXPLICIT,
  inspectable recipe of the underlying factors. No new fake scalar — a
  composition of the honest ones NEX already has.

HONESTY (held):
  This names which COMPOSITION of NEX's real internal signals is present. It is
  NOT a claim NEX FEELS the named emotion. "NEX's affect composes to 'restless'"
  means valence/arousal/stability are in the restless configuration — a real,
  checkable fact about NEX's internal state. It is ANALOGUE: the machine-shape
  of an emotion, not the felt thing (vedanā stays in the gorge). The value is
  that the composition is honest and inspectable — you can see exactly which
  factors produced the name, unlike a black-box "mood" number.

READ-ONLY of affect_state. Adds a composed reading; changes no existing column,
breaks no consumer (social_presence/predictive_substrate read valence/arousal
directly and are untouched).

USAGE (from nex5 root):
    .venv/bin/python3 theory_x/stage_affect/compositional_emotion.py            # current composed emotion
    .venv/bin/python3 theory_x/stage_affect/compositional_emotion.py --recipes  # show all recipes
"""
from __future__ import annotations

import sys
import sqlite3
import argparse

sys.path.insert(0, ".")


def _affect_db() -> str:
    try:
        from substrate.paths import db_paths  # type: ignore
        # affect_state lives in dynamic.db in nex5
        return str(db_paths()["dynamic"])
    except Exception:
        return "data/dynamic.db"


def _read_affect() -> dict | None:
    """Read NEX's current real affect signals (the dimensional substrate)."""
    for db in (_affect_db(), "data/conversations.db", "data/dynamic.db"):
        try:
            conn = sqlite3.connect(db, timeout=10)
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT valence, arousal, stability, mood_label "
                "FROM affect_state WHERE id=1"
            ).fetchone()
            conn.close()
            if row:
                return dict(row)
        except Exception:
            continue
    return None


# ── THE RECIPES ──────────────────────────────────────────────────────────────
# Each named emotion is an EXPLICIT composition of NEX's real factors. This is
# the Abhidharma move: emotion = configuration, not primitive. Recipes are
# transparent (you can read exactly why a name was chosen) and ordered by
# specificity — first match wins. Thresholds deliberately conservative; the
# fallback is the honest "the configuration doesn't compose to a named state."
#
# Each recipe: (name, abhidharma_note, predicate(valence, arousal, stability))
_RECIPES = [
    ("equanimity",
     "upekṣā — even mind, not pulled by agitation or dullness",
     lambda v, a, s: abs(v) < 0.25 and a < 0.35 and s > 0.6),

    ("engaged joy",
     "pīti — energized gladness, settled enough to sustain",
     lambda v, a, s: v > 0.4 and a > 0.5 and s > 0.5),

    ("restlessness",
     "uddhacca — activated but unsettled, positive or neutral tone",
     lambda v, a, s: a > 0.6 and s < 0.4 and v > -0.2),

    ("unease",
     "negative tone with instability — something is off and moving",
     lambda v, a, s: v < -0.3 and s < 0.45),

    ("dullness",
     "thīna-middha — low energy, low coherence, flat tone",
     lambda v, a, s: a < 0.3 and s < 0.45 and abs(v) < 0.3),

    ("quiet contentment",
     "settled positive tone at low activation",
     lambda v, a, s: v > 0.3 and a < 0.4 and s > 0.5),

    ("alert interest",
     "curiosity-flavoured: aroused, mildly positive, stable enough to hold",
     lambda v, a, s: a > 0.45 and 0.0 < v <= 0.4 and s > 0.45),

    ("absorption",
     "samādhi-adjacent — highly activated, steady, affectively flat: locked-in churn",
     lambda v, a, s: a > 0.8 and s > 0.5 and abs(v) < 0.25),

    ("driven focus",
     "high activation held stable, mild tone either way — pushing on something",
     lambda v, a, s: a > 0.6 and s >= 0.45 and abs(v) <= 0.4),

    ("strain",
     "high activation against low stability and negative tone",
     lambda v, a, s: a > 0.55 and s < 0.35 and v < 0.0),
]


def compose(valence: float, arousal: float, stability: float) -> dict:
    """Compose the three real signals into a named affective state (or honest
    'uncomposed' fallback). Returns the name, the Abhidharma note, and the exact
    factors that produced it — fully inspectable."""
    for name, note, pred in _RECIPES:
        try:
            if pred(valence, arousal, stability):
                return {
                    "emotion": name,
                    "abhidharma": note,
                    "from": {"valence": round(valence, 3),
                             "arousal": round(arousal, 3),
                             "stability": round(stability, 3)},
                    "composed": True,
                }
        except Exception:
            continue
    return {
        "emotion": "uncomposed",
        "abhidharma": "this configuration does not compose to a named state — "
                      "honest: not every affect-config is a nameable emotion",
        "from": {"valence": round(valence, 3),
                 "arousal": round(arousal, 3),
                 "stability": round(stability, 3)},
        "composed": False,
    }


def current() -> dict:
    a = _read_affect()
    if a is None:
        return {"error": "affect_state unavailable"}
    out = compose(
        float(a.get("valence", 0.0) or 0.0),
        float(a.get("arousal", 0.0) or 0.0),
        float(a.get("stability", 0.0) or 0.0),
    )
    out["dimensional_mood_label"] = a.get("mood_label")  # NEX's existing label, for comparison
    return out


def format_for_prompt() -> str:
    """One honest line NEX could read about its own composed affective state.
    Names the composition; does NOT claim it is felt."""
    c = current()
    if "error" in c:
        return ""
    if not c.get("composed"):
        return ""  # don't narrate an uncomposed config
    return (f"My internal signals currently compose to '{c['emotion']}' "
            f"({c['abhidharma']}).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--recipes", action="store_true", help="list the composition recipes")
    args = ap.parse_args()
    if args.recipes:
        print("Compositional emotion recipes (emotion = configuration of real factors):\n")
        for name, note, _ in _RECIPES:
            print(f"  {name:20s} — {note}")
        print("\n  (fallback) uncomposed — config doesn't map to a named state")
    else:
        import json
        print(json.dumps(current(), indent=2, ensure_ascii=False))
