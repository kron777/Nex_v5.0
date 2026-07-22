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
        # census #13 fix: re-scanning an unchanged rolling window re-derives
        # the same entity/branch-set every tick and re-emitted it as a "new"
        # signal every time. Fingerprint = sorted(branches) per entity;
        # skip emitting when unchanged from the last tick that DID emit for
        # that entity. Resets on restart (in-memory, per instance) -- one
        # fresh emission after a restart is honest, not spam.
        self._last_branches: dict[str, tuple] = {}

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
        entity_contexts: dict[str, list] = defaultdict(list)
        for r in rows:
            content = r["content"] or ""
            branch = r["branch_id"]
            for m in re.finditer(r"\b[A-Z][a-zA-Z]{2,}\b", content):
                w = m.group()
                if w.lower() in _ENTITY_STOPWORDS:
                    continue
                start = m.start()
                branch_entities[branch].add(w)
                snippet = content[max(0, start - 40):start + len(w) + 40].strip()
                if len(entity_contexts[w]) < 3:
                    entity_contexts[w].append(snippet)

        entity_branches: dict[str, set] = defaultdict(set)
        for branch, entities in branch_entities.items():
            for ent in entities:
                entity_branches[ent].add(branch)

        signals = []
        for entity, branches in entity_branches.items():
            if len(branches) < self._min_branches:
                continue
            fingerprint = tuple(sorted(branches))
            if self._last_branches.get(entity) == fingerprint:
                continue  # same branch-set as last emission -- stale re-scan, not new
            self._last_branches[entity] = fingerprint
            signals.append(Signal(
                detector_name="co_occurrence",
                signal_type=f"{len(branches)}_branch",
                payload={
                    "entity": entity,
                    "branches": sorted(branches),
                    "window_seconds": self._window,
                    "contexts": entity_contexts.get(entity, []),
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
        # census #13 fix: current_silence_seconds/multiplier_breach grow
        # every tick by construction (they're derived from `now`), so a
        # naive full-payload fingerprint would never dedupe. avg_gap_seconds
        # is the one field that's actually frozen when no new event has
        # landed for the stream -- that's the real "unchanged window"
        # signal. Skip re-emitting while it stays frozen; re-emit the
        # instant it moves (a real new data point arrived).
        self._last_avg_gap: dict[str, float] = {}

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
            if current_silence <= self._multiplier * avg_gap:
                self._last_avg_gap.pop(stream, None)  # recovered -- clear so a later, genuinely new silence episode can alert even if avg_gap matches by coincidence
                continue
            if self._last_avg_gap.get(stream) == avg_gap:
                continue  # avg_gap frozen -- no new event since last emission, stale re-scan
            self._last_avg_gap[stream] = avg_gap
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
        # census #13 fix: same (count, branch-set) re-qualifying the sliding
        # window on consecutive ticks means no new T6 promotion happened --
        # a stale re-scan, not a new burst. Skip re-emitting until either
        # changes.
        self._last_fingerprint: tuple | None = None

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
            self._last_fingerprint = None  # window dropped below threshold -- clear
            return []

        branches_raw = rows[0]["branches"] or ""
        branches = list({b for b in branches_raw.split(",") if b})

        fingerprint = (n, tuple(sorted(branches)))
        if self._last_fingerprint == fingerprint:
            return []  # same count + same branches as last emission -- stale re-scan
        self._last_fingerprint = fingerprint

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
