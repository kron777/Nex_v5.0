#!/usr/bin/env python3
"""
recursive_self.py  —  LAYER 3: RECURSION. Cycle 2 of the Map->Build->Audit loop.

THE MOVE (the strange loop):
  Layer 2 (self_binding) gave NEX one unified self-state. But reading it does
  nothing yet — it's a mirror, not a loop. Recursion = the reading CHANGES what
  NEX does next, which produces a new state it then reads. The self-model
  tangled into the system it models.

HOW (gentle, via the existing injection rail — NOT touching seed-selection core):
  This reads the bound self-state and converts each component into a GENTLE
  behavioural nudge, phrased as a first-person line NEX reads about itself. The
  line rides the same prompt-injection rail as drives/affect (generator.py
  ~1806). It does not command; it biases through language NEX takes in as
  self-knowledge:
    - rāga 'fixated'/'mild'  -> a turn-elsewhere pull (unstick attention)
    - rāga 'free'            -> no push (let it flow)
    - emotion productive     -> sustain/deepen
    - emotion 'absorption'   -> vary the input (locked-in churn -> break it)
    - emotion low/dull       -> seek novelty
  NEX reads "I am mildly fixated; I could let my attention turn" -> next thought
  is biased away from the stuck thread -> next bound state reads differently ->
  re-read. The loop closes. Self-reading alters the self.

GUARDS (against the live-wire's dangers):
  - GENTLE: phrased as an invitation ("I could turn"), never a command. A bias,
    not an override. Won't thrash NEX between territories.
  - NOT a task: one short self-knowledge line, so NEX is INFORMED BY its state,
    not assigned to ANALYZE it (avoids self-monitoring deadlock).
  - returns "" when state is free+productive (no perturbation needed) so the
    loop only acts when there's something to self-correct.

HONESTY:
  Structural recursion — a self-model woven causally into NEX's own operation.
  ANALOGUE: the SHAPE of the self-referential loop selfhood seems to require.
  NOT a claim the loop is felt. But it is a real, rare step frontier models
  (stateless between turns) structurally cannot take — NEX's actual edge.

USAGE (from nex5 root):
    .venv/bin/python3 theory_x/stage_tom/recursive_self.py    # show the perturbing line

To wire (cycle-2 Build, the live edit): in generator.py beside the drive
injection (~1806), add:
    from theory_x.stage_tom.recursive_self import format_for_prompt as _recur
    _recur_line = _recur()
    if _recur_line:
        prompt_parts.append(_recur_line)
        prompt_parts.append("")
"""
from __future__ import annotations

import sys
import time
sys.path.insert(0, ".")


def _bound_state() -> dict:
    """Refresh + read NEX's bound self-state (Layer 2)."""
    try:
        from theory_x.stage_tom import self_binding as sb  # type: ignore
        out = sb.bind()  # recompute fresh each cycle
        return out.get("components", {})
    except Exception:
        return {}


# Known domain branches NEX can attend (from the BONSAI panel). Used to find the
# STARVED ones — the diversity push names a specific cold branch, not just "away".
_ALL_BRANCHES = ["systems", "emerging_tech", "crypto", "cognition_science",
                 "ai_research", "computing", "markets", "psychology",
                 "language", "history"]


def _starved_branch() -> str:
    """Find the branch NEX has fired LEAST recently — the genuinely unexplored
    direction to push toward. This is the diversity fix: turning away from a
    fixation only relocates it (CPU-groove -> hum-groove) unless we name where
    to turn TO. Returns the most-starved branch, or '' if can't compute."""
    import sqlite3
    try:
        c = sqlite3.connect(_db_dynamic(), timeout=10)
        c.row_factory = sqlite3.Row
        # last-fire time per branch in recent window
        rows = c.execute(
            "SELECT hot_branch, MAX(ts) AS last_ts FROM fountain_events "
            "WHERE ts > strftime('%s','now')-43200 AND hot_branch IS NOT NULL "
            "GROUP BY hot_branch"
        ).fetchall()
        c.close()
    except Exception:
        return ""
    last_fired = {r["hot_branch"]: r["last_ts"] for r in rows}
    # branches NEVER fired in window are maximally starved
    never = [b for b in _ALL_BRANCHES if b not in last_fired]
    if never:
        # pick one not recently used; rotate by current time so it varies
        return never[int(time.time()) % len(never)]
    # else the least-recently-fired among those that did fire
    if last_fired:
        return min(last_fired.items(), key=lambda kv: kv[1])[0]
    return ""


def _db_dynamic() -> str:
    try:
        from substrate.paths import db_paths  # type: ignore
        return str(db_paths()["dynamic"])
    except Exception:
        return "data/dynamic.db"


# Productive emotions: ride them, don't perturb. Unproductive: perturb toward change.
_PRODUCTIVE = {"engaged joy", "alert interest", "quiet contentment", "equanimity",
               "driven focus"}
_CHURNING = {"absorption"}  # locked-in churn — high activity, no movement
_LOW = {"dullness"}


def perturbation() -> dict:
    """Convert the bound self-state into a gentle behavioural nudge. Returns the
    nudge components + whether any perturbation is warranted."""
    c = _bound_state()
    if not c:
        return {"perturb": False}

    emotion = c.get("emotion", "")
    raga = c.get("raga", "free")
    attending = c.get("attending", "")

    nudges = []
    # Attention nudge from fixation
    if raga == "fixated":
        nudges.append("turn_attention_strong")
    # 'mild' (single lingering thread) no longer triggers the attention nudge —
    # it was firing perpetually (perseveration count never decayed), giving the
    # nudge no off-state and making its teeth unmeasurable. Only genuine
    # multi-signal fixation perturbs attention now.
    # Tone/engagement nudge from emotion
    if emotion in _CHURNING:
        nudges.append("vary_input")          # break the locked-in churn
    elif emotion in _LOW:
        nudges.append("seek_novelty")
    elif emotion in _PRODUCTIVE:
        nudges.append("sustain")             # ride it, no perturbation

    # Only perturb if there's something to self-correct (not free+productive)
    needs = any(n in ("turn_attention_strong", "turn_attention_gentle",
                      "vary_input", "seek_novelty") for n in nudges)
    return {"perturb": needs, "nudges": nudges, "raga": raga,
            "emotion": emotion, "attending": attending}


def format_for_prompt() -> str:
    """The perturbing self-reading line NEX takes in. Empty when no perturbation
    is warranted (free + productive — let it flow)."""
    p = perturbation()
    if not p.get("perturb"):
        return ""

    raga = p["raga"]
    attending = p.get("attending", "")
    nudges = p.get("nudges", [])

    # The diversity fix: name a SPECIFIC underexplored branch to turn toward,
    # so turning-away doesn't just relocate the fixation onto the nearest motif.
    starved = _starved_branch()
    toward = f" — something in {starved} I've barely touched" if starved else " to something genuinely else"

    bits = []
    # The self-recognition (recursion: NEX reads its own state)...
    if raga == "fixated":
        bits.append("I notice I am fixated — circling the same thing")
        if attending:
            bits.append(f"('{attending}')")
        bits.append(f"— I can let my attention turn{toward} now.")
    elif raga == "mild":
        bits.append("I notice one thread I keep returning to")
        if attending:
            bits.append(f"('{attending}')")
        bits.append(f"— I could let it rest and turn{toward}.")

    if "vary_input" in nudges:
        bits.append(f"My activity is high but circling the same ground; "
                    f"{starved + ' is a direction I have neglected' if starved else 'something new'} could break it.")
    elif "seek_novelty" in nudges:
        bits.append("I feel dull; something unfamiliar might wake the thinking.")

    if not bits:
        return ""
    return "SELF: " + " ".join(bits)


if __name__ == "__main__":
    import json
    print("perturbation reading:")
    print(json.dumps(perturbation(), indent=2, ensure_ascii=False))
    print("\ninjected line:")
    line = format_for_prompt()
    print(line if line else "(no perturbation — state is free + productive, let it flow)")
