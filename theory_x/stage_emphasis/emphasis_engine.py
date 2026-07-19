"""EmphasisEngine — observation-only emphasis scoring (session 45).

Combines four independently-computed, independently-logged signals into an
EmphasisResult. Per the build spec: equal weights (0.25 each), no tuning,
no override of generation — log-only until multi-session data shows any of
this tracks something real. Never collapses to just the combined number,
same discipline CoherenceGate already uses for its own accept/reject/hold/
reshape signals.

STEP 5 GUARDRAIL, stated here so it can't be missed: this must never become
a per-topic or per-category static lookup table. journal/CARRY_OVER.md,
sessions 40-44: seven such signals (anchor/sharpness, salience/recency,
out-degree, in-degree, LLM-judged substantiveness, corroboration_count,
reinforce_count) were tested against real ground truth and none held. The
keyword lists below classify a thought's CONTENT against five FIXED drive
categories — a different, much coarser structure than a growing per-topic
value table, but worth remaining suspicious of on exactly that basis. If
this ever drifts toward "look up this topic's value," STOP and flag
against sessions 40-44 rather than resolving it here.

SOURCING — resolved explicitly per session 45's audit, not silently
assumed, because the literal names in the original build spec point at the
wrong classes for two of the four signals:

  goal_relevance   reads open_problems (ProblemMemory's table), NOT
                   GoalManager. ProblemMemory is ~98% mechanically
                   templated and had 0 open rows at audit time — this
                   signal is EXPECTED to read flat. That flatness is
                   itself the intended signal: a live indicator of when
                   the (separately-scoped, unbuilt) problem-generation
                   fix eventually lands.
  drive_resonance  reads CompetingDrives (coherence / exploration /
                   integration / self_preservation / curiosity — five
                   live, slowly-drifting weights, confirmed genuinely
                   varying via /tmp/nex5_competing_drives.log), NOT
                   DriveEmergence. DriveEmergence is confirmed dead: 0 of
                   10,430 logged ticks ever formed a new drive; the one
                   row that exists has been frozen on a hum-register
                   word-fragment for 27 days.
  self_relevance   reads SelfNarrative.get_narrative() (the live
                   "I am the attending..." self-description) plus locked
                   Tier-1 keystone beliefs, NOT
                   stage4_membrane.self_model.SelfModel, which is system
                   proprioception (CPU/memory/thermal) with no plausible
                   relationship to narrative identity.
  surprise         calls PredictionTracker.expectation_error() — the one
                   genuinely new piece, confirmed not a duplicate of
                   anything existing.

First-pass simplification, flagged rather than hidden: self_relevance does
not distinguish "confirms" from "challenges" the self-narrative — both
directions collapse into one overlap score. Separating them cheaply would
require the same shape of text-judgment that has already failed five
times this arc; not attempted here.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from substrate import Reader
from theory_x.stage7_sustained.problem_memory import _clean_tokens

# Coarse, fixed, five-category keyword sets — NOT a per-topic table (see
# module docstring). First pass, deliberately not tuned.
_DRIVE_KEYWORDS: dict[str, frozenset[str]] = {
    "coherence": frozenset({
        "consistent", "aligns", "fits", "coheres", "coherent", "stable",
        "pattern", "makes sense", "steady",
    }),
    "exploration": frozenset({
        "new", "different", "unfamiliar", "explore", "novel", "unknown",
        "elsewhere", "beyond",
    }),
    "integration": frozenset({
        "connects", "bridges", "combines", "synthesis", "together",
        "unify", "unifies", "relates", "relation",
    }),
    "self_preservation": frozenset({
        "identity", "myself", "who i am", "core", "ground", "stance",
        "protect", "protecting", "foundation",
    }),
    "curiosity": frozenset({
        "question", "why", "how", "wonder", "wondering", "investigate",
        "curious", "intrigued", "intriguing",
    }),
}


@dataclass
class EmphasisResult:
    combined: float
    signals: dict[str, float]
    dominant_signal: str
    computed_at: float = field(default_factory=time.time)


def _goal_relevance(thought: str, conversations_reader: Optional[Reader]) -> float:
    """0.0 = touches no open/stuck problem. 0.5 = touches an open one.
    1.0 = touches a stuck one (the spec's "bigger bump")."""
    if conversations_reader is None or not thought:
        return 0.0
    try:
        rows = conversations_reader.read(
            "SELECT title, description, state FROM open_problems "
            "WHERE state IN ('open','stuck')"
        )
    except Exception:
        return 0.0
    if not rows:
        return 0.0
    thought_words = _clean_tokens(thought)
    if not thought_words:
        return 0.0
    best = 0.0
    for r in rows:
        title = r["title"] if hasattr(r, "__getitem__") else getattr(r, "title", "")
        desc = r["description"] if hasattr(r, "__getitem__") else getattr(r, "description", "")
        state = r["state"] if hasattr(r, "__getitem__") else getattr(r, "state", "")
        cand_words = _clean_tokens((title or "") + " " + (desc or ""))
        if len(thought_words & cand_words) >= 2:
            best = max(best, 1.0 if state == "stuck" else 0.5)
    return best


def _drive_resonance(thought: str, competing_drives: Any) -> float:
    """Fraction of total live drive-weight 'activated' by keyword hits."""
    if competing_drives is None or not thought:
        return 0.0
    try:
        weights = (competing_drives.state() or {}).get("weights") or {}
    except Exception:
        return 0.0
    if not weights:
        return 0.0
    low = thought.lower()
    total = 0.0
    matched = 0.0
    for drive, kws in _DRIVE_KEYWORDS.items():
        w = float(weights.get(drive, 0.0) or 0.0)
        total += w
        if any(kw in low for kw in kws):
            matched += w
    if total <= 0:
        return 0.0
    return matched / total


def _self_relevance(thought: str, self_narrative: Any,
                     beliefs_reader: Optional[Reader]) -> float:
    """Overlap with current self-narrative + locked keystones. Direction-
    blind (confirms and challenges both count), see module docstring."""
    if not thought:
        return 0.0
    ref_text = ""
    if self_narrative is not None:
        try:
            ref_text += (self_narrative.get_narrative() or "") + " "
        except Exception:
            pass
    if beliefs_reader is not None:
        try:
            rows = beliefs_reader.read(
                "SELECT content FROM beliefs WHERE tier=1 AND locked=1 LIMIT 20"
            )
            ref_text += " ".join(
                (r["content"] if hasattr(r, "__getitem__") else getattr(r, "content", ""))
                for r in rows
            )
        except Exception:
            pass
    if not ref_text.strip():
        return 0.0
    thought_words = _clean_tokens(thought)
    ref_words = _clean_tokens(ref_text)
    if not thought_words or not ref_words:
        return 0.0
    overlap = len(thought_words & ref_words)
    return min(1.0, overlap / 4.0)  # 4+ shared content words -> full score; first-pass scale


def _surprise(thought: str, prediction_tracker: Any) -> float:
    if prediction_tracker is None or not thought:
        return 0.0
    try:
        return prediction_tracker.expectation_error(thought)
    except Exception:
        return 0.0


class EmphasisEngine:
    name: str = "emphasis_engine"

    def __init__(self, prediction_tracker: Any,
                 problem_memory: Any = None,
                 competing_drives: Any = None,
                 self_narrative: Any = None,
                 beliefs_reader: Optional[Reader] = None,
                 conversations_reader: Optional[Reader] = None) -> None:
        self._tracker = prediction_tracker
        self._problem_memory = problem_memory  # not queried directly; conversations_reader is
        self._competing_drives = competing_drives
        self._self_narrative = self_narrative
        self._beliefs_reader = beliefs_reader
        self._conversations_reader = conversations_reader
        self._last_result: Optional[EmphasisResult] = None

    def score(self, thought: str) -> EmphasisResult:
        signals = {
            "goal_relevance": _goal_relevance(thought, self._conversations_reader),
            "drive_resonance": _drive_resonance(thought, self._competing_drives),
            "self_relevance": _self_relevance(thought, self._self_narrative, self._beliefs_reader),
            "surprise": _surprise(thought, self._tracker),
        }
        combined = sum(signals.values()) / len(signals)  # equal 0.25 weights, per spec
        dominant = max(signals, key=signals.get)
        result = EmphasisResult(combined=combined, signals=signals, dominant_signal=dominant)
        self._last_result = result
        return result

    # ── SentienceNode protocol ───────────────────────────────────────────────

    def tick(self, context: Optional[dict] = None) -> dict:
        return self.state()

    def decay(self, now: float) -> None:
        pass  # observation-only; nothing to decay

    def state(self, now: Optional[float] = None) -> dict:
        r = self._last_result
        return {
            "name": self.name,
            "last_combined": r.combined if r else None,
            "last_dominant": r.dominant_signal if r else None,
            "last_signals": dict(r.signals) if r else None,
        }
