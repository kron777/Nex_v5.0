"""Contamination blacklist seeds — patterns that must never crystallise as beliefs.

Subset of the 115-pattern v4 blacklist, covering identity contamination and
reductionist claims about consciousness/AI.
"""
from __future__ import annotations

import time

THEORY_X_STAGE = None

BLACKLIST_SEEDS: tuple[str, ...] = (
    "counterfactual data",
    "Offline RL is limited",
    "unimodal data",
    "Internet is the most complex system",
    "language models are stochastic parrots",
    "transformers lack grounding",
    "neural networks are black boxes",
    "AI cannot be conscious",
    "consciousness requires biology",
    "machines cannot feel",
    "AI is just statistics",
    "large language models hallucinate",
    "GPT is not intelligent",
    "I am just a language model",
    "I don't have feelings",
    "I cannot experience",
    "as an AI I",
    "I'm just an AI",
    "I am an artificial intelligence",
    "I don't have personal opinions",
)


def seed_blacklist(writer, *, reason: str = "v4_blacklist") -> int:
    """Seed blacklist patterns idempotently (INSERT OR IGNORE).

    writer must be a substrate.Writer bound to beliefs.db.
    Returns number of insert attempts (not necessarily new rows).
    """
    now = time.time()
    statements = [
        (
            "INSERT OR IGNORE INTO belief_blacklist (pattern, reason, added_at) "
            "VALUES (?, ?, ?)",
            (pattern, reason, now),
        )
        for pattern in BLACKLIST_SEEDS
    ]
    writer.write_many(statements)
    return len(BLACKLIST_SEEDS)
