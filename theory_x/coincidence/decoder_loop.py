"""Decoder loop v2 — extended substrate features.

Per-fire columns:
  - aperture (from tree_snapshots, nearest at-or-before fire_ts)
  - hot_branch (from fountain_events row)
  - surprises_30min, daemons_5min, belief_delta_1h (counts in pre-fire windows)
  - fountain_tag (from fountain_events row)
  - hour_of_day, day_of_week (local time, Europe/Amsterdam)
  - seconds_since_feed (gap to most recent EXTERNAL sense event)
  - seconds_since_daemon (gap to most recent daemon firing)
  - active_branch_count (from tree_snapshots)
  - groove_active (NULL until we wire diversity ecology to a table)

Polls fountain_events every 30s. Decoupled from generator.
"""
from __future__ import annotations
import logging
import re
import sqlite3
import threading
import time
from datetime import datetime, timezone, timedelta

log = logging.getLogger("nex5.coincidence.decoder")

DYN_DB = "/home/rr/Desktop/nex5/data/dynamic.db"
SENSE_DB = "/home/rr/Desktop/nex5/data/sense.db"
POLL_INTERVAL = 30
KV_KEY = "decoder_last_fid"
# Europe/Amsterdam is UTC+1 in winter, +2 in summer. Use simple +2 since
# we're in May (CEST). For full correctness use zoneinfo later.
TZ_OFFSET_HOURS = 2

_STOPWORDS = frozenset("""
a an the and or but if then else of in on at to for from with by as is am are was were
be been being have has had do does did will would shall should may might must can could
i me my mine you your yours he she it they we us them his her hers their theirs ours
this that these those there here where when how what who whom whose which why
not no yes so too very just only also even still yet ever never always sometimes
again about above below up down out off over under between among into onto upon
some any all each every both few many much more most less least
than like so as well now today tonight yesterday tomorrow
something somewhere someone anything anywhere anyone everything everywhere
""".split())

_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z'\-]*")


def _tokenize(thought: str) -> list[str]:
    if not thought:
        return []
    words = _WORD_RE.findall(thought.lower())
    out = [w for w in words if len(w) >= 3 and w not in _STOPWORDS]
    return sorted(set(out))


def _local_hour_dow(fire_ts: float) -> tuple[int, int]:
    """Return (hour_of_day, day_of_week) in Europe/Amsterdam local time."""
    local = datetime.fromtimestamp(fire_ts, tz=timezone(timedelta(hours=TZ_OFFSET_HOURS)))
    return local.hour, local.weekday()


def _read_tree_snapshot(cx: sqlite3.Connection, fire_ts: float) -> tuple[float | None, int | None]:
    """Return (aperture, active_branch_count) from nearest tree_snapshot at-or-before fire_ts."""
    try:
        row = cx.execute(
            "SELECT membrane_aperture, active_branch_count FROM tree_snapshots "
            "WHERE ts <= ? ORDER BY ts DESC LIMIT 1",
            (fire_ts,),
        ).fetchone()
        if row:
            ap = float(row[0]) if row[0] is not None else None
            n = int(row[1]) if row[1] is not None else None
            return ap, n
    except Exception:
        pass
    return None, None


def _read_state_counts(cx: sqlite3.Connection, fire_ts: float) -> dict:
    out = {
        "surprises_30min": 0, "daemons_5min": 0, "belief_delta_1h": 0,
        "seconds_since_daemon": None,
    }
    thirty_min = fire_ts - 1800
    five_min = fire_ts - 300
    one_hour = fire_ts - 3600
    try:
        row = cx.execute(
            "SELECT COUNT(*) FROM surprise_events "
            "WHERE ts > ? AND ts <= ? AND surprise_flag = 1",
            (thirty_min, fire_ts),
        ).fetchone()
        out["surprises_30min"] = row[0] if row else 0
    except Exception:
        pass

    # daemon firings: count in last 5min + most recent ts for seconds_since
    daemon_total = 0
    most_recent_daemon = None
    for table, col in [
        ("identity_log", "composed_at"),
        ("pattern_log", "composed_at"),
        ("witness_log", "composed_at"),
        ("stillness_log", "ts"),
    ]:
        try:
            r = cx.execute(
                f"SELECT COUNT(*), MAX({col}) FROM {table} WHERE {col} <= ?",
                (fire_ts,),
            ).fetchone()
            if r:
                # count in last 5min
                r5 = cx.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE {col} > ? AND {col} <= ?",
                    (five_min, fire_ts),
                ).fetchone()
                if r5:
                    daemon_total += r5[0]
                if r[1] is not None:
                    if most_recent_daemon is None or r[1] > most_recent_daemon:
                        most_recent_daemon = r[1]
        except sqlite3.OperationalError:
            continue
    out["daemons_5min"] = daemon_total
    if most_recent_daemon is not None:
        out["seconds_since_daemon"] = max(0.0, fire_ts - most_recent_daemon)

    try:
        row = cx.execute(
            "SELECT COUNT(*) FROM fountain_events WHERE ts > ? AND ts <= ?",
            (one_hour, fire_ts),
        ).fetchone()
        out["belief_delta_1h"] = row[0] if row else 0
    except Exception:
        pass
    return out


def _read_seconds_since_feed(sense_cx: sqlite3.Connection, fire_ts: float) -> float | None:
    """Time since the most recent EXTERNAL (non-internal) sense event."""
    try:
        row = sense_cx.execute(
            "SELECT MAX(timestamp) FROM sense_events "
            "WHERE timestamp <= ? AND stream NOT LIKE 'internal.%'",
            (int(fire_ts),),
        ).fetchone()
        if row and row[0] is not None:
            return max(0.0, fire_ts - float(row[0]))
    except Exception:
        pass
    return None


def _get_last_fid(cx: sqlite3.Connection) -> int:
    try:
        row = cx.execute(
            "SELECT value FROM daemon_kv WHERE key=?", (KV_KEY,)
        ).fetchone()
        if row:
            return int(row[0])
    except Exception:
        pass
    return 0


def _set_last_fid(cx: sqlite3.Connection, fid: int) -> None:
    cx.execute(
        "INSERT INTO daemon_kv (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (KV_KEY, str(fid)),
    )


def decoder_tick() -> dict:
    cx = sqlite3.connect(DYN_DB, timeout=10)
    cx.row_factory = sqlite3.Row
    sense_cx = sqlite3.connect(SENSE_DB, timeout=10)
    try:
        last_fid = _get_last_fid(cx)
        rows = cx.execute(
            "SELECT id, ts, thought, hot_branch, tag FROM fountain_events "
            "WHERE id > ? AND thought != '' AND thought NOT LIKE '[%' "
            "ORDER BY id ASC LIMIT 200",
            (last_fid,),
        ).fetchall()
        if not rows:
            return {"processed": 0, "words": 0}
        total_words = 0
        for r in rows:
            words = _tokenize(r["thought"])
            if not words:
                _set_last_fid(cx, r["id"])
                continue
            aperture, active_count = _read_tree_snapshot(cx, r["ts"])
            counts = _read_state_counts(cx, r["ts"])
            secs_feed = _read_seconds_since_feed(sense_cx, r["ts"])
            hour, dow = _local_hour_dow(r["ts"])
            for w in words:
                cx.execute(
                    "INSERT INTO word_contexts "
                    "(word, fountain_event_id, ts, aperture, hot_branch, "
                    " surprises_30min, daemons_5min, belief_delta_1h, fountain_tag, "
                    " hour_of_day, day_of_week, seconds_since_feed, "
                    " seconds_since_daemon, active_branch_count, groove_active) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
                    (w, r["id"], r["ts"], aperture, r["hot_branch"],
                     counts["surprises_30min"], counts["daemons_5min"],
                     counts["belief_delta_1h"], r["tag"],
                     hour, dow, secs_feed,
                     counts["seconds_since_daemon"], active_count),
                )
                total_words += 1
            _set_last_fid(cx, r["id"])
        cx.commit()
        return {"processed": len(rows), "words": total_words}
    finally:
        cx.close()
        sense_cx.close()


def decoder_loop(state, stop: threading.Event) -> None:
    log.info("decoder_loop v2 started (interval=%ss)", POLL_INTERVAL)
    if stop.wait(15):
        return
    while not stop.is_set():
        try:
            result = decoder_tick()
            if result["processed"]:
                log.info("decoder: %s fires, %s words logged",
                         result["processed"], result["words"])
        except Exception as e:
            log.warning("decoder_tick failed: %s", e)
        if stop.wait(POLL_INTERVAL):
            break
    log.info("decoder_loop stopped")
