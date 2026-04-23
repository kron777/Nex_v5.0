"""Theory X Stage 4 — Membrane (Inside/Outside Boundary).

build_membrane(writers, readers, dynamic_state=None, world_model_state=None)
    → MembraneState

The membrane is not a physical boundary — it is a classification that makes
NEX's self/world distinction explicit in her representation and her speech.
"""
from __future__ import annotations

from dataclasses import dataclass

from substrate import Writer, Reader
from .classifier import MembraneClassifier, MembraneSide, CLASSIFIER
from .self_model import SelfModel, format_self_state
from .router import QueryRouter

THEORY_X_STAGE = 4


@dataclass
class MembraneState:
    classifier: MembraneClassifier
    self_model: SelfModel
    router: QueryRouter

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
    return MembraneState(
        classifier=classifier,
        self_model=self_model,
        router=router,
    )
