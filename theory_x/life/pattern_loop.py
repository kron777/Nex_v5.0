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
from substrate.paths import db_paths
import logging
from substrate import Reader, Writer, IntegrityError
import threading
import time
from datetime import datetime
from pathlib import Path
from nex_config import local_tz

log = logging.getLogger("theory_x.life.pattern_loop")

BELIEFS_DB = Path(str(db_paths()["beliefs"]))
DYNAMIC_DB = Path(str(db_paths()["dynamic"]))
TICK_SECONDS = 600
SOURCE = "pattern_loop"
COMPOSE_HOURS = {3, 15}  # twice a day, off-cycle from identity_loop


def _previous_statements(reader: Reader, n=4):
    rows = reader.read(
        "SELECT statement, composed_at FROM identity_log "
        "ORDER BY composed_at DESC LIMIT ?",
        (n,),
    )
    return [(r["statement"], r["composed_at"]) for r in rows]


def _already_composed_today(reader: Reader, writer: Writer, date_local, hour):
    """Ensure the pattern marker exists through the dynamic Writer, then read it."""
    writer.write(
        "CREATE TABLE IF NOT EXISTS pattern_log ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "composed_at REAL NOT NULL, "
        "date_local TEXT NOT NULL, "
        "hour_local INTEGER NOT NULL, "
        "statement TEXT NOT NULL, "
        "UNIQUE(date_local, hour_local))"
    )
    row = reader.read_one(
        "SELECT id FROM pattern_log WHERE date_local=? AND hour_local=?",
        (date_local, hour),
    )
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


def pattern_tick(
    voice,
    force=False,
    *,
    dynamic_reader: Reader | None = None,
    dynamic_writer: Writer | None = None,
    beliefs_writer: Writer | None = None,
):
    now = time.time()
    local = datetime.fromtimestamp(now, local_tz())
    hour = local.hour
    date_local = local.strftime("%Y-%m-%d")
    if not force and hour not in COMPOSE_HOURS:
        return {"skipped": "not_compose_hour", "hour": hour}
    reader = dynamic_reader or Reader(DYNAMIC_DB)
    own_dynamic_writer = dynamic_writer is None
    d_writer = dynamic_writer or Writer(DYNAMIC_DB, name="pattern_loop")
    own_beliefs_writer = beliefs_writer is None
    b_writer = beliefs_writer or Writer(BELIEFS_DB, name="pattern_loop")
    try:
        if not force and _already_composed_today(reader, d_writer, date_local, hour):
            return {"skipped": "already_composed"}
        statements = _previous_statements(reader, 4)
        if len(statements) < 2:
            return {"skipped": "not_enough_history", "have": len(statements)}
        pattern_text = _compose_pattern(voice, statements)
        if not pattern_text:
            return {"skipped": "voice_failed"}
        d_writer.write(
            "INSERT OR REPLACE INTO pattern_log "
            "(composed_at, date_local, hour_local, statement) VALUES (?, ?, ?, ?)",
            (now, date_local, hour, pattern_text),
        )
        try:
            b_writer.write(
                "INSERT INTO beliefs "
                "(content, tier, confidence, created_at, source, branch_id, tags) "
                "VALUES (?, 6, 0.85, ?, ?, ?, ?)",
                (pattern_text, int(now), SOURCE, "cognition", '["self_pattern"]'),
            )
        except IntegrityError:
            pass
        log.info("pattern_loop: composed pattern observation: %s", pattern_text[:120])
        return {"composed": True, "text": pattern_text[:160]}
    finally:
        if own_dynamic_writer:
            d_writer.close()
        if own_beliefs_writer:
            b_writer.close()


def pattern_loop(state, stop):
    log.info("pattern_loop started (compose_hours=%s)", sorted(COMPOSE_HOURS))
    voice = None
    while not stop.is_set():
        try:
            if voice is None:
                from voice.llm import VoiceClient, voice_model
                voice = VoiceClient(model=voice_model())
            stats = pattern_tick(
                voice,
                dynamic_reader=state.readers["dynamic"],
                dynamic_writer=state.writers["dynamic"],
                beliefs_writer=state.writers["beliefs"],
            )
            if stats.get("composed"):
                log.info("pattern_loop: %s", stats.get("text", ""))
        except Exception as e:
            log.error("pattern_loop tick failed: %s: %s",
                      type(e).__name__, str(e)[:200])
            voice = None
        stop.wait(TICK_SECONDS)
    log.info("pattern_loop stopped")
