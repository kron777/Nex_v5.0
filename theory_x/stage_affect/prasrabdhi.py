"""Pliancy (praśrabdhi) — releases stuck loops. When compose circles the same
belief cluster without progress, signal "let it move" (shift to fresh ground).

Faculty pattern per compassion.py: a bounded, graded, fail-safe read + signal.

Distinguishing a STUCK LOOP from a LEGITIMATELY SUSTAINED THREAD (the hard part,
and the difference from vīrya):
  * Circling is read from raga_detector (repetition / groove / branch-dominance
    -> the mind returning to the same territory).
  * But deep, productive work on her actual worked focus ALSO looks like staying
    on one topic. So praśrabdhi fires ONLY when the circling is NOT on her
    current focus — i.e. she is looping on aimless ground (no hard thread, or
    recent fires have drifted OFF the focus). Circling ON the focus = legitimate
    sustain (vīrya's territory) -> praśrabdhi stays SILENT, it does not cut it.

Coordinates with the crowding-trim seams, does NOT double-trim: praśrabdhi is a
behavioural nudge ("let it move"), never a content cut. It touches no belief
block, history, or best-of-cluster gate — those trim redundant CONTENT;
praśrabdhi only signals a shift. No overlap.

Graded LIGHT / FULL. Gated by NEX5_PRASRABDHI (default OFF). Fail-safe: '' on any
error or flag off.
"""
from __future__ import annotations

import os

import errors as error_channel

_LOG_SOURCE = "prasrabdhi"
_DRIFT_ON_FOCUS = 0.55   # drift below this = recent fires still ON the focus (legit)


def _circling() -> float:
    """0..1 circling severity from raga_detector: fixated=1.0, mild=0.5, free=0.0.
    Fail-safe 0.0."""
    try:
        from theory_x.stage_tom import raga_detector
        r = raga_detector.detect() or {}
        lvl = r.get("raga", "free")
        return 1.0 if lvl == "fixated" else (0.5 if lvl == "mild" else 0.0)
    except Exception:
        return 0.0


def _off_focus() -> bool:
    """True iff the circling is NOT on her current worked focus — no hard thread,
    or recent fires have drifted off it. When on-focus, circling is legitimate
    deep work and praśrabdhi must not break it. Fail-safe True only when there is
    genuinely no focus to protect; on error, conservative False (don't cut)."""
    try:
        from theory_x.stage_affect.virya import _hard_thread, _drift_fraction
        thread = _hard_thread()
        if not thread:
            return True                     # nothing to sustain -> circling is aimless
        return _drift_fraction(thread) >= _DRIFT_ON_FOCUS
    except Exception:
        return False                        # conservative: don't break a possible sustain


def prasrabdhi_read() -> dict:
    """Return {'grade':'none'|'light'|'full','circling':x,'off_focus':bool}. Fires
    only when circling AND off-focus (not a legitimately sustained thread)."""
    circ = _circling()
    if circ <= 0.0:
        return {"grade": "none", "circling": circ, "off_focus": False}
    off = _off_focus()
    if not off:
        # Circling ON the focus = legitimate sustain (vīrya) -> do not break it.
        return {"grade": "none", "circling": circ, "off_focus": False}
    grade = "full" if circ >= 1.0 else "light"
    return {"grade": grade, "circling": circ, "off_focus": True}


def stance_for() -> str:
    """Compose-path entry: a let-it-move nudge when she is circling aimlessly. ''
    when not circling, circling is on-focus (legit sustain), flag off, or error."""
    try:
        if os.environ.get("NEX5_PRASRABDHI") != "1":
            return ""
        read = prasrabdhi_read()
        if read["grade"] == "none":
            return ""
        if read["grade"] == "full":
            return (
                "[Pliancy: you're circling the same ground without it moving — let "
                "it go and shift to fresh material; you don't have to keep "
                "returning to this cluster.]\n\n"
            )
        return (
            "[Pliancy: a slight loop is forming — let it move, don't keep "
            "re-treading the same point.]\n\n"
        )
    except Exception as exc:
        error_channel.record(
            f"prasrabdhi stance failed (non-fatal): {exc}",
            source=_LOG_SOURCE, exc=exc,
        )
        return ""
