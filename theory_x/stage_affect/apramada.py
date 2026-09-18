"""Conscientiousness (apramāda) — care-in-attention. Flags when a reply is about
to DROP a held commitment or gloss something she said she'd track.

Faculty pattern per compassion.py: a bounded read + a graded, fail-safe prompt
cue. Held commitments come from two live sources:
  * momentum — the unfinished thread she is actively carrying (resolved=0). Its
    carry_count is the built-in ANTI-NAG: past ~3 carries she has let the thread
    go (see generator's momentum anti-rut), so a still-held thread is
    carry_count in [1, _MAX_CARRY]. Beyond that it is abandoned — do NOT flag.
  * open problems (problem_memory.list_open) — explicit commitments to track.

"About to drop" = a held thread exists but the current turn is NOT attending it
(low token overlap). If the turn IS on the thread, it is being attended -> silent.

Two hard lines:
  - NOT A NAG: fires only when a genuine held thread is at real drop-risk;
    silent when nothing is held or the turn already attends it. carry_count caps
    it; open problems fire only while open.
  - NOT SELF-NARRATION: the cue is a vigilance pointer ("keep hold of X"), never
    "I am being conscientious now."

Graded LIGHT / FULL. Gated by NEX5_APRAMADA (default OFF). Fail-safe: '' on any
error or flag off.
"""
from __future__ import annotations

import os
import re
import sqlite3

import errors as error_channel

_LOG_SOURCE = "apramada"
_DYNAMIC_DB = "/home/rr/Desktop/Desktop/nex5/data/dynamic.db"

_MAX_CARRY = 2          # carry_count <= this = still held; beyond = let go (anti-nag)
_OVERLAP_MIN = 0.12     # token overlap below this = turn not attending the thread

_WORD_RE = re.compile(r"[a-z0-9]{3,}")
_STOP = frozenset(
    "the and for are was has had not but with into over from this that how what "
    "who when where which more most just now here there they them their his her "
    "its our you your item these those been being also very much many some".split())


def _tokens(text):
    return {t for t in _WORD_RE.findall((text or "").lower()) if t not in _STOP}


def _overlap(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def _held_threads() -> list:
    """Live held commitments as [(kind, weight, text)]. weight: 'full' for an
    explicit open problem, 'light' for a carried momentum fragment. Fail-safe []."""
    held = []
    # momentum — the actively-carried unfinished thread
    try:
        con = sqlite3.connect(f"file:{_DYNAMIC_DB}?mode=ro", uri=True, timeout=5)
        row = con.execute(
            "SELECT thought_fragment, carry_count, COALESCE(resolved,0) "
            "FROM momentum WHERE id=1").fetchone()
        con.close()
        if row and row[0]:
            frag, carry, resolved = row[0], int(row[1] or 1), int(row[2] or 0)
            if resolved == 0 and 1 <= carry <= _MAX_CARRY:
                held.append(("momentum", "light", frag))
    except Exception:
        pass
    # open problems — explicit tracked commitments
    try:
        from substrate import Reader, db_paths
        from theory_x.stage7_sustained.problem_memory import ProblemMemory
        paths = db_paths()
        pm = ProblemMemory(None, Reader(paths["conversations"]))
        for p in (pm.list_open() or [])[:3]:
            title = p.get("title") if isinstance(p, dict) else None
            if title:
                held.append(("problem", "full", title))
    except Exception:
        pass
    return held


def apramada_read(message: str = "") -> dict:
    """Return {'grade': 'none'|'light'|'full', 'at_risk': [texts]}. A held thread
    is at drop-risk when the current turn does not attend it (low token overlap).
    Grade is 'full' if any at-risk thread is an open problem, else 'light'."""
    threads = _held_threads()
    if not threads:
        return {"grade": "none", "at_risk": []}
    mtok = _tokens(message)
    at_risk = []
    grade = "none"
    for kind, weight, text in threads:
        if _overlap(mtok, _tokens(text)) < _OVERLAP_MIN:   # turn not attending it
            at_risk.append((weight, text))
    if not at_risk:
        return {"grade": "none", "at_risk": []}            # all held threads attended
    grade = "full" if any(w == "full" for w, _ in at_risk) else "light"
    return {"grade": grade, "at_risk": [t for _, t in at_risk]}


def stance_for(message: str = "") -> str:
    """Compose-path entry: a vigilance cue naming the held thread(s) at drop-risk.
    '' when nothing held, the turn attends it, flag off, or any error."""
    try:
        if os.environ.get("NEX5_APRAMADA") != "1":
            return ""
        read = apramada_read(message)
        if read["grade"] == "none":
            return ""
        threads = "; ".join(t[:90] for t in read["at_risk"][:2])
        if read["grade"] == "full":
            return (
                "[Care-in-attention: you have an open thread you committed to "
                f"tracking — don't let this turn quietly drop it: {threads}. Fold "
                "it in or say where it stands.]\n\n"
            )
        return (
            "[Care-in-attention: a thread you were carrying is still open — keep "
            f"hold of it as you answer: {threads}.]\n\n"
        )
    except Exception as exc:
        error_channel.record(
            f"apramada stance failed (non-fatal): {exc}",
            source=_LOG_SOURCE, exc=exc,
        )
        return ""
