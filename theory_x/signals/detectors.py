"""Signal detectors — LLM-free structural pattern detection."""
from __future__ import annotations

import re
import time
import logging
from collections import defaultdict
from dataclasses import dataclass

logger = logging.getLogger("theory_x.signals")

# Stopwords filtered out of capitalized-word entity extraction
_ENTITY_STOPWORDS = frozenset({
    "the", "this", "that", "when", "where", "why", "how", "what", "who",
    "and", "but", "for", "with", "from", "into", "onto", "upon",
})


@dataclass
class Signal:
    detector_name: str
    signal_type: str
    payload: dict
    branches: list
    entities: list
    confidence: float


class CoOccurrenceDetector:
    """Detects when the same entity appears across multiple branches within a window."""

    def __init__(self, beliefs_reader, window_seconds: int = 1800,
                 min_branches: int = 2):
        self._reader = beliefs_reader
        self._window = window_seconds
        self._min_branches = min_branches

    def detect(self) -> list[Signal]:
        now = time.time()
        rows = self._reader.read(
            "SELECT content, branch_id FROM beliefs "
            "WHERE created_at > ? AND branch_id IS NOT NULL "
            "AND source NOT IN ('koan','tao','dont_know','keystone_seed','alpha') "
            "LIMIT 500",
            (now - self._window,),
        )
        if not rows:
            return []

        branch_entities: dict[str, set] = defaultdict(set)
        for r in rows:
            content = r["content"] or ""
            branch = r["branch_id"]
            for w in re.findall(r"\b[A-Z][a-zA-Z]{2,}\b", content):
                if w.lower() not in _ENTITY_STOPWORDS:
                    branch_entities[branch].add(w)

        entity_branches: dict[str, set] = defaultdict(set)
        for branch, entities in branch_entities.items():
            for ent in entities:
                entity_branches[ent].add(branch)

        signals = []
        for entity, branches in entity_branches.items():
            if len(branches) >= self._min_branches:
                signals.append(Signal(
                    detector_name="co_occurrence",
                    signal_type=f"{len(branches)}_branch",
                    payload={
                        "entity": entity,
                        "branches": sorted(branches),
                        "window_seconds": self._window,
                    },
                    branches=sorted(branches),
                    entities=[entity],
                    confidence=min(0.3 + 0.2 * len(branches), 0.95),
                ))
        return signals


class SilenceDetector:
    """Detects when a normally-active stream has gone quiet for N × its typical gap."""

    def __init__(self, sense_reader, silence_multiplier: float = 3.0,
                 min_history_events: int = 5):
        self._reader = sense_reader
        self._multiplier = silence_multiplier
        self._min_history = min_history_events

    def detect(self) -> list[Signal]:
        now = time.time()
        rows = self._reader.read(
            "SELECT stream, timestamp FROM sense_events "
            "WHERE timestamp > ? AND stream NOT LIKE 'internal.%' "
            "ORDER BY timestamp ASC",
            (now - 3600,),
        )
        if not rows:
            return []

        by_stream: dict[str, list] = defaultdict(list)
        for r in rows:
            by_stream[r["stream"]].append(r["timestamp"])

        signals = []
        for stream, timestamps in by_stream.items():
            if len(timestamps) < self._min_history:
                continue
            gaps = [timestamps[i + 1] - timestamps[i]
                    for i in range(len(timestamps) - 1)]
            if not gaps:
                continue
            avg_gap = sum(gaps) / len(gaps)
            if avg_gap <= 0:
                continue
            current_silence = now - timestamps[-1]
            if current_silence > self._multiplier * avg_gap:
                ratio = current_silence / avg_gap
                signals.append(Signal(
                    detector_name="silence",
                    signal_type="branch_silence_anomaly",
                    payload={
                        "stream": stream,
                        "avg_gap_seconds": avg_gap,
                        "current_silence_seconds": current_silence,
                        "multiplier_breach": ratio,
                    },
                    branches=[stream],
                    entities=[],
                    confidence=min(0.3 + 0.1 * (ratio - self._multiplier), 0.9),
                ))
        return signals


class BurstDetector:
    """Detects when many beliefs reach T6 within a short window."""

    def __init__(self, beliefs_reader, window_seconds: int = 900,
                 burst_threshold: int = 3):
        self._reader = beliefs_reader
        self._window = window_seconds
        self._threshold = burst_threshold

    def detect(self) -> list[Signal]:
        now = time.time()
        rows = self._reader.read(
            "SELECT COUNT(*) AS n, GROUP_CONCAT(branch_id, ',') AS branches "
            "FROM beliefs WHERE tier = 6 AND created_at > ?",
            (now - self._window,),
        )
        if not rows:
            return []
        n = rows[0]["n"] or 0
        if n < self._threshold:
            return []

        branches_raw = rows[0]["branches"] or ""
        branches = list({b for b in branches_raw.split(",") if b})

        return [Signal(
            detector_name="burst",
            signal_type="t6_promotion_burst",
            payload={
                "promotions": n,
                "window_seconds": self._window,
                "branches": branches,
            },
            branches=branches,
            entities=[],
            confidence=min(0.4 + 0.1 * (n - self._threshold), 0.9),
        )]
