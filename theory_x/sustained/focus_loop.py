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
import sqlite3
import threading
import time
from pathlib import Path

log = logging.getLogger("theory_x.sustained.focus_loop")

BELIEFS_DB = Path("/home/rr/Desktop/nex5/data/beliefs.db")
CONVERSATIONS_DB = Path("/home/rr/Desktop/nex5/data/conversations.db")
DYNAMIC_DB = Path("/home/rr/Desktop/nex5/data/dynamic.db")

TICK_SECONDS = 60
MAX_OBSERVATIONS = 50
STUCK_SIMILARITY = 0.85
STUCK_WINDOW = 3
PING_COOLDOWN_SECONDS = 1800  # don't re-ping the same problem within 30 min
INTERNAL_SESSION_ID = "internal_focus_loop"

_STOPWORDS = {
    "a", "an", "the", "is", "are", "what", "how", "why", "this", "that",
    "of", "in", "on", "to", "for", "with", "from", "signal", "investigate",
    "across", "these", "domains",
}


def _title_keywords(title: str) -> set[str]:
    tokens = (w.strip("\'\".,?!:;()") for w in title.lower().split())
    return {w for w in tokens if w not in _STOPWORDS and len(w) > 2}


def _pick_focus(b_cx, cv_cx) -> tuple[int, str, int] | None:
    """Return (problem_id, title, connection_count) for the most-connected open problem."""
    problems = cv_cx.execute(
        "SELECT id, title FROM open_problems WHERE state='open'"
    ).fetchall()
    if not problems:
        return None
    best = None
    for pid, title in problems:
        kws = _title_keywords(title or "")
        if not kws:
            continue
        # Count beliefs whose content contains any of the title keywords
        where = " OR ".join("content LIKE ?" for _ in kws)
        params = tuple(f"%{kw}%" for kw in kws)
        row = b_cx.execute(
            f"SELECT COUNT(*) FROM beliefs WHERE ({where})", params
        ).fetchone()
        n = row[0] if row else 0
        if best is None or n > best[2]:
            best = (pid, title, n)
    return best


def _update_current_focus(d_cx, problem_id: int, observations_count: int) -> None:
    d_cx.execute(
        "INSERT INTO current_focus (id, problem_id, picked_at, observations_at_pick) "
        "VALUES (1, ?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET problem_id=excluded.problem_id, "
        "picked_at=excluded.picked_at, observations_at_pick=excluded.observations_at_pick "
        "WHERE current_focus.problem_id != excluded.problem_id",
        (problem_id, time.time(), observations_count)
    )
    d_cx.commit()


def _latest_fountain_thought(d_cx) -> str | None:
    row = d_cx.execute(
        "SELECT thought FROM fountain_events WHERE thought != '' "
        "AND ts > (strftime(\'%s\',\'now\') - 600) "
        "ORDER BY ts DESC LIMIT 1"
    ).fetchone()
    if not row or not row[0]:
        return None
    return row[0]


def _related_to_focus(thought: str, focus_title: str) -> bool:
    """Cheap match: any title keyword appears in the thought."""
    kws = _title_keywords(focus_title)
    if not kws:
        return False
    t = thought.lower()
    return any(kw in t for kw in kws)


def _append_observation(cv_cx, problem_id: int, observation: str) -> int:
    """Append observation; return new count."""
    row = cv_cx.execute(
        "SELECT observations FROM open_problems WHERE id=?", (problem_id,)
    ).fetchone()
    if not row:
        return 0
    try:
        obs = json.loads(row[0]) if row[0] else []
    except Exception:
        obs = []
    obs.append({"text": observation, "ts": time.time()})
    if len(obs) > MAX_OBSERVATIONS:
        obs = obs[-MAX_OBSERVATIONS:]
    cv_cx.execute(
        "UPDATE open_problems SET observations=?, last_touched_at=? WHERE id=?",
        (json.dumps(obs), time.time(), problem_id)
    )
    cv_cx.commit()
    return len(obs)


def _check_stuck(cv_cx, problem_id: int) -> bool:
    """Stuck if last STUCK_WINDOW observations are pairwise too similar."""
    row = cv_cx.execute(
        "SELECT observations, state FROM open_problems WHERE id=?", (problem_id,)
    ).fetchone()
    if not row:
        return False
    if row[1] == "stuck":
        return False  # already marked
    try:
        obs = json.loads(row[0]) if row[0] else []
    except Exception:
        return False
    if len(obs) < STUCK_WINDOW:
        return False
    recent = [o["text"] for o in obs[-STUCK_WINDOW:]]
    try:
        from theory_x.diversity.embeddings import embed, cosine
        vecs = [embed(t) for t in recent]
        for i in range(len(vecs)):
            for j in range(i + 1, len(vecs)):
                if cosine(vecs[i], vecs[j]) < STUCK_SIMILARITY:
                    return False
        return True
    except Exception as e:
        log.warning("stuck check failed: %s", e)
        return False


def _last_ping_age(cv_cx, problem_id: int) -> float:
    row = cv_cx.execute(
        "SELECT MAX(timestamp) FROM messages "
        "WHERE role='nex' AND content LIKE ? AND content LIKE ?",
        ("%focus%", f"%{problem_id}%")
    ).fetchone()
    if not row or not row[0]:
        return 1e12
    return time.time() - row[0]


def _surface_to_chat(cv_cx, problem_id: int, title: str) -> None:
    """Write a ping message visible in the GUI chat pane."""
    msg = (
        f"I keep returning to my current focus and arriving at the same place. "
        f"The problem is: \"{title}\" (#{problem_id}). "
        f"Can you help me think about it?"
    )
    cv_cx.execute(
        "INSERT INTO sessions (id, started_at, admin, user_label) VALUES (?, ?, 0, ?) "
        "ON CONFLICT(id) DO NOTHING",
        (INTERNAL_SESSION_ID, int(time.time()), "focus_loop")
    )
    cv_cx.execute(
        "INSERT INTO messages (session_id, role, content, register, timestamp) "
        "VALUES (?, 'nex', ?, 'Internal', ?)",
        (INTERNAL_SESSION_ID, msg, int(time.time()))
    )
    cv_cx.execute(
        "UPDATE open_problems SET state='stuck' WHERE id=?",
        (problem_id,)
    )
    cv_cx.commit()
    log.info("focus_loop: surfaced ping for problem %s (%s)", problem_id, title[:60])


def focus_tick() -> dict:
    b_cx = sqlite3.connect(BELIEFS_DB, timeout=15)
    cv_cx = sqlite3.connect(CONVERSATIONS_DB, timeout=15)
    d_cx = sqlite3.connect(DYNAMIC_DB, timeout=15)
    try:
        pick = _pick_focus(b_cx, cv_cx)
        if not pick:
            return {"focus": None, "obs_added": 0, "stuck": False}
        problem_id, title, n_conn = pick

        # Get current observation count
        row = cv_cx.execute(
            "SELECT observations FROM open_problems WHERE id=?", (problem_id,)
        ).fetchone()
        try:
            obs_count = len(json.loads(row[0]) if row and row[0] else [])
        except Exception:
            obs_count = 0
        _update_current_focus(d_cx, problem_id, obs_count)

        # Append an observation if her latest fountain thought relates
        thought = _latest_fountain_thought(d_cx)
        obs_added = 0
        if thought and _related_to_focus(thought, title):
            new_count = _append_observation(cv_cx, problem_id, thought)
            obs_added = 1
            log.debug("focus_loop: appended obs to #%s (now %s)",
                      problem_id, new_count)

        # Stuck check
        stuck = False
        if _check_stuck(cv_cx, problem_id):
            if _last_ping_age(cv_cx, problem_id) > PING_COOLDOWN_SECONDS:
                _surface_to_chat(cv_cx, problem_id, title)
                stuck = True

        return {
            "focus": problem_id, "title": title[:60],
            "connections": n_conn, "obs_added": obs_added, "stuck": stuck
        }
    finally:
        b_cx.close()
        cv_cx.close()
        d_cx.close()


def focus_loop(state, stop: threading.Event) -> None:
    log.info("focus_loop started (tick=%ds, stuck_after=%d obs)",
             TICK_SECONDS, STUCK_WINDOW)
    while not stop.is_set():
        try:
            stats = focus_tick()
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
