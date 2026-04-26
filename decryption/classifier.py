"""
classifier.py — Template and register classifier for fountain output.

This is the same 8-category scheme used in the corpus analysis:
  ABSTRACT_NOMINAL  — abstract noun phrase as subject, no action
  DIALECTICAL       — two-sided tension or contrast structure
  SENSE_OBS         — direct reference to feed events/data
  SIMILE            — explicit comparison (like/as/feels like)
  QUESTION          — interrogative
  ACTION            — first-person action verb (I do/track/pivot/step)
  RECEPTIVITY       — passive reception (I find/notice/feel landing)
  UNCATEGORIZED     — none of the above

Register buckets derived from template:
  observer  — ABSTRACT_NOMINAL, DIALECTICAL, SENSE_OBS, SIMILE, RECEPTIVITY
  action    — ACTION
  question  — QUESTION
  unknown   — UNCATEGORIZED, TIMEOUT, ERROR
"""
from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# First-person action verbs (not pure perception/reception)
# ---------------------------------------------------------------------------

_ACTION_VERBS = re.compile(
    r"\bI\s+("
    r"pivot|track|step|push|update|set aside|mark|hold|move|test|"
    r"return|reach|build|map|resolve|shift|reframe|break|connect|"
    r"check|run|try|sort|fix|skip|drop|write|read|send|call|pull|"
    r"place|take|cut|open|close|keep|make|get|do|go|look|decide|"
    r"choose|pick|turn|aim|drive|act|apply|use|probe|scan|trace|"
    r"correct|adjust|recalibrate|reassess|redirect"
    r")\b",
    re.IGNORECASE,
)

# Perception / reception verbs — NOT action
_RECEPTION_VERBS = re.compile(
    r"\bI\s+("
    r"notice|find|feel|sense|observe|attend|witness|rest|sit|wait|"
    r"remain|stay|settle|drift|hover|watch|listen|catch|hold\s+this"
    r")\b",
    re.IGNORECASE,
)

_QUESTION = re.compile(r"\?")

_SIMILE = re.compile(
    r"\b(like|as if|as though|feels like|feels as|resembles|similar to|"
    r"reminds me of|like a|as a)\b",
    re.IGNORECASE,
)

# Feed/sense references
_SENSE_REF = re.compile(
    r"\b(btc|eth|bitcoin|ethereum|sol|kraken|coinbase|exchange|"
    r"price|volume|market|arxiv|paper|feed|stream|signal|data|"
    r"crypto|equity|trade|spike|diverge|correlation)\b",
    re.IGNORECASE,
)

# Abstract nominal: sentence begins with abstract noun phrase
_ABSTRACT_NOMINAL = re.compile(
    r"^(The|This|That|A|An)\s+\w+(ness|ity|ion|ment|ance|ence|ure|hood|ship|th)\b",
    re.IGNORECASE,
)

# Dialectical: two-sided phrasing
_DIALECTICAL = re.compile(
    r"\b(between|and yet|while|even as|though|despite|on one hand|"
    r"on the other|both .+ and|neither .+ nor|tension|paradox|"
    r"contrast|pull|balance|vs\.?|versus)\b",
    re.IGNORECASE,
)


def classify_text(text: str) -> str:
    """Return the primary template category for one fountain output."""
    if not text or not text.strip():
        return "UNCATEGORIZED"

    text = text.strip()

    # Priority order: ACTION > QUESTION > SENSE_OBS > SIMILE >
    #                 RECEPTIVITY > DIALECTICAL > ABSTRACT_NOMINAL > UNCATEGORIZED

    if _ACTION_VERBS.search(text):
        return "ACTION"

    if _QUESTION.search(text):
        return "QUESTION"

    if _SENSE_REF.search(text):
        return "SENSE_OBS"

    if _SIMILE.search(text):
        return "SIMILE"

    if _RECEPTION_VERBS.search(text):
        return "RECEPTIVITY"

    if _DIALECTICAL.search(text):
        return "DIALECTICAL"

    if _ABSTRACT_NOMINAL.search(text):
        return "ABSTRACT_NOMINAL"

    return "UNCATEGORIZED"


def register_from_template(template: str) -> str:
    """Map template category to register bucket."""
    return {
        "ABSTRACT_NOMINAL": "observer",
        "DIALECTICAL":       "observer",
        "SENSE_OBS":         "observer",
        "SIMILE":            "observer",
        "RECEPTIVITY":       "observer",
        "ACTION":            "action",
        "QUESTION":          "question",
        "UNCATEGORIZED":     "unknown",
        "TIMEOUT":           "unknown",
        "ERROR":             "unknown",
        "DRY_RUN":           "unknown",
    }.get(template, "unknown")


def classify_batch(texts: list[str]) -> list[tuple[str, str]]:
    """Classify a list of texts. Returns list of (template, register) pairs."""
    return [(classify_text(t), register_from_template(classify_text(t))) for t in texts]
