"""Theory X — Reshape Transformer.

Per FACULTY_MODEL.md §2.6 (committed 59c20d6).

Transforms a RESHAPE-pending thought via LLM, producing a new
ThoughtPacket with incremented reshape_depth and source_node
attribution of 'reshape_transformer'. Called by HoldingZoneResolver
during tick() processing — never inline in the gate hot path.
"""
from __future__ import annotations

import re
from typing import Any, Optional

import errors

THEORY_X_STAGE = "gate"

_LOG_SOURCE = "reshape_transformer"

_RESHAPE_PROMPT = """\
I held this thought: "{content}"
It conflicted with what I currently hold.
Restate it in a way that addresses the conflict, keeping the core meaning intact. One sentence.\
"""

_CONFIDENCE_DECAY = 0.9


class ReshapeTransformer:
    """Transforms RESHAPE-pending thoughts via LLM.

    Returns a new ThoughtPacket with depth+1 and attribution to
    'reshape_transformer'. Never raises — errors return None and the
    resolver falls through to reshape_failed.
    """

    def __init__(self, voice_client: Any) -> None:
        self._voice = voice_client

    def transform(
        self,
        packet: Any,
        original_thought_id: int,
        current_depth: int,
    ) -> Optional[Any]:
        """Transform packet. Returns new ThoughtPacket or None on failure."""
        from voice.llm import VoiceRequest
        from voice.registers import PHILOSOPHICAL
        from theory_x.stage_gate.coherence_gate import ThoughtPacket

        prompt = _RESHAPE_PROMPT.format(content=packet.content)
        try:
            req = VoiceRequest(
                prompt=prompt,
                register=PHILOSOPHICAL,
                max_tokens=80,
                temperature=0.85,
            )
            resp = self._voice.speak(req)
            text = resp.text.strip() if resp and resp.text else ""
        except Exception as exc:
            errors.record(
                f"reshape voice error: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )
            return None

        if text:
            m = re.search(r'^(.{20,200}?[.!?])', text, re.DOTALL)
            if m:
                text = m.group(1).strip()

        if not text or len(text) > 200:
            errors.record(
                f"reshape: empty or oversized output for held_id={original_thought_id}",
                source=_LOG_SOURCE, level="WARNING",
            )
            return None

        new_packet = ThoughtPacket(
            content=text,
            source_node="reshape_transformer",
            confidence=round(packet.confidence * _CONFIDENCE_DECAY, 4),
            branch_id=packet.branch_id,
            metadata={
                "reshape_depth": current_depth + 1,
                "original_from": packet.metadata.get("original_from", packet.source_node),
                "original_thought_id": original_thought_id,
                "reshape_hint": packet.metadata.get("reshape_hint", False),
            },
        )
        errors.record(
            f"reshape: held_id={original_thought_id} depth={current_depth + 1}: {text[:60]}",
            source=_LOG_SOURCE, level="INFO",
        )
        return new_packet
