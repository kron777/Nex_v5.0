"""
probe_set.py — Probe condition definitions and matrix generation.

A probe condition is a structured record describing one experimental
configuration. The runner instantiates each condition N times and
records the fountain outputs. Conditions are hashed for deduplication
and traceability.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass, asdict, field
from typing import Optional


# ---------------------------------------------------------------------------
# Vocabulary constants — the valid values for each dimension.
# ---------------------------------------------------------------------------

MODES = [
    "normal",    # empty focus_block, mundane drift
    "mind",      # self-referential focus, observer-register pull
    "market",    # outward-analytical, explicit "don't compose about yourself"
    "research",  # paper-connections register
    "news",      # framing/significance register
    "chat",      # minimal fountain, conversational
    "learn",     # novelty/discovery register
    "task",      # problem-stepping register
    "scribe",    # reflective accumulation, longer fragments
    "silent",    # fountain disabled — invalid for probing
]

SENSE_PATTERNS = [
    # What is flowing into the sense window at fire time.
    "crypto_only",       # only crypto/market feeds active
    "ai_research_only",  # only ai_research / emerging_tech feeds active
    "mixed_external",    # multiple external feeds active simultaneously
    "internal_only",     # only internal.* streams (no external events)
    "feed_quiet",        # no events in 5-min sense window
]

PRIOR_CONTEXTS = [
    # Template type of the most-recent fountain_insight belief in DB.
    "observer_saturated",   # prior N beliefs all ABSTRACT_NOMINAL or DIALECTICAL
    "action_saturated",     # prior N beliefs contain first-person action verbs
    "sense_saturated",      # prior N beliefs are SENSE_OBS or SIMILE referencing feeds
    "question_heavy",       # prior N beliefs skew to QUESTION template
    "mixed",                # no dominant template in recent priors
    "empty",                # no prior fountain_insight beliefs in DB yet
]

PROMPT_FRAMINGS = [
    "current",    # live _DRIFT_SYSTEM_PROMPT_TEMPLATE as deployed
    "no_focus",   # focus_block cleared (mode.drift_prompt_focus = "")
    "no_donot",   # DO NOT list removed from template
    "no_spectrum", # spectrum beliefs block omitted
    "minimal",    # system prompt reduced to one sentence + no ancillary context
]

FOUNDATION_TYPES = [
    "spectrum_random",   # 8 random spectrum beliefs as deployed
    "spectrum_process",  # 8 beliefs drawn only from process sub-corpus
    "spectrum_alpha",    # 8 beliefs drawn only from alpha sub-corpus
    "practice_only",     # 8 practice beliefs (action templates: "I right myself")
    "empty",             # no foundation block injected
]


# ---------------------------------------------------------------------------
# ProbeCondition — one cell in the probe matrix.
# ---------------------------------------------------------------------------

@dataclass
class ProbeCondition:
    """A single experimental configuration for one probe run."""

    mode: str
    sense_pattern: str
    prior_context: str
    prompt_framing: str = "current"
    foundation_type: str = "spectrum_random"
    n_reps: int = 5            # how many times to fire this condition
    notes: str = ""            # human-readable note for this condition

    def condition_hash(self) -> str:
        """Stable SHA-256 prefix over the five experimental dimensions."""
        key = json.dumps({
            "mode": self.mode,
            "sense_pattern": self.sense_pattern,
            "prior_context": self.prior_context,
            "prompt_framing": self.prompt_framing,
            "foundation_type": self.foundation_type,
        }, sort_keys=True)
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def as_dict(self) -> dict:
        return asdict(self)

    def label(self) -> str:
        return (f"{self.mode}|{self.sense_pattern}|{self.prior_context}"
                f"|{self.prompt_framing}|{self.foundation_type}")


# ---------------------------------------------------------------------------
# Small probe matrix — the initial 3×3×2 = 18 conditions.
# prompt_framing and foundation_type held at baseline.
# ---------------------------------------------------------------------------

SMALL_MATRIX_MODES = ["normal", "mind", "market"]
SMALL_MATRIX_SENSE = ["crypto_only", "ai_research_only", "feed_quiet"]
SMALL_MATRIX_PRIOR = ["observer_saturated", "mixed"]


def build_small_matrix(
    n_reps: int = 5,
    prompt_framing: str = "current",
    foundation_type: str = "spectrum_random",
) -> list[ProbeCondition]:
    """
    Returns the 18-condition baseline matrix:
      3 modes × 3 sense_patterns × 2 prior_contexts.
    Each condition will be run n_reps times → 90 total fires.
    """
    conditions: list[ProbeCondition] = []
    for mode, sense, prior in itertools.product(
        SMALL_MATRIX_MODES,
        SMALL_MATRIX_SENSE,
        SMALL_MATRIX_PRIOR,
    ):
        conditions.append(ProbeCondition(
            mode=mode,
            sense_pattern=sense,
            prior_context=prior,
            prompt_framing=prompt_framing,
            foundation_type=foundation_type,
            n_reps=n_reps,
        ))
    return conditions


# ---------------------------------------------------------------------------
# Expansion matrices — isolated single-dimension variation.
# ---------------------------------------------------------------------------

def build_framing_sweep(
    mode: str = "normal",
    sense_pattern: str = "ai_research_only",
    prior_context: str = "observer_saturated",
    n_reps: int = 5,
) -> list[ProbeCondition]:
    """
    Vary prompt_framing only. Holds mode/sense/prior constant.
    Tests whether removing focus_block, DO NOT list, or spectrum changes output.
    5 framings × 5 reps = 25 fires.
    """
    return [
        ProbeCondition(
            mode=mode,
            sense_pattern=sense_pattern,
            prior_context=prior_context,
            prompt_framing=framing,
            foundation_type="spectrum_random",
            n_reps=n_reps,
        )
        for framing in PROMPT_FRAMINGS
    ]


def build_foundation_sweep(
    mode: str = "normal",
    sense_pattern: str = "ai_research_only",
    prior_context: str = "observer_saturated",
    n_reps: int = 5,
) -> list[ProbeCondition]:
    """
    Vary foundation_type only. Tests whether what's in the foundation slot
    actually affects output register.
    5 foundation types × 5 reps = 25 fires.
    """
    return [
        ProbeCondition(
            mode=mode,
            sense_pattern=sense_pattern,
            prior_context=prior_context,
            prompt_framing="current",
            foundation_type=ft,
            n_reps=n_reps,
        )
        for ft in FOUNDATION_TYPES
    ]


def build_prior_sweep(
    mode: str = "normal",
    sense_pattern: str = "ai_research_only",
    n_reps: int = 5,
) -> list[ProbeCondition]:
    """
    Vary prior_context across all 6 values. Tests SUSTAIN vs SWITCH hypothesis.
    6 prior contexts × 5 reps = 30 fires.
    """
    return [
        ProbeCondition(
            mode=mode,
            sense_pattern=sense_pattern,
            prior_context=pc,
            prompt_framing="current",
            foundation_type="spectrum_random",
            n_reps=n_reps,
        )
        for pc in PRIOR_CONTEXTS
    ]


# ---------------------------------------------------------------------------
# Inventory utility.
# ---------------------------------------------------------------------------

def describe_matrix(conditions: list[ProbeCondition]) -> str:
    total_fires = sum(c.n_reps for c in conditions)
    lines = [
        f"Probe matrix: {len(conditions)} conditions × avg {total_fires // len(conditions)} reps"
        f" = {total_fires} total fires",
        "",
    ]
    for i, c in enumerate(conditions, 1):
        lines.append(
            f"  [{i:02d}] hash={c.condition_hash()} reps={c.n_reps}"
        )
        lines.append(f"       {c.label()}")
    return "\n".join(lines)


if __name__ == "__main__":
    matrix = build_small_matrix()
    print(describe_matrix(matrix))
