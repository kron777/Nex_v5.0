"""Throw-Net Monitor — TN-5.

SentienceNode wrapper around ThrowNetEngine.run_pending().
Polls pending triggers every 300s and runs a session for each
that has crossed its threshold. Daemon thread; never blocks
the main boot path.

Pattern matches HoldingZoneResolver exactly (DOCTRINE §4).
TN-4 ThrowNetEngine owns the cycle; this class owns the clock.

Design decisions (2026-05-10):
  D1 = α  300s tick interval — matches HoldingZoneResolver,
          aligns with fire-and-forget reshape tempo.
  D2 = α  AppState field: throw_net_monitor.
  D3 = α  Boot log: "Throw-net monitor ready — autonomous
          cycle every 300s when triggers pending"

Runtime wiring: run.py and gui/server.py build_state().
TN-5 completes Phase 25a — throw-net runs autonomously.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Optional

import errors

_LOG_SOURCE = "throw_net.monitor"
_DEFAULT_INTERVAL = 300.0


class ThrowNetMonitor:
    """SentienceNode that polls pending throw-net triggers on a clock.

    tick() calls engine.run_pending(); start_loop() spawns daemon thread.
    All state lives in throw_net_sessions / throw_net_triggers DB tables.
    """

    name: str = "throw_net_monitor"

    def __init__(
        self,
        engine,
        interval_seconds: float = _DEFAULT_INTERVAL,
    ) -> None:
        self._engine = engine
        self._interval = interval_seconds
        self._stop: Optional[threading.Event] = None
        self._thread: Optional[threading.Thread] = None
        self._tick_count: int = 0
        self._sessions_total: int = 0

    # ── SentienceNode protocol ────────────────────────────────────────────────

    def tick(self, context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Run all pending throw-net sessions for this tick."""
        try:
            sessions = self._engine.run_pending()
            self._sessions_total += len(sessions)
            if sessions:
                errors.record(
                    f"throw_net monitor tick: ran {len(sessions)} session(s)",
                    source=_LOG_SOURCE, level="INFO",
                )
        except Exception as exc:
            errors.record(
                f"throw_net monitor tick error: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )
        self._tick_count += 1
        return self.state()

    def decay(self, now: float) -> None:
        pass  # engine state lives in DB; no in-memory decay needed

    def state(self, now: Optional[float] = None) -> dict[str, Any]:
        return {
            "name": self.name,
            "tick_count": self._tick_count,
            "sessions_total": self._sessions_total,
            "interval_seconds": self._interval,
        }

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start_loop(self, interval_seconds: Optional[float] = None) -> None:
        """Spawn daemon thread that calls tick() every interval."""
        interval = interval_seconds if interval_seconds is not None else self._interval
        self._stop = threading.Event()

        def _run() -> None:
            while not self._stop.is_set():
                self._stop.wait(interval)
                if not self._stop.is_set():
                    self.tick()

        self._thread = threading.Thread(
            target=_run,
            name="throw_net_monitor",
            daemon=True,
        )
        self._thread.start()
        errors.record(
            f"throw_net monitor loop started (interval={int(interval)}s)",
            source=_LOG_SOURCE, level="INFO",
        )

    def stop(self) -> None:
        """Stop the daemon loop gracefully."""
        if self._stop is not None:
            self._stop.set()
