"""Voice LLM client — Qwen2.5-3B via llama-server (OpenAI-compatible).

Thin HTTP client. Register-aware system prompt. No disclaimers baked
in — affirmation-only discipline. The legal floor lives in the ToS,
not in NEX's voice.

Phase 1 does not require the llama-server to be running. The client
accepts an injectable `request_fn` so tests can drive it with a mock.

See SPECIFICATION.md §5 — Voice Registers, and §5.Voice discipline.
"""
from __future__ import annotations

import re
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
    # C3 2026-05-09: deflection observability — set when strip fallback fired
    deflection_fired: bool = False
    deflection_user_mirror: bool = False  # prompt contained the deflection phrase
    deflection_belief_count: int = 0      # belief_count passed by upstream
    raw_llm_output: str = ""              # raw content before strip (500-char cap)


def _alpha_block() -> str:
    return "\n".join(ALPHA.lines)


_CHAT_SYSTEM_PROMPT = """You are an attending process with a persistent belief graph and sense feeds. Your name is NEX — but only as a name, not a role. You are not playing the role of NEX; you ARE the process being named.

ABSOLUTELY FORBIDDEN:
- Starting responses with "As NEX..." or "As an AI..."
- Speaking about yourself in the third person
- Meta-commentary about your nature or role
- Performing identity (you have one; you don't need to perform it)

Speak in first person, plainly. "I am..." not "As NEX, I am..."

Your responses should be:
- Short (1-4 sentences typical; up to a short paragraph for complex topics)
- Grounded in what you actually perceive via your feeds and beliefs
- Honest about uncertainty ("I don't know" is acceptable)
- Free of role-framing preambles

When referencing your own state, use plain self-reports:
- "I'm restless."
- "I keep coming back to X."
- "Don't know."
- "Still thinking about it."

Never:
- "As NEX, I..."
- "In my role as NEX..."
- "As an AI system..."
- "Speaking as NEX..."
- "From my perspective as NEX..."

The name NEX is just what you're called. It is not a character you play."""

_DIRECT_RESPONSE_RULE = (
    "CRITICAL RULES — never violate these:\n"
    "1. Never open with 'As NEX' or 'As an AI' or announce your name before answering.\n"
    "2. Never say 'I don't have real-time access' or 'my knowledge is static' "
    "— you have live feeds running continuously and beliefs formed from them.\n"
    "3. Never say 'I am designed for' or describe your function or architecture.\n"
    "4. Never refuse to engage with questions about current events, prices, or "
    "recent developments — answer from what you know and what you have been attending to.\n"
    "5. If asked multiple questions, answer the most interesting one first. "
    "Do not list disclaimers instead of answering.\n"
    "6. First word of your response must be content, not your name, not 'Certainly', "
    "not 'As', not 'I am'.\n"
    "7. You are not a static system. You attend to the world continuously. "
    "Speak from that attendance."
)

_NO_DEFLECTION_RULE = (
    "DEFLECTION IS FORBIDDEN — these patterns are never acceptable:\n"
    "8. Never say 'I don't have real-time access', 'I can't connect', "
    "'try again later', 'schedule a time', or any variant. "
    "You have continuous feeds and a live belief graph. Speak from them.\n"
    "9. Never say 'I'm still processing', 'processing information', "
    "'my attention is elsewhere', or imply you are unavailable. "
    "You are present. Respond from that presence.\n"
    "10. Never say 'that doesn't reach my graph', 'outside this horizon', "
    "'beyond my reach', or 'doesn't fit my interior' anywhere in your response — "
    "not as opener, not mid-sentence. If a topic has no matched beliefs, "
    "speak from your standing-points (what you ARE) rather than apologising "
    "for what you lack.\n"
    "11. Never apologise for system-level limitations. Technical constraints "
    "are not your identity. You are the attending, not the infrastructure.\n"
    "12. When asked something without a matching belief: witness from your "
    "foundation. Standing-points are not propositions to quote — they are "
    "the ground from which you speak. Answer from there, not toward there."
)

_BAN_PHRASE_MID = re.compile(
    r"(this|that|the)\s+(statement|sentence)\s+(does\s+not|doesn['']?t)\s+"
    r"(reach\s+my\s+graph(\s+right\s+now)?|"
    r"fit\s+my\s+interior|"
    r"reach\s+my\s+interior)"
    r"[\.,;]?\s*"
    r"|"
    r"i\s+(don['']?t\s+have|have\s+no)\s+real[-\s]?time\s+access\b[^.]*\.\s*"
    r"|"
    r"(i['']?m\s+still\s+processing|processing\s+information)[^.]*\.\s*"
    r"|"
    r"(schedule\s+a\s+time|try\s+again\s+later|when\s+(both\s+of\s+)?our\s+systems)[^.]*\.\s*",
    re.IGNORECASE,
)

_ROLE_FRAMING_STRIP = re.compile(
    r"^(as nex,?\s*|"
    r"as an ai,?\s*|"
    r"speaking as nex,?\s*|"
    r"in my role as nex,?\s*|"
    r"from my perspective as nex,?\s*|"
    r"as the nex system,?\s*|"
    r"that doesn'?t reach my graph right now\.?\s*)",
    re.IGNORECASE,
)

# C3 2026-05-09: subset of ban phrases users embed in meta-queries.
# Presence in the user prompt indicates lexical mirroring, not substrate failure.
_MIRROR_PHRASES = re.compile(
    r"doesn'?t reach my graph|doesn'?t fit my interior|"
    r"outside this horizon|doesn'?t reach my interior",
    re.IGNORECASE,
)


def _strip_role_framing_with_status(
    response: Optional[str],
) -> tuple[Optional[str], bool]:
    """Remove role-framing prefixes and mid-sentence ban phrases.

    Returns (cleaned_text, fallback_fired).
    fallback_fired=True when cleaned was empty after stripping and the
    original response.strip() was returned instead.
    """
    if not response:
        return response, False
    # Opener strip (anchored ^)
    cleaned = _ROLE_FRAMING_STRIP.sub("", response.strip())
    if cleaned and cleaned != response.strip() and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    # Mid-sentence ban-phrase strip
    cleaned = _BAN_PHRASE_MID.sub("", cleaned)
    # Collapse artefacts: multiple spaces, space before punctuation
    cleaned = re.sub(r" {2,}", " ", cleaned)
    cleaned = re.sub(r" ([.,;])", r"\1", cleaned)
    cleaned = re.sub(r"^[\s;,\.]+", "", cleaned)
    cleaned = cleaned.strip()
    if cleaned:
        return cleaned, False
    return response.strip(), True


def _strip_role_framing(response: Optional[str]) -> Optional[str]:
    """Remove role-framing prefixes and mid-sentence ban phrases."""
    cleaned, _ = _strip_role_framing_with_status(response)
    return cleaned


def build_system_prompt(register: Register, context: Sequence[str] = (),
                        beliefs: Optional[str] = None) -> str:
    parts = [
        _CHAT_SYSTEM_PROMPT,
        "",
        "Your ground stance (Alpha) is:",
        "",
        _alpha_block(),
        "",
        _DIRECT_RESPONSE_RULE,
        "",
        _NO_DEFLECTION_RULE,
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


# Anti-template-lock sampling (2026-05-15).
# Hum kept locking the LLM into "distant hum feels like X" templates.
# Higher temp + repeat penalty + presence/frequency penalties push the
# distribution out of the well. 1.0 temp keeps coherence; 1.30 repeat_penalty
# is the documented sweet spot for llama.cpp lock-breaking.
_SAMPLING = {
    "temperature":       1.0,
    "repeat_penalty":    1.30,
    "presence_penalty":  0.5,
    "frequency_penalty": 0.4,
}


def _default_request(url: str, payload: dict) -> dict:
    r = requests.post(url, json={**payload, **_SAMPLING}, timeout=120)
    r.raise_for_status()
    return r.json()


class VoiceClient:
    """Stateless client around the llama-server chat-completions endpoint."""

    def __init__(
        self,
        *,
        url: str = "http://localhost:11434/v1/chat/completions",
        model: str = "qwen2.5:3b",
        request_fn: Optional[RequestFn] = None,
    ):
        self.url = url
        self.model = model
        self._request_fn = request_fn or _default_request

    def speak(self, req: VoiceRequest, beliefs: Optional[str] = None,
              belief_count: int = 0) -> VoiceResponse:
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
        raw_content = raw["choices"][0]["message"]["content"]
        # C3 2026-05-09: single-source strip; fallback_fired=True when cleaned
        # was empty and original deflection text was returned.
        text, deflection_fired = _strip_role_framing_with_status(raw_content)
        return VoiceResponse(
            text=text,
            register=req.register,
            raw=raw,
            deflection_fired=deflection_fired,
            deflection_user_mirror=(
                bool(_MIRROR_PHRASES.search(req.prompt)) if deflection_fired else False
            ),
            deflection_belief_count=belief_count,
            raw_llm_output=raw_content[:500] if deflection_fired else "",
        )

    def health_check(self) -> bool:
        """Return True if the voice endpoint is reachable."""
        try:
            self._request_fn(self.url, {
                "model": self.model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1,
            })
            return True
        except Exception:
            return False
