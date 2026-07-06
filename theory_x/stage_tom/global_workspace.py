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
import sqlite3
import time
from typing import Optional

_DYNAMIC_DB = "/home/rr/Desktop/nex5/data/dynamic.db"

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
    try:
        row = con.execute(
            "SELECT surprise_score, actual_content FROM surprise_events "
            "WHERE triggered_at > ? AND surprise_score > 0.3 "
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

        if not candidates:
            return ""

        # Competition: highest salience wins and is broadcast as the frame.
        winner = max(candidates, key=lambda c: c[0])
        return ("[WORKSPACE] Of everything active in you right now, this is "
                "most prominent: " + winner[1])
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
