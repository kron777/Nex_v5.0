"""Attention — proximity matching and magnitude calculation.

Maps incoming sense events to branches and computes how much each
event should move branch focus.
"""
from __future__ import annotations

import json
from typing import Any, Optional

THEORY_X_STAGE = 2

_DEFAULT_SCALE: dict[str, float] = {
    "internal.proprioception": 1.0,
    "internal.temporal":       0.5,
    "internal.interoception":  0.8,
    "internal.meta_awareness": 0.9,
    # external defaults handled by keyword overlap
}

_CHANNEL_HINTS: dict[str, set[str]] = {
    "systems": {
        "self", "identity", "soul", "duration", "hour",
        "circadian", "cpu", "memory", "process", "substrate",
    },
    "ai_research": {
        "ai", "arxiv", "paper", "model", "llm", "neural",
        "learning", "research", "lab", "anthropic", "openai",
        "deepmind", "transformer", "conference", "benchmark",
    },
    "emerging_tech": {
        "tech", "invention", "robotics", "hardware", "chip",
        "hacker", "ieee", "mit", "emerging", "breakthrough",
    },
    "cognition_science": {
        "consciousness", "brain", "neuroscience", "mind",
        "philosophy", "cognition", "biorxiv", "frontiers",
        "philpapers", "perception", "awareness",
    },
    "computing": {
        "architecture", "distributed", "compute", "gpu",
        "cpu", "silicon", "semiconductor", "register",
        "ars", "anandtech",
    },
    "crypto": {
        "bitcoin", "ethereum", "crypto", "btc", "eth",
        "sol", "binance", "coinbase", "kraken", "coingecko",
        "defi", "blockchain", "market", "price",
    },
    "markets": {
        "market", "stock", "finance", "reuters", "ap",
        "bbc", "economy", "trade", "inflation",
    },
    "language": {
        "language", "narrative", "text", "word", "meaning",
        "discourse", "frame", "story",
    },
    "history": {
        "history", "historical", "past", "pattern",
        "century", "evolution", "arc",
    },
    "psychology": {
        "psychology", "behavior", "sentiment", "cognitive",
        "human", "social", "emotion", "decision",
    },
}

# Stream prefix → branch for internal streams
_STREAM_BRANCH: dict[str, str] = {
    "internal.proprioception": "systems",
    "internal.temporal":       "systems",
    "internal.interoception":  "systems",
    "internal.meta_awareness": "systems",
    "ai_research":             "ai_research",
    "emerging_tech":           "emerging_tech",
    "cognition":               "cognition_science",
    "computing":               "computing",
    "crypto":                  "crypto",
    "news":                    "markets",
}


def _proximity(tokens: set[str], branch_id: str) -> float:
    """Jaccard-style proximity between token set and branch hints."""
    hints = _CHANNEL_HINTS.get(branch_id, set())
    if not hints:
        return 0.0
    overlap = len(tokens & hints)
    return overlap / len(hints)


def _match_branches(stream: str, value: Any) -> list[tuple[str, float]]:
    """Return (branch_id, proximity) pairs for all branches above 0."""
    tokens = _extract_tokens(stream, value)
    results = []
    for branch_id in _CHANNEL_HINTS:
        p = _proximity(tokens, branch_id)
        if p > 0:
            results.append((branch_id, p))
    # Also try stream-prefix lookup for internal streams
    for prefix, branch_id in _STREAM_BRANCH.items():
        if stream.startswith(prefix) and branch_id not in {b for b, _ in results}:
            results.append((branch_id, 0.3))
    if not results:
        # fallback: match to best channel via stream name tokens
        stream_tokens = set(stream.replace(".", " ").split())
        for branch_id in _CHANNEL_HINTS:
            p = _proximity(stream_tokens, branch_id)
            if p > 0:
                results.append((branch_id, p))
    return results


def _extract_tokens(stream: str, value: Any) -> set[str]:
    """Extract lowercase word tokens from stream name and value."""
    tokens: set[str] = set()
    # stream name tokens
    for part in stream.replace(".", " ").replace("_", " ").split():
        tokens.add(part.lower())
    if value is None:
        return tokens
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                for k in ("title", "summary", "description", "source"):
                    v = parsed.get(k, "")
                    if v:
                        for word in str(v).lower().split():
                            tokens.add(word.strip(".,;:!?\"'()[]"))
        except (json.JSONDecodeError, TypeError):
            for word in value.lower().split():
                tokens.add(word.strip(".,;:!?\"'()[]"))
    elif isinstance(value, (int, float)):
        pass  # numeric only; no tokens
    return tokens


def _magnitude_for(stream: str, value: Any, branch_id: str) -> float:
    """Compute magnitude of a sense event for a given branch."""
    if value is None:
        return 0.0

    # Text payload: keyword-overlap magnitude
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            parsed = None

        if parsed is not None and isinstance(parsed, dict) and "title" in parsed:
            title = str(parsed.get("title", ""))
            title_tokens = set(t.lower().strip(".,;:!?\"'()[]") for t in title.split())
            hints = _CHANNEL_HINTS.get(branch_id, set())
            overlap = len(title_tokens & hints)
            return min(1.0, overlap / max(1, len(hints)))
        else:
            # raw text — token overlap vs hints
            hints = _CHANNEL_HINTS.get(branch_id, set())
            tokens = _extract_tokens(stream, value)
            overlap = len(tokens & hints)
            return min(1.0, overlap / max(1, len(hints)))

    # Numeric payload: delta-vs-scale logic
    if isinstance(value, (int, float)):
        scale = _DEFAULT_SCALE.get(stream, 1.0)
        return min(1.0, abs(float(value)) / max(1e-9, scale))

    return 0.0
