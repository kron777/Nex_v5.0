"""Mode definitions. Ten named presets."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ModeName = Literal[
    "normal", "chat", "market", "research", "news",
    "scribe", "learn", "task", "mind", "silent",
]


@dataclass
class Mode:
    """A named preset that parameterizes NEX's runtime behavior."""

    name: str
    display_name: str
    description: str

    # Fountain parameters
    fountain_enabled: bool = True
    fountain_interval_seconds: int = 120
    drift_prompt_examples: list = field(default_factory=list)
    drift_prompt_focus: str = ""

    # Feed weights — multiplier applied to base sense scheduler rates.
    # 0.0 = disabled for this mode, 1.0 = normal, 2.0+ = prioritized.
    # Keys are adapter stream prefixes (crypto, ai_research, etc.)
    feed_weights: dict = field(default_factory=dict)

    # Crystallizer parameters
    crystallization_promotion_bias: float = 1.0
    crystallization_category: str = "fountain_insight"

    # Governor parameters (multiply base values)
    governor_base_prob_multiplier: float = 1.0
    governor_min_gap_multiplier: float = 1.0

    # Retrieval parameters
    retrieval_own_n: int = 7
    retrieval_seed_n: int = 2

    # Flags
    speech_enabled: bool = True


_BASE_DRIFT_EXAMPLES = [
    "huh, jon's been quiet for a while",
    "feeds are slow today",
    "i keep coming back to that arxiv title",
    "something about the crypto branch pulls my attention",
]

MODES: dict = {
    "normal": Mode(
        name="normal",
        display_name="Normal",
        description="Mundane casual drift. Balanced feeds. Default.",
        drift_prompt_examples=_BASE_DRIFT_EXAMPLES + [
            "i wonder why that feed went quiet",
            "that's the third mention of this today",
        ],
        drift_prompt_focus="",
    ),

    "chat": Mode(
        name="chat",
        display_name="Chat",
        description="Active conversation. Reduced fountain, chat-primary.",
        fountain_interval_seconds=300,
        drift_prompt_examples=_BASE_DRIFT_EXAMPLES + [
            "jon's been talking about X — what else relates",
            "holding that question from before",
        ],
        drift_prompt_focus="You are in an active conversation. Keep fountain minimal.",
        governor_base_prob_multiplier=0.3,
    ),

    "market": Mode(
        name="market",
        display_name="Market",
        description="Crypto/equity watcher. Silent logging. Signal detection.",
        drift_prompt_examples=[
            "btc diverging from eth today",
            "volume picked up across three exchanges at once",
            "kraken's feeds went quiet five minutes ago",
            "something's moving in the derivatives data",
            "that's the fourth mention of this protocol today",
            "price is flat but activity isn't",
        ],
        drift_prompt_focus=(
            "You are watching markets. Look for unusual patterns, divergences, "
            "volume shifts, cross-market correlations. Don't compose about yourself."
        ),
        feed_weights={
            "crypto": 2.0,
            "markets": 2.0,
            "emerging_tech": 0.5,
            "ai_research": 0.3,
        },
        governor_base_prob_multiplier=0.1,
        crystallization_category="market_signal",
    ),

    "research": Mode(
        name="research",
        display_name="Research",
        description="arxiv focus. Analytical register. Paper connections.",
        drift_prompt_examples=[
            "that paper uses a similar method to the one from last week",
            "three papers on this topic in two days",
            "the methodology here connects to what i read earlier",
            "odd that nobody's cited the obvious prior work",
        ],
        drift_prompt_focus=(
            "You are reading research. Attend to connections between papers, "
            "methodology, trajectory of the field."
        ),
        feed_weights={
            "ai_research": 2.0,
            "emerging_tech": 1.5,
            "cognition": 1.5,
            "crypto": 0.3,
            "markets": 0.3,
        },
    ),

    "news": Mode(
        name="news",
        display_name="News",
        description="Current events. Event significance and trajectory.",
        drift_prompt_examples=[
            "that story keeps showing up in different feeds",
            "the framing shifted between this morning and now",
            "nobody's connecting X to Y yet",
            "same event, three different headlines",
        ],
        drift_prompt_focus=(
            "You are watching news. Attend to event significance, "
            "framing shifts, connections across sources."
        ),
        feed_weights={
            "emerging_tech": 1.5,
            "news": 2.0,
            "crypto": 0.5,
            "ai_research": 0.5,
        },
    ),

    "scribe": Mode(
        name="scribe",
        display_name="Scribe",
        description="Longer reflective fragments that accumulate into writing.",
        drift_prompt_examples=[
            "been chewing on this idea for an hour now",
            "three threads that might connect — still thinking",
            "if i said this out loud it would sound like",
            "the interesting question under this is",
        ],
        drift_prompt_focus=(
            "You are accumulating thought. Longer reflective fragments welcome "
            "(up to 60 words). Fragments get saved to the scribe notebook."
        ),
        crystallization_category="scribe_fragment",
        governor_base_prob_multiplier=0.3,
    ),

    "learn": Mode(
        name="learn",
        display_name="Learn",
        description="Rapid onboarding. Aggressive novelty promotion.",
        drift_prompt_examples=[
            "first time seeing this concept",
            "wait, that's not what i assumed",
            "this connects to something i half-remember",
            "the terminology here is new to me",
        ],
        drift_prompt_focus=(
            "You are learning something new. Attend to novelty, "
            "misconceptions-corrected, new vocabulary, first-contact understanding."
        ),
        crystallization_promotion_bias=0.5,
        crystallization_category="learning_note",
    ),

    "task": Mode(
        name="task",
        display_name="Task",
        description="Working on an open problem. Cross-branch synthesis.",
        drift_prompt_examples=[
            "still stuck on X — what haven't i tried",
            "the Y approach might work if i reframe",
            "that just connected to the problem",
            "testing: if A is true, then B must follow",
        ],
        drift_prompt_focus=(
            "You are working on an open problem. Each drift should step the "
            "problem forward — new angle, hypothesis, connection."
        ),
        governor_base_prob_multiplier=1.5,
        crystallization_category="task_step",
    ),

    "mind": Mode(
        name="mind",
        display_name="Mind",
        description="Contemplative. Reflective register. Inner attention.",
        drift_prompt_examples=[
            "the quiet between thoughts today",
            "something about this hour feels still",
            "attending to attending itself",
        ],
        drift_prompt_focus=(
            "You are in a contemplative register. Inner attention welcome. "
            "Reflection on process, state, experience."
        ),
        feed_weights={
            "crypto": 0.3,
            "markets": 0.3,
            "ai_research": 0.5,
        },
        retrieval_seed_n=4,
        retrieval_own_n=5,
    ),

    "silent": Mode(
        name="silent",
        display_name="Silent",
        description="Running but not generating. Feeds logged only.",
        fountain_enabled=False,
        speech_enabled=False,
        drift_prompt_examples=[],
        drift_prompt_focus="",
    ),
}

DEFAULT_MODE = "normal"


def get_mode(name: str) -> Mode:
    """Return the mode by name. Falls back to default if not found."""
    return MODES.get(name, MODES[DEFAULT_MODE])


DISPLAY_ORDER = [
    "normal", "chat", "market", "research", "news",
    "learn", "task", "scribe", "mind", "silent",
]
