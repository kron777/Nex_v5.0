"""Membrane classifier — inside/outside distinction.

Every stream, belief, and query is either INSIDE (NEX's own state)
or OUTSIDE (the world's state). This distinction is the phenomenal
membrane: explicit, structural, not metaphorical.
"""
from __future__ import annotations

from enum import Enum

THEORY_X_STAGE = 4

_SELF_INQUIRY_KEYWORDS = {
    "you", "your", "yourself", "feel", "feeling", "think", "thinking",
    "believe", "want", "inside", "state", "are you", "how are",
    "what are you", "who are you", "do you",
}

_INSIDE_SOURCES = {
    "precipitated_from_dynamic", "nex_seed", "manual", "identity",
    "injector", "keystone",
}


class MembraneSide(Enum):
    INSIDE = "INSIDE"
    OUTSIDE = "OUTSIDE"


class MembraneClassifier:
    def classify_stream(self, stream: str) -> MembraneSide:
        """Internal streams (internal.*) → INSIDE. Everything else → OUTSIDE."""
        if stream.startswith("internal."):
            return MembraneSide.INSIDE
        return MembraneSide.OUTSIDE

    def classify_belief(self, belief: dict) -> MembraneSide:
        """Inside belief sources → INSIDE. Everything else → OUTSIDE."""
        source = belief.get("source") or ""
        if source in _INSIDE_SOURCES:
            return MembraneSide.INSIDE
        return MembraneSide.OUTSIDE

    def classify_query(self, query: str) -> MembraneSide:
        """Detect self-inquiry queries → INSIDE. World-inquiry → OUTSIDE."""
        lowered = query.lower()
        for keyword in _SELF_INQUIRY_KEYWORDS:
            if keyword in lowered:
                return MembraneSide.INSIDE
        return MembraneSide.OUTSIDE


CLASSIFIER = MembraneClassifier()
