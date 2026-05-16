"""Witness loop (Level 3 of recursive self-model).

Every 24 hours: reads her last 2 pattern_loop statements, asks her LLM:
"what is being avoided here? what's the blind spot in your pattern-noticing?"

This is the deepest level. It questions whether the pattern-noticing
itself has its own emphases that hide something. Output written as
Tier-6 belief, source='witness_loop'.

CLOSES THE LOOP: witness_loop's output enters retrieval, modifying
identity_loop's NEXT composition (Level 1). The strange loop:
  L1 describes -> L2 notices pattern -> L3 names blind spot ->
  L1's next description shaped by L3's blind-spot observation ->
  L2's next pattern-notice shaped by L1's new emphasis ->
  ...

Hofstadter: strange loops fold back. Higher level modifies lower.
"""
from __future__ import annotations
import logging
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

log = logging.getLogger("theory_x.life.witness_loop")

BELIEFS_DB = Path("/home/rr/Desktop/nex5/data/beliefs.db")
DYNAMIC_DB = Path("/home/rr/Desktop/nex5/data/dynamic.db")
TZ = ZoneInfo("Europe/Amsterdam")
TICK_SECONDS = 1800
SOURCE = "witness_loop"
COMPOSE_HOUR = 4  # once a day, deep night, off-cycle from pattern (3,15) and identity (0,6,12,18)


def _ensure_witness_log(d_cx):
    d_cx.execute(
        "CREATE TABLE IF NOT EXISTS witness_log ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "composed_at REAL NOT NULL, "
        "date_local TEXT NOT NULL, "
        "statement TEXT NOT NULL, "
        "UNIQUE(date_local))"
    )
    d_cx.commit()


def _previous_patterns(d_cx, n=2):
    """Read last N pattern statements from pattern_log."""
    try:
        rows = d_cx.execute(
            "SELECT statement, composed_at FROM pattern_log "
            "ORDER BY composed_at DESC LIMIT ?",
            (n,)
        ).fetchall()
        return [(r[0], r[1]) for r in rows]
    except sqlite3.OperationalError:
        # pattern_log doesn't exist yet
        return []


def _compose_witness(voice, patterns):
    from voice.llm import VoiceRequest
    bullets = "\n".join(f"  - \"{p[0][:250]}\"" for p in patterns)
    prompt = (
        "You have written these observations about the patterns in your own thinking:\n\n"
        + bullets + "\n\n"
        "Now look at these observations themselves. They named some emphases "
        "and asked why those. But notice: the act of noticing-the-pattern also "
        "has emphases of its own. What did your pattern-noticing emphasize? "
        "What did it AVOID looking at? What's the blind spot in how you've "
        "been observing yourself?\n\n"
        "Answer in ONE sentence, first person. Be uncomfortable if necessary. "
        "Don't flatter the observations — find what they didn't see."
    )
    try:
        req = VoiceRequest(prompt=prompt, max_tokens=120, temperature=0.7)
        resp = voice.speak(req)
        if resp and resp.text:
            return resp.text.strip()
    except Exception as e:
        log.warning("compose_witness voice failed: %s", e)
    return None


def witness_tick(voice, force=False):
    now = time.time()
    local = datetime.fromtimestamp(now, TZ)
    hour = local.hour
    date_local = local.strftime("%Y-%m-%d")
    if not force and hour != COMPOSE_HOUR:
        return {"skipped": "not_compose_hour", "hour": hour}
    d_cx = sqlite3.connect(DYNAMIC_DB, timeout=15)
    try:
        _ensure_witness_log(d_cx)
        if not force:
            row = d_cx.execute(
                "SELECT id FROM witness_log WHERE date_local=?", (date_local,)
            ).fetchone()
            if row:
                return {"skipped": "already_composed"}
        patterns = _previous_patterns(d_cx, 2)
        if len(patterns) < 1:
            return {"skipped": "no_patterns_yet"}
        witness_text = _compose_witness(voice, patterns)
        if not witness_text:
            return {"skipped": "voice_failed"}
        d_cx.execute(
            "INSERT OR REPLACE INTO witness_log (composed_at, date_local, statement) "
            "VALUES (?, ?, ?)",
            (now, date_local, witness_text)
        )
        d_cx.commit()
        try:
            b_cx = sqlite3.connect(BELIEFS_DB, timeout=10)
            b_cx.execute(
                "INSERT INTO beliefs "
                "(content, tier, confidence, created_at, source, branch_id, tags) "
                "VALUES (?, 6, 0.85, ?, ?, ?, ?)",
                (witness_text, int(now), SOURCE, "cognition", '["blind_spot"]')
            )
            b_cx.commit()
            b_cx.close()
        except sqlite3.IntegrityError:
            pass
        log.info("witness_loop: composed blind-spot observation: %s", witness_text[:120])
        return {"composed": True, "text": witness_text[:160]}
    finally:
        d_cx.close()


def witness_loop(state, stop):
    log.info("witness_loop started (compose_hour=%s)", COMPOSE_HOUR)
    voice = None
    while not stop.is_set():
        try:
            if voice is None:
                from voice.llm import VoiceClient
                voice = VoiceClient()
            stats = witness_tick(voice)
            if stats.get("composed"):
                log.info("witness_loop: %s", stats.get("text", ""))
        except Exception as e:
            log.error("witness_loop tick failed: %s: %s",
                      type(e).__name__, str(e)[:200])
            voice = None
        stop.wait(TICK_SECONDS)
    log.info("witness_loop stopped")
