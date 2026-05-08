"""executive_control.py — Executive Control node (Theory X port, DOCTRINE §5 #3).

Heuristic register classifier with session-continuity bias (Option D,
EXEC_CONTROL_DESIGN.md, approved 2026-05-08).

Replaces the classify() stub in voice/registers.py. Membrane's
Philosophical override remains authoritative and is NOT touched here.

Standalone module; no other theory_x imports. stdlib only.

Decision tree:
  1. Score prompt against Analytical and Technical signal sets.
  2. Apply session-continuity bias: boost last register by CONTINUITY_WEIGHT.
  3. Pick highest-scoring register above its threshold.
  4. Tie or insufficient signal → Conversational (floor).
  5. Any exception → Conversational (identical to stub behaviour).

Membrane's Philosophical override in gui/server.py:512-515 fires AFTER
this classifier and replaces its output. This module never returns
PHILOSOPHICAL.
"""
from __future__ import annotations

import re
import threading
import time
from typing import Optional

__all__ = ["ExecutiveControl"]

# ── tunable constants ─────────────────────────────────────────────────────────

_ANALYTICAL_THRESHOLD = 0.28   # 2 keywords (2×0.15=0.30) clears this; single-keyword (0.15) does not
_TECHNICAL_THRESHOLD  = 0.28   # same rationale; strong-pattern override floors at 0.36
_CONTINUITY_WEIGHT    = 0.15   # boost for previous session register

# ── signal sets ───────────────────────────────────────────────────────────────
# Substring matching: every keyword is checked via `kw in lower_prompt`.
# This handles plurals, compounds, and variations without stemming.

# Analytical: quantitative, financial, market, cross-domain synthesis
_ANALYTICAL_KEYWORDS = (
    # financial instruments / markets
    "bitcoin", "btc", "eth", "ethereum", "crypto", "cryptocurrency",
    "stock", "stocks", "market", "markets", "portfolio", "equity",
    "price", "prices",
    "yield", "yields", "bond", "bonds", "treasury", "fed funds",
    "interest rate", "inflation", "gdp", "recession",
    "overvalued", "undervalued", "momentum", "volatility",
    "trade volume", "liquidity",
    # quantitative / data
    "correlation", "correlates", "regression", "distribution",
    "probability", "bayesian", "forecast", "prediction",
    "statistical", "significance", "variance", "deviation",
    "data", "dataset", "metrics", "metric", "ratio", "ratios",
    "percent", "percentage", "basis points",
    "trend", "trends", "pattern", "patterns",
    # analysis verbs (financial context)
    "analyze", "analyse", "analysis", "evaluated", "evaluate",
    "compare returns", "compare prices", "benchmark",
    "cross-domain", "cross domain", "synthesis across",
)

_ANALYTICAL_PATTERNS = re.compile(
    r"""
    \b\d+\.?\d*\s*%           |   # percentage: 12.5%
    \$\s*\d[\d,]*             |   # dollar: $42 or $1,200
    \d+\s*(bps|bp)\b          |   # basis points: 25bps
    \bhow\s+much\b            |   # how much...
    \bhow\s+many\b            |   # how many...
    \bwhat\s+(is|are|'?s)\s+the\s+(price|cost|rate|value|return|yield)\b  |
    \bwhat\s+percent\b        |
    \bover\s+the\s+(last|past)\b   # time-series framing
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Technical: mechanism explanations, code, implementation, architecture
_TECHNICAL_KEYWORDS = (
    # languages + tools
    "python", "javascript", "typescript", "rust", "golang", "c++", "java",
    "sql", "nosql", "postgres", "redis", "docker", "kubernetes", "git",
    "api", "rest", "graphql", "grpc", "http", "tcp", "udp", "tls",
    # CS concepts
    "algorithm", "algorithms", "complexity", "big o", "big-o",
    "data structure", "hash table", "hashtable", "linked list",
    "binary tree", "heap", "stack overflow", "call stack",
    "mutex", "semaphore", "deadlock", "race condition", "concurrency", "concurrent",
    "multithreaded", "asynchronous", "async", "await",
    "memory leak", "garbage collection", "pointer",
    "neural network", "transformer", "backpropagation", "gradient",
    "embedding", "tokenizer", "attention mechanism",
    "lru cache", "cache invalidation",
    # ML / AI technical
    "fine-tuning", "fine tuning", "qlora", "lora", "inference",
    "quantization", "perplexity", "loss function",
    # architecture / systems
    "architecture", "microservice", "monolith", "distributed system",
    "load balancer", "message queue", "event-driven",
    "latency", "throughput", "bandwidth", "scalability",
    "infrastructure", "deployment", "ci/cd",
    # explanation vocabulary
    "mechanism", "mechanisms", "under the hood", "step by step",
    "step-by-step", "deep dive", "deep-dive", "in detail",
    "walk me through", "pros and cons", "trade-off", "tradeoff",
)

_TECHNICAL_PATTERNS = re.compile(
    r"""
    \bhow\s+does\s+(?:\S+\s+)+work\b       |   # "how does X work" (multi-word subject OK)
    \bhow\s+do\s+(?:\S+\s+)+work\b         |   # "how do Xs work" (multi-word subject OK)
    \bexplain\s+(how|what|why|the)\b       |   # "explain how/what/why/the"
    \bexplain\s+\w+                        |   # "explain X" (standalone explain)
    \bwhat\s+is\s+the\s+difference\b       |   # "what is the difference"
    \bwhat['']?s\s+the\s+difference\b      |   # "what's the difference"
    \bwhat\s+is\s+(a|an|the)\s+\w+\b       |   # "what is a/an/the X" (definition)
    \bimplement\w*\b                       |   # implement/implementation/implemented
    \bstep[- ]by[- ]step\b                |
    \bin\s+detail\b                       |
    \bwalk\s+(?:me\s+)?through\b           |
    \bhow\s+(?:would\s+you\s+)?(?:build|write|code|implement)\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Strong Technical signals that alone justify a Technical classification.
# These are patterns where the query intent is unambiguously mechanical/explanatory.
_TECHNICAL_STRONG = re.compile(
    r"""
    \bhow\s+does\s+(?:\S+\s+)+work\b      |   # mechanism question (multi-word subject OK)
    \bhow\s+do\s+(?:\S+\s+)+work\b        |
    \bexplain\s+how\b                     |   # "explain how X"
    \bwhat\s+is\s+the\s+difference\b      |   # comparison
    \bwhat['']?s\s+the\s+difference\b     |
    \bstep[- ]by[- ]step\b               |   # walkthrough request
    \bwalk\s+(?:me\s+)?through\b          |
    \bthe\s+algorithm\b                   |   # specific algorithm reference
    \balgorithm\s+(?:for|behind|to)\b     |   # "algorithm for/behind/to X"
    \bimplement\s                         |   # "implement X" (verb, not noun-like)
    \bunder\s+the\s+hood\b
    """,
    re.IGNORECASE | re.VERBOSE,
)


class ExecutiveControl:
    """Heuristic register classifier with session-continuity bias.

    Process-lifetime singleton. Thread-safe.

    Implements SentienceNode protocol (DOCTRINE §4):
      name, tick(context), decay(now), state(now=None)
    """

    name: str = "executive_control"

    def __init__(self, registers=None) -> None:
        # `registers` accepted for API symmetry with other nodes; scoring is
        # keyword-driven and does not iterate this tuple at runtime.
        self._registers = registers
        self._lock = threading.Lock()
        self._session_registers: dict[str, str] = {}
        self._call_count: int = 0
        self._register_counts: dict[str, int] = {
            "Analytical": 0, "Technical": 0, "Conversational": 0
        }

    # ── public API ────────────────────────────────────────────────────────────

    def select(
        self,
        prompt: str,
        session_id: Optional[str] = None,
    ) -> "Register":  # type: ignore[name-defined]  # avoid circular import
        """Classify prompt to register. Thread-safe. Never raises.

        Returns a Register object from voice.registers.
        """
        from voice.registers import ANALYTICAL, TECHNICAL, CONVERSATIONAL
        try:
            scores = self._score_prompt(prompt)
            if session_id:
                scores = self._apply_continuity_bias(scores, session_id)
            register = self._pick(scores, ANALYTICAL, TECHNICAL, CONVERSATIONAL)
            with self._lock:
                self._call_count += 1
                self._register_counts[register.name] = (
                    self._register_counts.get(register.name, 0) + 1
                )
                if session_id:
                    self._session_registers[session_id] = register.name
            return register
        except Exception:
            from voice.registers import CONVERSATIONAL as _C
            return _C

    def dry_run(self, prompt: str, session_id: Optional[str] = None) -> dict:
        """Classify and return full scoring detail without updating session state."""
        from voice.registers import ANALYTICAL, TECHNICAL, CONVERSATIONAL
        scores = self._score_prompt(prompt)
        biased_scores = self._apply_continuity_bias(scores, session_id) if session_id else scores
        register = self._pick(biased_scores, ANALYTICAL, TECHNICAL, CONVERSATIONAL)
        return {
            "prompt": prompt[:80],
            "raw_scores": {k: round(v, 4) for k, v in scores.items()},
            "biased_scores": {k: round(v, 4) for k, v in biased_scores.items()},
            "last_register": self._session_registers.get(session_id) if session_id else None,
            "result": register.name,
        }

    # ── SentienceNode protocol ────────────────────────────────────────────────

    def tick(self, context: Optional[dict] = None) -> dict:
        return self.state()

    def decay(self, now: float) -> None:
        pass  # event-driven; session state doesn't decay on a clock

    def state(self, now: Optional[float] = None) -> dict:
        with self._lock:
            return {
                "name": self.name,
                "call_count": self._call_count,
                "register_counts": dict(self._register_counts),
                "active_sessions": len(self._session_registers),
            }

    # ── internals ─────────────────────────────────────────────────────────────

    def _score_prompt(self, prompt: str) -> dict[str, float]:
        """Score prompt against register signal sets. Returns raw scores.

        Keyword matching: substring search on lowercased prompt.
        Handles plurals, compounds, and hyphenated forms without stemming.
        Pattern matching: compiled regex, higher weight per hit.
        """
        lower = prompt.lower()

        # Analytical: each keyword hit = 0.15; each pattern hit = 0.20
        a_hits = sum(1 for kw in _ANALYTICAL_KEYWORDS if kw in lower)
        a_pat = len(_ANALYTICAL_PATTERNS.findall(prompt))
        a_raw = min(1.0, (a_hits * 0.15) + (a_pat * 0.20))

        # Technical: keyword hits + pattern hits + strong-pattern override
        t_hits = sum(1 for kw in _TECHNICAL_KEYWORDS if kw in lower)
        t_pat = len(_TECHNICAL_PATTERNS.findall(prompt))
        t_raw = min(1.0, (t_hits * 0.15) + (t_pat * 0.20))
        # Strong patterns unambiguously signal Technical — floor at threshold
        if _TECHNICAL_STRONG.search(prompt):
            t_raw = max(t_raw, _TECHNICAL_THRESHOLD + 0.01)

        # Conversational floor: starts at 0.30; wins when signal is absent
        c_raw = 0.30

        return {"Analytical": a_raw, "Technical": t_raw, "Conversational": c_raw}

    def _apply_continuity_bias(
        self, scores: dict[str, float], session_id: Optional[str]
    ) -> dict[str, float]:
        """Boost the previous session register by CONTINUITY_WEIGHT."""
        if not session_id:
            return scores
        last = self._session_registers.get(session_id)
        if not last or last not in scores:
            return scores
        biased = dict(scores)
        biased[last] = min(1.0, biased[last] + _CONTINUITY_WEIGHT)
        return biased

    def _pick(
        self, scores: dict[str, float], ANALYTICAL, TECHNICAL, CONVERSATIONAL
    ):
        """Pick register from scores. Thresholds: Analytical/Technical at 0.45."""
        a = scores.get("Analytical", 0.0)
        t = scores.get("Technical", 0.0)

        if a >= _ANALYTICAL_THRESHOLD and a >= t:
            return ANALYTICAL
        if t >= _TECHNICAL_THRESHOLD and t > a:
            return TECHNICAL
        return CONVERSATIONAL
