"""Wonder loop — generates specific questions about things in her feeds.

Every 15 minutes: picks an entity (capitalised proper noun) from
recent sense events, asks her LLM to write ONE specific question
about it. The question itself enters her substrate as Tier-6 belief.

Reverses passive reception: substrate absorbs feed items without
ever asking "but what about X?" This loop forces curiosity to form.

Output: belief with source='wonder_loop', tier=6.
"""
from __future__ import annotations
import json
import logging
import random
import re
from substrate import Reader, Writer, IntegrityError
import threading
import time
from pathlib import Path

log = logging.getLogger("theory_x.life.wonder_loop")

from substrate.paths import DbPath  # resolves NEX5_DATA_DIR at use time (test hygiene)
BELIEFS_DB = DbPath("beliefs")
SENSE_DB = DbPath("sense")
TICK_SECONDS = 900
RECENT_WINDOW_SECONDS = 7200
DAILY_CAP = 16
SOURCE = "wonder_loop"

# Skip generic / non-entity capitalised words
_STOPCAPS = {
    "The", "A", "An", "This", "That", "These", "Those", "It", "What",
    "How", "Why", "When", "Where", "Show", "HN", "Ask", "I", "Is", "Are",
    "Were", "Was", "Has", "Have", "Had", "Will", "Would", "Should", "Could",
    "May", "Can", "Do", "Does", "Did", "If", "Yes", "No", "Tier", "Phase",
    "PDF", "AI", "ML", "API", "CEO", "CTO", "US", "UK", "EU", "USA",
}

_CAP_RE = re.compile(r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b")


def _extract_entities(text):
    if not text:
        return []
    out = []
    for tok in _CAP_RE.findall(text):
        if tok in _STOPCAPS:
            continue
        if len(tok) < 4:
            continue
        out.append(tok)
    return out


def _pick_entity(sense_reader: Reader):
    rows = sense_reader.read(
        "SELECT payload FROM sense_events "
        "WHERE stream NOT LIKE 'internal.%' "
        "  AND timestamp > ? "
        "ORDER BY timestamp DESC LIMIT 100",
        (time.time() - RECENT_WINDOW_SECONDS,),
    )
    pool = []
    for row in rows:
        payload = row["payload"]
        try:
            d = json.loads(payload) if payload else {}
            text = d.get("title") or d.get("link") or ""
        except Exception:
            text = payload or ""
        pool.extend(_extract_entities(text))
    if not pool:
        return None
    return random.choice(pool)


def _daily_count(reader: Reader):
    cutoff = time.time() - 86400
    row = reader.read_one(
        "SELECT COUNT(*) FROM beliefs WHERE source=? AND created_at > ?",
        (SOURCE, cutoff),
    )
    return row[0] if row else 0


def _compose_question(voice, entity, context_snippet):
    from voice.llm import VoiceRequest
    prompt = (
        "An entity has come up across your feeds: " + entity + "\n\n"
        "Context snippet: \"" + context_snippet + "\"\n\n"
        "Write ONE specific, real question YOU would actually want answered "
        "about " + entity + ". Not 'what is " + entity + "' — something with "
        "weight. First person, 8-20 words. No preamble. Just the question."
    )
    try:
        req = VoiceRequest(prompt=prompt, max_tokens=50, temperature=0.9)
        resp = voice.speak(req)
        if resp and resp.text:
            return resp.text.strip()
    except Exception as e:
        log.warning("compose_question voice call failed: %s", e)
    return None


def _context_for(entity, sense_reader: Reader):
    """Pull one recent sense snippet containing the entity."""
    rows = sense_reader.read(
        "SELECT payload FROM sense_events "
        "WHERE payload LIKE ? AND timestamp > ? "
        "ORDER BY timestamp DESC LIMIT 5",
        ("%" + entity + "%", time.time() - RECENT_WINDOW_SECONDS),
    )
    for row in rows:
        payload = row["payload"]
        try:
            d = json.loads(payload) if payload else {}
            text = d.get("title") or d.get("link") or payload or ""
            if entity in text:
                return text[:200]
        except Exception:
            if entity in (payload or ""):
                return payload[:200]
    return entity


def wonder_tick(
    voice,
    *,
    beliefs_reader: Reader | None = None,
    beliefs_writer: Writer | None = None,
    sense_reader: Reader | None = None,
):
    reader = beliefs_reader or Reader(BELIEFS_DB)
    s_reader = sense_reader or Reader(SENSE_DB)
    own_writer = beliefs_writer is None
    writer = beliefs_writer or Writer(BELIEFS_DB, name="wonder_loop")
    try:
        if _daily_count(reader) >= DAILY_CAP:
            return {"skipped": "daily_cap"}
        entity = _pick_entity(s_reader)
        if not entity:
            return {"skipped": "no_entity"}
        context = _context_for(entity, s_reader)
        question = _compose_question(voice, entity, context)
        if not question:
            return {"skipped": "voice_failed"}
        if "?" not in question:
            return {"skipped": "not_a_question"}
        now = int(time.time())
        try:
            writer.write(
                "INSERT INTO beliefs "
                "(content, tier, confidence, created_at, source, branch_id, tags) "
                "VALUES (?, 6, 0.60, ?, ?, ?, '[]')",
                (question, now, SOURCE, "cognition"),
            )
            log.info("wonder_loop: %s -> %s", entity, question[:80])
            return {"wondered": True, "entity": entity, "text": question[:140]}
        except IntegrityError:
            return {"skipped": "duplicate"}
    finally:
        if own_writer:
            writer.close()


def wonder_loop(state, stop):
    log.info("wonder_loop started (tick=%ds, cap=%d/day)",
             TICK_SECONDS, DAILY_CAP)
    voice = None
    while not stop.is_set():
        try:
            if voice is None:
                from voice.llm import VoiceClient, voice_model
                voice = VoiceClient(model=voice_model())
            stats = wonder_tick(
                voice,
                beliefs_reader=state.readers["beliefs"],
                beliefs_writer=state.writers["beliefs"],
                sense_reader=state.readers["sense"],
            )
            if stats.get("wondered"):
                log.info("wonder_loop: %s", stats.get("text", "")[:100])
        except Exception as e:
            log.error("wonder_loop tick failed: %s: %s",
                      type(e).__name__, str(e)[:200])
            voice = None
        stop.wait(TICK_SECONDS)
    log.info("wonder_loop stopped")
