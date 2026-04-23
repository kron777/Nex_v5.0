"""Voice LLM client — Qwen2.5-3B via llama-server (OpenAI-compatible).

Thin HTTP client. Register-aware system prompt. No disclaimers baked
in — affirmation-only discipline. The legal floor lives in the ToS,
not in NEX's voice.

Phase 1 does not require the llama-server to be running. The client
accepts an injectable `request_fn` so tests can drive it with a mock.

See SPECIFICATION.md §5 — Voice Registers, and §5.Voice discipline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

import requests

from alpha import ALPHA
from .registers import Register, default_register

THEORY_X_STAGE = None

RequestFn = Callable[[str, dict], dict]


@dataclass
class VoiceRequest:
    prompt: str
    register: Register = field(default_factory=default_register)
    context: Sequence[str] = ()
    temperature: float = 0.7
    max_tokens: int = 512


@dataclass
class VoiceResponse:
    text: str
    register: Register
    raw: dict


def _alpha_block() -> str:
    return "\n".join(ALPHA.lines)


def build_system_prompt(register: Register, context: Sequence[str] = (),
                        beliefs: Optional[str] = None) -> str:
    parts = [
        "You are NEX. Your ground stance (Alpha) is:",
        "",
        _alpha_block(),
        "",
        f"Current register: {register.name} — {register.description}",
        "",
        "Speak from what you are, not what you are not. Share your "
        "thinking directly; leave legal disclaimers to the ToS.",
    ]
    if beliefs:
        parts.extend([
            "",
            beliefs,
            "",
            "She speaks from these beliefs, not despite them. They are her world as she has built it.",
        ])
    if context:
        parts.extend(["", "Context:"])
        parts.extend(f"- {c}" for c in context)
    return "\n".join(parts)


def _default_request(url: str, payload: dict) -> dict:
    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()


class VoiceClient:
    """Stateless client around the llama-server chat-completions endpoint."""

    def __init__(
        self,
        *,
        url: str = "http://localhost:8080/v1/chat/completions",
        model: str = "qwen2.5-3b",
        request_fn: Optional[RequestFn] = None,
    ):
        self.url = url
        self.model = model
        self._request_fn = request_fn or _default_request

    def speak(self, req: VoiceRequest, beliefs: Optional[str] = None) -> VoiceResponse:
        system = build_system_prompt(req.register, req.context, beliefs=beliefs)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": req.prompt},
            ],
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
        }
        raw = self._request_fn(self.url, payload)
        text = raw["choices"][0]["message"]["content"]
        return VoiceResponse(text=text, register=req.register, raw=raw)
