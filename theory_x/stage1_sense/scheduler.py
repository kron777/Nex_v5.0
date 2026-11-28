"""SenseScheduler — coordinates all 28 adapters (4 internal, 24 external).

One thread is created per adapter. Internal sensors start immediately.
External feed threads are initially locally paused, but the constructor
calls start_all() before returning, so external feeds are auto-started during
normal construction/boot. stop_all() pauses external feeds; start_all()
resumes them. The global run-event gates external feeds, not internal ones.

Pausing / resuming:
    SenseScheduler.start_all()  — sets global run-event; all external feeds wake
    SenseScheduler.stop_all()   — clears global run-event; external feeds pause

Per-adapter control:
    SenseScheduler.enable(adapter_id)   — sets per-adapter local event
    SenseScheduler.disable(adapter_id)  — clears per-adapter local event

Both conditions must be met for an external adapter to poll:
    global_run IS SET  AND  per-adapter local IS SET

Internal adapters check only their local event (always set from boot).

See SPECIFICATION.md §4 — Sense Streams, and Phase 2 build prompt.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

import errors as error_channel
from .base import Adapter

THEORY_X_STAGE = 1

logger = logging.getLogger("stage1_sense.scheduler")


class _AdapterThread:
    """Manages one adapter: one background thread, status tracking."""

    def __init__(
        self,
        adapter: Adapter,
        global_run: threading.Event,
        mode_state=None,
        start_gate: threading.Event | None = None,
    ) -> None:
        self.adapter = adapter
        self._global_run = global_run
        self._start_gate = start_gate or threading.Event()
        if start_gate is None:
            self._start_gate.set()
        self._local_run = threading.Event()
        self._stop = threading.Event()
        self._mode_state = mode_state
        # First segment of stream name is the feed-weight key (e.g. "crypto" from "crypto.btc")
        self._weight_key = adapter.stream.split(".")[0] if adapter.stream else ""

        self.last_poll_at: int | None = None
        self.last_event_count: int = 0
        self.last_error: str | None = None

        if adapter.is_internal:
            self._local_run.set()
            adapter.enabled = True

        self._thread = threading.Thread(
            target=self._run,
            name=f"sense.{adapter.id}",
            daemon=True,
        )

    def start(self) -> None:
        """Start the prepared worker; scheduler owns the startup transaction."""
        self._thread.start()

    def _should_run(self) -> bool:
        if self.adapter.is_internal:
            return self._local_run.is_set()
        return self._global_run.is_set() and self._local_run.is_set()

    def _feed_weight(self) -> float:
        if self._mode_state is None or self.adapter.is_internal:
            return 1.0
        try:
            weights = self._mode_state.current().feed_weights
            return weights.get(self._weight_key, 1.0)
        except Exception:
            return 1.0

    def _run(self) -> None:
        # Scheduler workers are released together only after every thread has
        # started successfully. A partial startup therefore cannot poll or
        # submit before rollback has a chance to stop the prepared workers.
        self._start_gate.wait()
        while not self._stop.is_set():
            if not self._should_run():
                # Sleep in 1s slices so stop() and enable() wake us quickly.
                self._stop.wait(timeout=1.0)
                continue

            if self._feed_weight() == 0.0:
                self._stop.wait(timeout=self.adapter.poll_interval_seconds)
                continue

            try:
                events = self.adapter.poll()
                # Shutdown may be requested while poll() is blocked in network
                # I/O. Do not submit late results after producers are quiescing
                # and AppState may be draining/closing the shared Writers.
                if self._stop.is_set():
                    break
                count = self.adapter.submit(events)
                self.last_poll_at = int(time.time())
                self.last_event_count = count
                self.last_error = None
            except Exception as e:
                self.last_error = str(e)
                error_channel.record(
                    f"adapter[{self.adapter.id}] poll error: {e}",
                    source=f"sense.scheduler[{self.adapter.id}]",
                    exc=e,
                )

            # Sleep for the adapter's cadence, but wake immediately on stop().
            self._stop.wait(timeout=self.adapter.poll_interval_seconds)

    def enable(self) -> None:
        self._local_run.set()
        self.adapter.enabled = True

    def disable(self) -> None:
        self._local_run.clear()
        self.adapter.enabled = False

    def stop(self) -> None:
        self._stop.set()

    def join(self, timeout: float | None = None) -> bool:
        """Join this adapter thread; return False only if it remains alive."""
        thread = getattr(self, "_thread", None)
        if thread is None:
            return True
        if thread is threading.current_thread():
            return False
        # Thread.join() raises RuntimeError for a prepared but never-started
        # worker. Such a worker is already quiescent.
        if thread.ident is None and not thread.is_alive():
            return True
        thread.join(timeout=max(0.0, timeout) if timeout is not None else None)
        return not thread.is_alive()

    def status(self) -> dict[str, Any]:
        return {
            "id": self.adapter.id,
            "stream": self.adapter.stream,
            "is_internal": self.adapter.is_internal,
            "enabled": self.adapter.enabled,
            "poll_interval_seconds": self.adapter.poll_interval_seconds,
            "provenance": self.adapter.provenance,
            "last_poll_at": self.last_poll_at,
            "last_event_count": self.last_event_count,
            "last_error": self.last_error,
        }


class SenseScheduler:
    """Owns all adapter threads; exposes control and status surface."""

    def __init__(self, adapters: list[Adapter], mode_state=None) -> None:
        # Validate identity before creating any workers. A duplicate key must
        # never overwrite an already-started thread in the ownership map.
        adapter_ids = [adapter.id for adapter in adapters]
        if any(not isinstance(adapter_id, str) or not adapter_id for adapter_id in adapter_ids):
            raise ValueError("every sense adapter must have a non-empty string id")
        if len(set(adapter_ids)) != len(adapter_ids):
            duplicates = sorted({adapter_id for adapter_id in adapter_ids if adapter_ids.count(adapter_id) > 1})
            raise ValueError(f"duplicate sense adapter id(s): {', '.join(duplicates)}")

        self._global_run = threading.Event()
        self._start_gate = threading.Event()
        self._threads: dict[str, _AdapterThread] = {
            adapter.id: _AdapterThread(
                adapter, self._global_run, mode_state=mode_state, start_gate=self._start_gate
            )
            for adapter in adapters
        }

        # Start all prepared workers while the gate is closed. No adapter can
        # poll until every Thread.start() has succeeded.
        try:
            for worker in self._threads.values():
                worker.start()
        except BaseException:
            for worker in self._threads.values():
                worker.stop()
            self._start_gate.set()
            deadline = time.monotonic() + 1.0
            alive = []
            for adapter_id, worker in self._threads.items():
                remaining = max(0.0, deadline - time.monotonic())
                if not worker.join(remaining):
                    alive.append(f"sense.{adapter_id}")
            if alive:
                logger.error("SenseScheduler startup rollback left workers alive: %s", alive)
            raise
        self._start_gate.set()

        logger.info(
            "SenseScheduler started with %d adapters (%d internal, %d external)",
            len(adapters),
            sum(1 for a in adapters if a.is_internal),
            sum(1 for a in adapters if not a.is_internal),
        )
        # 2026-05-09: feeds auto-start on boot per Jon's request.
        # Was: paused-by-default per original design. Reversion:
        # remove this line.
        self.start_all()

    # -- global controls ---------------------------------------------------

    def start_all(self) -> None:
        """Start all external feeds. Internal sensors are unaffected."""
        self._global_run.set()
        for t in self._threads.values():
            if not t.adapter.is_internal:
                t.enable()
        logger.info("SenseScheduler: all external feeds started")

    def stop_all(self) -> None:
        """Pause all external feeds. Internal sensors continue."""
        self._global_run.clear()
        logger.info("SenseScheduler: all external feeds paused")

    # -- per-adapter controls ----------------------------------------------

    def enable(self, adapter_id: str) -> None:
        t = self._threads.get(adapter_id)
        if t is None:
            raise KeyError(f"no adapter with id {adapter_id!r}")
        t.enable()

    def disable(self, adapter_id: str) -> None:
        t = self._threads.get(adapter_id)
        if t is None:
            raise KeyError(f"no adapter with id {adapter_id!r}")
        if t.adapter.is_internal:
            raise ValueError(f"cannot disable internal adapter {adapter_id!r}")
        t.disable()

    def is_running(self) -> bool:
        return self._global_run.is_set()

    # -- status ------------------------------------------------------------

    def status(self) -> dict[str, Any]:
        return {
            "global_running": self._global_run.is_set(),
            "adapters": {aid: t.status() for aid, t in self._threads.items()},
        }

    # -- shutdown ----------------------------------------------------------

    def shutdown(self) -> None:
        """Request all adapter threads to stop; call join() to await exit."""
        for t in self._threads.values():
            t.stop()
        logger.info("SenseScheduler: adapter stop requested")

    def join(self, timeout: float | None = None) -> list[str]:
        """Join all adapter threads against one shared timeout budget.

        Returns adapter thread names that remain alive when the budget expires.
        """
        deadline = None if timeout is None else time.monotonic() + max(0.0, timeout)
        alive = []
        for adapter_id, worker in self._threads.items():
            remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
            if not worker.join(remaining):
                alive.append(f"sense.{adapter_id}")
        return alive
