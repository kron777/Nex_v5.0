"""Focus loop — sustained attention daemon.

Picks ONE open problem to focus on (the one with deepest substrate
engagement: most beliefs whose content matches the problem's title words).
Every fountain fire, appends an observation onto that problem from her
latest thought. When the last 3 observations are too similar (stuck),
writes a ping to the chat as role='nex' asking Jon for help.

Reverses the hum-drum: gives her a thread to hold across many fires
instead of starting fresh every 2 minutes.
"""
from __future__ import annotations
import json
import logging
from substrate import Reader, Writer
import threading
import time
from pathlib import Path

log = logging.getLogger("theory_x.sustained.focus_loop")

from substrate.paths import DbPath  # resolves NEX5_DATA_DIR at use time (test hygiene)
BELIEFS_DB = DbPath("beliefs")
CONVERSATIONS_DB = DbPath("conversations")
DYNAMIC_DB = DbPath("dynamic")

TICK_SECONDS = 60
MAX_OBSERVATIONS = 50
STUCK_SIMILARITY = 0.85
STUCK_WINDOW = 3
PING_COOLDOWN_SECONDS = 1800  # don't re-ping the same problem within 30 min
# 2026-05-30: global cooldown across ALL focus pings (per-problem cooldown
# does not stop spam when several distinct problems go stuck in the same
# window — seen on screen: 4 different-problem pings clustered together).
# Pings stop if a focus ping went out under any problem in the last
# GLOBAL_PING_COOLDOWN_SECONDS. Override with NEX5_FOCUS_PING_GLOBAL_COOLDOWN.
GLOBAL_PING_COOLDOWN_SECONDS = 1200  # 20 min between any two focus pings
INTERNAL_SESSION_ID = "internal_focus_loop"

_STOPWORDS = {
    "a", "an", "the", "is", "are", "what", "how", "why", "this", "that",
    "of", "in", "on", "to", "for", "with", "from", "signal", "investigate",
    "across", "these", "domains",
}


def _title_keywords(title: str) -> set[str]:
    tokens = (w.strip("\'\".,?!:;()") for w in title.lower().split())
    return {w for w in tokens if w not in _STOPWORDS and len(w) > 2}


def _pick_focus(
    beliefs_reader: Reader, conversations_reader: Reader
) -> tuple[int, str, int] | None:
    """Return (problem_id, title, connection_count) for the most-connected open problem."""
    problems = conversations_reader.read(
        "SELECT id, title FROM open_problems WHERE state='open'"
    )
    if not problems:
        return None
    best = None
    for problem in problems:
        problem_id, title = problem["id"], problem["title"]
        keywords = _title_keywords(title or "")
        if not keywords:
            continue
        where = " OR ".join("content LIKE ?" for _ in keywords)
        params = tuple(f"%{keyword}%" for keyword in keywords)
        row = beliefs_reader.read_one(
            f"SELECT COUNT(*) AS n FROM beliefs WHERE ({where})", params
        )
        count = int(row["n"]) if row else 0
        if best is None or count > best[2]:
            best = (problem_id, title, count)
    return best


def _update_current_focus(
    dynamic_writer: Writer, problem_id: int, observations_count: int
) -> None:
    dynamic_writer.write(
        "INSERT INTO current_focus (id, problem_id, picked_at, observations_at_pick) "
        "VALUES (1, ?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET problem_id=excluded.problem_id, "
        "picked_at=excluded.picked_at, observations_at_pick=excluded.observations_at_pick "
        "WHERE current_focus.problem_id != excluded.problem_id",
        (problem_id, time.time(), observations_count),
    )


def _latest_fountain_thought(dynamic_reader: Reader) -> str | None:
    row = dynamic_reader.read_one(
        "SELECT thought FROM fountain_events WHERE thought != '' "
        "AND ts > (strftime('%s','now') - 600) "
        "ORDER BY ts DESC LIMIT 1"
    )
    if not row or not row["thought"]:
        return None
    return row["thought"]


def _related_to_focus(thought: str, focus_title: str) -> bool:
    """Cheap match: any title keyword appears in the thought."""
    kws = _title_keywords(focus_title)
    if not kws:
        return False
    t = thought.lower()
    return any(kw in t for kw in kws)


def _append_observation(
    conversations_reader: Reader,
    conversations_writer: Writer,
    problem_id: int,
    observation: str,
) -> int:
    """Append observation; return the resulting count.

    No-ops if the new observation is byte-identical to the last entry already
    on file. The read uses Reader and the mutation is submitted through the
    one-pen conversations Writer.
    """
    row = conversations_reader.read_one(
        "SELECT observations FROM open_problems WHERE id=?", (problem_id,)
    )
    if not row:
        return 0
    try:
        observations = json.loads(row["observations"]) if row["observations"] else []
    except Exception:
        observations = []
    if observations:
        last = observations[-1]
        last_text = last.get("text", "") if isinstance(last, dict) else str(last)
        if observation.strip() == last_text.strip():
            return len(observations)
    observations.append({"text": observation, "ts": time.time()})
    if len(observations) > MAX_OBSERVATIONS:
        observations = observations[-MAX_OBSERVATIONS:]
    conversations_writer.write(
        "UPDATE open_problems SET observations=?, last_touched_at=? WHERE id=?",
        (json.dumps(observations), time.time(), problem_id),
    )
    return len(observations)


def _check_stuck(conversations_reader: Reader, problem_id: int) -> bool:
    """Stuck if last STUCK_WINDOW observations are pairwise too similar."""
    row = conversations_reader.read_one(
        "SELECT observations, state FROM open_problems WHERE id=?", (problem_id,)
    )
    if not row:
        return False
    if row["state"] == "stuck":
        return False  # already marked
    try:
        observations = json.loads(row["observations"]) if row["observations"] else []
    except Exception:
        return False
    if len(observations) < STUCK_WINDOW:
        return False
    recent = [item["text"] for item in observations[-STUCK_WINDOW:]]
    try:
        from theory_x.diversity.embeddings import embed, cosine
        vectors = [embed(text) for text in recent]
        for i in range(len(vectors)):
            for j in range(i + 1, len(vectors)):
                if cosine(vectors[i], vectors[j]) < STUCK_SIMILARITY:
                    return False
        return True
    except Exception as exc:
        log.warning("stuck check failed: %s", exc)
        return False


def _last_ping_age(conversations_reader: Reader, problem_id: int) -> float:
    row = conversations_reader.read_one(
        "SELECT MAX(timestamp) AS last_ts FROM messages "
        "WHERE role='nex' AND content LIKE ? AND content LIKE ?",
        ("%focus%", f"%{problem_id}%"),
    )
    if not row or not row["last_ts"]:
        return 1e12
    return time.time() - row["last_ts"]


def _global_ping_age(conversations_reader: Reader) -> float:
    """Age (seconds) of the most recent focus-ping for ANY problem."""
    row = conversations_reader.read_one(
        "SELECT MAX(timestamp) AS last_ts FROM messages "
        "WHERE role='nex' AND content LIKE ?",
        ("I keep returning to my current focus%",),
    )
    if not row or not row["last_ts"]:
        return 1e12
    return time.time() - row["last_ts"]


def _surface_to_chat(
    conversations_writer: Writer, problem_id: int, title: str
) -> None:
    """Atomically write the focus ping and stuck transition via one Writer."""
    message = (
        f"I keep returning to my current focus and arriving at the same place. "
        f"The problem is: \"{title}\" (#{problem_id}). "
        f"Can you help me think about it?"
    )
    conversations_writer.write_many([
        (
            "INSERT INTO sessions (id, started_at, admin, user_label) "
            "VALUES (?, ?, 0, ?) ON CONFLICT(id) DO NOTHING",
            (INTERNAL_SESSION_ID, int(time.time()), "focus_loop"),
        ),
        (
            "INSERT INTO messages "
            "(session_id, role, content, register, timestamp) "
            "VALUES (?, 'nex', ?, 'Internal', ?)",
            (INTERNAL_SESSION_ID, message, int(time.time())),
        ),
        (
            "UPDATE open_problems SET state='stuck' WHERE id=?",
            (problem_id,),
        ),
    ])
    log.info("focus_loop: surfaced ping for problem %s (%s)", problem_id, title[:60])


def focus_tick(state=None) -> dict:
    """One focus cycle using the canonical per-database Readers and Writers.

    The normal Stage-2 loop injects its shared handles through state. A
    standalone invocation remains available for tests/tools and creates
    short-lived Readers/Writers which it owns and closes.
    """
    owned_writers: list[Writer] = []
    if state is None:
        beliefs_reader = Reader(BELIEFS_DB)
        conversations_reader = Reader(CONVERSATIONS_DB)
        dynamic_reader = Reader(DYNAMIC_DB)
        conversations_writer = Writer(
            CONVERSATIONS_DB, name="focus_loop.conversations"
        )
        dynamic_writer = Writer(DYNAMIC_DB, name="focus_loop.dynamic")
        owned_writers.extend([conversations_writer, dynamic_writer])
    else:
        beliefs_reader = state.readers["beliefs"]
        conversations_reader = state.readers["conversations"]
        dynamic_reader = state.readers["dynamic"]
        conversations_writer = state.writers["conversations"]
        dynamic_writer = state.writers["dynamic"]

    try:
        pick = _pick_focus(beliefs_reader, conversations_reader)
        if not pick:
            return {"focus": None, "obs_added": 0, "stuck": False}
        problem_id, title, connection_count = pick

        row = conversations_reader.read_one(
            "SELECT observations FROM open_problems WHERE id=?", (problem_id,)
        )
        try:
            observation_count = len(
                json.loads(row["observations"]) if row and row["observations"] else []
            )
        except Exception:
            observation_count = 0
        _update_current_focus(dynamic_writer, problem_id, observation_count)

        thought = _latest_fountain_thought(dynamic_reader)
        observation_added = 0
        if thought and len(thought.strip()) >= 300 and _related_to_focus(thought, title):
            new_count = _append_observation(
                conversations_reader, conversations_writer, problem_id, thought
            )
            if new_count != observation_count:
                observation_added = 1
                log.debug(
                    "focus_loop: appended obs to #%s (now %s)",
                    problem_id, new_count,
                )

        stuck = False
        if _check_stuck(conversations_reader, problem_id):
            import os as _os
            global_cooldown = float(_os.environ.get(
                "NEX5_FOCUS_PING_GLOBAL_COOLDOWN",
                GLOBAL_PING_COOLDOWN_SECONDS,
            ))
            if (
                _last_ping_age(conversations_reader, problem_id) > PING_COOLDOWN_SECONDS
                and _global_ping_age(conversations_reader) > global_cooldown
            ):
                _surface_to_chat(conversations_writer, problem_id, title)
                stuck = True
            elif _last_ping_age(conversations_reader, problem_id) > PING_COOLDOWN_SECONDS:
                conversations_writer.write(
                    "UPDATE open_problems SET state='stuck' WHERE id=?",
                    (problem_id,),
                )
                log.info(
                    "focus_loop: problem %s stuck but global ping cooldown "
                    "active (%.0fs since last); silenced",
                    problem_id, _global_ping_age(conversations_reader),
                )

        return {
            "focus": problem_id,
            "title": title[:60],
            "connections": connection_count,
            "obs_added": observation_added,
            "stuck": stuck,
        }
    finally:
        for writer in owned_writers:
            writer.close()


def focus_loop(state, stop: threading.Event) -> None:
    log.info("focus_loop started (tick=%ds, stuck_after=%d obs)",
             TICK_SECONDS, STUCK_WINDOW)
    while not stop.is_set():
        try:
            stats = focus_tick(state)
            if stats.get("focus"):
                log.debug("focus_loop: %s", stats)
            if stats.get("stuck"):
                log.info("focus_loop: STUCK on \"%s\" - pinged jon",
                         stats.get("title"))
        except Exception as e:
            log.error("focus_loop tick failed: %s: %s",
                      type(e).__name__, str(e)[:200])
        stop.wait(TICK_SECONDS)
    log.info("focus_loop stopped")
