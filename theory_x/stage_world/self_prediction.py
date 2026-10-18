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

    # NEX's OWN call, from its OWN self-read -- against the LEARNED threshold
    # (3c: the predictor's own error moves its own gate), falling back to the
    # static constant until enough outcomes exist to calibrate.
    threshold = _current_threshold(db_path)
    self_pred = "fire" if readiness >= threshold else "nofire"
    # The control: a coin flip, no self-knowledge at all.
    coin_pred = random.choice(["fire", "nofire"])

    now = time.time()
    resolve_at = now + horizon
    conn = _connect(db_path)
    try:
        for src, pred in (("self", self_pred), ("random", coin_pred)):
            conn.execute(
                "INSERT INTO self_predictions "
                "(made_at, source, predicted, readiness, baseline_fires, resolve_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
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
            "WHERE resolved_at IS NULL AND resolve_at <= ?",
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
            "FROM self_predictions GROUP BY source"
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
            "WHERE source='self' AND readiness IS NOT NULL AND actual IS NOT NULL "
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
    """3(c): set the gate from recent outcomes -- the lowest readiness bin whose
    empirical P(fire) >= operating_p -- and persist it. operating_p encodes what
    'nofire' means: lower it to favour recall (catch missed fires), raise it to
    favour precision (trust a quiet window)."""
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
            "SELECT predicted, readiness, actual FROM self_predictions "
            "WHERE source='self' AND actual IS NOT NULL"
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
    curve = calibration_curve(db_path, n=n, bins=10)
    binmap = {int(round(b["readiness_lo"] * 10)): b["p_fire"] for b in curve}

    def _pf(readiness):
        if readiness is None:
            return base_fire
        return binmap.get(min(int(float(readiness) * 10), 9), base_fire)

    brier_model = sum((_pf(r["readiness"]) - (1 if r["actual"] == "fire" else 0)) ** 2
                      for r in rows) / n
    brier_clim = sum((base_fire - (1 if r["actual"] == "fire" else 0)) ** 2
                     for r in rows) / n
    skill = (1 - brier_model / brier_clim) if brier_clim > 0 else None
    return {
        "resolved": n,
        "base_rate_fire": base_fire,
        "accuracy": acc, "majority_floor": majority,
        "accuracy_rel_lift_over_floor": (acc - majority) / majority if majority else None,
        "minority_class": minority, "minority_base_rate": base_min,
        "minority_precision": precision, "minority_recall": recall,
        "minority_lift": lift,
        "brier_model": brier_model, "brier_climatology": brier_clim,
        "brier_skill": skill,
    }


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
    self_pred = "differ" if last_was_novel else "same"
    coin = random.choice(["differ", "same"])
    # resolves when the next statement appears; horizon is advisory only.
    _insert_pred(db_path, "selfdesc_novel",
                 [("self", self_pred), ("random", coin)],
                 time.time() + 86400, signal=float(len(cur)))
    return {"kind": "selfdesc_novel", "self": self_pred, "coin": coin,
            "last_was_novel": last_was_novel}


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
        # 3(c): close the loop — recalibrate the gate from the outcomes just resolved.
        try:
            upd = adapt_threshold(operating_p=self.operating_p)
            if upd:
                logger.info("self_pred threshold -> %.2f (op=%.2f, n=%d)",
                            upd["threshold"], upd["operating_p"], upd["n"])
        except Exception as e:
            logger.warning("self_pred adapt error: %s", e)
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
    ap.add_argument("--loop", type=int, metavar="SECONDS", help="run standalone loop")
    args = ap.parse_args()

    if args.by_kind:
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
