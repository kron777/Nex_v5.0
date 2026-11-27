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
from substrate import Reader, Writer, IntegrityError
import threading
import time
from pathlib import Path

log = logging.getLogger("theory_x.life.surprise_loop")

from substrate.paths import DbPath  # resolves NEX5_DATA_DIR at use time (test hygiene)
BELIEFS_DB = DbPath("beliefs")
DYNAMIC_DB = DbPath("dynamic")
TICK_SECONDS = 300
SOURCE = "surprise"
LAST_PROMOTED_TS_KEY = "surprise_loop_last_ts"
LAST_PROMOTED_ID_KEY = "surprise_loop_last_id"


def _ensure_kv_table(writer: Writer):
    writer.write(
        "CREATE TABLE IF NOT EXISTS daemon_kv ("
        "key TEXT PRIMARY KEY, value TEXT, updated_at REAL)"
    )


def _last_promoted_cursor(reader: Reader, writer: Writer) -> tuple[float, int]:
    """Load the durable event-ID cursor, migrating from the legacy timestamp.

    The event table's INTEGER PRIMARY KEY is monotonic and stable across VACUUM.
    On migration, rows strictly older than the old timestamp are treated as
    historical; rows exactly at that timestamp are replayed safely.
    """
    rows = reader.read(
        "SELECT key, value FROM daemon_kv WHERE key IN (?, ?)",
        (LAST_PROMOTED_TS_KEY, LAST_PROMOTED_ID_KEY),
    )
    values = {row["key"]: row["value"] for row in rows}
    try:
        since = float(values.get(LAST_PROMOTED_TS_KEY) or 0.0)
    except (TypeError, ValueError):
        since = 0.0
    if since == 0:
        since = time.time() - 600

    raw_id = values.get(LAST_PROMOTED_ID_KEY)
    if raw_id is not None:
        try:
            return since, int(raw_id)
        except (TypeError, ValueError):
            pass

    row = reader.read_one(
        "SELECT COALESCE(MAX(id), 0) FROM surprise_events WHERE triggered_at < ?",
        (since,),
    )
    last_id = int(row[0] or 0) if row else 0
    # Persist migration before processing. This freezes the initial/legacy
    # boundary even when there are no eligible rows or the first write fails.
    _set_last_promoted_cursor(writer, since, last_id)
    return since, last_id


def _set_last_promoted_cursor(writer: Writer, ts: float, event_id: int) -> None:
    """Persist the compatibility timestamp and authoritative event ID atomically."""
    now = time.time()
    writer.write_many([
        (
            "INSERT INTO daemon_kv (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (LAST_PROMOTED_TS_KEY, str(float(ts)), now),
        ),
        (
            "INSERT INTO daemon_kv (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (LAST_PROMOTED_ID_KEY, str(int(event_id)), now),
        ),
    ])


def _surprise_tags(big_surprise: bool) -> list[str]:
    return ["surprise", "big_surprise"] if big_surprise else ["surprise"]


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


def surprise_tick(
    *,
    dynamic_reader: Reader | None = None,
    dynamic_writer: Writer | None = None,
    beliefs_writer: Writer | None = None,
):
    d_reader = dynamic_reader or Reader(DYNAMIC_DB)
    own_dynamic_writer = dynamic_writer is None
    d_writer = dynamic_writer or Writer(DYNAMIC_DB, name="surprise_loop")
    own_beliefs_writer = beliefs_writer is None
    b_writer = beliefs_writer or Writer(BELIEFS_DB, name="surprise_loop")
    try:
        _ensure_kv_table(d_writer)
        since, last_id = _last_promoted_cursor(d_reader, d_writer)
        rows = d_reader.read(
            "SELECT * FROM surprise_events "
            "WHERE id > ? "
            "  AND surprise_flag = 1 "
            "  AND actual_content IS NOT NULL AND actual_content != '' "
            "  AND predicted_content IS NOT NULL AND predicted_content != '' "
            "ORDER BY id ASC LIMIT 20",
            (last_id,),
        )
        if not rows:
            return {"promoted": 0}

        promoted = 0
        processed = 0
        cursor_id = last_id
        cursor_ts = since
        for row in rows:
            try:
                content = _surprise_to_belief(row)
                b_writer.write(
                    "INSERT INTO beliefs "
                    "(content, tier, confidence, created_at, source, branch_id, tags) "
                    "VALUES (?, 6, 0.75, ?, ?, ?, ?)",
                    (
                        content,
                        int(row["triggered_at"]),
                        SOURCE,
                        "cognition",
                        json.dumps(_surprise_tags(bool(row["big_surprise"]))),
                    ),
                )
                promoted += 1
            except IntegrityError:
                # Duplicate content is already represented; it is safe to pass.
                pass
            except Exception as e:
                # Do not checkpoint this event or anything after it. The next
                # tick retries from the last fully handled event.
                log.warning("surprise belief write failed for event %s: %s", row["id"], e)
                break

            cursor_id = int(row["id"])
            cursor_ts = max(cursor_ts, float(row["triggered_at"]))
            processed += 1

        if processed:
            _set_last_promoted_cursor(d_writer, cursor_ts, cursor_id)
        log.info("surprise_loop: promoted %d surprise events", promoted)
        return {"promoted": promoted}
    finally:
        if own_dynamic_writer:
            d_writer.close()
        if own_beliefs_writer:
            b_writer.close()


def surprise_loop(state, stop):
    log.info("surprise_loop started (tick=%ds)", TICK_SECONDS)
    while not stop.is_set():
        try:
            stats = surprise_tick(
                dynamic_reader=state.readers["dynamic"],
                dynamic_writer=state.writers["dynamic"],
                beliefs_writer=state.writers["beliefs"],
            )
            if stats.get("promoted"):
                log.info("surprise_loop: %s", stats)
        except Exception as e:
            log.error("surprise_loop tick failed: %s: %s",
                      type(e).__name__, str(e)[:200])
        stop.wait(TICK_SECONDS)
    log.info("surprise_loop stopped")
