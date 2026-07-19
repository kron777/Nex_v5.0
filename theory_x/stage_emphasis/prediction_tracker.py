"""PredictionTracker — short-horizon expectation over her own recent trajectory.

SentienceNode (DOCTRINE §4). Session 45's audit confirmed this is genuinely
missing: existing "surprise" machinery (global_workspace's prediction-
violation arbitration; surprise_events/predictive_substrate.py) is tied to
specific market/behavioral predictions (prediction_id, prediction_type) —
nothing tracks expectation over arbitrary belief-graph content. This does,
cheaply. It is the THIRD thing in this codebase named around "surprise" —
deliberately not reusing that word in its own vocabulary (calls its output
`expectation_error`) so logs and code don't collide with the other two.

DESIGN CHOICES, flagged per the build spec's own instruction rather than
silently picked:
  - Representation: the "recent vocabulary" is the union of capitalized-
    entity extractions (same regex + stopword filter as
    theory_x.signals.detectors.CoOccurrenceDetector — reused, not
    reinvented) over the last N real fountain_events.thought values.
  - No new table, no persisted state: computed fresh from fountain_events
    on every call. Same "no schema churn" choice made for the
    memory-with-decay design in session 44 — always derived from ground
    truth, nothing to go stale or get out of sync.
  - N = 20 fires (~50 min at the live ~2.5min/fire cadence). Small, round,
    a first-pass choice, not tuned.
  - expectation_error(thought) = fraction of the candidate thought's own
    entities that do NOT appear anywhere in the last N fires' vocabulary.
    0.0 = every entity already present recently (fully expected
    continuation, or a thought with no extractable entities at all).
    1.0 = every entity is new. This is a coarse novelty proxy over a
    crude entity extraction, not a probabilistic sequence model — flagged
    as exactly that, not dressed up as more.
  - decay() is a no-op: nothing is persisted between calls, matching the
    pattern already used by FocalSet and CompetingDrives for tick-based
    (not wall-clock) state.
"""
from __future__ import annotations

import re
import time
from typing import Optional

from substrate import Reader

_ENTITY_STOPWORDS = frozenset({
    "the", "this", "that", "when", "where", "why", "how", "what", "who",
    "and", "but", "for", "with", "from", "into", "onto", "upon",
})
_ENTITY_RE = re.compile(r"\b[A-Z][a-zA-Z]{2,}\b")


def _entities(text: Optional[str]) -> set[str]:
    if not text:
        return set()
    out: set[str] = set()
    for m in _ENTITY_RE.finditer(text):
        w = m.group()
        if w.lower() not in _ENTITY_STOPWORDS:
            out.add(w)
    return out


class PredictionTracker:
    name: str = "prediction_tracker"

    def __init__(self, dynamic_reader: Reader, window_n: int = 20) -> None:
        self._reader = dynamic_reader
        self.window_n = window_n
        self._last_vocab_size: int = 0
        self._last_computed_at: float = 0.0

    def _recent_vocabulary(self) -> set[str]:
        try:
            rows = self._reader.read(
                "SELECT thought FROM fountain_events WHERE thought != '' "
                "ORDER BY id DESC LIMIT ?",
                (self.window_n,),
            )
        except Exception:
            return set()
        vocab: set[str] = set()
        for r in rows:
            t = r["thought"] if hasattr(r, "__getitem__") else getattr(r, "thought", "")
            vocab |= _entities(t)
        return vocab

    def expectation_error(self, thought: str) -> float:
        """0.0 = fully expected given recent trajectory, 1.0 = fully novel."""
        cand = _entities(thought)
        if not cand:
            return 0.0
        vocab = self._recent_vocabulary()
        self._last_vocab_size = len(vocab)
        self._last_computed_at = time.time()
        novel = sum(1 for e in cand if e not in vocab)
        return novel / len(cand)

    # ── SentienceNode protocol ───────────────────────────────────────────────

    def tick(self, context: Optional[dict] = None) -> dict:
        return self.state()

    def decay(self, now: float) -> None:
        pass  # nothing persisted; see module docstring

    def state(self, now: Optional[float] = None) -> dict:
        return {
            "name": self.name,
            "window_n": self.window_n,
            "last_vocab_size": self._last_vocab_size,
            "last_computed_at": self._last_computed_at,
        }
