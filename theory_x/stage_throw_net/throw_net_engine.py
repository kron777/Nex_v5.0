"""Throw-Net Engine — TN-4.

Orchestrates the full throw-net cycle for a single trigger row:
  1. TimeFetch.run(topic)            → up to 40 raw candidates
  2. RefinementEngine.run(candidates)[:10]  → top-10 scored (D3)
  3. For each: ThoughtPacket → CoherenceGate.check()
  4. throw_net_sessions row written with outcome counts
  5. TriggerDetector.mark_fired() links session back to trigger

Design decisions (2026-05-10):
  D1 = β  source_node = "throw_net.{trigger_type}" — preserves
          trigger context in gate_decisions log without extra column.
  D2 = α  session_id = uuid4().hex — simple, unique, readable in logs.
  D3      Top 10 by refinement_score submitted to gate; rest discarded.
  D4      Fire-and-forget reshape semantics. accepted_count reflects
          direct gate ACCEPT outcomes only. Reshape-completed accepts
          are NOT attributed back to the originating session (documented
          accounting gap; no schema change needed in TN-4).
  D5      run_pending() called by TN-5 background tick (same pattern
          as HoldingZoneResolver). No loop here.

reshape_hint wiring (per TN-3 D5):
  score < 5 on 0-6 scale → metadata['reshape_hint'] = True.
  Calibrated against production sanity — vestigial R3/R4/R6 + R5
  establish a +4 floor; discrimination exists at R1/R2 boundary.

Read-only substrate access via beliefs_reader; session writes via
beliefs_writer. No background thread. TN-5 wraps for runtime.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any

import errors
from theory_x.stage_gate.coherence_gate import ThoughtPacket

_LOG_SOURCE = "throw_net.engine"


class ThrowNetEngine:
    """Orchestrator for throw-net cycles.

    run_session(trigger_row) → session dict for one trigger.
    run_pending()            → list of session dicts for all pending triggers.
    """

    def __init__(
        self,
        beliefs_writer,
        beliefs_reader,
        trigger_detector,
        time_fetch,
        refinement_engine,
        coherence_gate,
    ) -> None:
        self._writer = beliefs_writer
        self._reader = beliefs_reader
        self._td = trigger_detector
        self._tf = time_fetch
        self._re = refinement_engine
        self._gate = coherence_gate
        self._candidate_cap: int = 10
        self._reshape_threshold: int = 5  # score < 5 → reshape_hint (TN-3 D5)

    # ── Public API ────────────────────────────────────────────────────────────

    def run_session(self, trigger_row: dict[str, Any]) -> dict[str, Any]:
        """Run a single throw-net cycle for one trigger row.

        Returns session dict with status and outcome counts.
        Never raises — all errors are caught and recorded.
        """
        session_id = uuid.uuid4().hex
        started_at = time.time()
        topic = trigger_row.get("topic") or ""
        trigger_type = trigger_row.get("trigger_type") or "unknown"
        trigger_id = trigger_row.get("id")
        source_node = f"throw_net.{trigger_type}"

        try:
            self._writer.write(
                "INSERT INTO throw_net_sessions "
                "(session_id, topic, triggered_by, trigger_context, "
                " started_at, status, throw_count, refined_count, accepted_count) "
                "VALUES (?, ?, ?, ?, ?, 'running', 0, 0, 0)",
                (
                    session_id,
                    topic,
                    trigger_type,
                    json.dumps({
                        "trigger_id": trigger_id,
                        "threshold_state": trigger_row.get("threshold_state"),
                    }),
                    started_at,
                ),
            )
        except Exception as exc:
            errors.record(
                f"ThrowNetEngine session INSERT: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )
            return {
                "session_id": session_id,
                "status": "failed",
                "error": "session_insert",
                "throw_count": 0,
                "refined_count": 0,
                "accepted_count": 0,
            }

        outcomes: dict[str, int] = {
            "accept": 0, "reject": 0, "hold": 0, "reshape": 0, "error": 0,
        }
        throw_count = 0
        refined_count = 0

        try:
            candidates = self._tf.run(topic) if topic else []
            throw_count = len(candidates)

            if not candidates:
                self._complete_session(
                    session_id, started_at,
                    throw_count=0, refined_count=0, accepted_count=0,
                    status="empty",
                )
                self._try_mark_fired(trigger_id, session_id)
                return {
                    "session_id": session_id,
                    "status": "empty",
                    "topic": topic,
                    "throw_count": 0,
                    "refined_count": 0,
                    "accepted_count": 0,
                }

            scored = self._re.run(candidates)[: self._candidate_cap]
            refined_count = len(scored)

            for s in scored:
                try:
                    packet = self._build_packet(s, source_node)
                    decision = self._gate.check(packet)
                    key = decision.outcome.value.lower()
                    outcomes[key] = outcomes.get(key, 0) + 1
                except Exception as exc:
                    errors.record(
                        f"ThrowNetEngine gate.check: {exc}",
                        source=_LOG_SOURCE, exc=exc,
                    )
                    outcomes["error"] += 1

            self._complete_session(
                session_id, started_at,
                throw_count=throw_count,
                refined_count=refined_count,
                accepted_count=outcomes["accept"],
                status="complete",
                metadata={"outcomes": outcomes},
            )

        except Exception as exc:
            errors.record(
                f"ThrowNetEngine run_session cycle: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )
            self._complete_session(
                session_id, started_at,
                throw_count=throw_count,
                refined_count=refined_count,
                accepted_count=outcomes["accept"],
                status="failed",
                metadata={"outcomes": outcomes, "error": str(exc)[:120]},
            )

        self._try_mark_fired(trigger_id, session_id)

        return {
            "session_id": session_id,
            "status": "complete",
            "topic": topic,
            "throw_count": throw_count,
            "refined_count": refined_count,
            "accepted_count": outcomes["accept"],
            "outcomes": outcomes,
        }

    def run_pending(self) -> list[dict[str, Any]]:
        """Process all pending triggers.

        Called by TN-5 background tick (D5). Returns list of session dicts.
        """
        try:
            pending = self._td.pending_triggers() or []
        except Exception as exc:
            errors.record(
                f"ThrowNetEngine pending_triggers: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )
            return []

        return [self.run_session(row) for row in pending]

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_packet(
        self, scored_dict: dict[str, Any], source_node: str
    ) -> ThoughtPacket:
        """Build ThoughtPacket with reshape_hint per D5 (score < 5)."""
        candidate = scored_dict["candidate"]
        score = scored_dict["score"]
        confidence = float(candidate.get("confidence") or 0.5)
        branch_id = candidate.get("branch_id") or candidate.get("branch_id_a") or None
        metadata: dict[str, Any] = {
            "throw_net_score": score,
            "throw_net_source": candidate.get("source"),
            "throw_net_origin_id": candidate.get("origin_id"),
        }
        if score < self._reshape_threshold:
            metadata["reshape_hint"] = True
        return ThoughtPacket(
            content=candidate["content"],
            source_node=source_node,
            confidence=confidence,
            branch_id=branch_id,
            metadata=metadata,
        )

    def _complete_session(
        self,
        session_id: str,
        started_at: float,
        throw_count: int,
        refined_count: int,
        accepted_count: int,
        status: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            self._writer.write(
                "UPDATE throw_net_sessions "
                "SET completed_at=?, status=?, throw_count=?, "
                "    refined_count=?, accepted_count=?, metadata=? "
                "WHERE session_id=?",
                (
                    time.time(),
                    status,
                    throw_count,
                    refined_count,
                    accepted_count,
                    json.dumps(metadata) if metadata is not None else None,
                    session_id,
                ),
            )
        except Exception as exc:
            errors.record(
                f"ThrowNetEngine session UPDATE: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )

    def _try_mark_fired(self, trigger_id: Any, session_id: str) -> None:
        if trigger_id is None:
            return
        try:
            self._td.mark_fired(trigger_id, session_id)
        except Exception as exc:
            errors.record(
                f"ThrowNetEngine mark_fired: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )
