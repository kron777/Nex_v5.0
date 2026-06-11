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
import sqlite3
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
HORIZON = int(os.environ.get("NEX5_SELFPRED_HORIZON", "900"))


def _db_path() -> str:
    sys.path.insert(0, ".")
    try:
        from substrate.paths import db_paths  # type: ignore
        return str(db_paths()["conversations"])
    except Exception:
        return os.environ.get("NEX5_CONV_DB", "data/conversations.db")


def _connect(db_path: str):
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
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

    # NEX's OWN call, from its OWN self-read.
    self_pred = "fire" if readiness >= FIRE_THRESHOLD else "nofire"
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


def resolve_due(db_path: Optional[str] = None, now: Optional[float] = None) -> int:
    """For every prediction whose time has come, read NEX's CURRENT fire count.
    If it rose above the baseline recorded at predict time, a fire happened.
    Stamp each prediction correct/wrong vs that truth."""
    db_path = db_path or _db_path()
    ensure_schema(db_path)
    now = now if now is not None else time.time()

    status = _read_status()
    if status is None:
        return 0
    current_fires = int(status.get("total_fires", 0) or 0)

    conn = _connect(db_path)
    resolved = 0
    try:
        due = conn.execute(
            "SELECT id, predicted, baseline_fires FROM self_predictions "
            "WHERE resolved_at IS NULL AND resolve_at <= ?",
            (now,),
        ).fetchall()
        for row in due:
            actual = "fire" if current_fires > row["baseline_fires"] else "nofire"
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


# Optional: standalone daemon loop, mirrors WorldPredictionLoop idiom.
class SelfPredictionLoop:
    def __init__(self, interval: int = 900, horizon: int = HORIZON):
        self.interval = interval
        self.horizon = horizon
        self._alive = False

    def tick(self):
        try:
            r = resolve_due()
            if r:
                logger.info("self_pred resolved=%d", r)
        except Exception as e:
            logger.warning("self_pred resolve error: %s", e)
        try:
            out = make_self_prediction(horizon=self.horizon)
            if "error" not in out:
                logger.info(
                    "self_pred self=%s random=%s readiness=%.2f",
                    out["self_pred"], out["coin_pred"], out["readiness"],
                )
        except Exception as e:
            logger.warning("self_pred make error: %s", e)

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
    ap.add_argument("--loop", type=int, metavar="SECONDS", help="run standalone loop")
    args = ap.parse_args()

    if args.scorecard:
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
