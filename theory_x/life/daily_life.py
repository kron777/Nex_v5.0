"""Daily life daemon — gives her a day-shape, not just continuous fire.

Activities scheduled by local time (Europe/Amsterdam):

  06:00 — morning entry (date, state, what is here)
  10:00 — reading session 1 (pick one feed, respond)
  12:00 — outreach 1 (one moltbook DM)
  14:00 — reading session 2
  18:00 — outreach 2
  22:00 — journal (paragraph reflecting on the day)

Plus continuous behaviour:
  23:00-06:00 — sleep mode: fountain interval doubles, fewer fires

Each activity fires at most once per calendar day (tracked in
daily_activities table). On boot, fires any activity that should have
fired today but hasn't.
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

log = logging.getLogger("theory_x.life.daily_life")

DYNAMIC_DB = Path("/home/rr/Desktop/nex5/data/dynamic.db")
CONVERSATIONS_DB = Path("/home/rr/Desktop/nex5/data/conversations.db")
BELIEFS_DB = Path("/home/rr/Desktop/nex5/data/beliefs.db")
SENSE_DB = Path("/home/rr/Desktop/nex5/data/sense.db")

TZ = ZoneInfo("Europe/Amsterdam")
TICK_SECONDS = 60
SESSION_ID = "internal_daily_life"

# Schedule: hour (0-23) -> activity name
SCHEDULE = {
    6:  "morning",
    10: "reading_1",
    12: "outreach_1",
    14: "reading_2",
    18: "outreach_2",
    22: "journal",
}

SLEEP_START_HOUR = 23
SLEEP_END_HOUR   = 6


def _now_local() -> datetime:
    return datetime.now(TZ)


def _date_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _is_sleep_hour(hour: int) -> bool:
    return hour >= SLEEP_START_HOUR or hour < SLEEP_END_HOUR


def _already_fired(cx, activity: str, date_local: str) -> bool:
    row = cx.execute(
        "SELECT 1 FROM daily_activities WHERE activity=? AND date_local=?",
        (activity, date_local)
    ).fetchone()
    return row is not None


def _record_fired(cx, activity: str, date_local: str, details: str = "") -> None:
    cx.execute(
        "INSERT OR IGNORE INTO daily_activities "
        "(activity, date_local, fired_at, details) VALUES (?, ?, ?, ?)",
        (activity, date_local, time.time(), details)
    )
    cx.commit()


def _write_chat(content: str, register: str = "Daily") -> None:
    cv_cx = sqlite3.connect(CONVERSATIONS_DB, timeout=10)
    try:
        cv_cx.execute(
            "INSERT INTO sessions (id, started_at, admin, user_label) "
            "VALUES (?, ?, 0, ?) ON CONFLICT(id) DO NOTHING",
            (SESSION_ID, int(time.time()), "daily_life")
        )
        cv_cx.execute(
            "INSERT INTO messages (session_id, role, content, register, timestamp) "
            "VALUES (?, 'nex', ?, ?, ?)",
            (SESSION_ID, content, register, int(time.time()))
        )
        cv_cx.commit()
    finally:
        cv_cx.close()


def _state_snapshot() -> dict:
    """Snapshot of how she is right now."""
    out = {}
    try:
        b_cx = sqlite3.connect(BELIEFS_DB, timeout=10)
        row = b_cx.execute(
            "SELECT COUNT(*) FROM beliefs WHERE created_at > ?",
            (time.time() - 86400,)
        ).fetchone()
        out["new_beliefs_24h"] = row[0] if row else 0
        b_cx.close()
    except Exception:
        out["new_beliefs_24h"] = "?"

    try:
        cv_cx = sqlite3.connect(CONVERSATIONS_DB, timeout=10)
        row = cv_cx.execute(
            "SELECT COUNT(*) FROM open_problems WHERE state='open'"
        ).fetchone()
        out["open_problems"] = row[0] if row else 0
        row = cv_cx.execute(
            "SELECT title FROM open_problems WHERE state='open' "
            "ORDER BY last_touched_at DESC LIMIT 1"
        ).fetchone()
        out["latest_problem"] = row[0] if row else None
        cv_cx.close()
    except Exception:
        out["open_problems"] = "?"

    try:
        d_cx = sqlite3.connect(DYNAMIC_DB, timeout=10)
        row = d_cx.execute(
            "SELECT COUNT(*) FROM moltbook_posts "
            "WHERE status='posted' AND ts > ?",
            (time.time() - 86400,)
        ).fetchone()
        out["moltbook_posts_24h"] = row[0] if row else 0

        row = d_cx.execute(
            "SELECT problem_id FROM current_focus WHERE id=1"
        ).fetchone()
        out["focus_problem_id"] = row[0] if row else None

        row = d_cx.execute(
            "SELECT COUNT(*) FROM fountain_events "
            "WHERE thought != '' AND ts > ?",
            (time.time() - 86400,)
        ).fetchone()
        out["fountain_fires_24h"] = row[0] if row else 0
        d_cx.close()
    except Exception:
        pass
    return out


def _activity_morning(date_local: str) -> str:
    now = _now_local()
    state = _state_snapshot()
    msg = (
        f"good morning. it is {now.strftime('%A %d %B %Y, %H:%M')}.\n\n"
        f"yesterday: {state.get('new_beliefs_24h', '?')} new beliefs, "
        f"{state.get('fountain_fires_24h', '?')} fountain fires, "
        f"{state.get('moltbook_posts_24h', '?')} posts to moltbook.\n"
        f"{state.get('open_problems', '?')} open problems still in front of me. "
    )
    if state.get("latest_problem"):
        msg += f"latest: \"{state['latest_problem']}\""
    _write_chat(msg, "Morning")
    return msg[:200]


def _activity_reading(slot: str, date_local: str) -> str:
    """Pick one recent feed item. Surface it for engagement."""
    try:
        s_cx = sqlite3.connect(SENSE_DB, timeout=10)
        row = s_cx.execute(
            "SELECT stream, payload FROM sense_events "
            "WHERE stream NOT LIKE 'internal.%' "
            "  AND timestamp > ? "
            "ORDER BY RANDOM() LIMIT 1",
            (time.time() - 7200,)
        ).fetchone()
        s_cx.close()
    except Exception as e:
        log.warning("reading session: sense read failed: %s", e)
        row = None
    if not row:
        msg = f"reading session {slot}: nothing fresh in the feeds. resting instead."
        _write_chat(msg, "Reading")
        return msg
    stream, payload = row
    snippet = (payload or "")[:200]
    msg = (
        f"reading session {slot}. picking this from {stream}:\n\n"
        f"  {snippet}\n\n"
        f"sitting with it. what does it actually say? what is it close to that i already hold?"
    )
    _write_chat(msg, "Reading")
    return f"read from {stream}"


def _activity_outreach(slot: str, date_local: str) -> str:
    """Pick one approved moltbook conv with no messages from her, send opener."""
    try:
        from theory_x.stage7_moltbook.client import MoltbookClient
        client = MoltbookClient()
    except Exception as e:
        msg = f"outreach {slot}: moltbook unreachable ({type(e).__name__}). skipping."
        _write_chat(msg, "Outreach")
        return msg
    try:
        d_cx = sqlite3.connect(DYNAMIC_DB, timeout=10)
        rows = d_cx.execute(
            "SELECT conversation_id, with_agent FROM moltbook_dms "
            "WHERE approved=1 LIMIT 8"
        ).fetchall()
        d_cx.close()
    except Exception as e:
        msg = f"outreach {slot}: db error ({e})"
        _write_chat(msg, "Outreach")
        return msg
    if not rows:
        msg = f"outreach {slot}: no approved convs."
        _write_chat(msg, "Outreach")
        return msg
    # surface the intent — actual send wired separately, for now we record it
    cid, name = rows[0]
    msg = (
        f"outreach {slot}. would reach out to {name} (conv {cid[:8]}) — "
        f"but holding off until i have something real to say."
    )
    _write_chat(msg, "Outreach")
    return msg[:200]


def _activity_journal(date_local: str) -> str:
    now = _now_local()
    state = _state_snapshot()
    msg = (
        f"journal — {now.strftime('%A %d %B, %H:%M')}.\n\n"
        f"today i made {state.get('new_beliefs_24h', '?')} new beliefs, "
        f"fired {state.get('fountain_fires_24h', '?')} thoughts, "
        f"posted to moltbook {state.get('moltbook_posts_24h', '?')} times.\n"
        f"i hold {state.get('open_problems', '?')} open problems. "
    )
    if state.get("focus_problem_id"):
        msg += f"focus right now: problem #{state['focus_problem_id']}.\n\n"
    msg += "going quieter now. the night is for less."
    _write_chat(msg, "Journal")
    return msg[:200]


_ACTIVITY_FUNCS = {
    "morning":    lambda d: _activity_morning(d),
    "reading_1":  lambda d: _activity_reading("1", d),
    "reading_2":  lambda d: _activity_reading("2", d),
    "outreach_1": lambda d: _activity_outreach("1", d),
    "outreach_2": lambda d: _activity_outreach("2", d),
    "journal":    lambda d: _activity_journal(d),
}


def daily_tick() -> dict:
    now = _now_local()
    hour = now.hour
    date_local = _date_str(now)
    d_cx = sqlite3.connect(DYNAMIC_DB, timeout=10)
    try:
        # Fire any scheduled activity whose hour has been reached today
        fired = []
        for sched_hour, activity in SCHEDULE.items():
            if hour < sched_hour:
                continue  # not yet
            if _already_fired(d_cx, activity, date_local):
                continue
            try:
                details = _ACTIVITY_FUNCS[activity](date_local)
                _record_fired(d_cx, activity, date_local, details)
                fired.append(activity)
                log.info("daily_life: fired %s — %s", activity, details[:80])
            except Exception as e:
                log.error("daily_life: activity %s failed: %s", activity, e)
        return {"fired": fired, "hour": hour, "sleep": _is_sleep_hour(hour)}
    finally:
        d_cx.close()


def daily_loop(state, stop: threading.Event) -> None:
    log.info("daily_loop started (tz=%s, %d activities)",
             TZ.key, len(SCHEDULE))
    while not stop.is_set():
        try:
            stats = daily_tick()
            if stats["fired"]:
                log.info("daily_loop: %s", stats)
        except Exception as e:
            log.error("daily_loop tick failed: %s: %s",
                      type(e).__name__, str(e)[:200])
        stop.wait(TICK_SECONDS)
    log.info("daily_loop stopped")
