"""world_loop.py  —  Stage C of "more than a prompt processor".

Stage A proved a plain function can read the live price and score a claim NEX
can't fake. Stage B let NEX's voice make its own claim, paired with a random
control. Both were CONFIRMED but ran only when invoked by hand.

Stage C makes it SELF-RUNNING. On a cadence, a background daemon thread:
  (1) resolves any claims whose window has closed (verdict re-fetched from the
      real price — Stage A resolver), and
  (2) fires a fresh voice prediction paired with a random control (Stage B).

Over days this fills the scorecard with no manual runs, turning voice-vs-random
into a real verdict on whether the voice carries predictive signal. Matches the
exact start_loop() daemon-thread idiom used by every other autonomous subsystem
in this codebase (predictive_substrate, self_mind_view, etc.).

Env-gated in run.py behind NEX5_WORLD_PRED=1, default OFF. Tunable:
  NEX5_WORLD_PRED_INTERVAL  seconds between ticks (default 900 = 15 min)
  NEX5_WORLD_PRED_HORIZON   prediction horizon seconds (default 3600 = 1 hour)
  NEX5_WORLD_PRED_ASSET     coingecko id (default 'bitcoin')

IMPORTANT: horizon is hour-scale on purpose. 30s windows are pure noise; only
hour-scale horizons over many samples can answer the skill question.
"""
from __future__ import annotations

import logging
import os
import sys
import threading
from typing import Optional

# Stage A + B. Robust import: package path in-process, sibling fallback if run
# as a loose script.
try:
    from theory_x.stage_world import world_predictions as wp
    from theory_x.stage_world import prediction_generator as pg
except ModuleNotFoundError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import world_predictions as wp
    import prediction_generator as pg

log = logging.getLogger("nex5.world_loop")


class WorldPredictionLoop:
    def __init__(
        self,
        asset: str = "bitcoin",
        interval_seconds: Optional[int] = None,
        horizon_seconds: Optional[int] = None,
    ) -> None:
        self.asset = os.environ.get("NEX5_WORLD_PRED_ASSET", asset)
        self._interval = int(
            interval_seconds
            if interval_seconds is not None
            else os.environ.get("NEX5_WORLD_PRED_INTERVAL", "900")
        )
        self._horizon = int(
            horizon_seconds
            if horizon_seconds is not None
            else os.environ.get("NEX5_WORLD_PRED_HORIZON", "3600")
        )
        self._stop: Optional[threading.Event] = None
        self._thread: Optional[threading.Thread] = None

    def tick(self) -> None:
        # 1. resolve any matured claims — the verdict comes from reality
        try:
            res = wp.resolve_due()
            if res.get("resolved"):
                log.info(
                    "world_pred resolved=%d correct=%d",
                    res["resolved"], res["correct"],
                )
        except Exception as e:  # never let a bad tick kill the loop
            log.warning("world_pred resolve failed (non-fatal): %s", e)

        # 2. fire a fresh voice prediction + random control
        try:
            r = pg.make_voice_prediction(self.asset, self._horizon)
            if "error" in r:
                log.warning("world_pred make skipped: %s", r["error"])
            else:
                log.info(
                    "world_pred voice=%s random=%s baseline=%.0f horizon=%ds",
                    r["voice_dir"], r["random_dir"], r["baseline"], self._horizon,
                )
        except Exception as e:
            log.warning("world_pred make failed (non-fatal): %s", e)

    def start_loop(self, interval_seconds: Optional[float] = None) -> None:
        interval = interval_seconds if interval_seconds is not None else self._interval
        self._stop = threading.Event()

        def _run() -> None:
            while not self._stop.is_set():
                self._stop.wait(interval)
                if not self._stop.is_set():
                    self.tick()

        self._thread = threading.Thread(
            target=_run, name="world_prediction_loop", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        if self._stop is not None:
            self._stop.set()
