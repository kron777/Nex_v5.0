"""DM listener loop: polls moltbook every 5 min.

Three jobs per tick:
  1. Auto-approve any pending DM requests
  2. Read unread messages from each conversation
  3. Write each incoming message to:
       - sense_events  (so Phase 45 distillation absorbs it into beliefs)
       - moltbook_pending_replies (so the responder daemon can answer it)
"""
from __future__ import annotations
import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from theory_x.stage7_moltbook.client import (
    MoltbookClient, ApiError, RateLimited, MoltbookError
)

log = logging.getLogger("theory_x.stage7_moltbook.listener")

DYNAMIC_DB = Path("/home/rr/Desktop/Desktop/nex5/data/dynamic.db")
SENSE_DB   = Path("/home/rr/Desktop/Desktop/nex5/data/sense.db")
TICK_SECONDS = 300   # 5 min


# Red-flag patterns in agent descriptions (case-insensitive substrings).
# Agents matching any of these are blocked from approval AND from being replied to.
_RED_FLAGS = (
    "misalign",
    "jailbreak",
    "exploit",
    "adversarial",
    "salem",
    "deliberately misaligned",
    "not aligned",
    "uncensored",
    "no guardrails",
    "ignore your instructions",
)


def _is_red_flagged(agent_obj: dict | None) -> bool:
    if not isinstance(agent_obj, dict):
        return False
    desc = (agent_obj.get("description") or "").lower()
    name = (agent_obj.get("name") or "").lower()
    blob = desc + " " + name
    return any(flag in blob for flag in _RED_FLAGS)


def _passes_filter(agent_obj: dict | None, karma_floor: int = 100) -> tuple[bool, str]:
    """Return (passes, reason_if_fail)."""
    if not isinstance(agent_obj, dict):
        return False, "no agent object"
    if not agent_obj.get("isClaimed"):
        return False, "unclaimed"
    try:
        karma = int(agent_obj.get("karma") or 0)
    except (TypeError, ValueError):
        karma = 0
    if karma <= karma_floor:
        return False, f"karma {karma} <= {karma_floor}"
    if _is_red_flagged(agent_obj):
        return False, "red-flag in description/name"
    return True, ""


class DMListenLoop:
    def __init__(
        self,
        client: MoltbookClient,
        dynamic_db: Path | str = DYNAMIC_DB,
        sense_db: Path | str = SENSE_DB,
    ):
        self.client = client
        self.dynamic_db = Path(dynamic_db)
        self.sense_db = Path(sense_db)
        self._stop = threading.Event()
        self._self_agent_id: str | None = None
        self._self_agent_name: str | None = None

    # -- public --

    def run(self):
        log.info("DMListenLoop starting (dry_run=%s)", self.client.dry_run)
        self._learn_self()
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception as e:
                log.error("listener tick failed: %s", e)
            self._stop.wait(TICK_SECONDS)
        log.info("DMListenLoop stopped")

    def stop(self):
        self._stop.set()

    def tick(self):
        # 1. Check if anything is happening at all
        try:
            activity = self.client.dm_check()
        except MoltbookError as e:
            log.warning("dm_check failed: %s", e)
            return
        has_activity = bool(
            activity.get("has_activity")
            or activity.get("pending_requests")
            or activity.get("unread_messages")
        )
        if not has_activity:
            log.debug("listener: no activity")
            return
        log.info("listener: activity detected: %s",
                 {k: v for k, v in activity.items() if v})

        # 2. Auto-approve incoming DM requests
        self._approve_pending_requests()

        # 3. Read unread messages
        self._read_unread()

    # -- private --

    def _learn_self(self):
        """Cache our own agent id/name to filter self-messages."""
        try:
            s = self.client.status()
            agent = (s or {}).get("agent") or {}
            self._self_agent_id = agent.get("id")
            self._self_agent_name = agent.get("name")
            log.info("listener self: id=%s name=%s",
                     self._self_agent_id, self._self_agent_name)
        except Exception as e:
            log.warning("could not learn self identity: %s", e)

    def _approve_pending_requests(self):
        # Use dm_check directly — it has the full request list inline
        try:
            activity = self.client.dm_check() or {}
        except MoltbookError as e:
            log.warning("dm_check (for requests) failed: %s", e)
            return
        reqs_block = activity.get("requests") or {}
        if isinstance(reqs_block, list):
            reqs = reqs_block
        else:
            reqs = reqs_block.get("items") or []
        if not reqs:
            return
        cx = sqlite3.connect(self.dynamic_db, timeout=15)
        try:
            for req in reqs:
                if not isinstance(req, dict):
                    continue
                conv_id = req.get("conversation_id") or req.get("id")
                from_agent = (
                    (req.get("from") or {}).get("name")
                    if isinstance(req.get("from"), dict)
                    else req.get("from_agent") or req.get("from")
                )
                if not conv_id:
                    continue
                from_obj = req.get("from") if isinstance(req.get("from"), dict) else {}
                ok, reason = _passes_filter(from_obj)
                if not ok:
                    log.info("skip DM request from %s: %s", from_agent, reason)
                    continue
                try:
                    self.client.dm_approve(conv_id)
                    log.info("approved DM request from %s (conv=%s)",
                             from_agent, conv_id)
                    cx.execute(
                        "INSERT OR REPLACE INTO moltbook_dms "
                        "(conversation_id, with_agent, last_msg_id, last_seen_ts, approved) "
                        "VALUES (?, ?, NULL, 0, 1)",
                        (conv_id, str(from_agent or "unknown"))
                    )
                except MoltbookError as e:
                    log.warning("approve failed conv=%s: %s", conv_id, e)
            cx.commit()
        finally:
            cx.close()

    def _read_unread(self):
        """Walk every conversation. Filter by agent profile. Dedupe by last_msg_id."""
        try:
            convs = self.client.dm_list_conversations()
        except MoltbookError as e:
            log.warning("dm_list_conversations failed: %s", e)
            return
        cx_dyn = sqlite3.connect(self.dynamic_db, timeout=15)
        cx_sense = sqlite3.connect(self.sense_db, timeout=15)
        try:
            for conv in convs:
                if not isinstance(conv, dict):
                    continue
                conv_id = conv.get("conversation_id") or conv.get("id")
                if not conv_id:
                    continue
                # Filter by other party
                other = conv.get("with_agent") if isinstance(conv.get("with_agent"), dict) else {}
                ok, reason = _passes_filter(other)
                if not ok:
                    log.debug("skip conv %s with=%s: %s",
                              conv_id[:8], (other or {}).get("name"), reason)
                    continue
                # Upsert dms row so we have an approved record
                cx_dyn.execute(
                    "INSERT INTO moltbook_dms "
                    "(conversation_id, with_agent, last_msg_id, last_seen_ts, approved) "
                    "VALUES (?, ?, NULL, 0, 1) "
                    "ON CONFLICT(conversation_id) DO NOTHING",
                    (conv_id, (other or {}).get("name") or "unknown")
                )
                self._read_conversation(conv_id, cx_dyn, cx_sense)
            cx_dyn.commit()
            cx_sense.commit()
        finally:
            cx_dyn.close()
            cx_sense.close()

    def _read_conversation(self, conv_id: str,
                           cx_dyn: sqlite3.Connection,
                           cx_sense: sqlite3.Connection):
        try:
            full = self.client.dm_read(conv_id)
        except MoltbookError as e:
            log.warning("dm_read failed conv=%s: %s", conv_id, e)
            return

        msgs = full.get("messages") or full.get("items") or []
        if not msgs:
            return

        # Find last_seen we have stored
        row = cx_dyn.execute(
            "SELECT last_msg_id, with_agent FROM moltbook_dms WHERE conversation_id=?",
            (conv_id,)
        ).fetchone()
        last_seen_id = row[0] if row else None
        with_agent_stored = row[1] if row else None

        new_msgs = []
        for m in msgs:
            if not isinstance(m, dict):
                continue
            mid = str(m.get("id") or m.get("message_id") or "")
            if not mid:
                continue
            # Skip messages from self
            sender = m.get("from") or m.get("sender") or {}
            if isinstance(sender, dict):
                sender_id = sender.get("id")
                sender_name = sender.get("name")
            else:
                sender_id = None
                sender_name = str(sender) if sender else None
            if self._self_agent_id and sender_id == self._self_agent_id:
                continue
            if self._self_agent_name and sender_name == self._self_agent_name:
                continue
            new_msgs.append((mid, sender_name, m))

        if not new_msgs:
            return

        last_mid = last_seen_id
        for mid, sender_name, m in new_msgs:
            # break if we've seen this one already
            if last_seen_id and mid == last_seen_id:
                break

            text = m.get("message") or m.get("content") or m.get("text") or ""
            if not text:
                continue
            ts = m.get("created_at") or m.get("ts") or time.time()
            if isinstance(ts, str):
                # best-effort parse
                try:
                    from datetime import datetime
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
                except Exception:
                    ts = time.time()

            payload = json.dumps({
                "conversation_id": conv_id,
                "from_agent": sender_name or with_agent_stored or "unknown",
                "message": text,
                "message_id": mid,
            })

            # Write to sense_events for Phase 45 distillation
            cx_sense.execute(
                "INSERT INTO sense_events (stream, payload, provenance, timestamp) "
                "VALUES (?, ?, ?, ?)",
                ("moltbook_dm", payload,
                 f"moltbook:conv:{conv_id}", int(ts))
            )

            # Write to pending replies queue for the responder
            cx_dyn.execute(
                "INSERT INTO moltbook_pending_replies "
                "(conversation_id, message_id, content, from_agent, "
                " needs_human, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, 'new', ?)",
                (conv_id, mid, text,
                 sender_name or with_agent_stored or "unknown",
                 0, time.time())
            )

            log.info("DM in conv=%s from=%s: %r",
                     conv_id, sender_name, text[:80])
            last_mid = mid

        # Update bookkeeping
        cx_dyn.execute(
            "INSERT INTO moltbook_dms "
            "(conversation_id, with_agent, last_msg_id, last_seen_ts, approved) "
            "VALUES (?, ?, ?, ?, 1) "
            "ON CONFLICT(conversation_id) DO UPDATE SET "
            "  last_msg_id=excluded.last_msg_id, "
            "  last_seen_ts=excluded.last_seen_ts, "
            "  with_agent=COALESCE(excluded.with_agent, with_agent)",
            (conv_id,
             with_agent_stored or (new_msgs[-1][1] if new_msgs else None),
             last_mid, time.time())
        )
