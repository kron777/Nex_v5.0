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
    # Direct stream→branch mappings always get proximity 1.0 — these are not
    # coincidental correlations, the stream IS the branch.
    direct: dict[str, float] = {}
    for prefix, bid in _STREAM_BRANCH.items():
        if stream.startswith(prefix):
            direct[bid] = 1.0
    if direct:
        results = [(b, direct.get(b, p)) for b, p in results]
        for bid, prox in direct.items():
            if bid not in {b for b, _ in results}:
                results.append((bid, prox))
    if not results:
        # fallback: match via stream name tokens only
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
    """Compute magnitude of a sense event for a given branch.

    Base of 0.35 for direct stream→branch mappings (stream prefix is definitive).
    Keyword bonus adds up to 0.65 more for each matching hint word.
    Stream name tokens are included in the token set so 'ai_research.arxiv'
    always contributes 'ai' and 'research' even when the title has no overlap.
    """
    if value is None:
        return 0.0

    # Guaranteed base for direct stream→branch mappings
    stream_prefix = stream.split(".")[0]
    direct_branch = (
        _STREAM_BRANCH.get(stream_prefix)
        or _STREAM_BRANCH.get(stream)
    )
    base = 0.35 if direct_branch == branch_id else 0.0

    # Text payload: combined stream + content token overlap against branch hints
    if isinstance(value, str):
        tokens = _extract_tokens(stream, value)
        hints = _CHANNEL_HINTS.get(branch_id, set())
        overlap = len(tokens & hints)
        keyword_bonus = min(0.65, overlap * 0.1)
        return min(1.0, base + keyword_bonus)

    # Numeric payload: delta-vs-scale logic
    if isinstance(value, (int, float)):
        scale = _DEFAULT_SCALE.get(stream, 1.0)
        return min(1.0, base + abs(float(value)) / max(1e-9, scale))

    return base
