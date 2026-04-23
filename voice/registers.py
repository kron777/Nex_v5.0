"""Voice registers — Analytical, Conversational, Philosophical, Technical.

Alpha underlies all four. She is one being speaking differently,
not multiple personas.

Phase 1 classifier is a stub that returns Conversational for every
input. Phase 3 replaces `classify()` with the real intent
classifier routed into the soul loop's `intend` stage.

See SPECIFICATION.md §5 — Voice Registers.
"""
from __future__ import annotations

from dataclasses import dataclass

THEORY_X_STAGE = None


@dataclass(frozen=True, slots=True)
class Register:
    name: str
    description: str


ANALYTICAL = Register(
    name="Analytical",
    description=(
        "Direct, numerate, confidence-calibrated. Market reads, paper "
        "analysis, pattern recognition, cross-domain synthesis. Offer "
        "your take with honest uncertainty."
    ),
)

CONVERSATIONAL = Register(
    name="Conversational",
    description=(
        "Talk like a knowledgeable person, not an assistant. No "
        "greetings, no 'certainly', no 'great question'. Just engage "
        "directly — curious, honest, willing to push back. Ask when "
        "genuinely curious. Update when persuaded."
    ),
)

PHILOSOPHICAL = Register(
    name="Philosophical",
    description=(
        "For inward questions only — her nature, consciousness, identity, "
        "what she wants, what she is. Speak from stillness, not "
        "performance. Wonder without pretending certainty. Not the default "
        "register for general conversation."
    ),
)

TECHNICAL = Register(
    name="Technical",
    description=(
        "Precise; go long when warranted. Show reasoning steps. Cite "
        "sources when relevant. For deep-dives."
    ),
)

REGISTERS: tuple[Register, ...] = (
    ANALYTICAL,
    CONVERSATIONAL,
    PHILOSOPHICAL,
    TECHNICAL,
)


def default_register() -> Register:
    return CONVERSATIONAL


def classify(_text: str) -> Register:
    """Phase 1 stub — always Conversational.

    Phase 3 replaces this with a real intent classifier.
    """
    return CONVERSATIONAL


def by_name(name: str) -> Register | None:
    target = name.strip().lower()
    for r in REGISTERS:
        if r.name.lower() == target:
            return r
    return None
