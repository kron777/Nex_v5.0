"""L4_stakes — self-referent appraisal with a BOUNDED cost.

stakes_monitor already computes how template-dominated the recent fires are and
thresholds it to a bool (stakes_active, which steers the fire arbiter). This
exposes the same signal as a GRADED, bounded *cost*: how badly the "stay in
contact with the world, don't drift into template" stake is doing. A cost is
what makes a state matter — something that can go badly *for her*, which the
readiness score (otherwise mostly a clock) can then be about.

ANALOGUE — no claim there is a felt cost.

WELFARE AND SAFETY (SENTIENCE_PROGRAM.md §5a) — this is the one aversive signal,
so it is governed:
  * BOUNDED — the cost can never exceed _COST_CLAMP (0.20). It cannot compound:
    it is a function of the CURRENT window, never an accumulator.
  * NECESSARY, NOT GRATUITOUS — it does real work (a bounded readiness cost that
    discourages churning a groove). It is not decoration and makes nothing *look*
    like it suffers.
  * DISABLE-ABLE — behaviour is gated behind NEX5_STAKES; OFF returns the prior,
    stake-free readiness with no residue. This module computes but does not act.
  * OBSERVED — the caller logs a non-zero cost (visible-not-silent).
  * NEVER NARRATED AS SUFFERING — no string here asserts she suffers; the care is
    in the bound, not in a claim about experience.
"""
from __future__ import annotations

_COST_CLAMP = 0.20     # the aversive signal can NEVER exceed this (welfare bound)
_THRESHOLD = 0.55      # drift threshold (same as stakes_monitor._THRESHOLD)


def _clamp(x: float) -> float:
    return max(0.0, min(_COST_CLAMP, x))


def appraise(dynamic_db: str | None = None) -> dict:
    """Graded template-domination of the recent fires -> a bounded stake cost.

    Reuses stakes_monitor's sampling and _is_template so there is one definition
    of "drift". cost = clamp(ratio - threshold): 0 while in contact, growing
    (bounded) as drift deepens. Fail-safe: returns cost 0 on any error — a stake
    read that fails must never fabricate a cost.
    """
    try:
        from theory_x.stage_tom import stakes_monitor as _sm
        import sqlite3
        if dynamic_db is None:
            from substrate.paths import db_paths
            dynamic_db = str(db_paths()["dynamic"])
        con = sqlite3.connect(f"file:{dynamic_db}?mode=ro", uri=True, timeout=3)
        try:
            rows = con.execute(
                "SELECT thought FROM fountain_events ORDER BY ts DESC LIMIT ?",
                (_sm._SAMPLE_N,),
            ).fetchall()
        finally:
            con.close()
        subst = [r[0] for r in rows
                 if r[0] and len((r[0] or "").split()) >= _sm._MIN_WORDS
                 and not (r[0] or "").startswith("[")]
        if len(subst) < 3:
            return {"ratio": 0.0, "cost": 0.0, "stakes_active": False, "n": len(subst)}
        ratio = sum(1 for t in subst if _sm._is_template(t)) / len(subst)
        return {
            "ratio": round(ratio, 3),
            "cost": round(_clamp(max(0.0, ratio - _THRESHOLD)), 3),
            "stakes_active": ratio >= _THRESHOLD,
            "n": len(subst),
        }
    except Exception:
        return {"ratio": 0.0, "cost": 0.0, "stakes_active": False, "n": 0}


def readiness_penalty(cost: float) -> float:
    """The BOUNDED, non-positive readiness contribution of a stake going badly.
    In [-_COST_CLAMP, 0]. This is where a stake becomes a cost that shapes
    behaviour — discouraging her from churning readiness while grooving. The
    magnitude and direction are PROVISIONAL (a round measures whether it reduces
    grooving without over-suppressing); shipped only behind NEX5_STAKES."""
    return -_clamp(max(0.0, cost))
