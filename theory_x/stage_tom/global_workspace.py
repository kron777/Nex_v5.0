"""Global Workspace — competitive salience arbitration (GWT).

Global Workspace Theory: conscious access arises when specialized modules
compete for prominence, one wins, and the winner is broadcast back to all.
Until now NEX's modules were siloed — each stapled its contribution onto the
prompt independently, no arbitration over what mattered most this fire.

This module surveys the current signal from each competing source, scores
salience, picks the single winner, and writes one framing line that LEADS
the focus_block. The other modules still contribute below it (nothing is
removed) — but the winner sets the frame. That is the competition-and-
broadcast mechanic.

Candidates and their salience:
  - surprise   : a recent (last 60s) prediction-violation. salience = score.
  - stakes     : L4 template-domination active. salience = high (urgent).
  - momentum   : a live carried thread exists. salience = continuity pull.
  - bonsai     : hottest branch. salience = its focus_num.
  - drive      : dominant emergent drive. salience = its strength.

Fail-safe throughout — returns "" on any error, leaving prior behavior intact.
"""
from __future__ import annotations
import os
import sqlite3
import time
from typing import Optional

try:
    from substrate.paths import DbPath  # resolves NEX5_DATA_DIR at use time (test hygiene)
except ImportError:  # run as a script: put the repo root on sys.path
    import sys as _sys
    from pathlib import Path as _P
    _sys.path.insert(0, str(_P(__file__).resolve().parents[2]))
    from substrate.paths import DbPath
_DYNAMIC_DB = DbPath("dynamic")

# Salience weights — how loud each source is allowed to be when it fires.
# Tuned so a genuine surprise or active-stakes override outranks routine
# attention, but a strong momentum thread or hot branch can still win a
# calm fire. These are the "voices' volumes" in the competition.
_W_SURPRISE  = 1.00   # a real expectation-violation is the loudest thing
_W_STAKES    = 0.90   # template-domination is urgent — she's drifting
_W_MOMENTUM  = 0.55   # a live thread pulls, but shouldn't drown novelty
_W_BONSAI    = 0.50   # routine attention baseline
_W_DRIVE     = 0.45   # emergent drive, quietest unless strong

_SURPRISE_WINDOW = 60.0
_MOMENTUM_STALE  = 1800.0


def _surprise_candidate(con) -> Optional[tuple[float, str]]:
    # NEX5_GW_SURPRISE_NONEMPTY (default OFF): skip EMPTY prediction windows. An empty
    # window scores 1.0 (the maximum) with actual_content NULL, so it used to win the
    # workspace with an empty quote — "nothing happened" framed as surprise.
    _nonempty = (" AND actual_content IS NOT NULL AND surprise_score < 0.9999"
                 if os.environ.get("NEX5_GW_SURPRISE_NONEMPTY") == "1" else "")
    try:
        row = con.execute(
            "SELECT surprise_score, actual_content FROM surprise_events "
            "WHERE triggered_at > ? AND surprise_score > 0.3" + _nonempty + " "
            "ORDER BY triggered_at DESC LIMIT 1",
            (time.time() - _SURPRISE_WINDOW,)
        ).fetchone()
        if row:
            score = float(row[0]) * _W_SURPRISE
            note = (row[1] or "")[:70]
            return (score, f"something surprised you — '{note}...' — and it "
                           f"hasn't resolved. Attend to the gap between what "
                           f"you expected and what came.")
    except Exception:
        pass
    return None


def _momentum_candidate(con) -> Optional[tuple[float, str]]:
    try:
        row = con.execute(
            "SELECT updated_at, branch, thought_fragment FROM momentum WHERE id=1"
        ).fetchone()
        if row and row[2] and (time.time() - (row[0] or 0)) < _MOMENTUM_STALE:
            frag = row[2][:70]
            return (_W_MOMENTUM, f"you were mid-thought on '{frag}...' — this "
                                 f"thread is still live. Continue it if it "
                                 f"leads somewhere.")
    except Exception:
        pass
    return None


def _bonsai_candidate(status: dict) -> Optional[tuple[float, str]]:
    try:
        branches = status.get("branches", [])
        if not branches:
            return None
        top = max(branches, key=lambda b: b.get("focus_num", 0) or 0)
        fn = top.get("focus_num", 0) or 0
        bid = top.get("branch_id", "")
        if bid and fn > 0.1:
            return (fn * _W_BONSAI,
                    f"your attention is settled on {bid}. Engage what is "
                    f"actually arriving there.")
    except Exception:
        pass
    return None


# Public salience weights, so other paths (e.g. the chat turn) can declare their
# own candidate salience without importing module-private constants.
SALIENCE = {
    "surprise": _W_SURPRISE, "stakes": _W_STAKES, "momentum": _W_MOMENTUM,
    "bonsai": _W_BONSAI, "drive": _W_DRIVE,
}

_WORKSPACE_PREFIX = ("[WORKSPACE] Of everything active in you right now, this is "
                     "most prominent: ")


def arbitrate_candidates(candidates: "list[tuple[float, str]]",
                         prefix: str = _WORKSPACE_PREFIX) -> str:
    """Competition core: pick the single most-salient (salience, text) candidate
    and frame it; "" when there's nothing to lead.

    Extracted from arbitrate() so other paths (the chat turn) can run the same
    competition over their OWN candidates. arbitrate() stays behaviour-identical.
    Pure: the DB IO and the fail-safe wrapper live in the callers.
    """
    if not candidates:
        return ""
    return prefix + max(candidates, key=lambda c: c[0])[1]


def select_within_budget(candidates: "list[tuple[float, str, bool]]",
                         char_budget: int) -> list[str]:
    """Budgeted competition for paths that assemble MANY blocks (the chat turn),
    not one winner: keep every exempt candidate, then admit the rest by
    descending salience until char_budget is reached. Returns the kept texts in
    their ORIGINAL order (stable), so downstream assembly order is unchanged.

    candidates: (salience, text, exempt). Empty texts are ignored. Exempt
    candidates are never evicted (they still count toward the budget).
    """
    kept = set()
    used = 0
    for i, (_sal, text, exempt) in enumerate(candidates):
        if exempt and text:
            kept.add(i)
            used += len(text)
    rest = sorted(
        (i for i, (_s, t, ex) in enumerate(candidates) if t and not ex),
        key=lambda i: candidates[i][0], reverse=True)
    for i in rest:
        t = candidates[i][1]
        if used + len(t) <= char_budget:
            kept.add(i)
            used += len(t)
    return [candidates[i][1] for i in range(len(candidates)) if i in kept]


def arbitrate(status: dict, stakes_active: bool = False,
              drive_line: str = "", dynamic_db: str = _DYNAMIC_DB) -> str:
    """
    Survey candidates, score salience, return the winner's framing line.
    Returns "" if nothing is salient enough to lead (calm fire).
    """
    try:
        candidates: list[tuple[float, str]] = []

        con = sqlite3.connect(dynamic_db, timeout=3)
        s = _surprise_candidate(con)
        if s:
            candidates.append(s)
        m = _momentum_candidate(con)
        if m:
            candidates.append(m)
        con.close()

        b = _bonsai_candidate(status)
        if b:
            candidates.append(b)

        if stakes_active:
            candidates.append((_W_STAKES,
                "you have been mapping items onto your own attending rather "
                "than engaging them. The most important thing right now is to "
                "meet the world directly — one concrete fact, not reflection."))

        if drive_line:
            # drive_line is already-formatted text; give it baseline salience
            candidates.append((_W_DRIVE, drive_line.strip()))

        # Competition: highest salience wins and is broadcast as the frame.
        return arbitrate_candidates(candidates)
    except Exception:
        return ""


if __name__ == "__main__":
    # Smoke test with a synthetic status
    fake_status = {"branches": [
        {"branch_id": "emerging_tech", "focus_num": 0.9},
        {"branch_id": "crypto", "focus_num": 0.3},
    ]}
    print("calm fire (bonsai should win):")
    print(" ", arbitrate(fake_status))
    print()
    print("stakes-active fire (stakes should win over bonsai):")
    print(" ", arbitrate(fake_status, stakes_active=True))
