"""Scorecard loop — keeps NEX's tested market-prediction self-belief current.

Wraps ground_self_belief.refresh_self_belief() (the same delete-then-insert
logic that lived only as a hand-run script) as a registered daemon loop.
Runs once immediately on start, then every TICK_SECONDS.

~3.6 voice predictions resolve per hour (world_loop's default horizon is
3600s) so the underlying numbers cannot move faster than that.
"""
from __future__ import annotations

import logging
import threading

log = logging.getLogger("theory_x.life.scorecard_loop")

TICK_SECONDS = 3600


def _tick() -> None:
    """One refresh attempt. Never raises -- logs and returns on failure."""
    try:
        import sys
        sys.path.insert(0, ".")
        import ground_self_belief as gsb
        result = gsb.refresh_self_belief()
        v, r = result["voice"], result["random"]
        log.info(
            "scorecard_loop: refreshed (voice=%s/%s random=%s/%s)",
            v.get("correct"), v.get("resolved"),
            r.get("correct"), r.get("resolved"),
        )
    except Exception as e:
        log.error("scorecard_loop tick failed: %s: %s", type(e).__name__, str(e)[:200])


def scorecard_loop(state, stop: threading.Event) -> None:
    log.info("scorecard_loop started (tick=%ds)", TICK_SECONDS)
    _tick()  # run once immediately -- belief is fresh without waiting an hour
    while not stop.is_set():
        stop.wait(TICK_SECONDS)
        if stop.is_set():
            break
        _tick()
    log.info("scorecard_loop stopped")
