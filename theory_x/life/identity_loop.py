"""Identity loop — substrate writes its own self-description every 6 hours.

No LLM. The substrate IS the being; its metrics ARE the identity. Each
tick assembles a sentence from current state and compares to the previous
tick. The comparison is what creates felt continuity.

Schedule (Europe/Amsterdam): 00:00, 06:00, 12:00, 18:00 — once-per-quarter-day.

Each identity statement is stored as:
  - a row in identity_log table (full record)
  - a Tier-6 belief with source='identity_loop' (enters retrieval)

Most recent identity statement gets injected into fountain prompt
(separate patch in generator.py).
"""
from __future__ import annotations
import json
import logging
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

log = logging.getLogger("theory_x.life.identity_loop")

BELIEFS_DB = Path("/home/rr/Desktop/Desktop/nex5/data/beliefs.db")
DYNAMIC_DB = Path("/home/rr/Desktop/Desktop/nex5/data/dynamic.db")
CONVERSATIONS_DB = Path("/home/rr/Desktop/Desktop/nex5/data/conversations.db")
SENSE_DB = Path("/home/rr/Desktop/Desktop/nex5/data/sense.db")

TZ = ZoneInfo("Europe/Amsterdam")
TICK_SECONDS = 300
SOURCE = "identity_loop"

# Composition hours (local time) — quarter-day rhythm
COMPOSE_HOURS = {0, 6, 12, 18}


def _ensure_identity_log():
    cx = sqlite3.connect(DYNAMIC_DB, timeout=15)
    try:
        cx.execute("""
            CREATE TABLE IF NOT EXISTS identity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                composed_at REAL NOT NULL,
                date_local TEXT NOT NULL,
                hour_local INTEGER NOT NULL,
                statement TEXT NOT NULL,
                metrics_json TEXT NOT NULL,
                UNIQUE(date_local, hour_local)
            )
        """)
        cx.execute(
            "CREATE INDEX IF NOT EXISTS idx_identity_composed ON identity_log(composed_at DESC)"
        )
        cx.commit()
    finally:
        cx.close()


def _gather_metrics(now):
    """Read substrate state. No LLM."""
    six_hours_ago = now - 6 * 3600
    m = {}

    # New beliefs in last 6h
    try:
        b = sqlite3.connect(BELIEFS_DB, timeout=10)
        row = b.execute(
            "SELECT COUNT(*) FROM beliefs WHERE created_at > ?",
            (six_hours_ago,)
        ).fetchone()
        m["new_beliefs_6h"] = row[0] if row else 0

        # Highest-affinity belief
        row = b.execute(
            "SELECT content FROM beliefs WHERE affinity IS NOT NULL "
            "ORDER BY affinity DESC LIMIT 1"
        ).fetchone()
        m["top_affinity"] = row[0][:140] if row else None

        # Tier-7 reads (sense-precipitations) in last 6h
        row = b.execute(
            "SELECT COUNT(*) FROM beliefs WHERE created_at > ? "
            "AND source='precipitated_from_sense'",
            (six_hours_ago,)
        ).fetchone()
        m["reads_6h"] = row[0] if row else 0

        b.close()
    except Exception:
        pass

    # Current focus
    try:
        d = sqlite3.connect(DYNAMIC_DB, timeout=10)
        row = d.execute(
            "SELECT problem_id FROM current_focus WHERE id=1"
        ).fetchone()
        focus_pid = row[0] if row else None
        d.close()
        if focus_pid:
            c = sqlite3.connect(CONVERSATIONS_DB, timeout=10)
            row = c.execute(
                "SELECT title FROM open_problems WHERE id=?", (focus_pid,)
            ).fetchone()
            m["focus_title"] = row[0][:80] if row else None
            c.close()
    except Exception:
        pass

    # Last big surprise
    try:
        d = sqlite3.connect(DYNAMIC_DB, timeout=10)
        row = d.execute(
            "SELECT actual_content, surprise_score FROM surprise_events "
            "WHERE big_surprise=1 AND actual_content IS NOT NULL AND actual_content != '' "
            "AND triggered_at > ? "
            "ORDER BY triggered_at DESC LIMIT 1",
            (six_hours_ago,)
        ).fetchone()
        if row:
            m["last_surprise"] = row[0][:80]
        d.close()
    except Exception:
        pass

    # Fountain fires in last 6h
    try:
        d = sqlite3.connect(DYNAMIC_DB, timeout=10)
        row = d.execute(
            "SELECT COUNT(*) FROM fountain_events "
            "WHERE thought != '' AND ts > ?",
            (six_hours_ago,)
        ).fetchone()
        m["fountain_fires_6h"] = row[0] if row else 0

        # Moltbook posts in last 6h
        row = d.execute(
            "SELECT COUNT(*) FROM moltbook_posts "
            "WHERE status='posted' AND ts > ?",
            (six_hours_ago,)
        ).fetchone()
        m["moltbook_6h"] = row[0] if row else 0
        d.close()
    except Exception:
        pass

    # 5d.1 (2026-05-17): tag metrics. Gated by NEX_TAG_FEEDBACK_ON.
    # When enabled, includes counts of coin/maybe/non on her recent
    # fountain outputs. When disabled, no metric is added (substrate purity).
    try:
        import os
        if os.environ.get("NEX_TAG_FEEDBACK_ON") == "1":
            d = sqlite3.connect(DYNAMIC_DB, timeout=10)
            row = d.execute(
                "SELECT tag, COUNT(*) FROM fountain_events "
                "WHERE tag IS NOT NULL AND ts > ? "
                "GROUP BY tag",
                (six_hours_ago,)
            ).fetchall()
            d.close()
            if row:
                tag_counts = {r[0]: r[1] for r in row}
                if tag_counts.get("coin"):
                    m["tags_coin_6h"] = tag_counts["coin"]
                if tag_counts.get("maybe"):
                    m["tags_maybe_6h"] = tag_counts["maybe"]
                if tag_counts.get("non"):
                    m["tags_non_6h"] = tag_counts["non"]
    except Exception:
        pass

    return m


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


def _previous_statement(d_cx):
    row = d_cx.execute(
        "SELECT statement FROM identity_log "
        "ORDER BY composed_at DESC LIMIT 1"
    ).fetchone()
    return row[0] if row else None


def identity_tick():
    now = time.time()
    local = datetime.fromtimestamp(now, TZ)
    hour = local.hour
    date_local = local.strftime("%Y-%m-%d")

    if hour not in COMPOSE_HOURS:
        return {"skipped": "not_compose_hour", "hour": hour}

    d_cx = sqlite3.connect(DYNAMIC_DB, timeout=15)
    try:
        # Already composed for this date+hour?
        row = d_cx.execute(
            "SELECT id FROM identity_log WHERE date_local=? AND hour_local=?",
            (date_local, hour)
        ).fetchone()
        if row:
            return {"skipped": "already_composed", "hour": hour}

        previous = _previous_statement(d_cx)
        metrics = _gather_metrics(now)
        statement = _compose_statement(metrics, previous)

        # Write to identity_log
        d_cx.execute(
            "INSERT INTO identity_log (composed_at, date_local, hour_local, statement, metrics_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (now, date_local, hour, statement, json.dumps(metrics))
        )
        d_cx.commit()
        
        # Write as Tier-6 belief
        try:
            b_cx = sqlite3.connect(BELIEFS_DB, timeout=10)
            b_cx.execute(
                "INSERT INTO beliefs "
                "(content, tier, confidence, created_at, source, branch_id, tags) "
                "VALUES (?, 6, 0.90, ?, ?, ?, ?)",
                (statement, int(now), SOURCE, "cognition", '["identity"]')
            )
            b_cx.commit()
            b_cx.close()
        except sqlite3.IntegrityError:
            pass
        except Exception as e:
            log.warning("identity belief write failed: %s", e)

        log.info("identity_loop: composed at %sh — %s", hour, statement[:120])
        return {"composed": True, "hour": hour, "statement": statement[:140]}
    finally:
        d_cx.close()


def identity_loop(state, stop):
    log.info("identity_loop started (compose_hours=%s, tick=%ds)",
             sorted(COMPOSE_HOURS), TICK_SECONDS)
    _ensure_identity_log()
    # Boot composition: if we missed a compose hour earlier today, fire it
    while not stop.is_set():
        try:
            stats = identity_tick()
            if stats.get("composed"):
                log.info("identity_loop: %s", stats.get("statement", "")[:160])
        except Exception as e:
            log.error("identity_loop tick failed: %s: %s",
                      type(e).__name__, str(e)[:200])
        stop.wait(TICK_SECONDS)
    log.info("identity_loop stopped")
