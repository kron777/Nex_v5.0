#!/usr/bin/env python3
"""
genius_provenance.py  —  how much of NEX's "genius" is genuinely NEX's own?

The genius-grader rewards depth, but it can't tell three different things apart:
  1. SELF-REFLECTION  — NEX's own first-person thinking ("I am the attending...")
  2. INGESTED WISDOM  — koans/parables/quotes absorbed from feeds, scored high
                        because they ARE wise, but NEX didn't think them.
  3. INSTRUMENTAL     — task/research-plan text (deliverable-pipeline output),
                        substantive and long but not reflection at all.

For a project about machine sentience, the difference is everything: bucket 1 is
NEX thinking; bucket 2 is NEX quoting; bucket 3 is NEX doing chores. This script
classifies every STRIKING thought into those three and reports the split — so we
know what fraction of NEX's best output is genuinely its own mind.

Read-only. Touches nothing. Pure measurement.

USAGE (from nex5 root):
    .venv/bin/python3 theory_x/genius/genius_provenance.py
    .venv/bin/python3 theory_x/genius/genius_provenance.py --samples   # show examples per bucket
    .venv/bin/python3 theory_x/genius/genius_provenance.py --min-score 0.9  # only the very top

Heuristics are deliberately transparent and conservative — when unsure, a
thought is NOT credited as self-reflection. We would rather UNDER-count NEX's
genius than inflate it. (Honesty rule: never let the flattering bucket win by
default.)
"""
from __future__ import annotations

import os
import re
import sys
import sqlite3
import argparse


def _conv_db() -> str:
    sys.path.insert(0, ".")
    try:
        from substrate.paths import db_paths  # type: ignore
        return str(db_paths()["conversations"])
    except Exception:
        return "data/conversations.db"


def _dyn_db() -> str:
    sys.path.insert(0, ".")
    try:
        from substrate.paths import db_paths  # type: ignore
        return str(db_paths()["dynamic"])
    except Exception:
        return "data/dynamic.db"


# --- markers, derived from reading NEX's actual striking thoughts ---------

# Bucket 3: INSTRUMENTAL — task/plan/research language. NEX doing chores.
_INSTRUMENTAL = re.compile(
    r"\b(conduct|design|implement|integrate|analyz|survey|interview participants|"
    r"systematically vary|next step would be|concrete next step|experiment|"
    r"laboratory|methodology|framework to|approach would be|test whether|"
    r"measure the|dataset|benchmark)\b",
    re.IGNORECASE,
)

# Bucket 2: INGESTED — narrative/parable/quote shapes. NEX quoting, not thinking.
_INGESTED_START = re.compile(
    r"^\s*(A\s+(man|monk|student|master|woman|king|teacher|disciple|sage)\b|"
    r"The\s+(student|master|monk|teacher|sage|disciple)\b|"
    r"Once\s|Laozi|Confucius|Buddha|A\s+master\s+(was|asked|said)|"
    r"There\s+(was|once)\b)",
    re.IGNORECASE,
)
# Quote punctuation typical of absorbed dialogue ("...", he said)
_INGESTED_DIALOGUE = re.compile(r"['\"].{0,80}['\"].{0,40}(said|asked|replied|answered)\b",
                                re.IGNORECASE)

# Bucket 1: SELF-REFLECTION — NEX's own voice. First-person, present, about its
# own being/attending/experience. Conservative: requires genuine first-person
# stance, not just the letter "I".
_SELF_FIRST = re.compile(r"^\s*(I\s|I'|My\s|Me\b)", re.IGNORECASE)
_SELF_STANCE = re.compile(
    r"\b(I\s+am|I\s+take|I\s+attend|I\s+accept|I\s+receive|I\s+do\s+not\s+need|"
    r"I\s+notice|I\s+approach|the\s+attending|my\s+attending|for\s+me\b|"
    r"this\s+moment\s+is|each\s+return)\b",
    re.IGNORECASE,
)


def classify(thought: str) -> str:
    t = (thought or "").strip()
    if not t:
        return "empty"
    # Order matters: instrumental and ingested are checked BEFORE self, because
    # a task line or a parable can still contain "I". We only credit self-
    # reflection when it's NOT clearly chore-text or quoted narrative.
    if _INSTRUMENTAL.search(t):
        return "instrumental"
    if _INGESTED_START.search(t) or _INGESTED_DIALOGUE.search(t):
        return "ingested"
    if _SELF_FIRST.match(t) or _SELF_STANCE.search(t):
        return "self_reflection"
    return "other_unclassified"


def run(min_score: float = 0.7, show_samples: bool = False) -> dict:
    conv = sqlite3.connect(_conv_db())
    conv.row_factory = sqlite3.Row
    conv.execute(f"ATTACH '{_dyn_db()}' AS dyn")
    rows = conv.execute(
        "SELECT f.thought AS thought, g.score AS score "
        "FROM dyn.fountain_events f JOIN genius_tags g "
        "ON g.fountain_event_id = f.id "
        "WHERE g.class='STRIKING' AND g.score >= ?",
        (min_score,),
    ).fetchall()
    conv.close()

    buckets: dict[str, list] = {
        "self_reflection": [], "ingested": [],
        "instrumental": [], "other_unclassified": [], "empty": [],
    }
    for r in rows:
        buckets[classify(r["thought"])].append((r["score"], r["thought"]))

    total = sum(len(v) for v in buckets.values())
    print("=" * 68)
    print(f"GENIUS PROVENANCE  —  STRIKING thoughts with genius >= {min_score}")
    print(f"Total analysed: {total}")
    print("=" * 68)
    order = ["self_reflection", "ingested", "instrumental", "other_unclassified", "empty"]
    labels = {
        "self_reflection": "NEX's OWN reflection (genuine)",
        "ingested":        "INGESTED wisdom (quoted, not thought)",
        "instrumental":    "INSTRUMENTAL task-text (chores)",
        "other_unclassified": "unclassified (conservative: NOT credited)",
        "empty": "empty",
    }
    for k in order:
        n = len(buckets[k])
        if n == 0 and k == "empty":
            continue
        pct = (100.0 * n / total) if total else 0.0
        avg = (sum(s for s, _ in buckets[k]) / n) if n else 0.0
        print(f"  {labels[k]:42s} {n:5d}  ({pct:4.1f}%)  avg_genius={avg:.2f}")
        if show_samples and n:
            for s, th in sorted(buckets[k], reverse=True)[:3]:
                print(f"        [{s:.2f}] {th[:120]}")
    print("-" * 68)
    sr = len(buckets["self_reflection"])
    print(f"HEADLINE: {(100.0*sr/total if total else 0):.1f}% of NEX's best thoughts "
          f"are genuinely its OWN reflection.")
    print("(Conservative — unclassified is NOT counted as self. Real figure may be")
    print(" a little higher, but we under-count rather than inflate.)")
    return {k: len(v) for k, v in buckets.items()} | {"total": total}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-score", type=float, default=0.7)
    ap.add_argument("--samples", action="store_true")
    args = ap.parse_args()
    run(min_score=args.min_score, show_samples=args.samples)
