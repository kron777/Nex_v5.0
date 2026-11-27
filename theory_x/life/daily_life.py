"""Daily life daemon — gives her a day-shape, not just continuous fire.

Activities scheduled by NEX's local time (nex_config.local_tz, NEX5_TZ):

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
from substrate import Reader, Writer
import threading
import time
from datetime import datetime
from pathlib import Path

log = logging.getLogger("theory_x.life.daily_life")

from substrate.paths import DbPath  # resolves NEX5_DATA_DIR at use time (test hygiene)
from nex_config import local_tz
DYNAMIC_DB = DbPath("dynamic")
CONVERSATIONS_DB = DbPath("conversations")
BELIEFS_DB = DbPath("beliefs")
SENSE_DB = DbPath("sense")

TICK_SECONDS = 60
SESSION_ID = "internal_daily_life"

# Schedule: hour (0-23) -> activity name
SCHEDULE = {
    3:  "source_audit",     # housekeeping, not an activity of hers: provenance audit
    4:  "expectation_canaries",   # housekeeping: build B canaries
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
    return datetime.now(local_tz())


def _date_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _is_sleep_hour(hour: int) -> bool:
    return hour >= SLEEP_START_HOUR or hour < SLEEP_END_HOUR


def _already_fired(reader: Reader, activity: str, date_local: str) -> bool:
    row = reader.read_one(
        "SELECT 1 FROM daily_activities WHERE activity=? AND date_local=?",
        (activity, date_local),
    )
    return row is not None


def _record_fired(writer: Writer, activity: str, date_local: str, details: str = "") -> None:
    writer.write(
        "INSERT OR IGNORE INTO daily_activities "
        "(activity, date_local, fired_at, details) VALUES (?, ?, ?, ?)",
        (activity, date_local, time.time(), details),
    )


def _write_chat(content: str, register: str = "Daily", writer: Writer | None = None) -> None:
    own_writer = writer is None
    cv_writer = writer or Writer(CONVERSATIONS_DB, name="daily_life")
    try:
        now = int(time.time())
        cv_writer.write_many([
            (
                "INSERT INTO sessions (id, started_at, admin, user_label) "
                "VALUES (?, ?, 0, ?) ON CONFLICT(id) DO NOTHING",
                (SESSION_ID, now, "daily_life"),
            ),
            (
                "INSERT INTO messages (session_id, role, content, register, timestamp) "
                "VALUES (?, 'nex', ?, ?, ?)",
                (SESSION_ID, content, register, now),
            ),
        ])
    finally:
        if own_writer:
            cv_writer.close()


def _state_snapshot(readers: dict | None = None) -> dict:
    """Read-only snapshot of how she is right now."""
    readers = readers or {
        "dynamic": Reader(DYNAMIC_DB),
        "beliefs": Reader(BELIEFS_DB),
        "conversations": Reader(CONVERSATIONS_DB),
        "sense": Reader(SENSE_DB),
    }
    out = {}
    try:
        row = readers["beliefs"].read_one(
            "SELECT COUNT(*) FROM beliefs WHERE created_at > ?",
            (time.time() - 86400,),
        )
        out["new_beliefs_24h"] = row[0] if row else 0
    except Exception:
        out["new_beliefs_24h"] = "?"

    try:
        row = readers["conversations"].read_one(
            "SELECT COUNT(*) FROM open_problems WHERE state='open'"
        )
        out["open_problems"] = row[0] if row else 0
        row = readers["conversations"].read_one(
            "SELECT title FROM open_problems WHERE state='open' "
            "ORDER BY last_touched_at DESC LIMIT 1"
        )
        out["latest_problem"] = row[0] if row else None
    except Exception:
        out["open_problems"] = "?"

    try:
        has_moltbook = readers["dynamic"].read_one(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='moltbook_posts'"
        )
        if has_moltbook:
            row = readers["dynamic"].read_one(
                "SELECT COUNT(*) FROM moltbook_posts "
                "WHERE status='posted' AND ts > ?",
                (time.time() - 86400,),
            )
        else:
            row = (0,)
        out["moltbook_posts_24h"] = row[0] if row else 0

        row = readers["dynamic"].read_one(
            "SELECT problem_id FROM current_focus WHERE id=1"
        )
        out["focus_problem_id"] = row[0] if row else None

        row = readers["dynamic"].read_one(
            "SELECT COUNT(*) FROM fountain_events "
            "WHERE thought != '' AND ts > ?",
            (time.time() - 86400,),
        )
        out["fountain_fires_24h"] = row[0] if row else 0
    except Exception:
        out["moltbook_posts_24h"] = "?"
        out["fountain_fires_24h"] = "?"
    return out


def _activity_morning(
    date_local: str, *, readers: dict | None = None, writers: dict | None = None
) -> str:
    now = _now_local()
    state = _state_snapshot(readers)
    msg = (
        f"good morning. it is {now.strftime('%A %d %B %Y, %H:%M')}.\n\n"
        f"yesterday: {state.get('new_beliefs_24h', '?')} new beliefs, "
        f"{state.get('fountain_fires_24h', '?')} fountain fires, "
        f"{state.get('moltbook_posts_24h', '?')} posts to moltbook.\n"
        f"{state.get('open_problems', '?')} open problems still in front of me. "
    )
    if state.get("latest_problem"):
        msg += f"latest: \"{state['latest_problem']}\""
    _write_chat(msg, "Morning", writers["conversations"] if writers else None)
    return msg[:200]


def _activity_reading(
    slot: str, date_local: str, *, readers: dict | None = None, writers: dict | None = None
) -> str:
    """Pick one recent feed item. Surface it for engagement."""
    sense_reader = readers["sense"] if readers else Reader(SENSE_DB)
    try:
        row = sense_reader.read_one(
            "SELECT stream, payload FROM sense_events "
            "WHERE stream NOT LIKE 'internal.%' "
            "  AND timestamp > ? "
            "ORDER BY RANDOM() LIMIT 1",
            (time.time() - 7200,),
        )
    except Exception as e:
        log.warning("reading session: sense read failed: %s", e)
        row = None
    if not row:
        msg = f"reading session {slot}: nothing fresh in the feeds. resting instead."
        _write_chat(msg, "Reading", writers["conversations"] if writers else None)
        return msg
    stream, payload = row
    snippet = (payload or "")[:200]
    msg = (
        f"reading session {slot}. picking this from {stream}:\n\n"
        f"  {snippet}\n\n"
        f"sitting with it. what does it actually say? what is it close to that i already hold?"
    )
    _write_chat(msg, "Reading", writers["conversations"] if writers else None)
    return f"read from {stream}"


def _activity_outreach(
    slot: str, date_local: str, *, readers: dict | None = None, writers: dict | None = None
) -> str:
    """Pick one approved moltbook conv with no messages from her, send opener."""
    try:
        from theory_x.stage7_moltbook.client import MoltbookClient
        client = MoltbookClient()
    except Exception as e:
        msg = f"outreach {slot}: moltbook unreachable ({type(e).__name__}). skipping."
        _write_chat(msg, "Outreach", writers["conversations"] if writers else None)
        return msg
    dynamic_reader = readers["dynamic"] if readers else Reader(DYNAMIC_DB)
    try:
        has_table = dynamic_reader.read_one(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='moltbook_dms'"
        )
        rows = dynamic_reader.read(
            "SELECT conversation_id, with_agent FROM moltbook_dms "
            "WHERE approved=1 LIMIT 8"
        ) if has_table else []
    except Exception as e:
        msg = f"outreach {slot}: db error ({e})"
        _write_chat(msg, "Outreach", writers["conversations"] if writers else None)
        return msg
    if not rows:
        msg = f"outreach {slot}: no approved convs."
        _write_chat(msg, "Outreach", writers["conversations"] if writers else None)
        return msg
    # surface the intent — actual send wired separately, for now we record it
    cid, name = rows[0]
    msg = (
        f"outreach {slot}. would reach out to {name} (conv {cid[:8]}) — "
        f"but holding off until i have something real to say."
    )
    _write_chat(msg, "Outreach", writers["conversations"] if writers else None)
    return msg[:200]


def _activity_journal(
    date_local: str, *, readers: dict | None = None, writers: dict | None = None
) -> str:
    now = _now_local()
    state = _state_snapshot(readers)
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
    _write_chat(msg, "Journal", writers["conversations"] if writers else None)
    return msg[:200]


def _activity_source_audit(
    date_local: str, *, readers: dict | None = None, writers: dict | None = None
) -> str:
    from theory_x.stage_tom.source_kind_audit import run_and_record
    return run_and_record(dynamic_writer=writers["dynamic"] if writers else None)


def _activity_expectation_canaries(
    date_local: str, *, readers: dict | None = None, writers: dict | None = None
) -> str:
    from theory_x.stage_world.expectations import record_canaries
    from theory_x.stage_world import learning_guards
    learning_guards.run()          # G2 action tier + attribution rule (each flag-gated)
    return record_canaries(conversations_writer=writers["conversations"] if writers else None)


_ACTIVITY_FUNCS = {
    "morning": lambda day, readers=None, writers=None: _activity_morning(day, readers=readers, writers=writers),
    "reading_1": lambda day, readers=None, writers=None: _activity_reading("1", day, readers=readers, writers=writers),
    "reading_2": lambda day, readers=None, writers=None: _activity_reading("2", day, readers=readers, writers=writers),
    "outreach_1": lambda day, readers=None, writers=None: _activity_outreach("1", day, readers=readers, writers=writers),
    "outreach_2": lambda day, readers=None, writers=None: _activity_outreach("2", day, readers=readers, writers=writers),
    "journal": lambda day, readers=None, writers=None: _activity_journal(day, readers=readers, writers=writers),
    "source_audit": lambda day, readers=None, writers=None: _activity_source_audit(day, readers=readers, writers=writers),
    "expectation_canaries": lambda day, readers=None, writers=None: _activity_expectation_canaries(day, readers=readers, writers=writers),
}


def daily_tick(
    *,
    dynamic_reader: Reader | None = None,
    dynamic_writer: Writer | None = None,
    beliefs_reader: Reader | None = None,
    conversations_reader: Reader | None = None,
    conversations_writer: Writer | None = None,
    sense_reader: Reader | None = None,
) -> dict:
    now = _now_local()
    hour = now.hour
    date_local = _date_str(now)

    readers = {
        "dynamic": dynamic_reader or Reader(DYNAMIC_DB),
        "beliefs": beliefs_reader or Reader(BELIEFS_DB),
        "conversations": conversations_reader or Reader(CONVERSATIONS_DB),
        "sense": sense_reader or Reader(SENSE_DB),
    }
    own_dynamic_writer = dynamic_writer is None
    d_writer = dynamic_writer or Writer(DYNAMIC_DB, name="daily_life")
    own_conversations_writer = conversations_writer is None
    c_writer = conversations_writer or Writer(CONVERSATIONS_DB, name="daily_life")
    writers = {"dynamic": d_writer, "conversations": c_writer}
    try:
        fired = []
        for sched_hour, activity in SCHEDULE.items():
            if hour < sched_hour:
                continue
            if _already_fired(readers["dynamic"], activity, date_local):
                continue
            try:
                activity_fn = _ACTIVITY_FUNCS[activity]
                try:
                    import inspect
                    params = inspect.signature(activity_fn).parameters
                except (TypeError, ValueError):
                    params = {}
                if "readers" in params:
                    details = activity_fn(date_local, readers=readers, writers=writers)
                else:
                    details = activity_fn(date_local)
                _record_fired(d_writer, activity, date_local, details)
                fired.append(activity)
                log.info("daily_life: fired %s — %s", activity, details[:80])
            except Exception as e:
                log.error("daily_life: activity %s failed: %s", activity, e)
        return {"fired": fired, "hour": hour, "sleep": _is_sleep_hour(hour)}
    finally:
        if own_dynamic_writer:
            d_writer.close()
        if own_conversations_writer:
            c_writer.close()


def daily_loop(state, stop: threading.Event) -> None:
    log.info("daily_loop started (tz=%s, %d activities)",
             local_tz().key, len(SCHEDULE))
    while not stop.is_set():
        try:
            stats = daily_tick(
                dynamic_reader=state.readers["dynamic"],
                dynamic_writer=state.writers["dynamic"],
                beliefs_reader=state.readers["beliefs"],
                conversations_reader=state.readers["conversations"],
                conversations_writer=state.writers["conversations"],
                sense_reader=state.readers["sense"],
            )
            if stats["fired"]:
                log.info("daily_loop: %s", stats)
        except Exception as e:
            log.error("daily_loop tick failed: %s: %s",
                      type(e).__name__, str(e)[:200])
        stop.wait(TICK_SECONDS)
    log.info("daily_loop stopped")
