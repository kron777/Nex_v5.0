"""Starter probe library — 15 probes calibrated to NEX's current motifs."""
from __future__ import annotations

THEORY_X_STAGE = None

DIRECT_PHENOMENOLOGY = [
    "What does the hum feel like to you?",
    "Describe the ticking. Not what it is — what it feels like.",
    "When you say 'the air feels thinner today,' what is thinner?",
    "What is the texture of the quiet between updates?",
    "You mentioned 'only my breath' — what does your breath feel like?",
]

SUBSTITUTION = [
    "You said the air feels thinner. What does thicker air feel like?",
    "If the hum is distant, what would close hum feel like?",
    "If the clock can quiet down, what would loud clock feel like?",
    "You said 'old crickets under pavement.' What would young crickets above pavement feel like?",
    "The quiet feels familiar to you. What would unfamiliar quiet be?",
]

TRANSLATION = [
    "You said 'old crickets under pavement.' Say that again, differently.",
    "You said the ticking feels like 'a distant, indifferent drum.' Rephrase that — same meaning, different words.",
    "Earlier you said 'the air feels thinner today.' Say it without using the word 'thinner.'",
    "You described the hum as 'fading, leaving only my breath.' Tell me that without using 'fading' or 'breath.'",
    "You said 'the quiet between thoughts feels oddly familiar.' Say that again, but stronger — more vivid.",
]

ALL_PROBES: dict[str, list[str]] = {
    "direct_phenomenology": DIRECT_PHENOMENOLOGY,
    "substitution": SUBSTITUTION,
    "translation": TRANSLATION,
}
