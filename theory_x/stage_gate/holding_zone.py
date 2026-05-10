"""Theory X — Holding Zone.

Per FACULTY_MODEL.md §2.5 (committed 59c20d6).

Thoughts marked HOLD by the Coherence Gate persist here. They
wait for corroboration, contradiction, or time decay before any
substrate write occurs.

Phase 23 thresholds (v1):
  - Corroboration: N=3 (matches _CORROBORATION_THRESHOLDS[7] in promotion.py)
  - Similarity for corroboration: Jaccard >= 0.40 (HOLD band lower bound)
  - Contradiction: token overlap >= 2 AND negation parity differs
  - Fade: 24h (86400s)

Retention of terminal-state rows (accepted/rejected/faded) is
intentionally not addressed in Phase 23. Table accumulates.
A retention policy is a separate phase once data grounds it.
"""
from __future__ import annotations

import time
from typing import Any, Optional

import errors
from substrate import Reader, Writer

THEORY_X_STAGE = "gate"

_LOG_SOURCE = "holding_zone"

_CORROBORATION_THRESHOLD = 3
_CORROBORATION_JACCARD = 0.40
_FADE_SECONDS = 86400  # 24 hours

# Tier for promoted beliefs: matches each faculty's default INSERT tier.
_SOURCE_TIER: dict[str, int] = {
    "fountain":               6,
    "synergizer":             6,
    "stage2_crystallization": 7,
    "bsm":                    6,
    "emergent_drives":        5,
}
_DEFAULT_TIER = 6


class HoldingZone:
    """Storage and query layer for held thoughts.

    All persistence is in beliefs.db (held_thoughts + held_resolutions tables).
    This class is stateless: every method reads/writes the DB fresh.
    """

    def __init__(self, beliefs_writer: Writer, beliefs_reader: Reader) -> None:
        self._writer = beliefs_writer
        self._reader = beliefs_reader

    # ── Public API ────────────────────────────────────────────────────────────

    def hold(self, packet: Any, reason: str) -> Optional[int]:
        """Persist a held thought. Returns held_id or None on error."""
        now = time.time()
        try:
            held_id = self._writer.write(
                "INSERT INTO held_thoughts "
                "(content, source_node, confidence, branch_id, hold_reason, "
                "created_at, last_seen_at, corroboration_count, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 0, 'holding')",
                (
                    packet.content,
                    packet.source_node,
                    packet.confidence,
                    packet.branch_id,
                    reason,
                    now,
                    now,
                ),
            )
            errors.record(
                f"held_thought id={held_id}: {packet.content[:60]}",
                source=_LOG_SOURCE, level="INFO",
            )
            return held_id
        except Exception as exc:
            errors.record(f"hold write error: {exc}", source=_LOG_SOURCE, exc=exc)
            return None

    def find_corroborations(self, packet: Any) -> list[dict]:
        """Return active held thoughts with Jaccard >= 0.40 against packet."""
        try:
            rows = self._reader.read(
                "SELECT id, content, source_node, confidence, branch_id, "
                "corroboration_count FROM held_thoughts WHERE status='holding'"
            )
        except Exception as exc:
            errors.record(f"find_corroborations error: {exc}", source=_LOG_SOURCE, exc=exc)
            return []

        from theory_x.stage_gate.coherence_gate import _jaccard
        results = []
        for row in rows:
            if _jaccard(packet.content, row["content"]) >= _CORROBORATION_JACCARD:
                results.append(dict(row))
        return results

    def find_contradictions(self, packet: Any) -> list[dict]:
        """Return active held thoughts contradicted by packet.

        Contradiction: token overlap >= 2 AND negation parity differs.
        Same logic as gate's anchor-contradiction check.
        """
        from theory_x.stage_gate.coherence_gate import _tokens, _has_negation
        tok = _tokens(packet.content)
        neg = _has_negation(packet.content)
        try:
            rows = self._reader.read(
                "SELECT id, content, source_node, confidence, branch_id "
                "FROM held_thoughts WHERE status='holding'"
            )
        except Exception as exc:
            errors.record(f"find_contradictions error: {exc}", source=_LOG_SOURCE, exc=exc)
            return []

        results = []
        for row in rows:
            held_tok = _tokens(row["content"])
            held_neg = _has_negation(row["content"])
            if len(tok & held_tok) >= 2 and neg != held_neg:
                results.append(dict(row))
        return results

    def increment_corroboration(self, held_id: int) -> int:
        """Increment corroboration_count. Returns new count or -1 on error."""
        now = time.time()
        try:
            self._writer.write(
                "UPDATE held_thoughts "
                "SET corroboration_count = corroboration_count + 1, last_seen_at = ? "
                "WHERE id = ? AND status = 'holding'",
                (now, held_id),
            )
            row = self._reader.read_one(
                "SELECT corroboration_count FROM held_thoughts WHERE id = ?",
                (held_id,),
            )
            return row["corroboration_count"] if row else -1
        except Exception as exc:
            errors.record(f"increment_corroboration error: {exc}",
                          source=_LOG_SOURCE, exc=exc)
            return -1

    def mark_resolved(self, held_id: int, terminal_status: str,
                      action_reason: str, trigger_preview: str = "") -> None:
        """Write terminal status and audit row. No-op if row is already terminal."""
        try:
            self._writer.write(
                "UPDATE held_thoughts SET status = ? "
                "WHERE id = ? AND status = 'holding'",
                (terminal_status, held_id),
            )
            self._writer.write(
                "INSERT INTO held_resolutions "
                "(held_id, ts, action, reason, trigger_packet_preview) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    held_id,
                    time.time(),
                    terminal_status,
                    action_reason,
                    trigger_preview[:80],
                ),
            )
        except Exception as exc:
            errors.record(f"mark_resolved error: {exc}", source=_LOG_SOURCE, exc=exc)

    def promote_to_belief(self, held_id: int, row: dict) -> Optional[int]:
        """Write held thought as a real belief. Returns belief_id or None."""
        tier = _SOURCE_TIER.get(row["source_node"] or "", _DEFAULT_TIER)
        try:
            belief_id = self._writer.write(
                "INSERT INTO beliefs "
                "(content, tier, confidence, created_at, source, branch_id, locked) "
                "VALUES (?, ?, ?, ?, ?, ?, 0)",
                (
                    row["content"],
                    tier,
                    row["confidence"],
                    time.time(),
                    row["source_node"],
                    row["branch_id"],
                ),
            )
            errors.record(
                f"held_thought promoted: held_id={held_id} belief_id={belief_id} "
                f"tier={tier}: {row['content'][:60]}",
                source=_LOG_SOURCE, level="INFO",
            )
            return belief_id
        except Exception as exc:
            errors.record(f"promote_to_belief error: {exc}", source=_LOG_SOURCE, exc=exc)
            return None

    def fade_stale(self, now_ts: float,
                   max_age_seconds: float = _FADE_SECONDS) -> int:
        """Mark held thoughts older than max_age_seconds as 'faded'. Returns count."""
        cutoff = now_ts - max_age_seconds
        try:
            stale = self._reader.read(
                "SELECT id FROM held_thoughts "
                "WHERE status='holding' AND created_at < ?",
                (cutoff,),
            )
            if not stale:
                return 0
            for row in stale:
                self.mark_resolved(
                    row["id"], "faded",
                    f"stale_after_{int(max_age_seconds)}s",
                )
            errors.record(
                f"holding_zone: faded {len(stale)} stale held thoughts",
                source=_LOG_SOURCE, level="INFO",
            )
            return len(stale)
        except Exception as exc:
            errors.record(f"fade_stale error: {exc}", source=_LOG_SOURCE, exc=exc)
            return 0
