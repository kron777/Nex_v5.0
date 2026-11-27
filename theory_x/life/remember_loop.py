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
from substrate import Reader, Writer, IntegrityError
import threading
import time
from pathlib import Path

log = logging.getLogger("theory_x.life.remember_loop")

from substrate.paths import DbPath  # resolves NEX5_DATA_DIR at use time (test hygiene)
BELIEFS_DB = DbPath("beliefs")
TICK_SECONDS = 600
OLD_MIN_AGE_DAYS = 7
RECENT_MAX_AGE_SECONDS = 3600
DAILY_CAP = 24
SOURCE = "remember_loop"


def _pick_old_belief(reader: Reader):
    cutoff = time.time() - OLD_MIN_AGE_DAYS * 86400
    row = reader.read_one(
        "SELECT id, content, branch_id, created_at "
        "FROM beliefs WHERE created_at < ? AND tier >= 6 "
        "AND source NOT IN ('remember_loop', 'spectrum') "
        "ORDER BY RANDOM() LIMIT 1",
        (cutoff,),
    )
    if not row:
        return None
    return {
        "id": row["id"],
        "content": row["content"],
        "branch": row["branch_id"],
        "created_at": row["created_at"],
    }


def _pick_recent_belief(reader: Reader):
    cutoff = time.time() - RECENT_MAX_AGE_SECONDS
    row = reader.read_one(
        "SELECT id, content, branch_id, created_at "
        "FROM beliefs WHERE created_at > ? AND tier >= 6 "
        "AND source NOT IN ('remember_loop', 'spectrum') "
        "ORDER BY RANDOM() LIMIT 1",
        (cutoff,),
    )
    if not row:
        return None
    return {
        "id": row["id"],
        "content": row["content"],
        "branch": row["branch_id"],
        "created_at": row["created_at"],
    }


def _daily_count(reader: Reader) -> int:
    cutoff = time.time() - 86400
    row = reader.read_one(
        "SELECT COUNT(*) AS n FROM beliefs WHERE source=? AND created_at > ?",
        (SOURCE, cutoff),
    )
    return int(row["n"]) if row else 0


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


def remember_tick(
    voice,
    *,
    beliefs_reader: Reader | None = None,
    beliefs_writer: Writer | None = None,
):
    """Run one temporal-link cycle through the canonical beliefs Reader/Writer.

    Standalone tools/tests may omit the handles; normal loop operation injects
    the shared per-database handles from Stage 2.
    """
    reader = beliefs_reader or Reader(BELIEFS_DB)
    own_writer = beliefs_writer is None
    writer = beliefs_writer or Writer(BELIEFS_DB, name="remember_loop")
    try:
        if _daily_count(reader) >= DAILY_CAP:
            return {"skipped": "daily_cap"}
        old = _pick_old_belief(reader)
        recent = _pick_recent_belief(reader)
        if not old or not recent:
            return {"skipped": "no_pair"}
        if old["id"] == recent["id"]:
            return {"skipped": "same_belief"}
        link_text = _compose_link(voice, old, recent)
        if not link_text:
            return {"skipped": "voice_failed"}
        now = int(time.time())
        try:
            writer.write(
                "INSERT INTO beliefs "
                "(content, tier, confidence, created_at, source, branch_id, tags) "
                "VALUES (?, 6, 0.70, ?, ?, ?, '[]')",
                (
                    link_text,
                    now,
                    SOURCE,
                    recent.get("branch") or old.get("branch") or "cognition",
                ),
            )
            log.info(
                "remember_loop: linked #%s + #%s -> %s",
                old["id"], recent["id"], link_text[:80],
            )
            return {
                "linked": True,
                "old_id": old["id"],
                "recent_id": recent["id"],
                "text": link_text[:120],
            }
        except IntegrityError:
            return {"skipped": "duplicate_content"}
    finally:
        if own_writer:
            writer.close()


def remember_loop(state, stop):
    log.info("remember_loop started (tick=%ds, cap=%d/day)",
             TICK_SECONDS, DAILY_CAP)
    voice = None
    while not stop.is_set():
        try:
            if voice is None:
                from voice.llm import VoiceClient, voice_model
                voice = VoiceClient(model=voice_model())
            stats = remember_tick(
                voice,
                beliefs_reader=state.readers["beliefs"],
                beliefs_writer=state.writers["beliefs"],
            )
            if stats.get("linked"):
                log.info("remember_loop: %s", stats.get("text", "")[:100])
        except Exception as e:
            log.error("remember_loop tick failed: %s: %s",
                      type(e).__name__, str(e)[:200])
            voice = None
        stop.wait(TICK_SECONDS)
    log.info("remember_loop stopped")
