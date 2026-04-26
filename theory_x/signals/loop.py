"""Background thread: runs detectors and template matching every 60s."""
from __future__ import annotations

import json
import threading
import time
import logging

from theory_x.signals.detectors import (
    CoOccurrenceDetector,
    SilenceDetector,
    BurstDetector,
)
from theory_x.signals.templates import PatternTemplateLibrary

logger = logging.getLogger("theory_x.signals")


class SignalLoop:
    """Runs detectors on a schedule, writes signals and patterns to DB."""

    def __init__(
        self,
        beliefs_writer,
        beliefs_reader,
        sense_reader,
        interval_seconds: int = 60,
    ):
        self._beliefs_writer = beliefs_writer
        self._beliefs_reader = beliefs_reader
        self._sense_reader = sense_reader
        self._interval = interval_seconds
        self._stop_flag = threading.Event()
        self._thread = None

        self._detectors = [
            CoOccurrenceDetector(beliefs_reader),
            SilenceDetector(sense_reader),
            BurstDetector(beliefs_reader),
        ]
        self._library = PatternTemplateLibrary(beliefs_writer, beliefs_reader)

    def start(self):
        if self._thread is not None:
            return
        self._stop_flag.clear()
        self._thread = threading.Thread(
            target=self._run, name="SignalLoop", daemon=True,
        )
        self._thread.start()
        logger.info("SignalLoop started (interval=%ds)", self._interval)

    def stop(self):
        self._stop_flag.set()

    def status(self) -> dict:
        return {
            "running": self._thread is not None and self._thread.is_alive(),
            "interval_seconds": self._interval,
        }

    def _run(self):
        while not self._stop_flag.is_set():
            try:
                self._tick()
            except Exception as e:
                logger.warning("SignalLoop tick failed: %s", e)
            self._stop_flag.wait(self._interval)

    def _tick(self):
        now = time.time()
        all_signals = []

        for det in self._detectors:
            try:
                sigs = det.detect()
                for s in sigs:
                    sig_id = self._beliefs_writer.write(
                        "INSERT INTO signals "
                        "(detected_at, detector_name, signal_type, payload, "
                        " branches, entities, confidence) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            now, s.detector_name, s.signal_type,
                            json.dumps(s.payload),
                            json.dumps(s.branches),
                            json.dumps(s.entities),
                            s.confidence,
                        ),
                    )
                    if sig_id:
                        all_signals.append({
                            "id": sig_id,
                            "detector_name": s.detector_name,
                            "payload": json.dumps(s.payload),
                        })
            except Exception as e:
                logger.warning("Detector %s failed: %s", det.__class__.__name__, e)

        if not all_signals:
            return

        logger.info("SignalLoop tick: %d signals emitted", len(all_signals))

        matches = self._library.match(all_signals)
        for m in matches:
            self._beliefs_writer.write(
                "INSERT INTO patterns "
                "(matched_at, template_name, signal_ids, "
                " predicted_window_seconds, prediction, template_confidence) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    now, m["template_name"],
                    json.dumps(m["signal_ids"]),
                    m["predicted_window_seconds"],
                    m["prediction"],
                    0.5,
                ),
            )
            logger.info("Pattern matched: %s — %s",
                        m["template_name"], m["prediction"][:80])


def build_signal_loop(writers: dict, readers: dict) -> SignalLoop:
    loop = SignalLoop(
        beliefs_writer=writers["beliefs"],
        beliefs_reader=readers["beliefs"],
        sense_reader=readers["sense"],
    )
    loop.start()
    return loop
