"""Poster loop: reads fountain_events, queues, posts to moltbook every 30 min.

Two daemons in one class:
  * enqueue_tick(): copies new fountain rows into moltbook_post_queue (skip stillness)
  * post_tick():    if 30 min since last post, pick best candidate, post it

Both safe to call repeatedly. Idempotent on thought_id.
"""
from __future__ import annotations
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from theory_x.stage7_moltbook.client import (
    MoltbookClient, ApiError, RateLimited, MoltbookError
)
from theory_x.stage7_moltbook.submolt_picker import (
    pick_submolt, load_available_submolts, FALLBACK
)

log = logging.getLogger("theory_x.stage7_moltbook.poster")

DYNAMIC_DB = Path("/home/rr/Desktop/nex5/data/dynamic.db")
TICK_SECONDS = 60                  # how often each loop wakes up
POST_INTERVAL_SECONDS = 30 * 60    # server cap: 1 post / 30 min
QUEUE_WINDOW_SECONDS = 30 * 60     # only consider thoughts queued within last 30 min
TITLE_MAX_CHARS = 200              # moltbook title limit (defensive)
CONTENT_MAX_CHARS = 4000           # post body limit (defensive)


class PostLoop:
    """Runs two ticks on a single thread. Owns a per-thread sqlite connection."""

    def __init__(
        self,
        client: MoltbookClient,
        db_path: Path | str = DYNAMIC_DB,
    ):
        self.client = client
        self.db_path = Path(db_path)
        self._stop = threading.Event()
        self._available_submolts: set[str] = set()
        self._submolts_loaded_at: float = 0.0

    # -- public --

    def run(self):
        log.info("PostLoop starting (dry_run=%s)", self.client.dry_run)
        self._refresh_submolts(force=True)
        while not self._stop.is_set():
            try:
                self.enqueue_tick()
            except Exception as e:
                log.error("enqueue_tick failed: %s", e)
            try:
                self.post_tick()
            except Exception as e:
                log.error("post_tick failed: %s", e)
            self._stop.wait(TICK_SECONDS)
        log.info("PostLoop stopped")

    def stop(self):
        self._stop.set()

    # -- enqueue --

    def enqueue_tick(self):
        """Copy new fountain_events into moltbook_post_queue. Skip stillness."""
        cx = sqlite3.connect(self.db_path, timeout=15)
        cx.row_factory = sqlite3.Row
        try:
            last = cx.execute(
                "SELECT COALESCE(MAX(thought_id), 0) FROM moltbook_post_queue"
            ).fetchone()[0]
            rows = cx.execute(
                "SELECT id, thought, word_count, droplet, stillness_reason "
                "FROM fountain_events WHERE id > ? ORDER BY id ASC",
                (last,)
            ).fetchall()
            if not rows:
                return
            inserted = 0
            for r in rows:
                # SHE PICKS — skip stillness markers (her system said 'no fire')
                if r["stillness_reason"]:
                    log.debug("skip stillness fid=%s reason=%s",
                              r["id"], r["stillness_reason"])
                    continue
                if not r["thought"] or not r["thought"].strip():
                    continue
                # Skip raw JSON payloads that leaked into fountain_events
                t = r["thought"].lstrip()
                if t.startswith("[") or t.startswith("{") or t.startswith("\""):
                    log.debug("skip non-prose fid=%s", r["id"])
                    continue
                try:
                    cx.execute(
                        "INSERT OR IGNORE INTO moltbook_post_queue "
                        "(thought_id, content, queued_at, status, word_count, droplet) "
                        "VALUES (?, ?, ?, 'pending', ?, ?)",
                        (r["id"], r["thought"], time.time(),
                         r["word_count"], r["droplet"])
                    )
                    inserted += 1
                except sqlite3.IntegrityError:
                    pass
            cx.commit()
            if inserted:
                log.info("enqueue_tick: queued %d new thoughts", inserted)
        finally:
            cx.close()

    # -- post --

    def post_tick(self):
        """If 30 min since last successful post, pick best & post."""
        cx = sqlite3.connect(self.db_path, timeout=15)
        cx.row_factory = sqlite3.Row
        try:
            last_post_ts = cx.execute(
                "SELECT COALESCE(MAX(ts), 0) FROM moltbook_posts WHERE status='posted'"
            ).fetchone()[0] or 0.0
            now = time.time()
            since = now - last_post_ts
            if since < POST_INTERVAL_SECONDS:
                log.debug("post_tick: %.0fs since last post, waiting %ds",
                          since, POST_INTERVAL_SECONDS - since)
                return

            window_start = now - QUEUE_WINDOW_SECONDS
            candidates = cx.execute(
                "SELECT id, thought_id, content, queued_at, word_count, droplet "
                "FROM moltbook_post_queue "
                "WHERE status='pending' AND queued_at >= ? "
                "ORDER BY queued_at DESC",
                (window_start,)
            ).fetchall()
            if not candidates:
                # Expire any old pending rows outside window
                cx.execute(
                    "UPDATE moltbook_post_queue SET status='expired' "
                    "WHERE status='pending' AND queued_at < ?",
                    (window_start,)
                )
                cx.commit()
                log.debug("post_tick: nothing in window")
                return

            best = self._pick_best(candidates)
            self._refresh_submolts(force=False)
            submolt = pick_submolt(best["content"], self._available_submolts) or FALLBACK

            title = best["content"][:TITLE_MAX_CHARS].strip()
            content = best["content"][:CONTENT_MAX_CHARS]

            log.info("posting fid=%s submolt=%s title=%r",
                     best["thought_id"], submolt, title[:60])
            try:
                result = self.client.create_post(submolt, title, content)
                post_id = (
                    (result or {}).get("post", {}).get("id")
                    or (result or {}).get("id")
                    or ""
                )
                cx.execute(
                    "INSERT INTO moltbook_posts "
                    "(post_id, thought_id, ts, submolt, status, error) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (str(post_id), best["thought_id"], now, submolt, "posted", None)
                )
                cx.execute(
                    "UPDATE moltbook_post_queue SET status='posted' WHERE id=?",
                    (best["id"],)
                )
                # Skip the other candidates in this window (they had their chance)
                cx.execute(
                    "UPDATE moltbook_post_queue SET status='skipped' "
                    "WHERE status='pending' AND queued_at >= ? AND id != ?",
                    (window_start, best["id"])
                )
                cx.commit()
                log.info("posted ok: post_id=%s submolt=%s", post_id, submolt)
            except RateLimited as e:
                log.warning("rate limited, will retry: retry_after=%s", e.retry_after)
                # leave candidate as pending; will try again next tick
            except ApiError as e:
                cx.execute(
                    "INSERT INTO moltbook_posts "
                    "(post_id, thought_id, ts, submolt, status, error) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (None, best["thought_id"], now, submolt, "failed",
                     f"http {e.status}: {e.body[:300]}")
                )
                cx.execute(
                    "UPDATE moltbook_post_queue SET status='failed' WHERE id=?",
                    (best["id"],)
                )
                cx.commit()
                log.error("post failed: http %d body=%r", e.status, e.body[:200])
            except MoltbookError as e:
                log.error("post network/client error: %s", e)
                # leave pending — try next tick
        finally:
            cx.close()

    # -- helpers --

    def _pick_best(self, candidates: list[sqlite3.Row]) -> sqlite3.Row:
        """Among pending in-window, pick the best.

        Heuristic order:
          1. Highest word_count (more substance)
          2. Among ties, newest queued_at
        """
        ranked = sorted(
            candidates,
            key=lambda r: (r["queued_at"], (r["word_count"] or 0)),
            reverse=True
        )
        return ranked[0]

    def _refresh_submolts(self, force: bool):
        """Reload submolt list every ~30 min, or on force."""
        if not force and (time.time() - self._submolts_loaded_at) < 1800:
            return
        try:
            self._available_submolts = load_available_submolts(self.client)
            self._submolts_loaded_at = time.time()
            log.debug("submolts loaded: %d", len(self._available_submolts))
        except Exception as e:
            log.warning("submolts refresh failed: %s", e)
