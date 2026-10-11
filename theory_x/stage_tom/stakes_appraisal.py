"""L4_stakes — self-referent appraisal with a BOUNDED cost.

A cost is what makes a state matter — something that can go badly *for her*,
which the readiness score (otherwise mostly a clock) can then be about. This
module exposes "the fire stream is grooving — drifting from world contact into
self-template" as a GRADED, bounded cost.

Two appraisals live here, for one reason (r79):

  * appraise()  — the drift-RATIO instrument. Reuses stakes_monitor's definition
    (fraction of the last 8 fires that _is_template). MEASURED INERT on the live
    instrument (r79 §2: live ratio ~0.08 vs its 0.55 threshold => cost ~0 always),
    so it is NOT wired into readiness. Retained as a measurement only.

  * appraise_groove()  — the LIVE-CALIBRATED onset cost (r79 Path A), the one
    readiness uses. The grooving the ratio instrument is blind to is real and
    frequent, but measured by a different detector: diversity/groove.py writes a
    'template_repetition' alert to beliefs.db:groove_alerts (~49.7x/day on live).
    This reads the RATE of those alerts and responds to a RISE above a frozen
    onset — never to the ever-present severity (~0.99), which would be a
    perpetual brake. Below onset => 0 (no brake at rest); above => bounded growth.

ANALOGUE — no claim there is a felt cost.

WELFARE AND SAFETY (SENTIENCE_PROGRAM.md §5a) — this is the one aversive signal,
so it is governed:
  * BOUNDED — the cost can never exceed _COST_CLAMP (0.20). It cannot compound:
    it is a function of the CURRENT trailing window, never an accumulator.
  * NECESSARY, NOT GRATUITOUS — it does real work only if it can fire. The ratio
    instrument could not (inert), so it is unwired; the groove onset cost is
    feasibility-checked to fire in ~35% of evals and rest at 0 in ~65% (r79 §2),
    i.e. it bites on bursts without braking at rest.
  * DISABLE-ABLE — behaviour is gated behind NEX5_STAKES; OFF returns the prior,
    stake-free readiness with no residue. This module computes but does not act.
  * OBSERVED — the caller logs a non-zero cost (visible-not-silent).
  * NEVER NARRATED AS SUFFERING — no string here asserts she suffers; the care is
    in the bound, not in a claim about experience.
"""
from __future__ import annotations

_COST_CLAMP = 0.20     # the aversive signal can NEVER exceed this (welfare bound)
_THRESHOLD = 0.55      # ratio-instrument threshold (same as stakes_monitor._THRESHOLD)


def _clamp(x: float) -> float:
    return max(0.0, min(_COST_CLAMP, x))


def appraise(dynamic_db: str | None = None) -> dict:
    """Drift-RATIO instrument (retained, NOT wired — inert on live, r79 §2).

    Reuses stakes_monitor's sampling and _is_template so there is one definition
    of "drift". cost = clamp(ratio - threshold). Kept as a measurement; readiness
    uses appraise_groove() instead. Fail-safe: returns cost 0 on any error.
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


# ── Path A (r79): the LIVE-CALIBRATED grooming-onset cost ────────────────────
# Params FROZEN on the 14d live baseline (2026-10-11); see
# observation_reports/r79_baselines/groove_rate.json. Re-measure before reuse
# (derived rates go stale): onset = all-hours mean (2.06 -> 2.0/hr),
# saturation = all-hours p90 (6.0/hr). Simulated over that history: cost==0 in
# 65% of evals, >0 in 35%, saturated in 15%; mean drag 0.05.
_GROOVE_WINDOW_S = 3600    # look at the trailing hour
_GROOVE_ONSET = 2.0        # alerts/hr at/below which the cost is 0 (no brake at rest)
_GROOVE_SAT = 6.0          # alerts/hr at which the bounded cost saturates
_GROOVE_CACHE_TTL = 30.0   # groove_alerts has NO index on detected_at; cap the
                           # 85k-row scan to ~once/30s (readiness calls score() often)
_groove_cache = {"val": None, "at": 0.0}


def _groove_cost(rate_per_hour: float) -> float:
    """Bounded onset cost: 0 at/below onset, linear to _COST_CLAMP at saturation."""
    if rate_per_hour <= _GROOVE_ONSET:
        return 0.0
    span = _GROOVE_SAT - _GROOVE_ONSET
    frac = (rate_per_hour - _GROOVE_ONSET) / span if span > 0 else 1.0
    return _clamp(_COST_CLAMP * frac)


def appraise_groove(beliefs_db: str | None = None, now: float | None = None) -> dict:
    """The Path-A (r79) stake cost: grooming ONSET from the live groove detector.

    Reads the rate of 'template_repetition' alerts (diversity/groove.py) in the
    trailing hour from beliefs.db:groove_alerts and maps a RISE above the frozen
    onset to a bounded cost. Steady grooming (rate ~ onset) => ~0, so it is not a
    perpetual brake; a burst => cost toward the bound. Short-cached (the table is
    unindexed) only for the default DB. Fail-safe: cost 0 on any error."""
    import time as _t
    now = _t.time() if now is None else now
    use_cache = beliefs_db is None
    if use_cache:
        c = _groove_cache
        if c["val"] is not None and (now - c["at"]) < _GROOVE_CACHE_TTL:
            return c["val"]
    try:
        import sqlite3
        if beliefs_db is None:
            from substrate.paths import db_paths
            beliefs_db = str(db_paths()["beliefs"])
        con = sqlite3.connect(f"file:{beliefs_db}?mode=ro", uri=True, timeout=3)
        try:
            n = con.execute(
                "SELECT COUNT(*) FROM groove_alerts "
                "WHERE alert_type='template_repetition' AND detected_at > ?",
                (now - _GROOVE_WINDOW_S,),
            ).fetchone()[0]
        finally:
            con.close()
        rate = n * 3600.0 / _GROOVE_WINDOW_S     # alerts per hour
        out = {
            "rate_per_hour": round(rate, 2),
            "cost": round(_groove_cost(rate), 3),
            "stakes_active": rate > _GROOVE_ONSET,
            "n": int(n),
        }
        if use_cache:
            _groove_cache["val"] = out
            _groove_cache["at"] = now
        return out
    except Exception:
        return {"rate_per_hour": 0.0, "cost": 0.0, "stakes_active": False, "n": 0}


def readiness_penalty(cost: float) -> float:
    """The BOUNDED, non-positive readiness contribution of a stake going badly.
    In [-_COST_CLAMP, 0]. SHELVED (not armed): r79's aversive design was found to be
    a volume brake on a cadence-proxy signal. Per the welfare dominance-out bar
    (SENTIENCE_PROGRAM §5a), the aversive term is admissible only if the reward arm
    (appraise_approach, r80) provably fails a pre-named discrimination. Retained as
    the to-be-admitted-against-a-gap option; shipped only behind NEX5_STAKES."""
    return -_clamp(max(0.0, cost))


# ── r80: the REWARD / approach arm — a bounded POSITIVE readiness term ────────
# Dominance-out (Beam 1b/1d): a reward term has a checkable positive prediction
# (readiness higher after world-contact) where the aversive term's success and
# failure both look like "less fire". Ship this first; admit the aversive arm only
# against a proven gap. "Mattering is the term, not its sign."
#
# Signal = recent world-contact = p_on_subject (fraction of recent fires sharing
# >=1 content token with their retrieved focal subject — subject_fidelity). It is a
# per-fire FRACTION, so (unlike the groove RATE) it is not a cadence proxy.
#
# SCOPE, measured 2026-10-11 (observation_reports/r80_baselines/approach.json):
# grounding is ORTHOGONAL to grooming on live (corr p_on_subject vs groove/fire =
# +0.08) and flat against the crystallizer reject rate. So this arm reshapes the
# GROUNDING mix (makes readiness ABOUT grounding); it does NOT target grooming —
# that is a separate axis for a later selection-coupling node (L4b). r80's primary
# is the grounded fraction at CONSTANT cadence (Beam 1a: ratio + cadence co-primary),
# non-tautological because it depends on grounding being autocorrelated.
#
# Params FROZEN from the 14d live baseline; re-measure before reuse (rates go stale).
_APPROACH_BONUS_MAX = 0.10   # positive readiness bonus cap. PROVISIONAL — 1c calibration
                             # (> readiness noise floor, < ~half smallest decision margin)
                             # is the principled way to set it; 0.10 < the smallest
                             # existing readiness term pending that measurement.
_APPROACH_WINDOW = 30        # recent fires defining "recent world-contact"
_APPROACH_ONSET = 0.767      # p75 of the 30-fire-WINDOW p_on_subject (reward engages in
                             # the clearly-above-baseline top quartile — ~25% duty cycle;
                             # NOT the mean, per A3; the daily p75 (0.676) was the wrong
                             # grain and engaged ~46% of windows)
_APPROACH_SAT = 0.90         # bonus saturates here (window p90 is 0.833; max 1.0)
_APPROACH_CACHE_TTL = 30.0
_approach_cache = {"val": None, "at": 0.0}


def _approach_bonus(p_on_subject: float) -> float:
    """Bounded onset ramp: 0 at/below onset, linear to _APPROACH_BONUS_MAX at sat."""
    if p_on_subject <= _APPROACH_ONSET:
        return 0.0
    span = _APPROACH_SAT - _APPROACH_ONSET
    frac = (p_on_subject - _APPROACH_ONSET) / span if span > 0 else 1.0
    return max(0.0, min(_APPROACH_BONUS_MAX, _APPROACH_BONUS_MAX * frac))


def appraise_approach(dynamic_db: str | None = None, now: float | None = None) -> dict:
    """The r80 reward: recent world-contact -> a bounded POSITIVE readiness bonus.

    Reads p_on_subject over the last _APPROACH_WINDOW fires (subject_fidelity) and
    ramps a bonus above the frozen onset. Below onset => 0. Cold-start safe (n<5 =>
    0). Short-cached for the default DB. Fail-safe: bonus 0 on any error — a reward
    read that fails must never fabricate readiness."""
    import time as _t
    now = _t.time() if now is None else now
    use_cache = dynamic_db is None
    if use_cache:
        c = _approach_cache
        if c["val"] is not None and (now - c["at"]) < _APPROACH_CACHE_TTL:
            return c["val"]
    try:
        from theory_x.stage6_fountain import subject_fidelity as _sf
        if dynamic_db is None:
            from substrate.paths import db_paths
            dynamic_db = str(db_paths()["dynamic"])
        f = _sf.subject_fidelity(window=_APPROACH_WINDOW, db_path=dynamic_db)
        p = float(f.get("p_on_subject", 0.0) or 0.0)
        n = int(f.get("n", 0) or 0)
        if n < 5:
            out = {"p_on_subject": round(p, 3), "bonus": 0.0, "contact_active": False, "n": n}
        else:
            out = {
                "p_on_subject": round(p, 3),
                "bonus": round(_approach_bonus(p), 3),
                "contact_active": p > _APPROACH_ONSET,
                "n": n,
            }
        if use_cache:
            _approach_cache["val"] = out
            _approach_cache["at"] = now
        return out
    except Exception:
        return {"p_on_subject": 0.0, "bonus": 0.0, "contact_active": False, "n": 0}


def readiness_bonus(bonus: float) -> float:
    """The BOUNDED, non-negative readiness contribution of world-contact going well.
    In [0, _APPROACH_BONUS_MAX]. This is where mattering becomes a term readiness is
    ABOUT — grounded firing is rewarded, not just clocked. Magnitude PROVISIONAL (r80
    measures whether grounded fraction rises at constant cadence); behind NEX5_APPROACH."""
    return max(0.0, min(_APPROACH_BONUS_MAX, bonus))
