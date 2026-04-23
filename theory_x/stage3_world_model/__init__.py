"""Theory X Stage 3 — World Model.

build_world_model(writers, readers, dynamic_state=None) → WorldModelState

Starts background loops:
  decay_loop       — hourly belief tier decay (Tier 5-7 idle beliefs)
  harmonizer_loop  — every 2 hours, conflict detection and resolution
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Optional

import errors
from substrate import Writer, Reader
from .retrieval import BeliefRetriever, format_beliefs_for_prompt
from .promotion import BeliefPromoter
from .harmonizer import Harmonizer
from .activation import ActivationEngine
from .erosion import ProvenanceErosion
from .pipeline_hooks import PipelineHooks

THEORY_X_STAGE = 3

_LOG_SOURCE = "world_model"


@dataclass
class WorldModelState:
    retriever: BeliefRetriever
    promoter: BeliefPromoter
    harmonizer: Harmonizer
    activation: ActivationEngine
    erosion: ProvenanceErosion
    hooks: PipelineHooks
    writers: dict
    readers: dict
    _decay_runs: int = field(default=0, init=False)
    _harmonizer_runs: int = field(default=0, init=False)
    _cross_domain_runs: int = field(default=0, init=False)
    _erosion_runs: int = field(default=0, init=False)
    _started_at: float = field(default_factory=time.time, init=False)
    _disturbance: Optional[dict] = field(default=None, init=False)

    def get_disturbance(self) -> Optional[dict]:
        """Return active disturbance if cycles remaining, else None. Decrements cycles."""
        d = self._disturbance
        if d is None or d.get("cycles_remaining", 0) <= 0:
            self._disturbance = None
            return None
        return d

    def set_disturbance(self, belief_id_a: int, belief_id_b: int,
                        content_a: str, content_b: str, intensity: float) -> None:
        self._disturbance = {
            "belief_id_a": belief_id_a,
            "belief_id_b": belief_id_b,
            "content_a": content_a,
            "content_b": content_b,
            "intensity": intensity,
            "cycles_remaining": 8,
        }

    def status(self) -> dict:
        return {
            "decay_runs": self._decay_runs,
            "harmonizer_runs": self._harmonizer_runs,
            "cross_domain_runs": self._cross_domain_runs,
            "erosion_runs": self._erosion_runs,
            "disturbance_active": self._disturbance is not None,
            "uptime_seconds": int(time.time() - self._started_at),
        }


def _decay_loop(state: WorldModelState, stop: threading.Event) -> None:
    while not stop.is_set():
        stop.wait(3600.0)
        if stop.is_set():
            break
        try:
            count = state.promoter.decay_pass()
            state._decay_runs += 1
            if count:
                errors.record(
                    f"decay_loop demoted {count} beliefs",
                    source=_LOG_SOURCE, level="INFO",
                )
        except Exception as exc:
            errors.record(f"decay_loop error: {exc}", source=_LOG_SOURCE, exc=exc)


def _harmonizer_loop(state: WorldModelState, stop: threading.Event) -> None:
    while not stop.is_set():
        stop.wait(7200.0)
        if stop.is_set():
            break
        try:
            resolved = state.harmonizer.run_scan_and_resolve(world_model_state=state)
            state._harmonizer_runs += 1
            if resolved:
                errors.record(
                    f"harmonizer_loop resolved {resolved} conflicts",
                    source=_LOG_SOURCE, level="INFO",
                )
        except Exception as exc:
            errors.record(f"harmonizer_loop error: {exc}", source=_LOG_SOURCE, exc=exc)


def _erosion_loop(state: WorldModelState, stop: threading.Event) -> None:
    while not stop.is_set():
        stop.wait(6 * 3600.0)
        if stop.is_set():
            break
        try:
            advanced = state.erosion.erosion_pass()
            state._erosion_runs += 1
            if advanced:
                errors.record(
                    f"erosion_loop advanced {advanced} beliefs",
                    source=_LOG_SOURCE, level="INFO",
                )
        except Exception as exc:
            errors.record(f"erosion_loop error: {exc}", source=_LOG_SOURCE, exc=exc)


def _cross_domain_loop(state: WorldModelState, stop: threading.Event) -> None:
    while not stop.is_set():
        stop.wait(6 * 3600.0)
        if stop.is_set():
            break
        try:
            written = state.harmonizer.detect_cross_domain()
            state._cross_domain_runs += 1
            if written:
                errors.record(
                    f"cross_domain_loop wrote {written} new edges",
                    source=_LOG_SOURCE, level="INFO",
                )
        except Exception as exc:
            errors.record(f"cross_domain_loop error: {exc}", source=_LOG_SOURCE, exc=exc)


def build_world_model(writers: dict, readers: dict,
                      dynamic_state=None) -> WorldModelState:
    """Factory: wire belief retrieval, promotion, harmonization, and pipeline hooks."""
    erosion = ProvenanceErosion(writers["beliefs"], readers["beliefs"])
    retriever = BeliefRetriever(readers["beliefs"], erosion=erosion)
    promoter = BeliefPromoter(writers["beliefs"], readers["beliefs"], erosion=erosion)
    harmonizer = Harmonizer(
        beliefs_writer=writers["beliefs"],
        beliefs_reader=readers["beliefs"],
        dynamic_writer=writers["dynamic"],
        promoter=promoter,
    )
    activation = ActivationEngine(readers["beliefs"])
    hooks = PipelineHooks(promoter=promoter, beliefs_reader=readers["beliefs"])

    if dynamic_state is not None:
        hooks.register(dynamic_state)

    state = WorldModelState(
        retriever=retriever,
        promoter=promoter,
        harmonizer=harmonizer,
        activation=activation,
        erosion=erosion,
        hooks=hooks,
        writers=writers,
        readers=readers,
    )

    stop = threading.Event()
    state._stop = stop  # type: ignore[attr-defined]

    for fn, name in [
        (_decay_loop,        "world_model.decay"),
        (_harmonizer_loop,   "world_model.harmonizer"),
        (_cross_domain_loop, "world_model.cross_domain"),
        (_erosion_loop,      "world_model.erosion"),
    ]:
        t = threading.Thread(target=fn, args=(state, stop), name=name, daemon=True)
        t.start()

    return state
