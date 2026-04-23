"""Harmonizer — detects and resolves conflicts between beliefs.

Runs every 2 hours. Finds conflicting belief pairs at Tier 4+,
pauses them, seeks synthesis, and resolves.
"""
from __future__ import annotations

import json
import re
import time
from typing import Optional

import errors
from substrate import Writer, Reader
from .retrieval import _tokenize
from .promotion import BeliefPromoter

THEORY_X_STAGE = 3

_LOG_SOURCE = "harmonizer"

_NEGATION_WORDS = {"not", "no", "never", "cannot", "isn't", "aren't", "doesn't",
                   "don't", "won't", "without", "lack", "lacks", "absent"}


def _has_negation(text: str) -> bool:
    words = set(text.lower().split())
    return bool(words & _NEGATION_WORDS)


def _conflict_score(tokens_a: set[str], text_a: str,
                    tokens_b: set[str], text_b: str) -> float:
    """Heuristic: high keyword overlap + one belief negated → conflict."""
    overlap = len(tokens_a & tokens_b)
    if overlap < 2:
        return 0.0
    neg_a = _has_negation(text_a)
    neg_b = _has_negation(text_b)
    if neg_a != neg_b:
        # One asserts, one denies
        score = overlap / max(1, len(tokens_a | tokens_b))
        return score
    return 0.0


class Harmonizer:
    def __init__(self, beliefs_writer: Writer, beliefs_reader: Reader,
                 dynamic_writer: Writer, promoter: BeliefPromoter) -> None:
        self._beliefs_writer = beliefs_writer
        self._beliefs_reader = beliefs_reader
        self._dynamic_writer = dynamic_writer
        self._promoter = promoter

    def scan_for_conflicts(self) -> list[tuple[int, int]]:
        """Find conflicting belief pairs at Tier 4+.

        Returns list of (belief_id_a, belief_id_b) pairs.
        """
        try:
            rows = self._beliefs_reader.read(
                "SELECT id, content, tier FROM beliefs "
                "WHERE tier <= 4 AND locked = 0 AND paused = 0 "
                "ORDER BY tier ASC LIMIT 100",
            )
        except Exception as exc:
            errors.record(f"scan_for_conflicts read error: {exc}", source=_LOG_SOURCE, exc=exc)
            return []

        conflicts = []
        beliefs = [dict(r) for r in rows]
        token_cache = {b["id"]: _tokenize(b["content"]) for b in beliefs}

        for i, a in enumerate(beliefs):
            for b in beliefs[i + 1:]:
                score = _conflict_score(
                    token_cache[a["id"]], a["content"],
                    token_cache[b["id"]], b["content"],
                )
                if score >= 0.15:
                    conflicts.append((a["id"], b["id"]))

        return conflicts

    def resolve(self, belief_id_a: int, belief_id_b: int) -> str:
        """Resolve a conflict between two beliefs.

        Returns resolution type: 'synthesized', 'both_deleted', 'error'.
        """
        try:
            row_a = self._beliefs_reader.read_one(
                "SELECT id, content, tier, confidence FROM beliefs WHERE id = ?",
                (belief_id_a,),
            )
            row_b = self._beliefs_reader.read_one(
                "SELECT id, content, tier, confidence FROM beliefs WHERE id = ?",
                (belief_id_b,),
            )
        except Exception as exc:
            errors.record(f"harmonizer resolve read error: {exc}", source=_LOG_SOURCE, exc=exc)
            return "error"

        if row_a is None or row_b is None:
            return "error"

        # Pause both
        now = int(time.time())
        self._beliefs_writer.write(
            "UPDATE beliefs SET paused = 1 WHERE id IN (?, ?)",
            (belief_id_a, belief_id_b),
        )

        # Log to harmonizer_events
        self._dynamic_writer.write(
            "INSERT INTO harmonizer_events (ts, belief_id_a, belief_id_b, resolution) "
            "VALUES (?, ?, ?, 'pending')",
            (time.time(), belief_id_a, belief_id_b),
        )

        # Seek synthesis: find a third belief with overlap to both
        tokens_a = _tokenize(row_a["content"])
        tokens_b = _tokenize(row_b["content"])
        combined_tokens = tokens_a | tokens_b
        synthesis_id: Optional[int] = None

        try:
            candidates = self._beliefs_reader.read(
                "SELECT id, content, tier FROM beliefs "
                "WHERE id NOT IN (?, ?) AND paused = 0 AND tier <= 5 LIMIT 50",
                (belief_id_a, belief_id_b),
            )
            for c in candidates:
                c_tokens = _tokenize(c["content"])
                if len(c_tokens & tokens_a) >= 2 and len(c_tokens & tokens_b) >= 2:
                    synthesis_id = c["id"]
                    break
        except Exception as exc:
            errors.record(f"harmonizer synthesis search error: {exc}", source=_LOG_SOURCE, exc=exc)

        lower_tier = max(row_a["tier"], row_b["tier"])

        if synthesis_id is not None:
            # Retire both originals
            retired_content_a = f"[RETIRED] {row_a['content']}"
            retired_content_b = f"[RETIRED] {row_b['content']}"
            self._beliefs_writer.write_many([
                ("UPDATE beliefs SET tier = 8, locked = 0, paused = 0, "
                 "content = ? WHERE id = ?", (retired_content_a, belief_id_a)),
                ("UPDATE beliefs SET tier = 8, locked = 0, paused = 0, "
                 "content = ? WHERE id = ?", (retired_content_b, belief_id_b)),
            ])
            self._dynamic_writer.write(
                "UPDATE harmonizer_events SET resolution = 'synthesized', "
                "synthesis_belief_id = ? WHERE belief_id_a = ? AND belief_id_b = ? "
                "AND resolution = 'pending'",
                (synthesis_id, belief_id_a, belief_id_b),
            )
            # Write synthesises edges from both retired beliefs to the synthesis belief
            self._promoter.write_edge(belief_id_a, synthesis_id, "synthesises", 0.7)
            self._promoter.write_edge(belief_id_b, synthesis_id, "synthesises", 0.7)
            self._promoter.decisive_contradiction(belief_id_b)
            errors.record(
                f"harmonizer synthesized conflict ({belief_id_a}, {belief_id_b}) "
                f"via belief {synthesis_id}",
                source=_LOG_SOURCE, level="INFO",
            )
            return "synthesized"
        else:
            # No synthesis — retire both
            self._beliefs_writer.write_many([
                ("UPDATE beliefs SET tier = 8, locked = 0, paused = 0, "
                 "content = ? WHERE id = ?",
                 (f"[RETIRED] {row_a['content']}", belief_id_a)),
                ("UPDATE beliefs SET tier = 8, locked = 0, paused = 0, "
                 "content = ? WHERE id = ?",
                 (f"[RETIRED] {row_b['content']}", belief_id_b)),
            ])
            self._dynamic_writer.write(
                "UPDATE harmonizer_events SET resolution = 'both_deleted' "
                "WHERE belief_id_a = ? AND belief_id_b = ? AND resolution = 'pending'",
                (belief_id_a, belief_id_b),
            )
            errors.record(
                f"harmonizer deleted both beliefs ({belief_id_a}, {belief_id_b}) — no synthesis found",
                source=_LOG_SOURCE, level="INFO",
            )
            return "both_deleted"

    def run_scan_and_resolve(self, world_model_state=None) -> int:
        """Full scan pass. Returns count of conflicts resolved.

        If world_model_state is provided, records the first conflict as a
        disturbance on WorldModelState before resolving.
        """
        conflicts = self.scan_for_conflicts()
        resolved = 0

        for idx, (a_id, b_id) in enumerate(conflicts):
            # Record the first unresolved conflict as a disturbance
            if idx == 0 and world_model_state is not None:
                try:
                    row_a = self._beliefs_reader.read_one(
                        "SELECT content FROM beliefs WHERE id = ?", (a_id,)
                    )
                    row_b = self._beliefs_reader.read_one(
                        "SELECT content FROM beliefs WHERE id = ?", (b_id,)
                    )
                    if row_a and row_b:
                        # Compute overlap score for intensity
                        ta = _tokenize(row_a["content"])
                        tb = _tokenize(row_b["content"])
                        union = len(ta | tb)
                        intensity = len(ta & tb) / union if union else 0.0
                        world_model_state.set_disturbance(
                            a_id, b_id,
                            row_a["content"], row_b["content"],
                            intensity,
                        )
                except Exception as exc:
                    errors.record(f"disturbance record error: {exc}", source=_LOG_SOURCE, exc=exc)

            result = self.resolve(a_id, b_id)
            if result != "error":
                resolved += 1
        return resolved

    def detect_cross_domain(self) -> int:
        """Scan Tier 1-4 beliefs for cross-domain pattern matches.

        For each pair in different branch_ids with keyword overlap >= 0.4
        and no existing edge, write a 'cross_domain' edge.
        Returns count of new edges written.
        """
        try:
            rows = self._beliefs_reader.read(
                "SELECT id, content, branch_id FROM beliefs "
                "WHERE tier <= 4 AND locked = 0 AND paused = 0 "
                "AND branch_id IS NOT NULL LIMIT 200",
            )
        except Exception as exc:
            errors.record(f"detect_cross_domain read error: {exc}", source=_LOG_SOURCE, exc=exc)
            return 0

        beliefs = [dict(r) for r in rows]
        if len(beliefs) < 2:
            return 0

        token_cache = {b["id"]: _tokenize(b["content"]) for b in beliefs}

        # Fetch existing edges to avoid duplicates
        ids = [b["id"] for b in beliefs]
        placeholders = ",".join("?" * len(ids))
        existing: set[tuple[int, int]] = set()
        try:
            edge_rows = self._beliefs_reader.read(
                f"SELECT source_id, target_id FROM belief_edges "
                f"WHERE source_id IN ({placeholders}) OR target_id IN ({placeholders})",
                tuple(ids) * 2,
            )
            for e in edge_rows:
                existing.add((e["source_id"], e["target_id"]))
                existing.add((e["target_id"], e["source_id"]))
        except Exception:
            pass

        written = 0
        for i, a in enumerate(beliefs):
            for b in beliefs[i + 1:]:
                if a["branch_id"] == b["branch_id"]:
                    continue
                if (a["id"], b["id"]) in existing:
                    continue
                ta = token_cache[a["id"]]
                tb = token_cache[b["id"]]
                union = len(ta | tb)
                if union == 0:
                    continue
                overlap = len(ta & tb) / union
                if overlap >= 0.4:
                    self._promoter.write_edge(a["id"], b["id"], "cross_domain", round(overlap, 3))
                    existing.add((a["id"], b["id"]))
                    existing.add((b["id"], a["id"]))
                    written += 1
                    errors.record(
                        f"cross_domain edge: belief {a['id']} ({a['branch_id']}) "
                        f"↔ {b['id']} ({b['branch_id']}) overlap={overlap:.2f}",
                        source=_LOG_SOURCE, level="INFO",
                    )

        return written
