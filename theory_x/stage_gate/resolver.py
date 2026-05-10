"""Theory X — Holding Zone Resolver.

Per FACULTY_MODEL.md §2.5 (committed 59c20d6).

SentienceNode that resolves held thoughts:
  - on_gate_accept(packet): called by gate on every ACCEPT;
    checks held zone for corroborations and contradictions
  - tick(): called by background loop (every 300s); fades
    stale held thoughts (24h age)

Integration:
  CoherenceGate calls on_gate_accept() after returning ACCEPT.
  run.py / gui/server.py start the background tick loop.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Optional

import errors

THEORY_X_STAGE = "gate"

_LOG_SOURCE = "holding_zone_resolver"


class HoldingZoneResolver:
    """
    Resolves held thoughts via corroboration, contradiction, time decay.

    Implements SentienceNode protocol (DOCTRINE §4).
    Stateless regarding decisions; all state lives in beliefs.db.
    """

    name: str = "holding_zone_resolver"

    def __init__(
        self,
        holding_zone,
        beliefs_writer=None,
        transformer=None,
        gate=None,
    ) -> None:
        self._zone = holding_zone
        self._beliefs_writer = beliefs_writer
        self._transformer = transformer
        self._gate = gate
        self._resolution_count: int = 0
        self._reshape_count: int = 0
        self._stop: Optional[threading.Event] = None
        self._thread: Optional[threading.Thread] = None

    def set_gate(self, gate) -> None:
        self._gate = gate

    def set_transformer(self, transformer) -> None:
        self._transformer = transformer

    # ── Public API ────────────────────────────────────────────────────────────

    def on_gate_accept(self, packet: Any) -> None:
        """Called by CoherenceGate on every ACCEPT.

        Checks held zone for corroborations and contradictions.
        Never raises — errors are recorded but do not propagate.
        """
        # Corroboration path: incoming ACCEPT may support held thoughts
        try:
            matches = self._zone.find_corroborations(packet)
            for held in matches:
                new_count = self._zone.increment_corroboration(held["id"])
                if new_count < 0:
                    continue
                errors.record(
                    f"corroboration: held_id={held['id']} "
                    f"count={new_count}/3: {held['content'][:50]}",
                    source=_LOG_SOURCE, level="INFO",
                )
                if new_count >= 3:
                    self._zone.promote_to_belief(held["id"], held)
                    self._zone.mark_resolved(
                        held["id"],
                        "accepted",
                        "corroboration_threshold_3",
                        trigger_preview=packet.content[:80],
                    )
                    self._resolution_count += 1
        except Exception as exc:
            errors.record(
                f"on_gate_accept corroboration error: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )

        # Contradiction path: incoming ACCEPT may reject held thoughts
        try:
            contras = self._zone.find_contradictions(packet)
            for held in contras:
                self._zone.mark_resolved(
                    held["id"],
                    "rejected",
                    "contradicted_by_accept",
                    trigger_preview=packet.content[:80],
                )
                self._resolution_count += 1
                errors.record(
                    f"held_thought rejected: held_id={held['id']} "
                    f"contradicted by: {packet.content[:50]}",
                    source=_LOG_SOURCE, level="INFO",
                )
        except Exception as exc:
            errors.record(
                f"on_gate_accept contradiction error: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )

    def start_loop(self, interval_seconds: int = 300) -> None:
        """Start background fade loop (daemon thread, 5-minute interval)."""
        self._stop = threading.Event()

        def _run() -> None:
            while not self._stop.is_set():
                self._stop.wait(interval_seconds)
                if not self._stop.is_set():
                    self.tick()

        self._thread = threading.Thread(
            target=_run,
            name="holding_zone_resolver",
            daemon=True,
        )
        self._thread.start()
        errors.record(
            "Holding zone resolver loop started (interval=300s)",
            source=_LOG_SOURCE, level="INFO",
        )

    def stop_loop(self) -> None:
        if self._stop is not None:
            self._stop.set()

    # ── SentienceNode protocol ────────────────────────────────────────────────

    def tick(self, context: dict[str, Any] = None) -> dict[str, Any]:
        """Background step: fade stale held thoughts + process reshape pending."""
        try:
            faded = self._zone.fade_stale(time.time())
            if faded:
                self._resolution_count += faded
        except Exception as exc:
            errors.record(f"resolver tick fade error: {exc}", source=_LOG_SOURCE, exc=exc)

        if self._transformer is not None and self._gate is not None:
            try:
                self._process_reshape_pending()
            except Exception as exc:
                errors.record(
                    f"resolver tick reshape error: {exc}", source=_LOG_SOURCE, exc=exc
                )

        return self.state()

    def _process_reshape_pending(self) -> None:
        """Transform up to 10 reshape_pending rows and re-submit through gate."""
        from theory_x.stage_gate.coherence_gate import ThoughtPacket
        pending = self._zone.find_reshape_pending(limit=10)
        for row in pending:
            packet = ThoughtPacket(
                content=row["content"],
                source_node=row["source_node"],
                confidence=row["confidence"],
                branch_id=row.get("branch_id"),
                metadata={
                    "reshape_hint": True,
                    "reshape_depth": row["reshape_depth"],
                    "original_thought_id": row["id"],
                },
            )
            new_packet = self._transformer.transform(
                packet, row["id"], row["reshape_depth"]
            )
            if new_packet is not None:
                try:
                    self._gate.check(new_packet)
                except Exception as exc:
                    errors.record(
                        f"reshape gate re-submit error: {exc}",
                        source=_LOG_SOURCE, exc=exc,
                    )
                self._zone.mark_reshape_complete(
                    row["id"],
                    "reshaped",
                    f"transformer_depth_{row['reshape_depth'] + 1}",
                    reshaped_preview=new_packet.content[:80],
                )
                self._reshape_count += 1
            else:
                self._zone.mark_reshape_complete(
                    row["id"],
                    "reshape_failed",
                    "transformer_returned_none",
                    None,
                )
            errors.record(
                f"reshape: held_id={row['id']} → "
                f"{'reshaped' if new_packet else 'reshape_failed'}: "
                f"{row['content'][:50]}",
                source=_LOG_SOURCE, level="INFO",
            )

    def decay(self, now: float) -> None:
        pass  # fade_stale handles time-based decay via tick()

    def state(self, now: float = None) -> dict[str, Any]:
        try:
            rows = self._zone._reader.read(
                "SELECT status, COUNT(*) as n FROM held_thoughts GROUP BY status"
            )
            counts = {r["status"]: r["n"] for r in rows}
        except Exception:
            counts = {}
        return {
            "name": self.name,
            "resolutions_this_session": self._resolution_count,
            "reshapes_this_session": self._reshape_count,
            "held_counts": counts,
        }
