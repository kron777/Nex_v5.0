"""Belief promotion and demotion — tier movement through phenomenon-triggered events.

Promotion triggers: corroborate(), survive_challenge()
Demotion triggers: decay_pass(), decisive_contradiction()
"""
from __future__ import annotations

import json
import time
from typing import Optional

import errors
from substrate import Writer, Reader

THEORY_X_STAGE = 3

_LOG_SOURCE = "promotion"

DECAY_IDLE_HOURS = 48

# Corroboration thresholds per source tier
_CORROBORATION_THRESHOLDS: dict[int, int] = {
    7: 3,   # Tier 7 → 6
    6: 5,   # Tier 6 → 5
    5: 8,   # Tier 5 → 4
    4: 12,  # Tier 4 → 3
    3: 20,  # Tier 3 → 2 (Bedrock — very hard)
    # Tier 2 → 1: re-seed ceremony only
}


class BeliefPromoter:
    def __init__(self, beliefs_writer: Writer, beliefs_reader: Reader) -> None:
        self._writer = beliefs_writer
        self._reader = beliefs_reader

    def write_edge(self, source_id: int, target_id: int, edge_type: str,
                   weight: float = 0.5) -> None:
        """Write or update a belief edge (one-pen rule: uses self._writer)."""
        now = time.time()
        try:
            self._writer.write(
                "INSERT INTO belief_edges (source_id, target_id, edge_type, weight, created_at) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(source_id, target_id, edge_type) DO UPDATE SET "
                "weight=excluded.weight, last_traversed_at=excluded.created_at",
                (source_id, target_id, edge_type, weight, now),
            )
        except Exception as exc:
            errors.record(f"write_edge error: {exc}", source=_LOG_SOURCE, exc=exc)

    def _write_corroboration_edge(self, belief_id: int, content: str) -> None:
        """Find highest-confidence peer belief with content overlap and write a supports edge."""
        if not content:
            return
        from .retrieval import _tokenize
        tokens = _tokenize(content)
        if not tokens:
            return
        try:
            candidates = self._reader.read(
                "SELECT id, content, confidence FROM beliefs "
                "WHERE id != ? AND tier <= 6 AND paused = 0 ORDER BY confidence DESC LIMIT 50",
                (belief_id,),
            )
        except Exception:
            return
        best_id: Optional[int] = None
        best_overlap = 0
        for c in candidates:
            c_tokens = _tokenize(c["content"] or "")
            overlap = len(tokens & c_tokens)
            if overlap > best_overlap:
                best_overlap = overlap
                best_id = c["id"]
        if best_id is not None and best_overlap >= 2:
            weight = min(1.0, best_overlap * 0.1 + 0.3)
            self.write_edge(best_id, belief_id, "supports", weight)

    def corroborate(self, belief_id: int) -> bool:
        """Increment corroboration_count; promote if threshold reached.

        Returns True if a promotion occurred.
        """
        try:
            row = self._reader.read_one(
                "SELECT id, content, tier, corroboration_count, locked FROM beliefs WHERE id = ?",
                (belief_id,),
            )
        except Exception as exc:
            errors.record(f"corroborate read error: {exc}", source=_LOG_SOURCE, exc=exc)
            return False

        if row is None:
            return False
        if row["locked"] and row["tier"] <= 1:
            return False  # Tier 1 locked — untouchable

        new_count = row["corroboration_count"] + 1
        now = int(time.time())
        threshold = _CORROBORATION_THRESHOLDS.get(row["tier"])

        if threshold is not None and new_count >= threshold and row["tier"] > 2:
            new_tier = row["tier"] - 1
            self._writer.write(
                "UPDATE beliefs SET tier = ?, corroboration_count = 0, "
                "last_promoted_at = ?, last_referenced_at = ?, "
                "promotion_log = json_insert(promotion_log, '$[#]', ?) "
                "WHERE id = ?",
                (new_tier, now, now,
                 json.dumps({"event": "corroboration", "from": row["tier"], "to": new_tier, "ts": now}),
                 belief_id),
            )
            # Find recent high-magnitude corroborating belief and write edge
            self._write_corroboration_edge(belief_id, row["content"] or "")
            errors.record(
                f"belief {belief_id} promoted Tier {row['tier']} → {new_tier} via corroboration",
                source=_LOG_SOURCE, level="INFO",
            )
            return True
        else:
            self._writer.write(
                "UPDATE beliefs SET corroboration_count = ?, last_referenced_at = ? WHERE id = ?",
                (new_count, now, belief_id),
            )
            return False

    def survive_challenge(self, belief_id: int) -> bool:
        """Promote belief by 1 tier immediately (survived direct contradiction).

        Returns True if promotion occurred.
        """
        try:
            row = self._reader.read_one(
                "SELECT id, tier, locked FROM beliefs WHERE id = ?",
                (belief_id,),
            )
        except Exception as exc:
            errors.record(f"survive_challenge read error: {exc}", source=_LOG_SOURCE, exc=exc)
            return False

        if row is None or row["tier"] <= 1:
            return False

        now = int(time.time())
        new_tier = max(2, row["tier"] - 1)
        self._writer.write(
            "UPDATE beliefs SET tier = ?, last_promoted_at = ?, "
            "promotion_log = json_insert(promotion_log, '$[#]', ?) "
            "WHERE id = ?",
            (new_tier, now,
             json.dumps({"event": "survive_challenge", "from": row["tier"], "to": new_tier, "ts": now}),
             belief_id),
        )
        errors.record(
            f"belief {belief_id} promoted Tier {row['tier']} → {new_tier} via challenge survival",
            source=_LOG_SOURCE, level="INFO",
        )
        return True

    def decay_pass(self) -> int:
        """Demote Tier 5-7 beliefs idle for > DECAY_IDLE_HOURS. Returns demotion count."""
        cutoff = int(time.time()) - DECAY_IDLE_HOURS * 3600
        try:
            rows = self._reader.read(
                "SELECT id, tier FROM beliefs "
                "WHERE tier BETWEEN 5 AND 7 AND locked = 0 "
                "AND (last_referenced_at IS NULL OR last_referenced_at < ?)",
                (cutoff,),
            )
        except Exception as exc:
            errors.record(f"decay_pass read error: {exc}", source=_LOG_SOURCE, exc=exc)
            return 0

        count = 0
        now = int(time.time())
        for row in rows:
            new_tier = min(7, row["tier"] + 1)
            if new_tier == row["tier"]:
                continue
            try:
                self._writer.write(
                    "UPDATE beliefs SET tier = ?, last_demoted_at = ?, "
                    "promotion_log = json_insert(promotion_log, '$[#]', ?) "
                    "WHERE id = ?",
                    (new_tier, now,
                     json.dumps({"event": "decay", "from": row["tier"], "to": new_tier, "ts": now}),
                     row["id"]),
                )
                count += 1
            except Exception as exc:
                errors.record(f"decay_pass write error: {exc}", source=_LOG_SOURCE, exc=exc)

        if count:
            errors.record(f"decay_pass demoted {count} beliefs", source=_LOG_SOURCE, level="INFO")
        return count

    def decisive_contradiction(self, belief_id: int) -> bool:
        """Demote belief by 2 tiers (or discard if already at Tier 7).

        Returns True if demotion/discard occurred.
        """
        try:
            row = self._reader.read_one(
                "SELECT id, content, tier, locked FROM beliefs WHERE id = ?",
                (belief_id,),
            )
        except Exception as exc:
            errors.record(f"decisive_contradiction read error: {exc}", source=_LOG_SOURCE, exc=exc)
            return False

        if row is None or row["locked"]:
            return False

        now = int(time.time())
        current = row["tier"]
        new_tier = min(7, current + 2)

        self._writer.write(
            "UPDATE beliefs SET tier = ?, last_demoted_at = ?, "
            "promotion_log = json_insert(promotion_log, '$[#]', ?) "
            "WHERE id = ?",
            (new_tier, now,
             json.dumps({"event": "decisive_contradiction", "from": current, "to": new_tier, "ts": now}),
             belief_id),
        )
        # Write opposes edges to high-overlap beliefs
        self._write_contradiction_edges(belief_id, row["content"] or "")
        errors.record(
            f"belief {belief_id} demoted Tier {current} → {new_tier} via decisive contradiction",
            source=_LOG_SOURCE, level="INFO",
        )
        return True

    def _write_contradiction_edges(self, belief_id: int, content: str) -> None:
        """Write opposes edges between the contradicted belief and high-overlap peers."""
        if not content:
            return
        from .retrieval import _tokenize
        tokens = _tokenize(content)
        if not tokens:
            return
        try:
            candidates = self._reader.read(
                "SELECT id, content FROM beliefs "
                "WHERE id != ? AND tier <= 6 AND locked = 0 LIMIT 50",
                (belief_id,),
            )
        except Exception:
            return
        for c in candidates:
            c_tokens = _tokenize(c["content"] or "")
            overlap = len(tokens & c_tokens)
            if overlap >= 3:
                self.write_edge(belief_id, c["id"], "opposes", 0.8)
