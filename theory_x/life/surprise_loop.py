"""Surprise loop — promote substrate surprise events into beliefs.

Every 5 minutes: looks for surprise_events from the last window where
surprise_flag=1 and not yet promoted to a belief. Writes them as
Tier-6 beliefs with source='surprise' so they enter retrieval and
become available to fountain composition.

Also: if a big_surprise fires, signals focus_loop to consider pivoting
(via a special row in current_focus table).

Without this loop, the PredictiveSubstrate's surprises stay buried in
dynamic.db and never reach her felt experience.
"""
from __future__ import annotations
import json
import logging
import sqlite3
import threading
import time
from pathlib import Path

log = logging.getLogger("theory_x.life.surprise_loop")

BELIEFS_DB = Path("/home/rr/Desktop/nex5/data/beliefs.db")
DYNAMIC_DB = Path("/home/rr/Desktop/nex5/data/dynamic.db")
TICK_SECONDS = 300
SOURCE = "surprise"
LAST_PROMOTED_TS_KEY = "surprise_loop_last_ts"


def _ensure_kv_table(d_cx):
    d_cx.execute(
        "CREATE TABLE IF NOT EXISTS daemon_kv ("
        "key TEXT PRIMARY KEY, value TEXT, updated_at REAL)"
    )
    d_cx.commit()


def _last_promoted_ts(d_cx):
    row = d_cx.execute(
        "SELECT value FROM daemon_kv WHERE key=?", (LAST_PROMOTED_TS_KEY,)
    ).fetchone()
    if row and row[0]:
        try:
            return float(row[0])
        except Exception:
            return 0.0
    return 0.0


def _set_last_promoted_ts(d_cx, ts):
    d_cx.execute(
        "INSERT INTO daemon_kv (key, value, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        (LAST_PROMOTED_TS_KEY, str(ts), time.time())
    )
    d_cx.commit()


def _surprise_to_belief(surprise_row):
    """Render a surprise_events row as a first-person belief sentence."""
    ptype = surprise_row["prediction_type"]
    score = surprise_row["surprise_score"]
    predicted = (surprise_row["predicted_content"] or "")[:150]
    actual = (surprise_row["actual_content"] or "")[:150]
    big = bool(surprise_row["big_surprise"])
    # Type-specific phrasing — first person, brief
    if ptype == "internal_belief":
        head = "I expected my next thought to be near:"
        tail = "But what came was:"
    elif ptype == "external_input":
        head = "I expected the next sense input to be near:"
        tail = "What actually arrived:"
    else:
        head = "I expected:"
        tail = "But:"
    marker = "Big surprise" if big else "Surprise"
    return (
        f"{head}\n  \"{predicted}\"\n"
        f"{tail}\n  \"{actual}\"\n"
        f"{marker}: {score:.2f}"
    )


def surprise_tick():
    d_cx = sqlite3.connect(DYNAMIC_DB, timeout=15)
    b_cx = sqlite3.connect(BELIEFS_DB, timeout=15)
    d_cx.row_factory = sqlite3.Row
    try:
        _ensure_kv_table(d_cx)
        since = _last_promoted_ts(d_cx)
        if since == 0:
            # First run — start from 10 min ago, don't import full history
            since = time.time() - 600
        rows = d_cx.execute(
            "SELECT * FROM surprise_events "
            "WHERE triggered_at > ? AND surprise_flag = 1 "
            "  AND actual_content IS NOT NULL AND actual_content != '' "
            "  AND predicted_content IS NOT NULL AND predicted_content != '' "
            "ORDER BY triggered_at ASC LIMIT 20",
            (since,)
        ).fetchall()
        if not rows:
            return {"promoted": 0}
        promoted = 0
        max_ts = since
        for r in rows:
            try:
                content = _surprise_to_belief(r)
                b_cx.execute(
                    "INSERT INTO beliefs "
                    "(content, tier, confidence, created_at, source, branch_id, tags) "
                    "VALUES (?, 6, 0.75, ?, ?, ?, ?)",
                    (content, int(r["triggered_at"]), SOURCE,
                     "cognition",
                     json.dumps(["surprise", "big_surprise" if r["big_surprise"] else "surprise"]))
                )
                b_cx.commit()
                promoted += 1
            except sqlite3.IntegrityError:
                # duplicate content — skip
                pass
            except Exception as e:
                log.warning("surprise belief write failed: %s", e)
            max_ts = max(max_ts, r["triggered_at"])
        _set_last_promoted_ts(d_cx, max_ts)
        log.info("surprise_loop: promoted %d surprise events", promoted)
        return {"promoted": promoted}
    finally:
        d_cx.close()
        b_cx.close()


def surprise_loop(state, stop):
    log.info("surprise_loop started (tick=%ds)", TICK_SECONDS)
    while not stop.is_set():
        try:
            stats = surprise_tick()
            if stats.get("promoted"):
                log.info("surprise_loop: %s", stats)
        except Exception as e:
            log.error("surprise_loop tick failed: %s: %s",
                      type(e).__name__, str(e)[:200])
        stop.wait(TICK_SECONDS)
    log.info("surprise_loop stopped")
