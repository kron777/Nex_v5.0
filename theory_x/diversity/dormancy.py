"""Quiet Corner Finder — tracks dormant graph regions and flags them."""
from __future__ import annotations

import logging
import time

log = logging.getLogger("theory_x.diversity.dormancy")

DORMANCY_MULTIPLIER = 4.0
MIN_BELIEFS_FOR_SCAN = 10


class DormancyScanner:
    def __init__(self, beliefs_writer, beliefs_reader):
        self._writer = beliefs_writer
        self._reader = beliefs_reader

    def scan_incremental(self) -> int:
        """Update dormancy scores for a batch of beliefs. Returns count updated."""
        rows = self._reader.read(
            "SELECT id, created_at, last_referenced_at FROM beliefs "
            "WHERE source IN ('fountain_insight', 'synergized', 'behavioural_observation') "
            "ORDER BY created_at ASC LIMIT 50"
        )
        if len(rows) < MIN_BELIEFS_FOR_SCAN:
            return 0

        avg_gap = self._average_gap()
        if avg_gap <= 0:
            return 0

        threshold = DORMANCY_MULTIPLIER * avg_gap
        now = time.time()
        updated = 0

        for row in rows:
            last_active = row["last_referenced_at"] or row["created_at"]
            silence = now - last_active
            if silence < threshold:
                continue
            dormancy_score = min(1.0, silence / (threshold * 5.0))
            self._writer.write(
                "INSERT INTO dormant_beliefs "
                "(belief_id, last_active_at, dormancy_score, flagged_at) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(belief_id) DO UPDATE SET "
                "  last_active_at=excluded.last_active_at, "
                "  dormancy_score=excluded.dormancy_score, "
                "  flagged_at=excluded.flagged_at",
                (row["id"], last_active, dormancy_score, now),
            )
            updated += 1

        if updated:
            log.info("Dormancy scan: flagged/updated %d beliefs", updated)
        return updated

    def _average_gap(self) -> float:
        rows = self._reader.read(
            "SELECT AVG(created_at) AS avg_ts, MAX(created_at) AS max_ts, "
            "       MIN(created_at) AS min_ts, COUNT(*) AS n FROM beliefs "
            "WHERE source IN ('fountain_insight', 'synergized')"
        )
        if not rows or not rows[0]["n"] or rows[0]["n"] < 2:
            return 86400.0
        r = rows[0]
        span = (r["max_ts"] or 0) - (r["min_ts"] or 0)
        return max(1.0, span / r["n"])

    def pick_dormant(self) -> list[dict]:
        """Return top dormant beliefs not yet reanimated."""
        rows = self._reader.read(
            "SELECT d.belief_id, d.dormancy_score, b.content "
            "FROM dormant_beliefs d JOIN beliefs b ON d.belief_id = b.id "
            "WHERE d.reanimated_at IS NULL "
            "ORDER BY d.dormancy_score DESC LIMIT 5"
        )
        return [dict(r) for r in rows]
