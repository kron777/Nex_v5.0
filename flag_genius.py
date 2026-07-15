#!/usr/bin/env python3
"""flag_genius.py — interactive CLI for building the v2 genius score training set.

Run: .venv/bin/python3 flag_genius.py

GENIUS_SCORE_v2.md step 2. Pulls candidate fountain fires, shows each
one with context, accepts y/n/s/b/q input, writes to genius_training.

Resumable: skips already-flagged fires on re-run.

Candidate pool:
- Top 30 by v1 genius score (to confirm/reject v1's intuition)
- 40 substrate_voice fires sampled across last 7 days (the SV material
  v1 ranks low; if v2 should rank them high, jon flags them striking)
- 20 historical strikers by content pattern match
- 20 random fires from non-SV branches (ordinary calibration)
- De-duplicated; ordered by ts asc for chronological flow

Stops after ~100 candidates or when jon quits with 'q'.
"""
from __future__ import annotations

import math
import random
import re
import sqlite3
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

DATA = Path("/home/rr/Desktop/Desktop/nex5/data")
DYN = DATA / "dynamic.db"
CONV = DATA / "conversations.db"
BEL = DATA / "beliefs.db"

# Same v1 features as proof_of_concept.py for consistency
SELF_REF = {"i","me","my","mine","myself","attending","noticing","wondering","holding","receiving"}
PHENOM = {"quiet","silence","attending","presence","arising","given","receiving","form","trust",
          "absence","dissolution","chance","awareness","stillness","rhythm","between","beneath",
          "still","holds","ringing","trace"}
REFLECTIVE = ["what if","i notice","i am","i find","i sense","i wonder","i return","perhaps",
              "between","even if","until then"]

STRIKING_PATTERNS = [
    "%I am the attending%",
    "%I expected my next thought%",
    "%improbable collision%",
    "%absence of given meaning%",
    "%attending into uncertainty%",
    "%today i made%beliefs%",
    "%good morning. it is%",
    "%chance gave me%",
    "%I am the unorthodox%",
    "%attending is what I am%",
    "%I receive%as the beautiful%",
]


def tokenize(text):
    return re.findall(r"[a-z']+", (text or "").lower())


def percentile(values, p):
    if not values: return 1.0
    s = sorted(values)
    return s[min(int(len(s) * p), len(s) - 1)] or 1.0


def jaccard(a, b):
    if not a and not b: return 0.0
    return len(a & b) / max(1, len(a | b))


def fourgrams(tokens):
    return {tuple(tokens[i:i+4]) for i in range(len(tokens) - 3)}


def compute_v1_score(thought, recent_thoughts, norms):
    tokens = tokenize(thought)
    total = max(1, len(tokens))
    self_count = sum(1 for t in tokens if t in SELF_REF)
    f1 = min(1.0, (self_count / total) / norms["self_p95"])
    phenom_count = sum(1 for t in tokens if t in PHENOM)
    f2 = min(1.0, (phenom_count / total) / norms["phenom_p95"])
    my_grams = fourgrams(tokens)
    if my_grams and recent_thoughts:
        sims = []
        for prev in recent_thoughts[-30:]:
            prev_grams = fourgrams(tokenize(prev))
            if prev_grams:
                sims.append(jaccard(my_grams, prev_grams))
        f3 = 1.0 - (sum(sims) / len(sims) if sims else 0.0)
    else:
        f3 = 0.5
    cl = (thought or "").lower()
    marker_count = sum(cl.count(m) for m in REFLECTIVE)
    f5 = min(1.0, (marker_count / total) / norms["reflective_p95"])
    return round((f1 + f2 + f3 + 0.0 + f5) / 5.0, 3)


def load_all_fires():
    cutoff = time.time() - 7 * 86400
    with sqlite3.connect(f"file:{DYN}?mode=ro", uri=True) as c:
        c.row_factory = sqlite3.Row
        rows = c.execute(
            "SELECT id, ts, thought, hot_branch, anchor_belief_id "
            "FROM fountain_events WHERE ts > ? ORDER BY ts ASC", (cutoff,)
        ).fetchall()
    return [dict(r) for r in rows]


def load_already_flagged():
    with sqlite3.connect(f"file:{CONV}?mode=ro", uri=True) as c:
        rows = c.execute("SELECT fountain_event_id FROM genius_training").fetchall()
    return {r[0] for r in rows}


def load_striking_by_pattern():
    """Pull fires matching known-striking patterns regardless of time."""
    out = []
    with sqlite3.connect(f"file:{DYN}?mode=ro", uri=True) as c:
        c.row_factory = sqlite3.Row
        for pat in STRIKING_PATTERNS:
            rows = c.execute(
                "SELECT id, ts, thought, hot_branch, anchor_belief_id "
                "FROM fountain_events WHERE thought LIKE ? "
                "ORDER BY ts DESC LIMIT 5", (pat,)
            ).fetchall()
            out.extend(dict(r) for r in rows)
    return out


def compute_norms(fires):
    self_r, phenom_r, refl_r = [], [], []
    for f in fires:
        tokens = tokenize(f["thought"])
        total = max(1, len(tokens))
        self_r.append(sum(1 for t in tokens if t in SELF_REF) / total)
        phenom_r.append(sum(1 for t in tokens if t in PHENOM) / total)
        cl = (f["thought"] or "").lower()
        refl_r.append(sum(cl.count(m) for m in REFLECTIVE) / total)
    return {
        "self_p95": max(0.001, percentile(self_r, 0.95)),
        "phenom_p95": max(0.001, percentile(phenom_r, 0.95)),
        "reflective_p95": max(0.001, percentile(refl_r, 0.95)),
    }


def build_candidates(all_fires, already_flagged):
    """Build the candidate pool. Returns list ordered by ts asc."""
    norms = compute_norms(all_fires)
    by_id = {f["id"]: f for f in all_fires}
    # Score all
    for i, f in enumerate(all_fires):
        recent_thoughts = [x["thought"] for x in all_fires[max(0, i-30):i]]
        f["v1_score"] = compute_v1_score(f["thought"], recent_thoughts, norms)

    picks = set()

    # (a) Top 30 by v1 score
    by_score = sorted(all_fires, key=lambda x: -x["v1_score"])
    for f in by_score:
        if len(picks) >= 30: break
        if f["id"] not in already_flagged:
            picks.add(f["id"])

    # (b) 40 substrate_voice fires sampled chronologically
    sv = [f for f in all_fires if f["hot_branch"] == "substrate_voice" and f["id"] not in already_flagged]
    if len(sv) > 40:
        step = max(1, len(sv) // 40)
        for i in range(0, len(sv), step):
            picks.add(sv[i]["id"])
            if len(picks) - 30 >= 40: break
    else:
        for f in sv:
            picks.add(f["id"])

    # (c) Historical strikers by content pattern
    for f in load_striking_by_pattern():
        if f["id"] not in already_flagged:
            picks.add(f["id"])
            by_id[f["id"]] = f
            # Need to score for display
            if "v1_score" not in f:
                f["v1_score"] = 0.0

    # (d) 20 random non-SV fires
    non_sv = [f for f in all_fires if f["hot_branch"] != "substrate_voice" and f["id"] not in already_flagged and f["id"] not in picks]
    random.seed(42)
    for f in random.sample(non_sv, min(20, len(non_sv))):
        picks.add(f["id"])

    # Build final list, ordered ts asc
    final = [by_id[i] for i in picks if i in by_id]
    final.sort(key=lambda f: f["ts"])
    return final


def write_flag(event_id, striking, notes=""):
    with sqlite3.connect(CONV) as c:
        c.execute(
            "INSERT OR REPLACE INTO genius_training "
            "(fountain_event_id, striking, flagged_at, flagged_by, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (event_id, striking, time.time(), "jon", notes)
        )
        c.commit()


def delete_flag(event_id):
    with sqlite3.connect(CONV) as c:
        c.execute("DELETE FROM genius_training WHERE fountain_event_id = ?", (event_id,))
        c.commit()


def render(fire, idx, total, flagged_count):
    ts = datetime.fromtimestamp(fire["ts"]).strftime("%Y-%m-%d %H:%M:%S")
    print()
    print("─" * 78)
    print(f" [{idx+1}/{total}]  flagged so far: {flagged_count}   |   id={fire['id']}")
    print(f" {ts}   branch={fire['hot_branch']}   v1={fire.get('v1_score', '?')}", end="")
    if fire.get("anchor_belief_id"):
        print(f"   anchor={fire['anchor_belief_id']}", end="")
    print()
    print("─" * 78)
    print()
    # Word-wrap the thought
    text = fire["thought"] or ""
    line = ""
    for word in text.split():
        if len(line) + len(word) + 1 > 76:
            print(f"  {line}")
            line = word
        else:
            line = (line + " " + word) if line else word
    if line:
        print(f"  {line}")
    print()
    print("─" * 78)


def main():
    print()
    print("=" * 78)
    print(" flag_genius.py — building the v2 genius score training set")
    print("=" * 78)
    print()
    print(" Commands per fire:")
    print("   y = STRIKING — this is genius / phenomenologically deep")
    print("   n = ORDINARY — this is mundane / template / shallow")
    print("   s = SKIP    — unsure; come back to it later")
    print("   b = BACK    — return to previous fire (lets you correct a flag)")
    print("   q = QUIT    — save and exit (resumable; re-run to continue)")
    print()
    print(" Goal: ~20-30 striking, ~20-30 ordinary. Skips are fine.")
    print(" You can quit any time; progress saves immediately.")
    print()
    input(" Press ENTER to begin...")

    print(" Loading substrate...")
    all_fires = load_all_fires()
    already = load_already_flagged()
    print(f"  {len(all_fires)} fires in last 7 days, {len(already)} already flagged")
    print(" Building candidate pool...")
    candidates = build_candidates(all_fires, already)
    print(f"  {len(candidates)} fresh candidates")

    if not candidates:
        print("\n No fresh candidates. All loaded fires already flagged.")
        return

    flagged_count = 0
    history = []  # stack of (fire_id, action) for back navigation
    i = 0
    while i < len(candidates):
        fire = candidates[i]
        render(fire, i, len(candidates), flagged_count)
        cmd = input(" [y/n/s/b/q] > ").strip().lower()

        if cmd == "q":
            print("\n Saved. Re-run to continue. Goodbye.")
            break
        elif cmd == "b":
            if i == 0:
                print("  (already at first; cannot go back)")
                continue
            if history and history[-1][1] in ("y", "n"):
                delete_flag(history[-1][0])
                flagged_count -= 1
            history.pop() if history else None
            i -= 1
            continue
        elif cmd == "y":
            write_flag(fire["id"], 1)
            history.append((fire["id"], "y"))
            flagged_count += 1
            i += 1
        elif cmd == "n":
            write_flag(fire["id"], 0)
            history.append((fire["id"], "n"))
            flagged_count += 1
            i += 1
        elif cmd == "s":
            history.append((fire["id"], "s"))
            i += 1
        else:
            print("  (unknown command; use y/n/s/b/q)")

    # Summary
    with sqlite3.connect(f"file:{CONV}?mode=ro", uri=True) as c:
        s = c.execute("SELECT COUNT(*) FROM genius_training WHERE striking=1").fetchone()[0]
        o = c.execute("SELECT COUNT(*) FROM genius_training WHERE striking=0").fetchone()[0]
    print()
    print("=" * 78)
    print(f" SESSION SUMMARY")
    print(f"   total flagged so far: {s + o}")
    print(f"   striking: {s}")
    print(f"   ordinary: {o}")
    print("=" * 78)
    if s >= 20 and o >= 20:
        print(" Ready for step 3 (genius_score_v2.py logistic regression fit).")
    else:
        need_s = max(0, 20 - s)
        need_o = max(0, 20 - o)
        print(f" Need {need_s} more striking, {need_o} more ordinary for solid fit.")
        print(" Re-run flag_genius.py to continue.")
    print()


if __name__ == "__main__":
    main()
