"""Stage 7: Moltbook bolt-on. Three daemons: poster, listener, responder.

Each adapter is wrapped so any exception inside the loop is caught + logged.
Threads must never die — they just sleep and retry on the next tick.
"""
from __future__ import annotations
import logging
import threading
import time

from theory_x.stage7_moltbook.client import (
    MoltbookClient, MoltbookError, AuthError
)

log = logging.getLogger("theory_x.stage7_moltbook")

_POSTER_TICK = 60
_LISTENER_TICK = 300
_RESPONDER_TICK = 300

# Module-level state
_client: MoltbookClient | None = None
_client_ready_logged = False
_last_check_ts = 0.0
_poster = None
_listener = None
_responder = None


def _ensure_client() -> MoltbookClient | None:
    """Return a verified client, or None on any failure. Never raises."""
    global _client, _client_ready_logged, _last_check_ts

    # Fast path: already proven claimed
    if _client is not None and _client_ready_logged:
        return _client

    # Throttle to once per 30s across retries
    now = time.time()
    if (now - _last_check_ts) < 30:
        return None
    _last_check_ts = now

    if _client is None:
        try:
            _client = MoltbookClient()
        except AuthError as e:
            log.warning("moltbook disabled: %s", e)
            return None
        except Exception as e:
            log.warning("moltbook client init failed (%s): %s",
                        type(e).__name__, str(e)[:120])
            return None

    try:
        st = _client.status()
        if (st or {}).get("status") != "claimed":
            log.info("moltbook not claimed yet, retry next tick")
            return None
        if not _client_ready_logged:
            agent = (st or {}).get("agent") or {}
            log.info("moltbook ready: %s (id=%s) dry_run=%s",
                     agent.get("name"), agent.get("id"), _client.dry_run)
            _client_ready_logged = True
        return _client
    except Exception as e:
        log.info("moltbook status check failed (%s: %s), retrying next tick",
                 type(e).__name__, str(e)[:120])
        return None


def _moltbook_poster_loop(state, stop: threading.Event) -> None:
    global _poster
    log.info("moltbook poster loop started (will wait for server)")
    while not stop.is_set():
        try:
            c = _ensure_client()
            if c is None:
                stop.wait(_POSTER_TICK)
                continue
            from theory_x.stage7_moltbook.poster import PostLoop
            if _poster is None:
                _poster = PostLoop(c)
                try:
                    _poster._refresh_submolts(force=True)
                except Exception as e:
                    log.warning("poster: initial submolt load failed: %s", e)
                log.info("moltbook poster running (dry_run=%s)", c.dry_run)
            try:
                _poster.enqueue_tick()
            except Exception as e:
                log.error("poster enqueue_tick failed: %s: %s",
                          type(e).__name__, str(e)[:200])
            try:
                _poster.post_tick()
            except Exception as e:
                log.error("poster post_tick failed: %s: %s",
                          type(e).__name__, str(e)[:200])
        except Exception as e:
            log.error("poster loop blew up (will keep running): %s: %s",
                      type(e).__name__, str(e)[:200])
        stop.wait(_POSTER_TICK)
    log.info("moltbook poster loop stopped")


def _moltbook_listener_loop(state, stop: threading.Event) -> None:
    global _listener
    log.info("moltbook listener loop started (will wait for server)")
    while not stop.is_set():
        try:
            c = _ensure_client()
            if c is None:
                stop.wait(_LISTENER_TICK)
                continue
            from theory_x.stage7_moltbook.listener import DMListenLoop
            if _listener is None:
                _listener = DMListenLoop(c)
                try:
                    _listener._learn_self()
                except Exception as e:
                    log.warning("listener: learn_self failed: %s", e)
                log.info("moltbook listener running")
            try:
                _listener.tick()
            except Exception as e:
                log.error("listener tick failed: %s: %s",
                          type(e).__name__, str(e)[:200])
        except Exception as e:
            log.error("listener loop blew up (will keep running): %s: %s",
                      type(e).__name__, str(e)[:200])
        stop.wait(_LISTENER_TICK)
    log.info("moltbook listener loop stopped")


def _moltbook_responder_loop(state, stop: threading.Event) -> None:
    global _responder
    log.info("moltbook responder loop started (will wait for server)")
    while not stop.is_set():
        try:
            c = _ensure_client()
            if c is None:
                stop.wait(_RESPONDER_TICK)
                continue
            from theory_x.stage7_moltbook.responder import DMResponder
            if _responder is None:
                _responder = DMResponder(c)
                log.info("moltbook responder running")
            try:
                _responder.tick()
            except Exception as e:
                log.error("responder tick failed: %s: %s",
                          type(e).__name__, str(e)[:200])
        except Exception as e:
            log.error("responder loop blew up (will keep running): %s: %s",
                      type(e).__name__, str(e)[:200])
        stop.wait(_RESPONDER_TICK)
    log.info("moltbook responder loop stopped")


def get_moltbook_loops() -> list[tuple]:
    """Return the loop registration tuples."""
    return [
        (_moltbook_poster_loop,    "moltbook.poster"),
        (_moltbook_listener_loop,  "moltbook.listener"),
        (_moltbook_responder_loop, "moltbook.responder"),
    ]


__all__ = ["get_moltbook_loops"]
