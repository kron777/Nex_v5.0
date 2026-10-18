#!/usr/bin/env python3
"""
self_prediction.py  —  deepening the REAL column.

NEX predicts its OWN next action — "will I fire a thought in the next
interval?" — then checks against what it actually did. A coin-flip control
runs beside every prediction, exactly like the market scorecard.

The question this answers, honestly and falsifiably:
    Does NEX actually know itself — can its own readiness signal predict its
    own firing better than a coin? Or is its self-read no better than chance?

Both answers are real:
  - beats the coin  -> NEX has genuine (partial) self-knowledge. REAL column grows.
  - ties the coin   -> NEX's readiness doesn't predict its own behaviour; same
                       honest null as markets. Still real knowledge about NEX.

This is the market-scorecard machine pointed INWARD. No external data. The
verdict comes from NEX's own behaviour, read through the same fountain status
the dashboard uses. No edits to live fountain code.

USAGE (from nex5 root, app venv):
    .venv/bin/python3 theory_x/stage_world/self_prediction.py --once     # one cycle (make + resolve due)
    .venv/bin/python3 theory_x/stage_world/self_prediction.py --scorecard
    .venv/bin/python3 theory_x/stage_world/self_prediction.py --loop 900  # run standalone (optional)

Or wire SelfPredictionLoop into run.py like the world loop (env-gated). See bottom.

HOW IT WORKS
  make_self_prediction():
    reads fountain status -> current readiness, total_fires (the baseline).
    NEX predicts fire/no-fire from its OWN readiness (>= threshold => 'fire').
    a coin flip predicts the same. both recorded with the baseline fire count
    and a resolve_at one interval out.
  resolve_due():
    re-reads total_fires. if it went up since baseline -> a fire happened.
    stamps each due prediction correct/wrong vs that truth.
"""
from __future__ import annotations

import os
import sys
import time
import random
from substrate import connect, Row
import argparse
import logging
import urllib.request
import json
from typing import Optional

logger = logging.getLogger("nex5.self_pred")

# How NEX reads its own state — same endpoint the dashboard uses.
STATUS_URL = os.environ.get(
    "NEX5_FOUNTAIN_STATUS_URL", "http://localhost:8765/api/fountain/status"
)
# Readiness at/above this => NEX predicts it WILL fire. Tunable.
FIRE_THRESHOLD = float(os.environ.get("NEX5_SELFPRED_THRESHOLD", "0.70"))
# How far ahead a prediction looks before we check it (seconds).
#
# 420s is the MEASURED median inter-fire gap (n=1997 real fires from
# fountain_events). At this horizon P(no fire) = 50.1% -- a coin-flip base
# rate, so 'nofire' is a live answer and readiness has something to prove.
# The old 900s gave P(no fire) = 11.8%: 'fire' was nearly always correct,
# so the test could not distinguish self-knowledge from the fountain's period.
HORIZON = int(os.environ.get("NEX5_SELFPRED_HORIZON", "420"))

# Persistent fire log. total_fires from the status endpoint is an IN-MEMORY
# counter that RESETS TO ZERO on restart -- resolving against it compared a
# post-restart count (7) to a pre-restart baseline (203), so `actual` was
# 'fire' within an uptime and 'nofire' across a restart. Neither measured NEX.
DYNAMIC_DB = os.environ.get("NEX5_DYNAMIC_DB", "data/dynamic.db")


def _db_path() -> str:
    sys.path.insert(0, ".")
    try:
        from substrate.paths import db_paths  # type: ignore
        return str(db_paths()["conversations"])
    except Exception:
        return os.environ.get("NEX5_CONV_DB", "data/conversations.db")


def _connect(db_path: str):
    conn = connect(db_path, timeout=10)
    conn.row_factory = Row
    return conn


def ensure_schema(db_path: str) -> None:
    conn = _connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS self_predictions ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "made_at REAL NOT NULL, "
            "source TEXT NOT NULL, "            # 'self' or 'random'
            "predicted TEXT NOT NULL, "         # 'fire' or 'nofire'
            "readiness REAL, "                  # NEX's self-read at predict time
            "baseline_fires INTEGER NOT NULL, " # total_fires when predicted
            "resolve_at REAL NOT NULL, "
            "resolved_at REAL, "
            "actual TEXT, "                     # 'fire' or 'nofire'
            "outcome TEXT)"                     # 'correct' or 'wrong'
        )
        # 3(b): generalise to multiple prediction KINDS. Default 'fire' for the
        # existing rows so the original scorecard is unchanged.
        cols = [r[1] for r in conn.execute("PRAGMA table_info(self_predictions)")]
        if "kind" not in cols:
            conn.execute(
                "ALTER TABLE self_predictions ADD COLUMN kind TEXT NOT NULL DEFAULT 'fire'"
            )
        conn.commit()
    finally:
        conn.close()


def _read_status() -> Optional[dict]:
    """Read NEX's own current state through the fountain status endpoint."""
    try:
        req = urllib.request.Request(STATUS_URL)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.warning("self_pred: status read failed (%s)", e)
        return None


def make_self_prediction(db_path: Optional[str] = None, horizon: int = HORIZON) -> dict:
    """NEX predicts whether it will fire in the next `horizon` seconds, from its
    own readiness. A coin flip predicts the same. Both recorded."""
    db_path = db_path or _db_path()
    ensure_schema(db_path)

    status = _read_status()
    if status is None:
        return {"error": "status_unavailable"}

    readiness = float(status.get("readiness_score", 0.0) or 0.0)
    baseline_fires = int(status.get("total_fires", 0) or 0)

    # NEX's OWN call, from its OWN self-read, at the STATIC threshold.
    # Q3: the fire target has no variance (P(fire)=0.992), so a learned gate only
    # tracks the lowest populated readiness bin and cannot move -- feeding it back
    # would be a vacuous "update" (item 4's trap in new plumbing). The fire gate is
    # NOT adapted; adapt_threshold runs as a LOGGED MONITOR only (see its docstring).
    # The real predict->observe->error->UPDATE loop lives on selfdesc_novel.
    self_pred = "fire" if readiness >= FIRE_THRESHOLD else "nofire"
    # The control: a coin flip, no self-knowledge at all.
    coin_pred = random.choice(["fire", "nofire"])

    # Q1 write-time guard: the fire path OWNS the meaning of its generic columns.
    # readiness must be a probability-like self-read, actual∈{fire,nofire}. A count-
    # valued readiness (a new-kind signal) in a fire row must be impossible, not
    # merely filtered out downstream.
    if not (0.0 <= readiness <= 1.0):
        return {"error": f"fire readiness out of [0,1]: {readiness}"}

    now = time.time()
    resolve_at = now + horizon
    conn = _connect(db_path)
    try:
        for src, pred in (("self", self_pred), ("random", coin_pred)):
            conn.execute(
                "INSERT INTO self_predictions "
                "(made_at, source, kind, predicted, readiness, baseline_fires, resolve_at) "
                "VALUES (?, ?, 'fire', ?, ?, ?, ?)",
                (now, src, pred, readiness, baseline_fires, resolve_at),
            )
        conn.commit()
    finally:
        conn.close()

    return {
        "self_pred": self_pred,
        "coin_pred": coin_pred,
        "readiness": readiness,
        "baseline_fires": baseline_fires,
    }


def _fired_between(t0: float, t1: float) -> bool:
    """Did NEX actually produce a thought in (t0, t1]?

    Reads the persistent fountain_events log. A real fire has a non-empty
    thought; rows with stillness_reason='duplicate_retrieval' have empty
    thoughts (4,965 of 26,299 cycles) and are NOT speech.

    Restart-proof, unlike the in-memory total_fires counter.
    """
    try:
        conn = connect(f"file:{DYNAMIC_DB}?mode=ro", uri=True, timeout=5.0)
    except Exception as e:
        logger.warning("self_pred: fire-log open failed (%s)", e)
        return None
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM fountain_events "
            "WHERE ts > ? AND ts <= ? AND thought IS NOT NULL AND thought != ''",
            (t0, t1),
        ).fetchone()
        return (row[0] or 0) > 0
    except Exception as e:
        logger.warning("self_pred: fire-log query failed (%s)", e)
        return None
    finally:
        try: conn.close()
        except Exception: pass


def resolve_due(db_path: Optional[str] = None, now: Optional[float] = None) -> int:
    """Resolve each due prediction against the WINDOW IT NAMED.

    For every prediction, ask the persistent fire log whether a thought was
    produced between made_at and resolve_at. Each row gets its own window --
    the old code read one global counter and applied it to all of them.
    """
    db_path = db_path or _db_path()
    ensure_schema(db_path)
    now = now if now is not None else time.time()

    conn = _connect(db_path)
    resolved = 0
    try:
        due = conn.execute(
            "SELECT id, predicted, made_at, resolve_at FROM self_predictions "
            "WHERE resolved_at IS NULL AND resolve_at <= ? "
            "AND COALESCE(kind,'fire')='fire'",   # fire resolver: fire rows only
            (now,),
        ).fetchall()
        for row in due:
            fired = _fired_between(row["made_at"], row["resolve_at"])
            if fired is None:
                continue          # fire log unreadable -- leave pending, retry later
            actual = "fire" if fired else "nofire"
            outcome = "correct" if actual == row["predicted"] else "wrong"
            conn.execute(
                "UPDATE self_predictions SET resolved_at=?, actual=?, outcome=? WHERE id=?",
                (now, actual, outcome, row["id"]),
            )
            resolved += 1
        conn.commit()
    finally:
        conn.close()
    return resolved


def scorecard(db_path: Optional[str] = None) -> dict:
    """Split self vs random: how well does NEX predict its own firing?"""
    db_path = db_path or _db_path()
    ensure_schema(db_path)
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT source, "
            "COUNT(*) FILTER (WHERE outcome IS NOT NULL) AS resolved, "
            "COUNT(*) FILTER (WHERE outcome='correct') AS correct, "
            "COUNT(*) FILTER (WHERE outcome IS NULL) AS pending "
            "FROM self_predictions WHERE COALESCE(kind,'fire')='fire' GROUP BY source"
        ).fetchall()
    finally:
        conn.close()
    out = {}
    for r in rows:
        res = r["resolved"] or 0
        cor = r["correct"] or 0
        out[r["source"]] = {
            "resolved": res,
            "correct": cor,
            "pending": r["pending"] or 0,
            "hit_rate": (cor / res) if res else None,
        }
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Round 11, item 3 — make the metric honest (3a) and close the loop (3c).
#
# 3(a) HONEST SCORECARD. Accuracy against a 0.8%-minority target is dominated by
# the majority class and reports fake grip. Report three numbers: accuracy vs the
# majority FLOOR; the minority-class lift/recall/precision (the real signal); and a
# Brier score vs the constant climatological forecast, read straight off the
# readiness column we already record.
#
# 3(c) THE UPDATE. The loop was predict -> observe -> error -> STORE (a sensor).
# adapt_threshold closes it: predict -> observe -> error -> UPDATE, by setting the
# fire/nofire gate from recent outcomes at the readiness where empirical P(fire)
# crosses the operating point. The predictor's own error now moves its own gate.
# ─────────────────────────────────────────────────────────────────────────────

def ensure_params_schema(db_path: str) -> None:
    conn = _connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS self_pred_params ("
            "kind TEXT PRIMARY KEY, threshold REAL NOT NULL, "
            "updated_at REAL NOT NULL, n INTEGER, operating_p REAL)"
        )
        conn.commit()
    finally:
        conn.close()


def _current_threshold(db_path: str, kind: str = "fire") -> float:
    """The learned gate for `kind`, or the static constant until one is calibrated."""
    try:
        ensure_params_schema(db_path)
        conn = _connect(db_path)
        try:
            r = conn.execute(
                "SELECT threshold FROM self_pred_params WHERE kind=?", (kind,)
            ).fetchone()
            return float(r["threshold"]) if r else FIRE_THRESHOLD
        finally:
            conn.close()
    except Exception:
        return FIRE_THRESHOLD


def calibration_curve(db_path: Optional[str] = None, n: int = 500,
                      bins: int = 10) -> list:
    """Empirical P(fire) by readiness bin over the last n resolved self rows.
    This IS the calibration curve, from data already recorded."""
    db_path = db_path or _db_path()
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT readiness, actual FROM self_predictions "
            "WHERE source='self' AND COALESCE(kind,'fire')='fire' "
            "AND readiness IS NOT NULL AND actual IS NOT NULL "
            "ORDER BY resolved_at DESC LIMIT ?",
            (n,),
        ).fetchall()
    finally:
        conn.close()
    buckets: dict[int, list] = {}
    for r in rows:
        k = min(int(float(r["readiness"]) * bins), bins - 1)
        b = buckets.setdefault(k, [0, 0])
        b[0] += 1 if r["actual"] == "fire" else 0
        b[1] += 1
    return [{"readiness_lo": k / bins, "readiness_hi": (k + 1) / bins,
             "p_fire": fires / tot, "n": tot}
            for k, (fires, tot) in sorted(buckets.items())]


def adapt_threshold(db_path: Optional[str] = None, kind: str = "fire",
                    n: int = 500, operating_p: float = 0.5, bins: int = 10) -> Optional[dict]:
    """MONITOR ONLY (Q3). Computes the would-be gate from recent outcomes -- the
    lowest readiness bin whose empirical P(fire) >= operating_p -- and persists it for
    inspection. It does NOT feed make_self_prediction: at P(fire)=0.992 the learned
    threshold only tracks the lowest populated readiness bin and cannot move, so
    wiring it to the gate would be a vacuous 'update' (item 4's trap). The real
    predict->observe->error->UPDATE loop is on selfdesc_novel. Kept to log the
    threshold the fire target WOULD learn, and to show it standing still."""
    db_path = db_path or _db_path()
    curve = calibration_curve(db_path, n=n, bins=bins)
    if not curve:
        return None
    thr = next((b["readiness_lo"] for b in curve if b["p_fire"] >= operating_p), 1.0)
    try:
        ensure_params_schema(db_path)
        conn = _connect(db_path)
        try:
            conn.execute(
                "INSERT INTO self_pred_params (kind, threshold, updated_at, n, operating_p) "
                "VALUES (?,?,?,?,?) ON CONFLICT(kind) DO UPDATE SET "
                "threshold=excluded.threshold, updated_at=excluded.updated_at, "
                "n=excluded.n, operating_p=excluded.operating_p",
                (kind, thr, time.time(), sum(b["n"] for b in curve), operating_p),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        logger.warning("self_pred adapt_threshold persist failed: %s", e)
    return {"threshold": thr, "operating_p": operating_p,
            "n": sum(b["n"] for b in curve)}


def scorecard_detailed(db_path: Optional[str] = None) -> dict:
    """3(a): the honest read. Accuracy vs the majority floor is reported but is NOT
    the verdict for an imbalanced target; the minority-class lift and the Brier
    skill are."""
    db_path = db_path or _db_path()
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT predicted, readiness, actual, made_at FROM self_predictions "
            "WHERE source='self' AND COALESCE(kind,'fire')='fire' AND actual IS NOT NULL "
            "ORDER BY made_at, id"   # Q5: deterministic temporal order (made_at is REAL)
        ).fetchall()
    finally:
        conn.close()
    n = len(rows)
    if not n:
        return {"resolved": 0}
    actual_fire = sum(1 for r in rows if r["actual"] == "fire")
    base_fire = actual_fire / n
    majority = max(base_fire, 1 - base_fire)
    acc = sum(1 for r in rows if r["predicted"] == r["actual"]) / n
    minority = "nofire" if base_fire >= 0.5 else "fire"
    base_min = 1 - majority
    pred_min = [r for r in rows if r["predicted"] == minority]
    actual_min = sum(1 for r in rows if r["actual"] == minority)
    tp = sum(1 for r in pred_min if r["actual"] == minority)
    precision = (tp / len(pred_min)) if pred_min else None
    recall = (tp / actual_min) if actual_min else None
    lift = (precision / base_min) if (precision is not None and base_min > 0) else None

    # Q2: Brier skill is quoted ONLY out-of-sample. Fit calibration bins on the OLDER
    # half, score the NEWER half (rows are in made_at/rowid order). A climatology
    # forecast at a 0.992 base rate is hard to beat, so an in-sample number is mostly
    # fit; a temporal holdout + bootstrap CI is the honest version. Returns None (with
    # a reason) when there is too little held-out data to quote it.
    def _round3(x):
        return round(x, 3) if isinstance(x, float) else x
    brier = _holdout_brier_skill(rows, bins=10)

    rec_ci = _wilson(tp, actual_min) if actual_min else (None, None)
    prec_ci = _wilson(tp, len(pred_min)) if pred_min else (None, None)
    return {
        "resolved": n,
        "base_rate_fire": round(base_fire, 4),
        "accuracy": round(acc, 4), "majority_floor": round(majority, 4),
        "accuracy_rel_lift_over_floor": round((acc - majority) / majority, 4) if majority else None,
        "minority_class": minority, "minority_base_rate": round(base_min, 4),
        "minority_precision": _round3(precision),
        "minority_precision_ci95": [_round3(prec_ci[0]), _round3(prec_ci[1])],
        "minority_recall": _round3(recall),
        "minority_recall_ci95": [_round3(rec_ci[0]), _round3(rec_ci[1])],
        "minority_events": actual_min,
        "minority_lift": round(lift, 2) if lift else None,
        "brier_skill_holdout": brier,   # {skill, ci95, n_test} or {skill: None, reason}
    }


def _brier_at_cut(rows, cutoff, bins: int = 10, boots: int = 300):
    """One PINNED-cutoff holdout (Q5.3): fit bins on made_at <= cutoff, score the rest.
    Pinning to a made_at VALUE (not a moving index) makes the number reproducible, so
    0.067 becomes a citable figure. Reports cutoff + fit_n + score_n + minority_n."""
    import random as _r
    fit = [x for x in rows if x["made_at"] <= cutoff]
    test = [x for x in rows if x["made_at"] > cutoff]
    if len(fit) < 200 or len(test) < 200:
        return {"skill": None, "reason": f"fit={len(fit)} test={len(test)} (<200 each)",
                "cutoff": round(cutoff, 3)}
    base = sum(1 for x in fit if x["actual"] == "fire") / len(fit)
    buckets = {}
    for x in fit:
        rd = x["readiness"]
        if rd is None:
            continue
        k = min(int(float(rd) * bins), bins - 1)
        b = buckets.setdefault(k, [0, 0])
        b[0] += 1 if x["actual"] == "fire" else 0
        b[1] += 1
    binp = {k: (f / t) for k, (f, t) in buckets.items() if t >= 10}

    def pf(rd):
        return base if rd is None else binp.get(min(int(float(rd) * bins), bins - 1), base)

    def skill_of(sample):
        y = [1 if x["actual"] == "fire" else 0 for x in sample]
        bm = sum((pf(x["readiness"]) - yi) ** 2 for x, yi in zip(sample, y)) / len(sample)
        bc = sum((base - yi) ** 2 for yi in y) / len(sample)
        return (1 - bm / bc) if bc > 0 else None

    point = skill_of(test)
    skills = []
    for _ in range(boots):
        samp = [test[_r.randrange(len(test))] for _ in range(len(test))]
        s = skill_of(samp)
        if s is not None:
            skills.append(s)
    skills.sort()
    ci = ([round(skills[int(0.025 * len(skills))], 3),
           round(skills[int(0.975 * len(skills))], 3)] if skills else [None, None])
    minority_n = (sum(1 for x in test if x["actual"] != "fire") if base >= 0.5
                  else sum(1 for x in test if x["actual"] == "fire"))
    return {"skill": round(point, 3) if point is not None else None, "ci95": ci,
            "cutoff": round(cutoff, 3), "fit_n": len(fit), "score_n": len(test),
            "minority_n": minority_n}


def _holdout_brier_skill(rows, bins: int = 10, boots: int = 300):
    """Q5: run the pinned-cutoff holdout at THREE cut points (40/50/60%). A thin lower
    bound (0.024) could land near zero on a different split, so a claim requires
    positive skill at ALL three; a flip at one is disclosed, not hidden. Stamped with
    measurement time (the table resolves live)."""
    import time as _t
    stamp = _t.strftime("%Y-%m-%dT%H:%M:%SZ", _t.gmtime())
    n = len(rows)
    if n < 500:
        return {"skill": None, "reason": f"need >= 500 resolved, have {n}", "measured_at": stamp}
    cuts = [{"frac": frac, **_brier_at_cut(rows, rows[int(frac * n)]["made_at"], bins, boots)}
            for frac in (0.4, 0.5, 0.6)]
    # Q9: Brier is gated on minority EVENTS, not rows. At P(fire)=0.992 a ~1000-row
    # window holds ~1-8 minority events; the "skill" is then one row plus rounding, so
    # a positive number is arithmetic, not evidence -- and a caveated vacuous number
    # gets quoted without the caveat. Require >= 30 minority events per cut, else the
    # verdict is "not measurable" and NO skill number is claimed.
    MIN_MINORITY = 30
    thin = [c for c in cuts if (c.get("minority_n") or 0) < MIN_MINORITY]
    if thin:
        worst = max((c.get("minority_n") or 0) for c in cuts)
        return {"cuts": cuts, "all_cuts_positive": None,
                "verdict": (f"NOT MEASURABLE by holdout -- minority events too few "
                            f"(max {worst} per cut, need >= {MIN_MINORITY}); deferred, "
                            f"not failed. Evidence for this target is full-sample "
                            f"lift/recall, not Brier."),
                "measured_at": stamp}
    skills = [c["skill"] for c in cuts if c.get("skill") is not None]
    all_pos = bool(skills) and all(s > 0 for s in skills)
    any_neg = any(s <= 0 for s in skills)
    verdict = ("skill positive at all 3 cuts" if all_pos
               else "flips sign across cuts -- do not claim" if any_neg
               else "insufficient held-out data")
    return {"cuts": cuts, "all_cuts_positive": all_pos, "verdict": verdict,
            "measured_at": stamp}


# ─────────────────────────────────────────────────────────────────────────────
# Round 11, item 3(b) — two VARIANCE-BEARING targets (screened by rule C: marginal
# base rate inside [5%, 95%], else rejected). Both pure internal state, no chat-turn
# instrumentation:
#   authored_30m : will the next 30-min window produce >= 1 authored belief?
#                  (live base rate ~0.81)  predictor = persistence on the prior window.
#   selfdesc_novel: will the next self-description introduce a distinctive token the
#                  current one lacks? (live base rate ~0.51)  predictor = persistence
#                  on the last transition. A coin control runs beside each.
# ─────────────────────────────────────────────────────────────────────────────

# Q8: the decay and the conditional-path threshold are COUPLED, so they cannot
# silently disagree (an independent magic MIN_EFF_N is exactly how one knob moved and
# the other didn't). per_state_cap ~= 1/(2*(1-decay)); require eff_n >= 0.6*cap.
#
# Decay is NOT raised to 0.995 (4-day memory). The mandated stationarity check on the
# LIVE identity_log showed the conditional rates DRIFT -- P(differ|prev same) falls
# 0.561 -> 0.371 across halves, crossing the 0.5 decision boundary -- so a long window
# would average over a regime shift. Per-state resolution is gated on stationarity
# (selfdesc_stationarity); when the target is non-stationary the predictor uses the
# pooled estimate rather than a falsely-precise per-state one.
_SELFDESC_DECAY = 0.98
_SELFDESC_PER_STATE_CAP = 1.0 / (2.0 * (1.0 - _SELFDESC_DECAY))
_SELFDESC_MIN_EFF_N = round(0.6 * _SELFDESC_PER_STATE_CAP)

# Startup sanity guard: an unreachable conditional path is a loud config error, not a
# silent permanent fallback.
if _SELFDESC_MIN_EFF_N >= _SELFDESC_PER_STATE_CAP:
    logger.error(
        "self_pred CONFIG: selfdesc conditional path UNREACHABLE -- MIN_EFF_N=%s >= "
        "per_state_cap=%.1f for decay=%.3f", _SELFDESC_MIN_EFF_N,
        _SELFDESC_PER_STATE_CAP, _SELFDESC_DECAY)

AUTHORED_SOURCES = (
    "fountain_insight", "synergized", "counterfactual_node", "remember_loop",
    "wonder_loop", "hot_observer", "surprise", "fountain", "emergent_drive",
)
_AUTHORED_HORIZON = 1800  # 30 min


def _beliefs_db() -> str:
    try:
        from substrate.paths import db_paths  # type: ignore
        return str(db_paths()["beliefs"])
    except Exception:
        return os.environ.get("NEX5_BELIEFS_DB", "data/beliefs.db")


def _distinctive_tokens(s: str) -> set:
    import re
    return set(re.findall(r"[a-z]{5,}", (s or "").lower()))


def _insert_pred(db_path, kind, rows, resolve_at, signal=None):
    """rows: list of (source, predicted). signal stored in the readiness column."""
    conn = _connect(db_path)
    now = time.time()
    try:
        for src, pred in rows:
            conn.execute(
                "INSERT INTO self_predictions "
                "(made_at, source, kind, predicted, readiness, baseline_fires, resolve_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (now, src, kind, pred, signal, 0, resolve_at),
            )
        conn.commit()
    finally:
        conn.close()


def _authored_count(beliefs_db, t0, t1) -> Optional[int]:
    try:
        conn = connect(f"file:{beliefs_db}?mode=ro", uri=True, timeout=5.0)
    except Exception:
        return None
    try:
        ph = ",".join("?" * len(AUTHORED_SOURCES))
        row = conn.execute(
            f"SELECT COUNT(*) FROM beliefs WHERE created_at > ? AND created_at <= ? "
            f"AND source IN ({ph})",
            (t0, t1, *AUTHORED_SOURCES),
        ).fetchone()
        return row[0] or 0
    except Exception:
        return None
    finally:
        try: conn.close()
        except Exception: pass


def make_authored_prediction(db_path: Optional[str] = None,
                             beliefs_db: Optional[str] = None,
                             horizon: int = _AUTHORED_HORIZON) -> dict:
    """Predict >=1 authored belief in the next `horizon`s from the PRIOR window
    (persistence); coin control."""
    db_path = db_path or _db_path(); ensure_schema(db_path)
    beliefs_db = beliefs_db or _beliefs_db()
    now = time.time()
    prior = _authored_count(beliefs_db, now - horizon, now)
    if prior is None:
        return {"error": "beliefs_unreadable"}
    self_pred = "yes" if prior >= 1 else "no"
    coin = random.choice(["yes", "no"])
    _insert_pred(db_path, "authored_30m",
                 [("self", self_pred), ("random", coin)], now + horizon, signal=prior)
    return {"kind": "authored_30m", "self": self_pred, "coin": coin, "prior_count": prior}


def resolve_authored(db_path: Optional[str] = None,
                     beliefs_db: Optional[str] = None,
                     now: Optional[float] = None) -> int:
    db_path = db_path or _db_path(); ensure_schema(db_path)
    beliefs_db = beliefs_db or _beliefs_db()
    now = now if now is not None else time.time()
    conn = _connect(db_path); resolved = 0
    try:
        due = conn.execute(
            "SELECT id, predicted, made_at, resolve_at FROM self_predictions "
            "WHERE kind='authored_30m' AND resolved_at IS NULL AND resolve_at <= ?",
            (now,),
        ).fetchall()
        for r in due:
            c = _authored_count(beliefs_db, r["made_at"], r["resolve_at"])
            if c is None:
                continue
            actual = "yes" if c >= 1 else "no"
            conn.execute(
                "UPDATE self_predictions SET resolved_at=?, actual=?, outcome=? WHERE id=?",
                (now, actual, "correct" if actual == r["predicted"] else "wrong", r["id"]),
            )
            resolved += 1
        conn.commit()
    finally:
        conn.close()
    return resolved


def _identity_statements(dynamic_db):
    conn = connect(f"file:{dynamic_db}?mode=ro", uri=True, timeout=5.0)
    conn.row_factory = Row
    try:
        return conn.execute(
            "SELECT statement, composed_at FROM identity_log ORDER BY composed_at ASC"
        ).fetchall()
    finally:
        try: conn.close()
        except Exception: pass


def make_selfdesc_prediction(db_path: Optional[str] = None,
                             dynamic_db: Optional[str] = None) -> dict:
    """Predict whether the NEXT self-description introduces a new distinctive token,
    from whether the LAST transition did (persistence); coin control."""
    db_path = db_path or _db_path(); ensure_schema(db_path)
    dynamic_db = dynamic_db or DYNAMIC_DB
    try:
        st = _identity_statements(dynamic_db)
    except Exception:
        return {"error": "identity_log_unreadable"}
    if len(st) < 2:
        return {"error": "insufficient_history"}
    prev, cur = _distinctive_tokens(st[-2][0]), _distinctive_tokens(st[-1][0])
    last_was_novel = bool(cur - prev)
    last_label = "differ" if last_was_novel else "same"
    # 3(c) THE UPDATE on the learnable target. Q6: use the CONDITIONAL model C'
    # actually validated -- P(next differ | prev = last_label), estimated per prev
    # state with recency decay -- not a pooled symmetric persistence (the two agree on
    # the LABEL by luck but differ on the PROBABILITY, which Brier consumes). Fall back
    # to the pooled marginal when a state's effective N < 30 (two posteriors split one
    # sample). Reduces to symmetric as the rates converge, so strictly more general.
    cond = selfdesc_conditional(dynamic_db)
    eff = cond["eff_n_differ"] if last_label == "differ" else cond["eff_n_same"]
    p_cond = (cond["p_differ_given_differ"] if last_label == "differ"
              else cond["p_differ_given_same"])
    # Branch on EFFECTIVE N ONLY (Q8 final): the coupled threshold (0.6*per_state_cap)
    # already makes the conditional path reachable, so the gate's whole job is done by
    # eff_n. Stationarity is NOT a branch condition -- a runtime switch driven by an
    # underpowered two-sample test is a coin flip that makes the emitted probability
    # history-order-dependent noise and re-creates the inertness it was meant to avoid
    # (the retired +/-2% gate's shape). It is computed and LOGGED as a diagnostic only.
    if p_cond is not None and eff >= _SELFDESC_MIN_EFF_N:
        p_differ, branch = p_cond, "conditional"
    else:
        p_differ, branch = cond["p_differ_pooled"], "pooled_low_eff_n"
    self_pred = "differ" if p_differ >= 0.5 else "same"   # argmax
    p = p_differ                                 # emitted probability (for Brier)
    coin = random.choice(["differ", "same"])
    stat = selfdesc_stationarity(dynamic_db)     # diagnostic only, never branched on
    logger.info("self_pred selfdesc branch=%s eff_n=%.1f stationarity=%s",
                branch, eff, stat)
    # persist the learned parameter for inspection (monitor)
    try:
        ensure_params_schema(db_path)
        _c = _connect(db_path)
        try:
            _c.execute(
                "INSERT INTO self_pred_params (kind, threshold, updated_at, n, operating_p) "
                "VALUES ('selfdesc_novel', ?, ?, ?, 0.5) ON CONFLICT(kind) DO UPDATE SET "
                "threshold=excluded.threshold, updated_at=excluded.updated_at, n=excluded.n",
                (p, time.time(), cond.get("n", 0)),
            )
            _c.commit()
        finally:
            _c.close()
    except Exception:
        pass
    # resolves when the next statement appears; horizon is advisory only.
    _insert_pred(db_path, "selfdesc_novel",
                 [("self", self_pred), ("random", coin)],
                 time.time() + 86400, signal=float(len(cur)))
    return {"kind": "selfdesc_novel", "self": self_pred, "coin": coin,
            "last_was_novel": last_was_novel, "p_differ": round(p, 4),
            "branch": branch, "eff_n": round(eff, 1),
            "min_eff_n": _SELFDESC_MIN_EFF_N}


def selfdesc_stationarity(dynamic_db: Optional[str] = None) -> dict:
    """DIAGNOSTIC ONLY -- never a branch condition (Q8 final). Split the RAW (unweighted)
    transition history in half and compare each conditional rate across halves with its
    per-cell n and a two-proportion z-test. Reported and logged so drift can be WATCHED
    as transitions accrue; it does NOT switch the live estimator. Two reasons: (1) an
    underpowered two-sample test wired into a decision path is a coin flip (the retired
    +/-2% gate's shape); (2) a rate merely sitting NEAR 0.5 flips its label on a few
    observations and that is not drift -- only |z|>1.96 is called significant. If drift
    ever becomes real at higher n, the fix is a shorter decay or state-in-the-model, not
    a per-tick estimator switch."""
    import math
    dynamic_db = dynamic_db or DYNAMIC_DB
    try:
        st = _identity_statements(dynamic_db)
    except Exception:
        return {"reason": "unreadable", "raw_unweighted": True}
    toks = [_distinctive_tokens(s["statement"]) for s in st]
    labels = [bool(toks[i] - toks[i - 1]) for i in range(1, len(toks))]

    def rates(labs):
        nd = ns = kd = ks = 0
        for i in range(1, len(labs)):
            prev, nxt = labs[i - 1], labs[i]
            if prev:
                nd += 1; kd += 1 if nxt else 0
            else:
                ns += 1; ks += 1 if nxt else 0
        return (kd / nd if nd else None, ks / ns if ns else None, nd, ns)

    if len(labels) < 40:
        return {"reason": f"only {len(labels)} transitions", "raw_unweighted": True}
    h = len(labels) // 2
    f_dd, f_ds, f_nd, f_ns = rates(labels[:h])
    s_dd, s_ds, s_nd, s_ns = rates(labels[h:])

    def _z(p1, n1, p2, n2):
        if None in (p1, p2) or not n1 or not n2:
            return None
        se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
        return ((p1 - p2) / se) if se > 0 else None

    z_dd, z_ds = _z(f_dd, f_nd, s_dd, s_nd), _z(f_ds, f_ns, s_ds, s_ns)
    sig = lambda z: z is not None and abs(z) > 1.96
    return {
        "raw_unweighted": True,   # halves are raw transition counts, not decay-weighted
        "prev_differ": {"first": [round(f_dd, 3) if f_dd is not None else None, f_nd],
                        "second": [round(s_dd, 3) if s_dd is not None else None, s_nd],
                        "z": round(z_dd, 2) if z_dd is not None else None,
                        "significant": sig(z_dd)},
        "prev_same": {"first": [round(f_ds, 3) if f_ds is not None else None, f_ns],
                      "second": [round(s_ds, 3) if s_ds is not None else None, s_ns],
                      "z": round(z_ds, 2) if z_ds is not None else None,
                      "significant": sig(z_ds)},
        "significant_drift": sig(z_dd) or sig(z_ds),
    }


def selfdesc_conditional(dynamic_db: Optional[str] = None, decay: float = _SELFDESC_DECAY) -> dict:
    """Recency-decayed P(next differ | prev transition label), estimated separately for
    prev=differ and prev=same, plus the pooled marginal P(next differ). This is the
    conditional model rule C' validated (Q6); the pooled marginal is the fallback when
    a state's effective N is too small to trust its own rate."""
    dynamic_db = dynamic_db or DYNAMIC_DB
    try:
        st = _identity_statements(dynamic_db)
    except Exception:
        st = []
    toks = [_distinctive_tokens(s["statement"]) for s in st]
    labels = [bool(toks[i] - toks[i - 1]) for i in range(1, len(toks))]  # True=differ
    ed = sm = 0.0   # effective N for prev=differ / prev=same
    kd = ks = 0.0   # weighted count of next=differ, given prev
    tot = totd = 0.0
    w = 1.0
    for i in range(len(labels) - 1, 0, -1):   # newest transition first
        prev, nxt = labels[i - 1], labels[i]
        if prev:
            ed += w; kd += w if nxt else 0.0
        else:
            sm += w; ks += w if nxt else 0.0
        tot += w; totd += w if nxt else 0.0
        w *= decay
    return {
        "p_differ_given_differ": (kd / ed) if ed > 0 else None, "eff_n_differ": ed,
        "p_differ_given_same": (ks / sm) if sm > 0 else None, "eff_n_same": sm,
        "p_differ_pooled": (totd / tot) if tot > 0 else 0.5,
        "n": max(len(labels) - 1, 0),
    }


def selfdesc_persistence(dynamic_db: Optional[str] = None, decay: float = _SELFDESC_DECAY,
                         prior: float = 1.0) -> dict:
    """Recency-decayed Beta-Bernoulli estimate of persistence p = P(next transition
    label == previous one), from identity_log. Newer transitions weigh more (decay
    per step back). This is the one learned parameter of the selfdesc_novel update."""
    dynamic_db = dynamic_db or DYNAMIC_DB
    try:
        st = _identity_statements(dynamic_db)
    except Exception:
        return {"persistence": 0.5, "n": 0, "error": "unreadable"}
    toks = [_distinctive_tokens(s["statement"]) for s in st]
    labels = [bool(toks[i] - toks[i - 1]) for i in range(1, len(toks))]
    persist_obs = [labels[i] == labels[i - 1] for i in range(1, len(labels))]
    a = b = prior
    w = 1.0
    for persisted in reversed(persist_obs):   # newest first, decay going back
        if persisted:
            a += w
        else:
            b += w
        w *= decay
    return {"persistence": a / (a + b), "alpha": a, "beta": b, "n": len(persist_obs)}


def resolve_selfdesc(db_path: Optional[str] = None,
                     dynamic_db: Optional[str] = None) -> int:
    """Resolve once a self-description appears AFTER made_at: 'differ' if it carries a
    distinctive token the one current at made_at lacked. Not gated on resolve_at."""
    db_path = db_path or _db_path(); ensure_schema(db_path)
    dynamic_db = dynamic_db or DYNAMIC_DB
    try:
        st = _identity_statements(dynamic_db)
    except Exception:
        return 0
    conn = _connect(db_path); resolved = 0
    try:
        due = conn.execute(
            "SELECT id, predicted, made_at FROM self_predictions "
            "WHERE kind='selfdesc_novel' AND resolved_at IS NULL"
        ).fetchall()
        now = time.time()
        for r in due:
            made = r["made_at"]
            current = [s for s in st if s["composed_at"] <= made]
            nxt = [s for s in st if s["composed_at"] > made]
            if not current or not nxt:
                continue  # can't resolve yet
            cur_tok = _distinctive_tokens(current[-1]["statement"])
            nxt_tok = _distinctive_tokens(nxt[0]["statement"])
            actual = "differ" if (nxt_tok - cur_tok) else "same"
            conn.execute(
                "UPDATE self_predictions SET resolved_at=?, actual=?, outcome=? WHERE id=?",
                (now, actual, "correct" if actual == r["predicted"] else "wrong", r["id"]),
            )
            resolved += 1
        conn.commit()
    finally:
        conn.close()
    return resolved


def _wilson(k: int, n: int, z: float = 1.96):
    """95% Wilson score interval for a proportion k/n."""
    if n == 0:
        return (None, None)
    import math
    p = k / n
    d = 1 + z * z / n
    centre = p + z * z / (2 * n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((centre - half) / d, (centre + half) / d)


def selfdesc_structure(dynamic_db: Optional[str] = None) -> dict:
    """Rule C' for selfdesc_novel: variance is necessary but not sufficient. Does the
    NEXT transition's label depend on the PREVIOUS one? Compare P(differ|prev differ)
    vs P(differ|prev same) with a 95% CI on the difference (normal approx). If the
    interval straddles 0 the process is ~i.i.d. -- maximum variance, zero conditional
    structure -- and an adaptive persistence learner would fit noise, not grip."""
    import math
    dynamic_db = dynamic_db or DYNAMIC_DB
    st = _identity_statements(dynamic_db)
    toks = [_distinctive_tokens(s["statement"]) for s in st]
    labels = [bool(toks[i] - toks[i - 1]) for i in range(1, len(toks))]  # True=differ
    # condition transition i+1 on transition i
    nd = ns = 0          # denom: prev=differ / prev=same
    kd = ks = 0          # numer: next=differ given prev
    for i in range(1, len(labels)):
        prev, nxt = labels[i - 1], labels[i]
        if prev:
            nd += 1; kd += 1 if nxt else 0
        else:
            ns += 1; ks += 1 if nxt else 0
    if nd == 0 or ns == 0:
        return {"error": "insufficient_transitions", "n_transitions": len(labels)}
    p_dd = kd / nd       # P(differ | prev differ)
    p_sd = ks / ns       # P(differ | prev same)
    diff = p_dd - p_sd
    se = math.sqrt(p_dd * (1 - p_dd) / nd + p_sd * (1 - p_sd) / ns)
    lo, hi = diff - 1.96 * se, diff + 1.96 * se
    has_structure = not (lo <= 0 <= hi)
    return {
        "n_transitions": len(labels),
        "p_differ_given_prev_differ": round(p_dd, 4), "n_prev_differ": nd,
        "p_differ_given_prev_same": round(p_sd, 4), "n_prev_same": ns,
        "difference": round(diff, 4), "ci95": [round(lo, 4), round(hi, 4)],
        "has_conditional_structure": has_structure,
    }


def scorecard_by_kind(db_path: Optional[str] = None) -> dict:
    """Base-rate-aware read per kind: for the 'self' source, accuracy vs the majority
    floor and the minority-class lift (the honest verdict for any target)."""
    db_path = db_path or _db_path(); ensure_schema(db_path)
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT kind, source, predicted, actual FROM self_predictions "
            "WHERE actual IS NOT NULL"
        ).fetchall()
    finally:
        conn.close()
    from collections import defaultdict
    groups = defaultdict(list)
    for r in rows:
        groups[(r["kind"], r["source"])].append((r["predicted"], r["actual"]))
    out = {}
    for (kind, source), pairs in groups.items():
        n = len(pairs)
        labels = {a for _, a in pairs}
        acc = sum(1 for p, a in pairs if p == a) / n
        # majority floor from the actual distribution
        from collections import Counter
        ac = Counter(a for _, a in pairs)
        maj_label, maj_n = ac.most_common(1)[0]
        floor = maj_n / n
        minority = min(labels, key=lambda L: ac.get(L, 0)) if len(labels) > 1 else None
        lift = None
        if minority is not None:
            base_min = ac.get(minority, 0) / n
            pm = [1 for p, a in pairs if p == minority]
            tp = sum(1 for p, a in pairs if p == minority and a == minority)
            prec = (tp / len(pm)) if pm else None
            lift = (prec / base_min) if (prec is not None and base_min > 0) else None
        out[f"{kind}/{source}"] = {
            "resolved": n, "accuracy": round(acc, 4), "majority_floor": round(floor, 4),
            "acc_rel_lift": round((acc - floor) / floor, 4) if floor else None,
            "minority": minority, "minority_lift": round(lift, 2) if lift else None,
        }
    return out


# Optional: standalone daemon loop, mirrors WorldPredictionLoop idiom.
class SelfPredictionLoop:
    def __init__(self, interval: int = 900, horizon: int = HORIZON,
                 operating_p: float = 0.5):
        self.interval = interval
        self.horizon = horizon
        # operating point for the learned gate (3c). 0.5 = balanced; lower favours
        # recall on the rare 'nofire', higher favours precision.
        self.operating_p = float(os.environ.get("NEX5_SELFPRED_OPERATING_P", operating_p))
        self._alive = False

    def tick(self):
        try:
            r = resolve_due()
            if r:
                logger.info("self_pred resolved=%d", r)
        except Exception as e:
            logger.warning("self_pred resolve error: %s", e)
        # fire gate MONITOR (Q3): log the threshold the fire target would learn, to
        # show it standing still at P(fire)=0.992. Does NOT set the live gate.
        try:
            upd = adapt_threshold(operating_p=self.operating_p)
            if upd:
                logger.info("self_pred fire-gate MONITOR -> %.2f (op=%.2f, n=%d; not wired)",
                            upd["threshold"], upd["operating_p"], upd["n"])
        except Exception as e:
            logger.warning("self_pred monitor error: %s", e)
        try:
            out = make_self_prediction(horizon=self.horizon)
            if "error" not in out:
                logger.info(
                    "self_pred self=%s random=%s readiness=%.2f",
                    out["self_pred"], out["coin_pred"], out["readiness"],
                )
        except Exception as e:
            logger.warning("self_pred make error: %s", e)
        # 3(b): the two variance-bearing targets (resolve due, then make fresh).
        for _resolve, _make, _name in (
            (resolve_authored, make_authored_prediction, "authored_30m"),
            (resolve_selfdesc, make_selfdesc_prediction, "selfdesc_novel"),
        ):
            try:
                _resolve()
                _make()
            except Exception as e:
                logger.warning("self_pred %s error: %s", _name, e)

    def start_loop(self):
        import threading
        self._alive = True
        def _run():
            while self._alive:
                self.tick()
                time.sleep(self.interval)
        threading.Thread(target=_run, daemon=True).start()
        logger.info(
            "SelfPredictionLoop ready — self+coin firing prediction, "
            "interval=%ds horizon=%ds", self.interval, self.horizon
        )

    def stop(self):
        self._alive = False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="resolve due + make one prediction")
    ap.add_argument("--scorecard", action="store_true", help="print self-vs-coin scorecard")
    ap.add_argument("--honest", action="store_true",
                    help="print the 3-number honest scorecard (floor/minority-lift/Brier)")
    ap.add_argument("--adapt", action="store_true",
                    help="recalibrate the gate from recent outcomes (3c update)")
    ap.add_argument("--by-kind", action="store_true",
                    help="base-rate-aware scorecard per target kind (3b)")
    ap.add_argument("--structure", action="store_true",
                    help="rule C' conditional-structure test for selfdesc_novel")
    ap.add_argument("--loop", type=int, metavar="SECONDS", help="run standalone loop")
    args = ap.parse_args()

    if args.structure:
        import json as _j
        print(_j.dumps(selfdesc_structure(), indent=2))
    elif args.by_kind:
        import json as _j
        print(_j.dumps(scorecard_by_kind(), indent=2))
    elif args.honest:
        import json as _j
        print(_j.dumps(scorecard_detailed(), indent=2))
    elif args.adapt:
        import json as _j
        print(_j.dumps(adapt_threshold(), indent=2))
    elif args.scorecard:
        import json as _j
        print(_j.dumps(scorecard(), indent=2))
    elif args.loop:
        SelfPredictionLoop(interval=args.loop).start_loop()
        while True:
            time.sleep(60)
    else:  # --once (default)
        r = resolve_due()
        print(f"resolved: {r}")
        out = make_self_prediction()
        print(out)
