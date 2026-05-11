"""CounterfactualNode — Phase 25b.

DOCTRINE §5 row 10b (Option γ). SentienceNode that works open
problems proactively: fetches belief candidates, scores via
RefinementEngine, submits to CoherenceGate. After 3 ACCEPTs per
problem the problem is promoted to review_queue.

Tick interval: 300s (matches ThrowNetMonitor, HoldingZoneResolver).

Move semantics: DELETE from open_problems + INSERT into review_queue
preserving id. ID stability required because beliefs.problem_id
references it. Idempotency: skip move if id already in review_queue.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Optional

import errors

_LOG_SOURCE = "counterfactual_node"
_DEFAULT_INTERVAL = 300.0
_ACCEPT_THRESHOLD = 3  # ACCEPTs before problem is promoted to review_queue


class CounterfactualNode:
    """SentienceNode that generates counterfactual beliefs for open problems.

    Reads open_problems (conversations DB), fetches belief candidates
    matching each problem's title/description via TimeFetch, scores via
    RefinementEngine, submits buildable candidates to CoherenceGate.
    Promotes problems with >= _ACCEPT_THRESHOLD accepted beliefs to
    review_queue.
    """

    name: str = "counterfactual_node"

    def __init__(
        self,
        beliefs_reader,
        beliefs_writer,
        conversations_reader,
        conversations_writer,
        coherence_gate,
        time_fetch,
        refinement_engine,
        interval_seconds: float = _DEFAULT_INTERVAL,
    ) -> None:
        self._beliefs_reader = beliefs_reader
        self._beliefs_writer = beliefs_writer
        self._conversations_reader = conversations_reader
        self._conversations_writer = conversations_writer
        self._gate = coherence_gate
        self._time_fetch = time_fetch
        self._refinement_engine = refinement_engine
        self._interval = interval_seconds
        self._stop: Optional[threading.Event] = None
        self._thread: Optional[threading.Thread] = None
        self._tick_count: int = 0
        self._problems_processed: int = 0
        self._candidates_accepted: int = 0
        self._promotions_total: int = 0

    # ── SentienceNode protocol ────────────────────────────────────────────────

    def tick(self, context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Process one open problem per tick (oldest last_touched_at first)."""
        try:
            self._process_one()
        except Exception as exc:
            errors.record(
                f"counterfactual_node tick error: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )
        self._tick_count += 1
        return self.state()

    def decay(self, now: float) -> None:
        pass  # all state lives in DB; no in-memory decay needed

    def state(self, now: Optional[float] = None) -> dict[str, Any]:
        return {
            "name": self.name,
            "tick_count": self._tick_count,
            "problems_processed": self._problems_processed,
            "candidates_accepted": self._candidates_accepted,
            "promotions_total": self._promotions_total,
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
            name="counterfactual_node",
            daemon=True,
        )
        self._thread.start()
        errors.record(
            f"counterfactual_node loop started (interval={int(interval)}s)",
            source=_LOG_SOURCE, level="INFO",
        )

    def stop(self) -> None:
        if self._stop is not None:
            self._stop.set()

    # ── Core logic ────────────────────────────────────────────────────────────

    def _process_one(self) -> None:
        """Work the oldest-touched open problem."""
        rows = self._conversations_reader.read(
            "SELECT id, title, description, created_at, tags "
            "FROM open_problems "
            "WHERE state = 'open' ORDER BY last_touched_at ASC LIMIT 1"
        )
        if not rows:
            return
        problem = dict(rows[0])
        problem_id = problem["id"]
        constraint = _constraint_from_problem(problem)
        if not constraint:
            return

        candidates = self._time_fetch.fetch_from_beliefs(constraint, limit=10)
        if not candidates:
            return
        scored = self._refinement_engine.run(candidates)
        buildable = [s for s in scored if s["buildable"]]
        if not buildable:
            return

        from theory_x.stage_gate.coherence_gate import GateOutcome, ThoughtPacket
        source_node = f"counterfactual.{problem_id}"
        accepts_this_tick = 0
        for result in buildable:
            candidate = result["candidate"]
            packet = ThoughtPacket(
                content=candidate["content"],
                source_node=source_node,
                confidence=float(candidate.get("confidence", 0.7)),
                branch_id=candidate.get("branch_id"),
                metadata={"problem_id": problem_id, "score": result["score"]},
            )
            try:
                decision = self._gate.check(packet)
            except Exception as exc:
                errors.record(
                    f"counterfactual_node gate.check error: {exc}",
                    source=_LOG_SOURCE, exc=exc,
                )
                continue
            if decision.outcome == GateOutcome.ACCEPT:
                self._insert_belief(candidate["content"], problem_id)
                accepts_this_tick += 1

        self._problems_processed += 1
        if accepts_this_tick:
            self._candidates_accepted += accepts_this_tick
            errors.record(
                f"counterfactual_node: {accepts_this_tick} accept(s) for "
                f"problem {problem_id}",
                source=_LOG_SOURCE, level="INFO",
            )
            self._maybe_promote(problem_id, problem)

    def _insert_belief(self, content: str, problem_id: int) -> None:
        """INSERT OR IGNORE belief linked to this problem. Wrapper auto-tags."""
        self._beliefs_writer.write(
            "INSERT OR IGNORE INTO beliefs "
            "(content, tier, confidence, source, problem_id, created_at) "
            "VALUES (?, 3, 0.65, 'counterfactual_node', ?, ?)",
            (content, problem_id, time.time()),
        )

    def _accept_count_for(self, problem_id: int) -> int:
        """Count beliefs inserted for this problem."""
        try:
            rows = self._beliefs_reader.read(
                "SELECT COUNT(*) AS n FROM beliefs WHERE problem_id = ?",
                (problem_id,),
            )
            return rows[0]["n"] if rows else 0
        except Exception:
            return 0

    def _maybe_promote(self, problem_id: int, problem: dict) -> None:
        """Promote to review_queue once accept count reaches threshold."""
        if self._accept_count_for(problem_id) < _ACCEPT_THRESHOLD:
            return

        # Idempotency guard
        try:
            existing = self._conversations_reader.read(
                "SELECT id FROM review_queue WHERE id = ?", (problem_id,)
            )
            if existing:
                return
        except Exception:
            return

        # Move: INSERT into review_queue (same id), then DELETE from open_problems
        now = time.time()
        self._conversations_writer.write(
            "INSERT INTO review_queue "
            "(id, title, description, created_at, flagged_at, tags) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                problem_id,
                problem.get("title", ""),
                problem.get("description", ""),
                problem.get("created_at", now),
                now,
                problem.get("tags", "[]"),
            ),
        )
        self._conversations_writer.write(
            "DELETE FROM open_problems WHERE id = ?", (problem_id,)
        )
        self._promotions_total += 1
        errors.record(
            f"counterfactual_node: problem {problem_id} promoted to review_queue",
            source=_LOG_SOURCE, level="INFO",
        )


def _constraint_from_problem(problem: dict) -> str:
    """Build a constraint string from problem title + description snippet."""
    title = problem.get("title") or ""
    desc = (problem.get("description") or "")[:120]
    return (title + " " + desc).strip()
