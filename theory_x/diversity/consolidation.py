"""Three Clocks — fast/medium/slow consolidation triggers."""
from __future__ import annotations

import json
import logging
import time

from theory_x.diversity.boost import apply_decay
from theory_x.diversity.dormancy import DormancyScanner
from theory_x.diversity.reanimate import wake_one

log = logging.getLogger("theory_x.diversity.consolidation")

FAST_INTERVAL = 20
MEDIUM_INTERVAL = 200
SLOW_INTERVAL = 2000


class ClockRunner:
    def __init__(self, writers: dict, readers: dict):
        self._writers = writers
        self._readers = readers
        self._last_fast = 0
        self._last_medium = 0
        self._last_slow = 0
        self._reanimated_belief: dict | None = None

    def tick(self, fire_count: int, *, stop_event=None) -> None:
        def _stopping() -> bool:
            return stop_event is not None and stop_event.is_set()

        if _stopping():
            return
        if fire_count - self._last_fast >= FAST_INTERVAL:
            self._run_fast(fire_count, stop_event=stop_event)
            if _stopping():
                return
            self._last_fast = fire_count

        if fire_count - self._last_medium >= MEDIUM_INTERVAL:
            self._run_medium(fire_count, stop_event=stop_event)
            if _stopping():
                return
            self._last_medium = fire_count

        if fire_count - self._last_slow >= SLOW_INTERVAL:
            self._run_slow(fire_count, stop_event=stop_event)
            if _stopping():
                return
            self._last_slow = fire_count

    def get_reanimated_belief(self) -> dict | None:
        r = self._reanimated_belief
        self._reanimated_belief = None
        return r

    def _run_fast(self, fire_count: int, *, stop_event=None) -> None:

        actions = {}
        try:
            removed = apply_decay(self._writers["beliefs"], self._readers["beliefs"], stop_event=stop_event)
            actions["boosts_decayed"] = removed
        except Exception as e:
            log.warning("fast clock: boost decay failed: %s", e)

        if stop_event is not None and stop_event.is_set():
            return
        try:
            dormancy = DormancyScanner(self._writers["beliefs"], self._readers["beliefs"])
            updated = dormancy.scan_incremental(stop_event=stop_event)
            actions["dormancy_updated"] = updated
        except Exception as e:
            log.warning("fast clock: dormancy scan failed: %s", e)

        if stop_event is not None and stop_event.is_set():
            return
        try:
            reanimated = wake_one(self._writers["beliefs"], self._readers["beliefs"], stop_event=stop_event)
            if reanimated:
                self._reanimated_belief = reanimated
                actions["reanimated"] = reanimated["belief_id"]
        except Exception as e:
            log.warning("fast clock: reanimation failed: %s", e)

        if stop_event is not None and stop_event.is_set():
            return
        self._record("fast", fire_count, actions, stop_event=stop_event)
        log.info("Fast clock ran at fire=%d: %s", fire_count, actions)

    def _run_medium(self, fire_count: int, *, stop_event=None) -> None:
        findings: dict = {}
        try:
            rows = self._readers["beliefs"].read(
                "SELECT COUNT(*) AS n FROM groove_alerts "
                "WHERE acknowledged_at IS NULL AND detected_at > ?",
                (time.time() - 7200,),
            )
            findings["active_groove_alerts"] = rows[0]["n"] if rows else 0
        except Exception as e:
            log.warning("medium clock: groove query failed: %s", e)

        if stop_event is not None and stop_event.is_set():
            return
        try:
            rows = self._readers["beliefs"].read(
                "SELECT branch_id, AVG(grade) AS avg_grade, COUNT(*) AS n "
                "FROM collision_grades g JOIN beliefs pa ON g.parent_a_id = pa.id "
                "GROUP BY branch_id ORDER BY avg_grade DESC LIMIT 3"
            )
            findings["top_branches"] = [
                {"branch": r["branch_id"], "avg_grade": round(r["avg_grade"] or 0, 3)}
                for r in rows
            ]
        except Exception as e:
            log.warning("medium clock: branch analysis failed: %s", e)

        if stop_event is not None and stop_event.is_set():
            return
        self._record("medium", fire_count, {}, findings, stop_event=stop_event)
        log.info("Medium clock ran at fire=%d: %s", fire_count, findings)

    def _run_slow(self, fire_count: int, *, stop_event=None) -> None:
        if stop_event is not None and stop_event.is_set():
            return
        try:
            from theory_x.diversity.evolver import GraderEvolver
            evolver = GraderEvolver(self._writers["beliefs"], self._readers["beliefs"])
            result = evolver.evolve()
            if stop_event is not None and stop_event.is_set():
                return
            self._record("slow", fire_count, result or {}, stop_event=stop_event)
            log.info("Slow clock: grader evolver ran at fire=%d", fire_count)
        except Exception as e:
            log.warning("slow clock: evolver failed: %s", e)
            if stop_event is None or not stop_event.is_set():
                self._record("slow", fire_count, {"error": str(e)}, stop_event=stop_event)

    def _record(self, clock: str, fire_count: int,
                actions: dict, findings: dict | None = None, *, stop_event=None) -> None:
        if stop_event is not None and stop_event.is_set():
            return
        try:
            self._writers["beliefs"].write(
                "INSERT INTO consolidations "
                "(clock, ran_at, fire_count_at_run, actions_taken, findings) "
                "VALUES (?, ?, ?, ?, ?)",
                (clock, time.time(), fire_count,
                 json.dumps(actions), json.dumps(findings or {})),
            )
        except Exception as e:
            log.warning("consolidation record failed: %s", e)
