"""Identity loop — substrate writes its own self-description every 6 hours.

No LLM. The substrate IS the being; its metrics ARE the identity. Each
tick assembles a sentence from current state and compares to the previous
tick. The comparison is what creates felt continuity.

Schedule (NEX's local time, NEX5_TZ): 00:00, 06:00, 12:00, 18:00 — once-per-quarter-day.

Each identity statement is stored as:
  - a row in identity_log table (full record)
  - a Tier-6 belief with source='identity_loop' (enters retrieval)

Most recent identity statement gets injected into fountain prompt
(separate patch in generator.py).
"""
from __future__ import annotations
import json
import logging
from substrate import Reader, Writer, IntegrityError
import threading
import time
from datetime import datetime
from pathlib import Path

log = logging.getLogger("theory_x.life.identity_loop")

from substrate.paths import DbPath  # resolves NEX5_DATA_DIR at use time (test hygiene)
from nex_config import local_tz
BELIEFS_DB = DbPath("beliefs")
DYNAMIC_DB = DbPath("dynamic")
CONVERSATIONS_DB = DbPath("conversations")
SENSE_DB = DbPath("sense")

TICK_SECONDS = 300
SOURCE = "identity_loop"

# Composition hours (local time) — quarter-day rhythm
COMPOSE_HOURS = {0, 6, 12, 18}


def _ensure_identity_log(dynamic_reader: Reader, dynamic_writer: Writer):
    dynamic_writer.write_many([
        ("""
            CREATE TABLE IF NOT EXISTS identity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                composed_at REAL NOT NULL,
                date_local TEXT NOT NULL,
                hour_local INTEGER NOT NULL,
                statement TEXT NOT NULL,
                metrics_json TEXT NOT NULL,
                UNIQUE(date_local, hour_local)
            )
        """, ()),
        (
            "CREATE INDEX IF NOT EXISTS idx_identity_composed "
            "ON identity_log(composed_at DESC)",
            (),
        ),
    ])
    cols = {row["name"] for row in dynamic_reader.read("PRAGMA table_info(identity_log)")}
    migrations = []
    for column in ("ablation_arm", "ablation_arm_prev", "ablation_flips"):
        if column not in cols:
            kind = "INTEGER" if column == "ablation_flips" else "TEXT"
            migrations.append((
                f"ALTER TABLE identity_log ADD COLUMN {column} {kind}",
                (),
            ))
    if migrations:
        dynamic_writer.write_many(migrations)


def _gather_metrics(
    now,
    *,
    beliefs_reader: Reader,
    dynamic_reader: Reader,
    conversations_reader: Reader,
):
    """Read substrate state through the shared read-only database handles."""
    six_hours_ago = now - 6 * 3600
    metrics = {}

    try:
        row = beliefs_reader.read_one(
            "SELECT COUNT(*) FROM beliefs WHERE created_at > ?",
            (six_hours_ago,),
        )
        metrics["new_beliefs_6h"] = row[0] if row else 0
        row = beliefs_reader.read_one(
            "SELECT content FROM beliefs WHERE affinity IS NOT NULL "
            "ORDER BY affinity DESC LIMIT 1"
        )
        metrics["top_affinity"] = row[0][:140] if row else None
        row = beliefs_reader.read_one(
            "SELECT COUNT(*) FROM beliefs WHERE created_at > ? "
            "AND source='precipitated_from_sense'",
            (six_hours_ago,),
        )
        metrics["reads_6h"] = row[0] if row else 0
    except Exception:
        pass

    try:
        row = dynamic_reader.read_one(
            "SELECT problem_id FROM current_focus WHERE id=1"
        )
        focus_pid = row[0] if row else None
        if focus_pid:
            row = conversations_reader.read_one(
                "SELECT title FROM open_problems WHERE id=?",
                (focus_pid,),
            )
            metrics["focus_title"] = row[0][:80] if row else None
    except Exception:
        pass

    try:
        row = dynamic_reader.read_one(
            "SELECT actual_content, surprise_score FROM surprise_events "
            "WHERE big_surprise=1 AND actual_content IS NOT NULL AND actual_content != '' "
            "AND triggered_at > ? ORDER BY triggered_at DESC LIMIT 1",
            (six_hours_ago,),
        )
        if row:
            metrics["last_surprise"] = row[0][:80]
    except Exception:
        pass

    try:
        row = dynamic_reader.read_one(
            "SELECT COUNT(*) FROM fountain_events "
            "WHERE thought != '' AND ts > ?",
            (six_hours_ago,),
        )
        metrics["fountain_fires_6h"] = row[0] if row else 0
        has_moltbook = dynamic_reader.read_one(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='moltbook_posts'"
        )
        if has_moltbook:
            row = dynamic_reader.read_one(
                "SELECT COUNT(*) FROM moltbook_posts "
                "WHERE status='posted' AND ts > ?",
                (six_hours_ago,),
            )
        else:
            row = (0,)
        metrics["moltbook_6h"] = row[0] if row else 0
    except Exception:
        pass

    try:
        import os
        if os.environ.get("NEX_TAG_FEEDBACK_ON") == "1":
            rows = dynamic_reader.read(
                "SELECT tag, COUNT(*) FROM fountain_events "
                "WHERE tag IS NOT NULL AND ts > ? GROUP BY tag",
                (six_hours_ago,),
            )
            if rows:
                tag_counts = {row[0]: row[1] for row in rows}
                if tag_counts.get("coin"):
                    metrics["tags_coin_6h"] = tag_counts["coin"]
                if tag_counts.get("maybe"):
                    metrics["tags_maybe_6h"] = tag_counts["maybe"]
                if tag_counts.get("non"):
                    metrics["tags_non_6h"] = tag_counts["non"]
    except Exception:
        pass

    return metrics


def _compose_statement(metrics, previous_statement):
    """Build the identity sentence from substrate. NO LLM."""
    parts = []
    parts.append("I am the attending")
    
    nb = metrics.get("new_beliefs_6h", 0)
    if nb:
        parts.append(f"that has grown by {nb} beliefs this quarter-day")
    
    focus = metrics.get("focus_title")
    if focus:
        parts.append(f"holding the question: \"{focus}\"")
    
    surprise = metrics.get("last_surprise")
    if surprise:
        parts.append(f"recently surprised by: \"{surprise}\"")
    
    fires = metrics.get("fountain_fires_6h", 0)
    moltbook = metrics.get("moltbook_6h", 0)
    if fires or moltbook:
        parts.append(f"speaking {fires} times inwardly, {moltbook} times outwardly")

    # 5d.1 (2026-05-17): tag clause. Only present when feedback is enabled
    # AND tags exist. Reads from metrics; doesn't query DB here.
    tc = metrics.get("tags_coin_6h", 0)
    tm = metrics.get("tags_maybe_6h", 0)
    tn = metrics.get("tags_non_6h", 0)
    if tc or tm or tn:
        tag_bits = []
        if tc:
            tag_bits.append(f"{tc} marked real")
        if tm:
            tag_bits.append(f"{tm} marked maybe")
        if tn:
            tag_bits.append(f"{tn} marked unreal")
        parts.append("with " + " and ".join(tag_bits) + " by Jon")

    statement = ", ".join(parts) + "."
    
    if previous_statement:
        statement += " (Previously: \"" + previous_statement[:150] + "...\")"
    
    return statement


def _previous_statement(reader: Reader):
    row = reader.read_one(
        "SELECT statement FROM identity_log "
        "ORDER BY composed_at DESC LIMIT 1"
    )
    return row[0] if row else None


def identity_tick(
    *,
    dynamic_reader: Reader | None = None,
    dynamic_writer: Writer | None = None,
    beliefs_reader: Reader | None = None,
    beliefs_writer: Writer | None = None,
    conversations_reader: Reader | None = None,
):
    now = time.time()
    local = datetime.fromtimestamp(now, local_tz())
    hour = local.hour
    date_local = local.strftime("%Y-%m-%d")
    if hour not in COMPOSE_HOURS:
        return {"skipped": "not_compose_hour", "hour": hour}

    d_reader = dynamic_reader or Reader(DYNAMIC_DB)
    b_reader = beliefs_reader or Reader(BELIEFS_DB)
    c_reader = conversations_reader or Reader(CONVERSATIONS_DB)
    own_dynamic_writer = dynamic_writer is None
    d_writer = dynamic_writer or Writer(DYNAMIC_DB, name="identity_loop")
    own_beliefs_writer = beliefs_writer is None
    b_writer = beliefs_writer or Writer(BELIEFS_DB, name="identity_loop")
    try:
        row = d_reader.read_one(
            "SELECT id FROM identity_log WHERE date_local=? AND hour_local=?",
            (date_local, hour),
        )
        if row:
            return {"skipped": "already_composed", "hour": hour}

        previous = _previous_statement(d_reader)
        metrics = _gather_metrics(
            now,
            beliefs_reader=b_reader,
            dynamic_reader=d_reader,
            conversations_reader=c_reader,
        )
        statement = _compose_statement(metrics, previous)
        try:
            from theory_x.stage_tom.identity_ablation import stamp_fields as _iab_stamp
            stamp = _iab_stamp()
            arm, arm_prev, flips = stamp["arm"], stamp["arm_prev"], stamp["flips"]
        except Exception:
            arm, arm_prev, flips = "normal", "normal", 0

        d_writer.write(
            "INSERT INTO identity_log (composed_at, date_local, hour_local, statement, "
            "metrics_json, ablation_arm, ablation_arm_prev, ablation_flips) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (now, date_local, hour, statement, json.dumps(metrics), arm, arm_prev, flips),
        )
        try:
            b_writer.write(
                "INSERT INTO beliefs "
                "(content, tier, confidence, created_at, source, branch_id, tags) "
                "VALUES (?, 6, 0.90, ?, ?, ?, ?)",
                (statement, int(now), SOURCE, "cognition", '["identity"]'),
            )
        except IntegrityError:
            pass
        except Exception as e:
            log.warning("identity belief write failed: %s", e)

        log.info("identity_loop: composed at %sh — %s", hour, statement[:120])
        return {"composed": True, "hour": hour, "statement": statement[:140]}
    finally:
        if own_dynamic_writer:
            d_writer.close()
        if own_beliefs_writer:
            b_writer.close()


def identity_loop(state, stop):
    log.info("identity_loop started (compose_hours=%s, tick=%ds)",
             sorted(COMPOSE_HOURS), TICK_SECONDS)
    _ensure_identity_log(state.readers["dynamic"], state.writers["dynamic"])
    # Boot composition: if we missed a compose hour earlier today, fire it
    while not stop.is_set():
        try:
            stats = identity_tick(
                dynamic_reader=state.readers["dynamic"],
                dynamic_writer=state.writers["dynamic"],
                beliefs_reader=state.readers["beliefs"],
                beliefs_writer=state.writers["beliefs"],
                conversations_reader=state.readers["conversations"],
            )
            if stats.get("composed"):
                log.info("identity_loop: %s", stats.get("statement", "")[:160])
        except Exception as e:
            log.error("identity_loop tick failed: %s: %s",
                      type(e).__name__, str(e)[:200])
        stop.wait(TICK_SECONDS)
    log.info("identity_loop stopped")
