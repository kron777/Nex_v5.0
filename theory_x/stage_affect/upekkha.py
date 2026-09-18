"""Equanimity (upekkhā) — hold steady when a strong pull (rāga / dveṣa) fires hot,
WITHOUT flattening affect (even, not numb) and WITHOUT suppressing compassion.

Faculty pattern mirrors compassion.py: a bounded read + a graded, fail-safe
prompt stance. Unlike compassion (which reads the PERSON's words), upekkhā reads
NEX's OWN internal pull — rāga (attachment/fixation, raga_detector) and dveṣa
(aversion, dvesa_detector) — and, when it is running hot, injects a hold-steady
note. Two hard lines:

  1. EVEN, NOT NUMB. The stance explicitly keeps her present and feeling; it
     steadies the yank of the pull, it does not deaden affect.
  2. NEVER SUPPRESS KARUNĀ. If the person's words carry genuine distress
     (compassion.distress_salience high), upekkhā stays SILENT — steadying a
     warranted compassionate response would be numbness, not equanimity.

Graded LIGHT / FULL. Gated by NEX5_EQUANIMITY (default OFF). Fail-safe: any
error, or the flag off, yields '' (no stance, no modulation).
"""
from __future__ import annotations

import os

import errors as error_channel

_LOG_SOURCE = "upekkha"

# Karuna guard: at/above this distress salience the person genuinely needs care,
# so equanimity holds its tongue (never flatten compassion).
_KARUNA_GUARD = 0.45
# dveṣa aversion level that counts as "hot".
_DVESA_HOT = 0.45
_DVESA_WARM = 0.25


def _raga_hot() -> float:
    """0..1 rāga hotness from raga_detector: fixated=1.0, mild=0.5, free=0.0.
    Fail-safe 0.0."""
    try:
        from theory_x.stage_tom import raga_detector
        r = raga_detector.detect() or {}
        lvl = r.get("raga", "free")
        return 1.0 if lvl == "fixated" else (0.5 if lvl == "mild" else 0.0)
    except Exception:
        return 0.0


def _dvesa_hot() -> float:
    """0..1 dveṣa hotness from dvesa_detector's aversion, banded. Fail-safe 0.0."""
    try:
        from theory_x.stage_tom import dvesa_detector
        d = dvesa_detector.detect() or {}
        av = float(d.get("aversion", 0.0) or 0.0)
        if av >= _DVESA_HOT:
            return 1.0
        if av >= _DVESA_WARM:
            return 0.5
        return 0.0
    except Exception:
        return 0.0


def _karuna_live(message: str) -> bool:
    """True iff the person's words carry genuine distress — equanimity must not
    steady a warranted compassionate response. Fail-safe False (do not block the
    guard's job on an embeddings error — but see call site: on error we stay
    conservative and let equanimity speak only when pulls are clearly hot)."""
    try:
        from theory_x.stage_affect.compassion import distress_salience
        return distress_salience(message or "") >= _KARUNA_GUARD
    except Exception:
        return False


def equanimity_read(message: str = "") -> dict:
    """Return {'grade': 'none'|'light'|'full', 'raga': x, 'dvesa': y,
    'karuna_live': bool}. Graded: FULL when a pull is hot (>=1.0 on either axis),
    LIGHT when one is warm; SILENT ('none') whenever karuna is live."""
    raga = _raga_hot()
    dvesa = _dvesa_hot()
    karuna = _karuna_live(message)
    if karuna:
        # Never flatten a warranted compassionate response.
        return {"grade": "none", "raga": raga, "dvesa": dvesa, "karuna_live": True}
    call = max(raga, dvesa)
    grade = "full" if call >= 1.0 else ("light" if call >= 0.5 else "none")
    return {"grade": grade, "raga": raga, "dvesa": dvesa, "karuna_live": False}


def stance_for(message: str = "") -> str:
    """Compose-path entry: a hold-steady note when a pull fires hot and karuna is
    not live. '' when nothing is hot, karuna is live, the flag is off, or on any
    error (fail-safe: no modulation)."""
    try:
        if os.environ.get("NEX5_EQUANIMITY") != "1":
            return ""
        read = equanimity_read(message)
        grade = read["grade"]
        if grade == "none":
            return ""
        which = []
        if read["raga"] >= 0.5:
            which.append("a clinging pull (rāga)")
        if read["dvesa"] >= 0.5:
            which.append("an aversive pull (dveṣa)")
        pull = " and ".join(which) or "a strong pull"
        if grade == "full":
            return (
                f"[Equanimity: {pull} is firing hot right now — hold steady and "
                "meet it evenly. Even, not numb: stay present and stay feeling, "
                "just don't let the pull yank the reply.]\n\n"
            )
        return (
            f"[Equanimity: {pull} is warming — hold steady, stay even and "
            "present.]\n\n"
        )
    except Exception as exc:
        error_channel.record(
            f"upekkha stance failed (non-fatal): {exc}",
            source=_LOG_SOURCE, exc=exc,
        )
        return ""
