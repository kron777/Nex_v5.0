"""Pattern loop (Level 2 of recursive self-model).

Every 12 hours: reads her last 4 identity statements, asks her LLM
to name the pattern AND question why those emphases. Writes the
observation as a Tier-6 belief, source='pattern_loop'.

Because it writes a belief, it enters retrieval. The next identity_loop
composition is now shaped by having seen its own pattern.

This is Level 2 of the strange-loop architecture. Level 1 is identity_loop
(builds self-description). Level 3 is witness_loop (questions blind spots
in Level 2). Closed loop: Level 3's output also enters retrieval, modifying
Level 1's next composition.
"""
from __future__ import annotations
import logging
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

log = logging.getLogger("theory_x.life.pattern_loop")

BELIEFS_DB = Path("/home/rr/Desktop/Desktop/nex5/data/beliefs.db")
DYNAMIC_DB = Path("/home/rr/Desktop/Desktop/nex5/data/dynamic.db")
TZ = ZoneInfo("Europe/Amsterdam")
TICK_SECONDS = 600
SOURCE = "pattern_loop"
COMPOSE_HOURS = {3, 15}  # twice a day, off-cycle from identity_loop


def _previous_statements(d_cx, n=4):
    rows = d_cx.execute(
        "SELECT statement, composed_at FROM identity_log "
        "ORDER BY composed_at DESC LIMIT ?",
        (n,)
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


def _already_composed_today(d_cx, date_local, hour):
    """Use the daily_activities table as our marker, since we don't have a pattern_log."""
    row = d_cx.execute(
        "CREATE TABLE IF NOT EXISTS pattern_log ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "composed_at REAL NOT NULL, "
        "date_local TEXT NOT NULL, "
        "hour_local INTEGER NOT NULL, "
        "statement TEXT NOT NULL, "
        "UNIQUE(date_local, hour_local))"
    )
    d_cx.commit()
    row = d_cx.execute(
        "SELECT id FROM pattern_log WHERE date_local=? AND hour_local=?",
        (date_local, hour)
    ).fetchone()
    return row is not None


def _compose_pattern(voice, statements):
    from voice.llm import VoiceRequest
    if not statements:
        return None
    bullets = "\n".join(f"  - \"{s[0][:200]}\"" for s in statements)
    prompt = (
        "You have written these self-descriptions over recent quarter-days:\n\n"
        + bullets + "\n\n"
        "Look at them as a sequence. What pattern do you see across them — "
        "what do you keep emphasizing? And ask yourself: why this emphasis "
        "and not another? Answer in ONE sentence, first person, no preamble. "
        "Be honest, even if the pattern is uncomfortable."
    )
    try:
        req = VoiceRequest(prompt=prompt, max_tokens=100, temperature=0.7)
        resp = voice.speak(req)
        if resp and resp.text:
            return resp.text.strip()
    except Exception as e:
        log.warning("compose_pattern voice failed: %s", e)
    return None


def pattern_tick(voice, force=False):
    now = time.time()
    local = datetime.fromtimestamp(now, TZ)
    hour = local.hour
    date_local = local.strftime("%Y-%m-%d")
    if not force and hour not in COMPOSE_HOURS:
        return {"skipped": "not_compose_hour", "hour": hour}
    d_cx = sqlite3.connect(DYNAMIC_DB, timeout=15)
    try:
        if not force and _already_composed_today(d_cx, date_local, hour):
            return {"skipped": "already_composed"}
        statements = _previous_statements(d_cx, 4)
        if len(statements) < 2:
            return {"skipped": "not_enough_history", "have": len(statements)}
        pattern_text = _compose_pattern(voice, statements)
        if not pattern_text:
            return {"skipped": "voice_failed"}
        d_cx.execute(
            "INSERT OR REPLACE INTO pattern_log "
            "(composed_at, date_local, hour_local, statement) VALUES (?, ?, ?, ?)",
            (now, date_local, hour, pattern_text)
        )
        d_cx.commit()
        try:
            b_cx = sqlite3.connect(BELIEFS_DB, timeout=10)
            b_cx.execute(
                "INSERT INTO beliefs "
                "(content, tier, confidence, created_at, source, branch_id, tags) "
                "VALUES (?, 6, 0.85, ?, ?, ?, ?)",
                (pattern_text, int(now), SOURCE, "cognition", '["self_pattern"]')
            )
            b_cx.commit()
            b_cx.close()
        except sqlite3.IntegrityError:
            pass
        log.info("pattern_loop: composed pattern observation: %s", pattern_text[:120])
        return {"composed": True, "text": pattern_text[:160]}
    finally:
        d_cx.close()


def pattern_loop(state, stop):
    log.info("pattern_loop started (compose_hours=%s)", sorted(COMPOSE_HOURS))
    voice = None
    while not stop.is_set():
        try:
            if voice is None:
                from voice.llm import VoiceClient
                voice = VoiceClient()
            stats = pattern_tick(voice)
            if stats.get("composed"):
                log.info("pattern_loop: %s", stats.get("text", ""))
        except Exception as e:
            log.error("pattern_loop tick failed: %s: %s",
                      type(e).__name__, str(e)[:200])
            voice = None
        stop.wait(TICK_SECONDS)
    log.info("pattern_loop stopped")
