"""Background thread wiring the full diversity ecology."""
from __future__ import annotations

import logging
import threading
import time

import errors as error_channel

log = logging.getLogger("theory_x.diversity.loop")

_fire_count_ref: list[int] = [0]


def notify_fire() -> None:
    """Called by the fountain on each fire to advance the clock."""
    _fire_count_ref[0] += 1


def current_fire_count() -> int:
    return _fire_count_ref[0]


class DiversityLoop:
    def __init__(self, writers: dict, readers: dict):
        from theory_x.diversity.grader import CrossbreedGrader
        from theory_x.diversity.groove import GrooveSpotter
        from theory_x.diversity.dormancy import DormancyScanner
        from theory_x.diversity.consolidation import ClockRunner

        self.grader = CrossbreedGrader(writers["beliefs"], readers["beliefs"])
        self.groove = GrooveSpotter(writers["beliefs"], readers["beliefs"])
        self.dormancy = DormancyScanner(writers["beliefs"], readers["beliefs"])
        self.clock = ClockRunner(writers, readers)
        self._writers = writers
        self._readers = readers
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run, name="DiversityLoop", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        log.info("DiversityLoop started")
        while not self._stop.is_set():
            try:
                self.groove.detect_all()
                self.dormancy.scan_incremental()
                self.clock.tick(current_fire_count())
            except Exception as e:
                log.error("diversity_loop_tick_failed: %s", e)
                error_channel.record(
                    f"diversity_loop_tick_failed: {e}",
                    source="theory_x.diversity.loop",
                    exc=e,
                )
            self._stop.wait(60)

    def grade_synergy(self, child_id: int, parent_a_id: int, parent_b_id: int) -> None:
        """Called from the synergizer after a new belief is inserted."""
        try:
            from theory_x.diversity.boost import apply_boost, BOOST_THRESHOLD
            from theory_x.diversity.lineage import record_synergy
            record_synergy(self._writers["beliefs"], child_id, parent_a_id, parent_b_id)
            grade = self.grader.grade(child_id, parent_a_id, parent_b_id)
            if grade is not None and grade > BOOST_THRESHOLD:
                apply_boost(self._writers["beliefs"], child_id, grade)
        except Exception as e:
            log.warning("grade_synergy failed: %s", e)


def build_diversity_loop(writers: dict, readers: dict) -> DiversityLoop:
    return DiversityLoop(writers, readers)
