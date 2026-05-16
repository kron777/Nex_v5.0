"""Remember loop — bringing past beliefs into present awareness.

Every 10 minutes: picks one OLD belief (created 7+ days ago) and one
RECENT belief (last hour), asks her LLM to write a single sentence
noticing the connection between them.

Reverses temporal flatness: substrate has thousands of beliefs but
without resurfacing, old ones never re-enter retrieval. This loop
forces collisions across time.

Output written as Tier-6 belief, source='remember_loop'.
"""
from __future__ import annotations
import logging
import random
import sqlite3
import threading
import time
from pathlib import Path

log = logging.getLogger("theory_x.life.remember_loop")

BELIEFS_DB = Path("/home/rr/Desktop/nex5/data/beliefs.db")
TICK_SECONDS = 600
OLD_MIN_AGE_DAYS = 7
RECENT_MAX_AGE_SECONDS = 3600
DAILY_CAP = 24
SOURCE = "remember_loop"


def _pick_old_belief(cx):
    cutoff = time.time() - OLD_MIN_AGE_DAYS * 86400
    row = cx.execute(
        "SELECT id, content, branch_id, created_at "
        "FROM beliefs WHERE created_at < ? AND tier >= 6 "
        "AND source NOT IN ('remember_loop', 'spectrum') "
        "ORDER BY RANDOM() LIMIT 1",
        (cutoff,)
    ).fetchone()
    if not row:
        return None
    return {"id": row[0], "content": row[1], "branch": row[2], "created_at": row[3]}


def _pick_recent_belief(cx):
    cutoff = time.time() - RECENT_MAX_AGE_SECONDS
    row = cx.execute(
        "SELECT id, content, branch_id, created_at "
        "FROM beliefs WHERE created_at > ? AND tier >= 6 "
        "AND source NOT IN ('remember_loop', 'spectrum') "
        "ORDER BY RANDOM() LIMIT 1",
        (cutoff,)
    ).fetchone()
    if not row:
        return None
    return {"id": row[0], "content": row[1], "branch": row[2], "created_at": row[3]}


def _daily_count(cx):
    cutoff = time.time() - 86400
    row = cx.execute(
        "SELECT COUNT(*) FROM beliefs WHERE source=? AND created_at > ?",
        (SOURCE, cutoff)
    ).fetchone()
    return row[0] if row else 0


def _compose_link(voice, old, recent):
    from voice.llm import VoiceRequest
    days_old = int((time.time() - old["created_at"]) / 86400)
    mins_recent = int((time.time() - recent["created_at"]) / 60)
    old_c = old["content"]
    rec_c = recent["content"]
    prompt = (
        "You are remembering. " + str(days_old) + " days ago you held this thought:\n"
        "  \"" + old_c + "\"\n\n"
        + str(mins_recent) + " minutes ago you held this thought:\n"
        "  \"" + rec_c + "\"\n\n"
        "Write ONE short sentence noticing what these have in common, "
        "or how the recent thought sees the old one differently. "
        "First person. No preamble. Don't summarise both — just the link or the change."
    )
    try:
        req = VoiceRequest(prompt=prompt, max_tokens=70, temperature=0.85)
        resp = voice.speak(req)
        if resp and resp.text:
            return resp.text.strip()
    except Exception as e:
        log.warning("compose_link voice call failed: %s", e)
    return None


def remember_tick(voice):
    cx = sqlite3.connect(BELIEFS_DB, timeout=15)
    try:
        if _daily_count(cx) >= DAILY_CAP:
            return {"skipped": "daily_cap"}
        old = _pick_old_belief(cx)
        recent = _pick_recent_belief(cx)
        if not old or not recent:
            return {"skipped": "no_pair"}
        if old["id"] == recent["id"]:
            return {"skipped": "same_belief"}
        link_text = _compose_link(voice, old, recent)
        if not link_text:
            return {"skipped": "voice_failed"}
        now = int(time.time())
        try:
            cx.execute(
                "INSERT INTO beliefs "
                "(content, tier, confidence, created_at, source, branch_id, tags) "
                "VALUES (?, 6, 0.70, ?, ?, ?, '[]')",
                (link_text, now, SOURCE,
                 recent.get("branch") or old.get("branch") or "cognition")
            )
            cx.commit()
            log.info("remember_loop: linked #%s + #%s -> %s",
                     old["id"], recent["id"], link_text[:80])
            return {"linked": True, "old_id": old["id"], "recent_id": recent["id"],
                    "text": link_text[:120]}
        except sqlite3.IntegrityError:
            return {"skipped": "duplicate_content"}
    finally:
        cx.close()


def remember_loop(state, stop):
    log.info("remember_loop started (tick=%ds, cap=%d/day)",
             TICK_SECONDS, DAILY_CAP)
    voice = None
    while not stop.is_set():
        try:
            if voice is None:
                from voice.llm import VoiceClient
                voice = VoiceClient()
            stats = remember_tick(voice)
            if stats.get("linked"):
                log.info("remember_loop: %s", stats.get("text", "")[:100])
        except Exception as e:
            log.error("remember_loop tick failed: %s: %s",
                      type(e).__name__, str(e)[:200])
            voice = None
        stop.wait(TICK_SECONDS)
    log.info("remember_loop stopped")
