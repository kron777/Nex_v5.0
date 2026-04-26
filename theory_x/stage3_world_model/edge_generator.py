"""Tropic Gradient Phase 1 — populates belief_edges with heuristic proposals.

No LLM calls. Four edge types mapped to schema values:
  SUPPORTS   → 'supports'    (same source, moderate overlap, no negation flip)
  REFINES    → 'refines'     (same source, high overlap, one is more specific)
  CONTRADICTS→ 'opposes'     (any source, moderate overlap, negation inversion)
  BRIDGES    → 'cross_domain'(different branches, low overlap, shared content nouns)
"""
from __future__ import annotations

import logging
import re
import threading
import time
from typing import Optional

log = logging.getLogger("theory_x.edge_generator")

_NEGATION_WORDS = frozenset({
    "not", "no", "never", "nobody", "nothing", "nowhere", "neither", "nor",
    "isn't", "aren't", "wasn't", "weren't", "doesn't", "don't", "didn't",
    "won't", "wouldn't", "can't", "cannot", "couldn't", "shouldn't",
    "hardly", "barely", "scarcely",
})

_OPPOSITION_MARKERS = frozenset({
    "but", "however", "instead", "yet", "although", "though", "while",
    "whereas", "contrary", "nevertheless", "nonetheless", "conversely",
    "despite", "unlike", "rather",
})

_QUALIFIER_WORDS = frozenset({
    "specifically", "particularly", "especially", "only", "always", "never",
    "precisely", "exactly", "solely", "exclusively", "strictly", "purely",
    "merely", "uniquely", "inherently", "fundamentally",
})

_STOPWORDS = frozenset({
    "i", "me", "my", "myself", "we", "our", "ours", "you", "your", "he",
    "she", "it", "they", "them", "what", "which", "who", "this", "that",
    "these", "those", "am", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "a", "an", "the",
    "and", "but", "or", "nor", "for", "so", "yet", "as", "at", "by", "in",
    "of", "on", "to", "up", "via", "with", "from", "into", "through",
    "during", "before", "after", "above", "below", "between", "out", "off",
    "over", "under", "again", "then", "once", "here", "there", "when",
    "where", "why", "how", "all", "each", "more", "most", "other", "some",
    "such", "than", "too", "very", "just", "because", "if", "about",
    "against", "along", "around", "near", "also", "even", "still", "back",
    "now", "both", "either", "while", "since",
})


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"\b[a-z]{3,}\b", text.lower()))


def _jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    union = len(ta | tb)
    return len(ta & tb) / union if union else 0.0


def _negation_count(text: str) -> int:
    return sum(1 for w in _tokens(text) if w in _NEGATION_WORDS)


def _has_opposition_marker(text: str) -> bool:
    return bool(_tokens(text) & _OPPOSITION_MARKERS)


def _qualifier_count(text: str) -> int:
    return sum(1 for w in _tokens(text) if w in _QUALIFIER_WORDS)


def _shared_content_nouns(a: str, b: str) -> int:
    ta = _tokens(a) - _STOPWORDS - _NEGATION_WORDS - _OPPOSITION_MARKERS
    tb = _tokens(b) - _STOPWORDS - _NEGATION_WORDS - _OPPOSITION_MARKERS
    return len(ta & tb)


class EdgeGenerator:
    def __init__(self, writer, reader):
        self._writer = writer
        self._reader = reader

    def propose_edges_for_belief(
        self, belief_id: int, max_edges: int = 5
    ) -> list[tuple[int, str, float]]:
        rows = self._reader.read(
            "SELECT id, content, source, branch_id FROM beliefs WHERE id = ?",
            (belief_id,),
        )
        if not rows:
            return []
        src = rows[0]
        src_content = src["content"] or ""
        src_source = src["source"] or ""
        src_branch = src["branch_id"] or ""

        cutoff = time.time() - 7 * 86400
        candidates = self._reader.read(
            "SELECT id, content, source, branch_id FROM beliefs "
            "WHERE id != ? AND tier <= 7 AND created_at >= ? "
            "ORDER BY created_at DESC LIMIT 100",
            (belief_id, cutoff),
        )
        if not candidates:
            return []

        existing = self._reader.read(
            "SELECT target_id FROM belief_edges WHERE source_id = ? "
            "UNION "
            "SELECT source_id FROM belief_edges WHERE target_id = ?",
            (belief_id, belief_id),
        )
        already_connected = {r["target_id"] for r in existing}

        src_neg = _negation_count(src_content)
        src_qualifiers = _qualifier_count(src_content)

        proposals: list[tuple[float, int, str]] = []

        for cand in candidates:
            cid = cand["id"]
            if cid in already_connected:
                continue
            cand_content = cand["content"] or ""
            cand_branch = cand["branch_id"] or ""
            cand_source = cand["source"] or ""

            j = _jaccard(src_content, cand_content)
            cand_neg = _negation_count(cand_content)
            same_source = src_source == cand_source and src_source != ""

            best_type: Optional[str] = None
            best_weight: float = 0.0

            # REFINES: same source, high overlap, one belief is more specific
            if same_source and j > 0.5:
                len_ratio = max(len(src_content), len(cand_content)) / max(
                    min(len(src_content), len(cand_content)), 1
                )
                qualifier_diff = abs(src_qualifiers - _qualifier_count(cand_content))
                if len_ratio > 1.3 or qualifier_diff >= 1:
                    w = j * 0.7
                    if w > best_weight:
                        best_type, best_weight = "refines", w

            # SUPPORTS: same source, moderate overlap, no negation flip
            if same_source and j > 0.4 and abs(src_neg - cand_neg) == 0:
                w = j * 0.6
                if w > best_weight:
                    best_type, best_weight = "supports", w

            # OPPOSES: any source, moderate overlap, negation inversion or opposition
            if j > 0.3:
                negation_flip = (src_neg == 0 and cand_neg > 0) or (
                    src_neg > 0 and cand_neg == 0
                )
                opposition = _has_opposition_marker(
                    src_content
                ) or _has_opposition_marker(cand_content)
                if negation_flip or opposition:
                    w = j * 0.8
                    if w > best_weight:
                        best_type, best_weight = "opposes", w

            # CROSS_DOMAIN: different branches, low overlap, shared content nouns
            if src_branch and cand_branch and src_branch != cand_branch and j < 0.4:
                shared = _shared_content_nouns(src_content, cand_content)
                if shared >= 2:
                    w = min(0.3 + shared * 0.05, 0.6)
                    if w > best_weight:
                        best_type, best_weight = "cross_domain", w

            if best_type and best_weight >= 0.2:
                proposals.append((best_weight, cid, best_type))

        proposals.sort(key=lambda x: x[0], reverse=True)
        return [(cid, etype, round(w, 4)) for w, cid, etype in proposals[:max_edges]]

    def persist_edges(
        self, source_id: int, edges: list[tuple[int, str, float]]
    ) -> int:
        now = time.time()
        for target_id, edge_type, weight in edges:
            self._writer.write(
                "INSERT OR IGNORE INTO belief_edges "
                "(source_id, target_id, edge_type, weight, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (source_id, target_id, edge_type, weight, now),
            )
        return len(edges)


class EdgeGeneratorLoop:
    TICK_SECONDS = 1800
    BOOT_DELAY_SECONDS = 60
    BATCH_SIZE = 20
    MAX_EDGES_PER_BELIEF = 5

    def __init__(self, writers: dict, readers: dict):
        self._generator = EdgeGenerator(writers["beliefs"], readers["beliefs"])
        self._reader = readers["beliefs"]
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run, name="EdgeGeneratorLoop", daemon=True,
        )
        self._thread.start()
        log.info("EdgeGeneratorLoop started (tick=30min, boot_delay=60s)")

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        self._stop.wait(self.BOOT_DELAY_SECONDS)
        if self._stop.is_set():
            return
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception as e:
                log.warning("EdgeGeneratorLoop tick failed: %s", e)
            self._stop.wait(self.TICK_SECONDS)

    def _tick(self) -> None:
        beliefs = self._reader.read(
            "SELECT id FROM beliefs "
            "WHERE source IN ('fountain_insight', 'synergized') "
            "AND id NOT IN (SELECT source_id FROM belief_edges) "
            "AND id NOT IN (SELECT target_id FROM belief_edges) "
            "ORDER BY created_at DESC LIMIT ?",
            (self.BATCH_SIZE,),
        )
        if not beliefs:
            log.debug("EdgeGeneratorLoop: no unedged beliefs this tick")
            return

        processed = 0
        proposed = 0
        persisted = 0

        for row in beliefs:
            bid = row["id"]
            edges = self._generator.propose_edges_for_belief(
                bid, max_edges=self.MAX_EDGES_PER_BELIEF
            )
            proposed += len(edges)
            if edges:
                persisted += self._generator.persist_edges(bid, edges)
            processed += 1

        log.info(
            "EdgeGeneratorLoop tick: %d beliefs processed, %d edges proposed, %d persisted",
            processed, proposed, persisted,
        )


def build_edge_generator_loop(writers: dict, readers: dict) -> EdgeGeneratorLoop:
    loop = EdgeGeneratorLoop(writers, readers)
    return loop
