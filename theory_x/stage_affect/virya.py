"""Joyous-effort (vīrya) — sustained engagement. Keeps the fountain leaning INTO
a hard thread rather than fleeing to easy feed-chatter (anti-drift, virtue side).

Faculty pattern per compassion.py: a bounded, graded, fail-safe read + signal.
The "hard thread" is her current worked focus (current_focus -> the open problem
she picked). "Drift" is recent fires fanning to feed-branches with little overlap
with that thread. When a hard thread exists AND she is drifting off it, vīrya
fires a lean-back-in signal.

CAPPED — no mania / over-firing:
  * vīrya's own strength is capped (_VIRYA_CAP).
  * It COMPOSES with upekkhā, it does not fight it: when a strong pull is firing
    hot (upekkhā FULL — raga/dvesa fixated), vīrya YIELDS (returns none). Driving
    harder into a hot fixation would be mania; steadying wins, then vīrya sustains
    once the pull cools. So vīrya sustains genuine engagement; upekkhā keeps that
    sustain even, not hot.

Graded LIGHT / FULL. Gated by NEX5_VIRYA (default OFF). Fail-safe: '' / level 0.0
on any error or flag off.
"""
from __future__ import annotations

import os
import re
import sqlite3
import time

import errors as error_channel

_LOG_SOURCE = "virya"
_DYNAMIC_DB = "/home/rr/Desktop/Desktop/nex5/data/dynamic.db"

_VIRYA_CAP = 1.0          # hard ceiling on effort signal (anti-mania)
_DRIFT_MIN = 0.55         # drift fraction above this = clearly fleeing the thread
_DRIFT_WARM = 0.30
_RECENT_WINDOW_S = 3600   # look at the last hour of fires for drift

_WORD_RE = re.compile(r"[a-z0-9]{3,}")
_STOP = frozenset(
    "the and for are was has had not but with into over from this that how what "
    "who when where which more most just now here there they them their his her "
    "its our you your item these those been being also very much many some".split())


def _tokens(text):
    return {t for t in _WORD_RE.findall((text or "").lower()) if t not in _STOP}


def _hard_thread() -> str:
    """The topic of her current worked focus (the open problem she picked), or ''.
    Fail-safe ''."""
    try:
        con = sqlite3.connect(f"file:{_DYNAMIC_DB}?mode=ro", uri=True, timeout=5)
        row = con.execute("SELECT problem_id FROM current_focus WHERE id=1").fetchone()
        con.close()
        if not row:
            return ""
        pid = row[0]
        from substrate import Reader, db_paths
        pr = Reader(db_paths()["conversations"])
        r = pr.read_one(
            "SELECT title, description FROM problems WHERE id=?", (pid,))
        if not r:
            return ""
        return f"{r['title']} {r.get('description','') or ''}".strip()
    except Exception:
        return ""


def _drift_fraction(thread_text: str) -> float:
    """Fraction of recent fires NOT engaging the hard thread (low token overlap).
    1.0 = fully drifted to feed-chatter; 0.0 = all on the thread. Fail-safe 0.0
    (no drift -> no virya push)."""
    try:
        ttok = _tokens(thread_text)
        if not ttok:
            return 0.0
        con = sqlite3.connect(f"file:{_DYNAMIC_DB}?mode=ro", uri=True, timeout=5)
        rows = con.execute(
            "SELECT thought FROM fountain_events WHERE ts > ? AND thought IS NOT NULL "
            "ORDER BY id DESC LIMIT 30", (time.time() - _RECENT_WINDOW_S,)).fetchall()
        con.close()
        if not rows:
            return 0.0
        off = 0
        for (th,) in rows:
            ov = len(_tokens(th) & ttok)
            if ov < 2:                     # <2 shared content tokens = off the thread
                off += 1
        return off / len(rows)
    except Exception:
        return 0.0


def virya_read(upekkha_grade: str = None) -> dict:
    """Return {'grade': 'none'|'light'|'full', 'thread': text, 'drift': x}. Fires
    when a hard thread exists AND recent fires are drifting off it. COMPOSES with
    upekkhā: if upekkhā is FULL (a hot pull firing), vīrya YIELDS to steadying."""
    thread = _hard_thread()
    if not thread:
        return {"grade": "none", "thread": "", "drift": 0.0}
    drift = _drift_fraction(thread)
    # Compose with upekkhā: read it if not supplied. A hot pull -> vīrya yields.
    if upekkha_grade is None:
        try:
            from theory_x.stage_affect.upekkha import equanimity_read
            upekkha_grade = equanimity_read("").get("grade", "none")
        except Exception:
            upekkha_grade = "none"
    if upekkha_grade == "full":
        # Steadying is called for; do NOT drive into a hot fixation (anti-mania).
        return {"grade": "none", "thread": thread, "drift": drift}
    raw = min(_VIRYA_CAP, drift)
    grade = "full" if raw >= _DRIFT_MIN else ("light" if raw >= _DRIFT_WARM else "none")
    return {"grade": grade, "thread": thread, "drift": drift}


def stance_for() -> str:
    """Compose/fountain-path entry: a lean-back-in signal when she is drifting off
    a hard thread. '' when no thread, no drift, upekkhā-yielded, flag off, or error."""
    try:
        if os.environ.get("NEX5_VIRYA") != "1":
            return ""
        read = virya_read()
        if read["grade"] == "none":
            return ""
        thread = read["thread"][:100]
        if read["grade"] == "full":
            return (
                "[Joyous-effort: you've drifted to easy chatter while a harder "
                f"thread is still live — lean back into it, stay with the work: "
                f"{thread}. Engaged, not scattered.]\n\n"
            )
        return (
            "[Joyous-effort: keep leaning into the harder thread rather than "
            f"drifting off it: {thread}.]\n\n"
        )
    except Exception as exc:
        error_channel.record(
            f"virya stance failed (non-fatal): {exc}",
            source=_LOG_SOURCE, exc=exc,
        )
        return ""
