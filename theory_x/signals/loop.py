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
        start_gate = threading.Event()

        def _run_after_start():
            start_gate.wait()
            if not self._stop_flag.is_set():
                self._run()

        self._thread = threading.Thread(
            target=_run_after_start, name="SignalLoop", daemon=True,
        )
        try:
            self._thread.start()
        except BaseException:
            # A patched/failed start may raise after the OS thread exists.
            # Request stop before releasing the gate so no detector tick can
            # run for a builder that did not successfully start.
            self._stop_flag.set()
            start_gate.set()
            if self._thread.ident is not None:
                self._thread.join(timeout=1.0)
                if self._thread.is_alive():
                    logger.error("SignalLoop worker survived startup rollback")
            raise
        start_gate.set()
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
                self._tick(stop_event=self._stop_flag)
            except Exception as e:
                logger.warning("SignalLoop tick failed: %s", e)
            self._stop_flag.wait(self._interval)

    def _tick(self, *, stop_event=None):
        if stop_event is not None and stop_event.is_set():
            return
        now = time.time()

        # Round 70: bounded retention for `signals`. Self-throttled to one pass
        # per hour and bounded per pass, so this adds at most one small DELETE
        # to a tick. Never raises -- see theory_x/signals/reaper.py for why a
        # 7-day window is safe against every reader (widest is 24h).
        try:
            from theory_x.signals.reaper import reap as _reap_signals
            _reap_signals(self._beliefs_writer, now)
        except Exception as _re:
            logger.warning("signals reap skipped (non-fatal): %s", _re)

        if stop_event is not None and stop_event.is_set():
            return
        all_signals = []

        for det in self._detectors:
            if stop_event is not None and stop_event.is_set():
                return
            try:
                sigs = det.detect(stop_event=stop_event)
                if stop_event is not None and stop_event.is_set():
                    return
                for s in sigs:
                    if stop_event is not None and stop_event.is_set():
                        return
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

        if not all_signals or (stop_event is not None and stop_event.is_set()):
            return

        logger.info("SignalLoop tick: %d signals emitted", len(all_signals))

        matches = self._library.match(all_signals, stop_event=stop_event)
        if stop_event is not None and stop_event.is_set():
            return
        for m in matches:
            if stop_event is not None and stop_event.is_set():
                return
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
