"""Theory X Stage 4 — Membrane (Inside/Outside Boundary).

build_membrane(writers, readers, dynamic_state=None, world_model_state=None)
    → MembraneState

The membrane is not a physical boundary — it is a classification that makes
NEX's self/world distinction explicit in her representation and her speech.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Optional

import errors
from substrate import Writer, Reader
from .classifier import MembraneClassifier, MembraneSide, CLASSIFIER
from .self_model import SelfModel, format_self_state
from .router import QueryRouter
from .behavioural_self_model import BehaviouralSelfModel

THEORY_X_STAGE = 4

_LOG_SOURCE = "membrane"


@dataclass
class MembraneState:
    classifier: MembraneClassifier
    self_model: SelfModel
    router: QueryRouter
    behavioural: Optional[BehaviouralSelfModel]
    _writers: dict = None
    _readers: dict = None

    def snapshot(self) -> dict:
        return self.self_model.snapshot()

    def classify_stream(self, stream: str) -> str:
        return self.classifier.classify_stream(stream).value

    def classify_query(self, query: str) -> str:
        return self.classifier.classify_query(query).value

    def route(self, query: str, belief_retriever, dynamic_state=None) -> dict:
        return self.router.route(
            query=query,
            belief_retriever=belief_retriever,
            self_model=self.self_model,
            dynamic_state=dynamic_state,
        )


def _behavioural_loop(state: MembraneState, stop: threading.Event) -> None:
    while not stop.is_set():
        stop.wait(4 * 3600.0)
        if stop.is_set():
            break
        if state.behavioural is None or state._writers is None or state._readers is None:
            continue
        try:
            written = state.behavioural.write_behavioural_beliefs(
                state._writers["beliefs"],
                state._readers["beliefs"],
            )
            if written:
                errors.record(
                    f"behavioural_loop wrote {written} new beliefs",
                    source=_LOG_SOURCE, level="INFO",
                )
        except Exception as exc:
            errors.record(f"behavioural_loop error: {exc}", source=_LOG_SOURCE, exc=exc)


def build_membrane(writers: dict, readers: dict,
                   dynamic_state=None,
                   world_model_state=None) -> MembraneState:
    """Factory: create the membrane layer."""
    classifier = MembraneClassifier()
    self_model = SelfModel(
        sense_reader=readers["sense"],
        beliefs_reader=readers["beliefs"],
        dynamic_state=dynamic_state,
    )
    router = QueryRouter(classifier=classifier)

    behavioural: Optional[BehaviouralSelfModel] = None
    if "conversations" in readers:
        behavioural = BehaviouralSelfModel(readers["conversations"])

    state = MembraneState(
        classifier=classifier,
        self_model=self_model,
        router=router,
        behavioural=behavioural,
    )
    state._writers = writers
    state._readers = readers

    if behavioural is not None:
        stop = threading.Event()
        state._stop = stop  # type: ignore[attr-defined]
        t = threading.Thread(
            target=_behavioural_loop, args=(state, stop),
            name="membrane.behavioural", daemon=True,
        )
        t.start()

    return state
