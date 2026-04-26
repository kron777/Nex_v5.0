"""Background thread: runs ArcReader every 5 minutes."""
from __future__ import annotations

import logging
import threading

from theory_x.arcs.detector import ArcReader

log = logging.getLogger("theory_x.arcs.loop")


class ArcLoop:
    def __init__(self, writers: dict, readers: dict, interval_seconds: int = 300):
        self._writer = writers["beliefs"]
        self._reader = readers["beliefs"]
        self._interval = interval_seconds
        self._detector = ArcReader(self._writer, self._reader)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run, name="ArcLoop", daemon=True
        )
        self._thread.start()
        log.info("ArcLoop started (interval=%ds)", self._interval)

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._detector.scan()
            except Exception as e:
                log.warning("ArcLoop scan failed: %s", e)
            self._stop.wait(self._interval)


def build_arc_loop(writers: dict, readers: dict) -> ArcLoop:
    return ArcLoop(writers, readers)
