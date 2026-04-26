"""Condenser: compresses a fountain fire into a 3-6 word droplet.

The droplet captures the cognitive move the fire is making, stripped
of verbal decoration. Enables idea-level deduplication and similarity
checking beyond word-overlap Jaccard.

Reference: Architectural Doctrine v1 Section III.2
"""
from __future__ import annotations

import logging
import re
from typing import Optional

import errors
from voice.llm import VoiceClient, VoiceRequest
from voice.registers import ANALYTICAL

log = logging.getLogger(__name__)
_LOG_SOURCE = "condenser"

_CONDENSE_PROMPT = """Condense the following thought into a 3-6 word \
droplet capturing its core cognitive move. No decoration, no prose.

Rules:
- 3 to 6 words only
- Use hyphens to connect multi-word concepts
- Keep it abstract — the move, not the specifics
- No articles ("the", "a", "an") unless essential
- Lowercase
- Strip "I", "my", "me" where possible

Examples:
Thought: "The weight of being alone in this vast silence, yet knowing my very presence fills every moment"
Droplet: alone-yet-pervasive

Thought: "huh, markets feel slow today"
Droplet: low-market-tempo

Thought: "Meta cutting jobs again"
Droplet: tech-layoffs-continuing

Thought: "The oscillation between inquiry and recognition of my own limitations"
Droplet: inquiry-vs-limitation

Thought: "wait, bitcoin's moving"
Droplet: btc-movement-detected

Thought: "didn't i already read about this?"
Droplet: possible-repetition

Now condense this thought:
Thought: {thought}
Droplet:"""


class Condenser:
    """Compresses fountain fires to cognitive-move droplets."""

    def __init__(self, voice_client: Optional[VoiceClient] = None):
        self._voice = voice_client

    def condense(self, thought: str) -> Optional[str]:
        """Return a 3-6 word droplet, or None on failure."""
        if not thought or not thought.strip():
            return None

        if self._voice is None:
            return self._fallback_condense(thought)

        try:
            prompt = _CONDENSE_PROMPT.format(thought=thought.strip())
            resp = self._voice.speak(
                VoiceRequest(prompt=prompt, register=ANALYTICAL, max_tokens=20),
            )
            raw = resp.text if resp else ""
            droplet = self._clean(raw)

            word_count = len(droplet.split())
            if not (3 <= word_count <= 8):
                errors.record(
                    f"Condenser word-count reject ({word_count}): {droplet}",
                    source=_LOG_SOURCE, level="DEBUG",
                )
                return self._fallback_condense(thought)

            return droplet
        except Exception as e:
            errors.record(f"Condenser failed: {e}", source=_LOG_SOURCE, level="WARNING")
            return self._fallback_condense(thought)

    def _clean(self, raw: str) -> str:
        text = (raw or "").strip()
        if "Droplet:" in text:
            text = text.split("Droplet:")[-1].strip()
        text = text.split("\n")[0].strip()
        text = text.lower().strip('"').strip("'").rstrip(".")
        return text.strip()

    def _fallback_condense(self, thought: str) -> str:
        """Simple heuristic when LLM unavailable — extract content words."""
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "of", "to",
            "in", "on", "at", "my", "i", "me", "this", "that", "it",
            "and", "or", "but", "as", "so", "for", "with", "by", "from",
        }
        words = re.findall(r"\b[a-z]+\b", thought.lower())
        content = [w for w in words if w not in stopwords and len(w) > 2]
        selected = content[:4]
        if len(selected) < 3:
            return "raw-fragment"
        return "-".join(selected)
