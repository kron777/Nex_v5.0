"""Decoder loop v2 — extended substrate features.

Per-fire columns:
  - aperture (from tree_snapshots, nearest at-or-before fire_ts)
  - hot_branch (from fountain_events row)
  - surprises_30min, daemons_5min, belief_delta_1h (counts in pre-fire windows)
  - fountain_tag (from fountain_events row)
  - hour_of_day, day_of_week (NEX's local time, NEX5_TZ)
  - seconds_since_feed (gap to most recent EXTERNAL sense event)
  - seconds_since_daemon (gap to most recent daemon firing)
  - active_branch_count (from tree_snapshots)
  - groove_active (NULL until we wire diversity ecology to a table)

Polls fountain_events every 30s. Decoupled from generator.
"""
from __future__ import annotations
from substrate.paths import db_paths
import logging
import re
from substrate import Reader, Writer, OperationalError
import threading
import time
from datetime import datetime

log = logging.getLogger("nex5.coincidence.decoder")

DYN_DB = str(db_paths()["dynamic"])
SENSE_DB = str(db_paths()["sense"])
POLL_INTERVAL = 30
KV_KEY = "decoder_last_fid"

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
    """Return (hour_of_day, day_of_week) in NEX's local time (NEX5_TZ)."""
    from nex_config import local_dt
    local = local_dt(fire_ts)
    return local.hour, local.weekday()


def _read_tree_snapshot(reader: Reader, fire_ts: float) -> tuple[float | None, int | None]:
    """Return the nearest tree snapshot at-or-before fire_ts."""
    try:
        row = reader.read_one(
            "SELECT membrane_aperture, active_branch_count FROM tree_snapshots "
            "WHERE ts <= ? ORDER BY ts DESC LIMIT 1",
            (fire_ts,),
        )
        if row:
            aperture = float(row[0]) if row[0] is not None else None
            count = int(row[1]) if row[1] is not None else None
            return aperture, count
    except Exception:
        pass
    return None, None


def _read_state_counts(reader: Reader, fire_ts: float) -> dict:
    out = {
        "surprises_30min": 0, "daemons_5min": 0, "belief_delta_1h": 0,
        "seconds_since_daemon": None,
    }
    thirty_min = fire_ts - 1800
    five_min = fire_ts - 300
    one_hour = fire_ts - 3600
    try:
        row = reader.read_one(
            "SELECT COUNT(*) FROM surprise_events "
            "WHERE triggered_at > ? AND triggered_at <= ? AND surprise_flag = 1",
            (thirty_min, fire_ts),
        )
        out["surprises_30min"] = row[0] if row else 0
    except Exception:
        pass

    daemon_total = 0
    most_recent_daemon = None
    for table, column in [
        ("identity_log", "composed_at"),
        ("pattern_log", "composed_at"),
        ("witness_log", "composed_at"),
        ("stillness_log", "ts"),
    ]:
        try:
            row = reader.read_one(
                f"SELECT COUNT(*), MAX({column}) FROM {table} WHERE {column} <= ?",
                (fire_ts,),
            )
            if row:
                recent = reader.read_one(
                    f"SELECT COUNT(*) FROM {table} WHERE {column} > ? AND {column} <= ?",
                    (five_min, fire_ts),
                )
                if recent:
                    daemon_total += recent[0]
                if row[1] is not None:
                    if most_recent_daemon is None or row[1] > most_recent_daemon:
                        most_recent_daemon = row[1]
        except OperationalError:
            continue
    out["daemons_5min"] = daemon_total
    if most_recent_daemon is not None:
        out["seconds_since_daemon"] = max(0.0, fire_ts - most_recent_daemon)

    try:
        row = reader.read_one(
            "SELECT COUNT(*) FROM fountain_events WHERE ts > ? AND ts <= ?",
            (one_hour, fire_ts),
        )
        out["belief_delta_1h"] = row[0] if row else 0
    except Exception:
        pass
    return out


def _read_seconds_since_feed(sense_reader: Reader, fire_ts: float) -> float | None:
    """Time since the most recent EXTERNAL (non-internal) sense event."""
    try:
        row = sense_reader.read_one(
            "SELECT MAX(timestamp) FROM sense_events "
            "WHERE timestamp <= ? AND stream NOT LIKE 'internal.%'",
            (int(fire_ts),),
        )
        if row and row[0] is not None:
            return max(0.0, fire_ts - float(row[0]))
    except Exception:
        pass
    return None


def _get_last_fid(reader: Reader) -> int:
    try:
        row = reader.read_one(
            "SELECT value FROM daemon_kv WHERE key=?",
            (KV_KEY,),
        )
        if row:
            return int(row[0])
    except Exception:
        pass
    return 0


def _last_fid_statement(fid: int):
    return (
        "INSERT INTO daemon_kv (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (KV_KEY, str(fid)),
    )


def decoder_tick(
    *,
    dynamic_reader: Reader | None = None,
    dynamic_writer: Writer | None = None,
    sense_reader: Reader | None = None,
) -> dict:
    d_reader = dynamic_reader or Reader(DYN_DB)
    s_reader = sense_reader or Reader(SENSE_DB)
    own_writer = dynamic_writer is None
    d_writer = dynamic_writer or Writer(DYN_DB, name="decoder_loop")
    try:
        last_fid = _get_last_fid(d_reader)
        rows = d_reader.read(
            "SELECT id, ts, thought, hot_branch, tag FROM fountain_events "
            "WHERE id > ? AND thought != '' AND thought NOT LIKE '[%' "
            "ORDER BY id ASC LIMIT 200",
            (last_fid,),
        )
        if not rows:
            return {"processed": 0, "words": 0}
        total_words = 0
        statements = []
        for row in rows:
            words = _tokenize(row["thought"])
            if not words:
                statements.append(_last_fid_statement(row["id"]))
                continue
            aperture, active_count = _read_tree_snapshot(d_reader, row["ts"])
            counts = _read_state_counts(d_reader, row["ts"])
            seconds_since_feed = _read_seconds_since_feed(s_reader, row["ts"])
            hour, dow = _local_hour_dow(row["ts"])
            for word in words:
                statements.append((
                    "INSERT INTO word_contexts "
                    "(word, fountain_event_id, ts, aperture, hot_branch, "
                    " surprises_30min, daemons_5min, belief_delta_1h, fountain_tag, "
                    " hour_of_day, day_of_week, seconds_since_feed, "
                    " seconds_since_daemon, active_branch_count, groove_active) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
                    (word, row["id"], row["ts"], aperture, row["hot_branch"],
                     counts["surprises_30min"], counts["daemons_5min"],
                     counts["belief_delta_1h"], row["tag"],
                     hour, dow, seconds_since_feed,
                     counts["seconds_since_daemon"], active_count),
                ))
                total_words += 1
            statements.append(_last_fid_statement(row["id"]))
        d_writer.write_many(statements)
        return {"processed": len(rows), "words": total_words}
    finally:
        if own_writer:
            d_writer.close()


def decoder_loop(state, stop: threading.Event) -> None:
    log.info("decoder_loop v2 started (interval=%ss)", POLL_INTERVAL)
    if stop.wait(15):
        return
    while not stop.is_set():
        try:
            result = decoder_tick(
                dynamic_reader=state.readers["dynamic"],
                dynamic_writer=state.writers["dynamic"],
                sense_reader=state.readers["sense"],
            )
            if result["processed"]:
                log.info("decoder: %s fires, %s words logged",
                         result["processed"], result["words"])
        except Exception as e:
            log.warning("decoder_tick failed: %s", e)
        if stop.wait(POLL_INTERVAL):
            break
    log.info("decoder_loop stopped")
