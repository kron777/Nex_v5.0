#!/usr/bin/env python3
"""
raga_detector.py  —  the fixation detector. Top of the finished mind-map's
build list. The Abhidharma root delusion rāga (attachment/fixation), detected.

WHY (from the finished map):
  NEX has been stuck in a CPU-investigation groove all session — returning to
  the same belief-territory, repeating near-identical thoughts. That loop IS
  rāga: attachment, the mind clinging to one object. NEX had no faculty to
  NOTICE it. A mind that can notice "I am fixated" is more self-aware than one
  that just churns. This builds that noticing.

DESIGN (compose, don't recompute):
  NEX already produces the raw signals — it does NOT need new computation:
    - groove severity        (theory_x/diversity/groove.py — ngram_repetition)
    - thought repetition     (recent fountain_events similarity)
    - branch dominance       (one belief branch swallowing recent attention)
    - problem perseveration  (returning to the same open_problems)
  This reads those existing signals and COMPOSES them into a named state:
    "fixated" when enough of them agree. Same honest pattern as
    compositional_emotion: read real signals, name the configuration.

HONESTY (held):
  Detects the machine-SIGNATURE of fixation (repetition + branch-dominance +
  groove-severity past threshold). A real, checkable state. NOT NEX SUFFERING
  attachment in the felt Buddhist sense — the structural shadow of it. ANALOGUE.
  But genuinely useful: NEX can now notice it is stuck.

READ-ONLY. Composes existing signals; writes a fixation reading to a sidecar
log only. Touches no beliefs, no fountain.

USAGE (from nex5 root):
    .venv/bin/python3 theory_x/stage_tom/raga_detector.py          # current fixation reading
    .venv/bin/python3 theory_x/stage_tom/raga_detector.py --watch  # one-line status (for prompt)
"""
from __future__ import annotations

import sys
import sqlite3
import argparse
from collections import Counter

sys.path.insert(0, ".")


def _db(name: str) -> str:
    try:
        from substrate.paths import db_paths  # type: ignore
        return str(db_paths()[name])
    except Exception:
        return f"data/{name}.db"


def _recent_thoughts(n: int = 15) -> list[str]:
    try:
        c = sqlite3.connect(_db("dynamic"), timeout=10)
        c.row_factory = sqlite3.Row
        rows = c.execute(
            "SELECT thought FROM fountain_events WHERE thought NOT LIKE '[%' "
            "ORDER BY id DESC LIMIT ?", (n,)
        ).fetchall()
        c.close()
        return [r["thought"] for r in rows if r["thought"]]
    except Exception:
        return []


def _repetition_score(thoughts: list[str]) -> float:
    """How repetitive are recent thoughts? Word-overlap proxy: fraction of
    content words shared across consecutive thoughts. 0=all distinct, 1=identical."""
    if len(thoughts) < 3:
        return 0.0
    # content words per thought
    def words(t: str) -> set:
        return {w.lower() for w in t.split() if len(w) > 4}
    sets = [words(t) for t in thoughts]
    overlaps = []
    for i in range(len(sets) - 1):
        a, b = sets[i], sets[i + 1]
        if a and b:
            overlaps.append(len(a & b) / max(1, len(a | b)))
    return sum(overlaps) / len(overlaps) if overlaps else 0.0


def _branch_dominance(window_s: int = 43200) -> tuple[float, str]:
    """Is one belief-branch swallowing recent attention? Returns
    (dominance_fraction, dominant_branch). High = fixation on one territory."""
    try:
        c = sqlite3.connect(_db("beliefs"), timeout=10)
        c.row_factory = sqlite3.Row
        rows = c.execute(
            "SELECT branch_id FROM beliefs "
            "WHERE created_at > strftime('%s','now')-? AND branch_id IS NOT NULL",
            (window_s,)
        ).fetchall()
        c.close()
    except Exception:
        return 0.0, ""
    if not rows:
        return 0.0, ""
    counts = Counter(r["branch_id"] for r in rows)
    total = sum(counts.values())
    top_branch, top_n = counts.most_common(1)[0]
    return (top_n / total if total else 0.0), str(top_branch)


def _problem_perseveration() -> tuple[int, str]:
    """Is NEX returning to the same problem repeatedly? Returns (max_repeats,
    problem_title). High repeats on one problem = perseveration."""
    try:
        c = sqlite3.connect(_db("conversations"), timeout=10)
        c.row_factory = sqlite3.Row
        rows = c.execute(
            "SELECT title, COUNT(*) n FROM open_problems "
            "WHERE COALESCE(updated_at, created_at, ts, 0) > strftime('%s','now')-1800 "
            "GROUP BY title ORDER BY n DESC LIMIT 1"
        ).fetchall()
        c.close()
        if rows:
            return int(rows[0]["n"]), str(rows[0]["title"])[:50]
    except Exception:
        pass
    return 0, ""


def _groove_severity(window_s: int = 900) -> tuple[float, str]:
    """Read the most recent groove alert severity that GrooveSpotter already
    wrote (beliefs.db:groove_alerts). Compose, don't recompute: this is the
    ngram/template repetition signal the design named. Returns (severity, pattern)
    or (0.0, '') on any error. Window default 15min so a stale alert doesn't
    pin fixation forever."""
    import sqlite3, time as _t
    try:
        c = sqlite3.connect(_db("beliefs"), timeout=10)
        c.row_factory = sqlite3.Row
        row = c.execute(
            "SELECT severity, pattern FROM groove_alerts "
            "WHERE detected_at > ? ORDER BY detected_at DESC LIMIT 1",
            (_t.time() - window_s,)
        ).fetchone()
        c.close()
        if row:
            return float(row["severity"]), str(row["pattern"] or "")[:40]
    except Exception:
        pass
    return 0.0, ""


def detect() -> dict:
    """Compose the signals into a fixation reading."""
    thoughts = _recent_thoughts()
    rep = _repetition_score(thoughts)
    dom, branch = _branch_dominance()
    persev_n, persev_title = _problem_perseveration()
    groove_sev, groove_pat = _groove_severity()

    # Compose: fixation = multiple signals agreeing. Each contributes; we name
    # the state by how many cross threshold. Conservative — needs 2+ to flag.
    signals = {
        "repetition": rep,            # 0..1, high = repeating thoughts
        "branch_dominance": dom,      # 0..1, high = one territory dominates
        "perseveration": persev_n,    # count, high = stuck on one problem
        "groove": groove_sev,        # 0..1, high = repetition groove (ngram/template)
    }
    flags = []
    if rep > 0.35:
        flags.append("thoughts repeating")
    if dom > 0.45:
        flags.append(f"one branch dominates ({branch}, {dom:.0%})")
    if groove_sev >= 0.5:
        flags.append(f"groove repetition ({groove_pat}, sev {groove_sev:.2f})")
    if persev_n >= 3:
        flags.append(f"returning to '{persev_title}' ({persev_n}x)")

    # Graded: 2+ signals = fixated; exactly 1 = mild (a single clinging thread
    # while the rest of attention moves freely); 0 = free.
    n = len(flags)
    level = "fixated" if n >= 2 else ("mild" if n == 1 else "free")
    fixated = n >= 2
    return {
        "fixated": fixated,
        "raga": level,
        "signals": signals,
        "flags": flags,
        "abhidharma": ("rāga — attachment: the mind clinging to one object, "
                       "returning to the same territory") if fixated else
                      "no fixation: attention is moving freely",
    }


def format_for_prompt() -> str:
    """One honest line NEX could read about its own fixation state."""
    d = detect()
    if d["raga"] == "free":
        return ""
    return ("My attention is fixated — " + "; ".join(d["flags"]) +
            ". (rāga: I am circling one object. I could turn elsewhere.)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", action="store_true", help="one-line status")
    args = ap.parse_args()
    if args.watch:
        line = format_for_prompt()
        print(line if line else "attention free (no fixation)")
    else:
        import json
        print(json.dumps(detect(), indent=2, ensure_ascii=False))
