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
from substrate.paths import db_paths
import logging
from substrate import Reader, Writer, IntegrityError, OperationalError
import threading
import time
from datetime import datetime
from pathlib import Path
from nex_config import local_tz

log = logging.getLogger("theory_x.life.witness_loop")

BELIEFS_DB = Path(str(db_paths()["beliefs"]))
DYNAMIC_DB = Path(str(db_paths()["dynamic"]))
TICK_SECONDS = 1800
SOURCE = "witness_loop"
COMPOSE_HOUR = 4  # once a day, deep night, off-cycle from pattern (3,15) and identity (0,6,12,18)


def _ensure_witness_log(writer: Writer):
    writer.write(
        "CREATE TABLE IF NOT EXISTS witness_log ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "composed_at REAL NOT NULL, "
        "date_local TEXT NOT NULL, "
        "statement TEXT NOT NULL, "
        "UNIQUE(date_local))"
    )


def _previous_patterns(reader: Reader, n=2):
    """Read last N pattern statements from pattern_log."""
    try:
        rows = reader.read(
            "SELECT statement, composed_at FROM pattern_log "
            "ORDER BY composed_at DESC LIMIT ?",
            (n,),
        )
        return [(r["statement"], r["composed_at"]) for r in rows]
    except OperationalError:
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


def witness_tick(
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
    if not force and hour != COMPOSE_HOUR:
        return {"skipped": "not_compose_hour", "hour": hour}
    reader = dynamic_reader or Reader(DYNAMIC_DB)
    own_dynamic_writer = dynamic_writer is None
    d_writer = dynamic_writer or Writer(DYNAMIC_DB, name="witness_loop")
    own_beliefs_writer = beliefs_writer is None
    b_writer = beliefs_writer or Writer(BELIEFS_DB, name="witness_loop")
    try:
        _ensure_witness_log(d_writer)
        if not force:
            row = reader.read_one(
                "SELECT id FROM witness_log WHERE date_local=?",
                (date_local,),
            )
            if row:
                return {"skipped": "already_composed"}
        patterns = _previous_patterns(reader, 2)
        if len(patterns) < 1:
            return {"skipped": "no_patterns_yet"}
        witness_text = _compose_witness(voice, patterns)
        if not witness_text:
            return {"skipped": "voice_failed"}
        d_writer.write(
            "INSERT OR REPLACE INTO witness_log (composed_at, date_local, statement) "
            "VALUES (?, ?, ?)",
            (now, date_local, witness_text),
        )
        try:
            b_writer.write(
                "INSERT INTO beliefs "
                "(content, tier, confidence, created_at, source, branch_id, tags) "
                "VALUES (?, 6, 0.85, ?, ?, ?, ?)",
                (witness_text, int(now), SOURCE, "cognition", '["blind_spot"]'),
            )
        except IntegrityError:
            pass
        log.info("witness_loop: composed blind-spot observation: %s", witness_text[:120])
        return {"composed": True, "text": witness_text[:160]}
    finally:
        if own_dynamic_writer:
            d_writer.close()
        if own_beliefs_writer:
            b_writer.close()


def witness_loop(state, stop):
    log.info("witness_loop started (compose_hour=%s)", COMPOSE_HOUR)
    voice = None
    while not stop.is_set():
        try:
            if voice is None:
                from voice.llm import VoiceClient, voice_model
                voice = VoiceClient(model=voice_model())
            stats = witness_tick(
                voice,
                dynamic_reader=state.readers["dynamic"],
                dynamic_writer=state.writers["dynamic"],
                beliefs_writer=state.writers["beliefs"],
            )
            if stats.get("composed"):
                log.info("witness_loop: %s", stats.get("text", ""))
        except Exception as e:
            log.error("witness_loop tick failed: %s: %s",
                      type(e).__name__, str(e)[:200])
            voice = None
        stop.wait(TICK_SECONDS)
    log.info("witness_loop stopped")
