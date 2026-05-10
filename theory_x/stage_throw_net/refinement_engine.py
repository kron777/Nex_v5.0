"""Throw-Net Refinement Engine — TN-3.

Scores TimeFetch candidates against R1-R6 checks adapted from
nex_core's RefinementEngine. Returns a scored, sorted list.

Score scale: 0–6 (one point per passing check).
PASS_THRESHOLD: 3 (score >= 3 → buildable, per nex_core).
D5 reshape_hint threshold: score < 4 (recalibrated from the assumed
  0-10 scale in TN-1 to the actual 0-6 scale here — documented for TN-4).

R1–R6 origins and nex5 adaptation (design decisions 2026-05-10):
  R1 wires_to_existing   — DB read: beliefs WHERE confidence > 0.5
                           Passes if count >= 5. nex_core default was
                           >= 2; tuned for nex5 substrate density.
  R2 uses_belief_edges   — DB read: belief_edges JOIN beliefs.
                           nex_core used belief_links + topic column
                           (both absent in nex5). Adapted: keyword
                           JOIN on belief_edges any edge_type (D1=α).
                           Passes if count >= 3. nex_core default was
                           > 0; tuned for nex5 substrate density.
  R3 safe_for_live       — pure string: bot/service safety patterns.
                           Vestigial in nex5 (D3=A); always passes on
                           belief content. Retained for nex_core parity.
  R4 schema_change_safe  — pure string: destructive SQL patterns.
                           Vestigial in nex5 (D3=A). Retained.
  R5 right_size          — word_count > 80 AND compound-signal >= 2.
                           Discriminating for long compound candidates.
  R6 graceful_degradation — pure string: liveness constraint patterns.
                           Vestigial in nex5 (D3=A). Retained.

Read-only. No gate calls, no session writes, no background thread.
TN-4 ThrowNetEngine wires this with the corrected D5 threshold (< 4).
"""
from __future__ import annotations

from typing import Any

import errors

_LOG_SOURCE = "throw_net.refinement_engine"


class RefinementEngine:
    """Score TimeFetch candidates against six architecture questions.

    score(candidate) → dict with score, max_score, checks, buildable.
    run(candidates) → sorted list of score dicts, highest first.
    """

    _max_score: int = 6
    _pass_threshold: int = 3  # score >= 3 → buildable (nex_core PASS_THRESHOLD)
    # D5 reshape_hint threshold (TN-4 will wire): score < 5 on 0-6 scale.
    # Calibrated against production sanity — vestigial R3/R4/R6 + R5 establish
    # a +4 floor on normal belief content, so D5 sits at < 5 to capture
    # R1/R2 discrimination (which appears on sparse-topic queries like
    # 'curiosity': R1=95%, R2=91%). Was < 4 in TN-1 commit (assumed 0-10 scale);
    # corrected here via two rounds of production sanity (2026-05-10).

    _risky_patterns: tuple[str, ...] = (
        'delete all', 'drop table', 'truncate', 'restart service',
        'kill process', 'format ', 'rm -rf', 'overwrite soul loop',
    )
    _unsafe_schema: tuple[str, ...] = (
        'drop column', 'alter column', 'drop table', 'truncate table',
    )
    _oversized_signals: tuple[str, ...] = (
        ' and also ', ' plus ', ' additionally ', ' furthermore ',
        ' moreover ', ' on top of that ',
    )
    _blocking: tuple[str, ...] = (
        'must succeed', 'cannot fail', 'required to work',
        'no fallback', 'will always',
    )

    def __init__(self, beliefs_reader) -> None:
        self._reader = beliefs_reader

    # ── Public API ────────────────────────────────────────────────────────────

    def score(self, candidate: dict[str, Any]) -> dict[str, Any]:
        """Score a single candidate against R1-R6.

        Never raises — individual check failures are caught and treated
        as the check's default result.
        """
        content = candidate.get("content", "")
        checks = {
            "r1_wires_to_existing":    self._r1(content),
            "r2_uses_belief_edges":    self._r2(content),
            "r3_safe_for_live_service": self._r3(content),
            "r4_schema_change_safe":   self._r4(content),
            "r5_right_size":           self._r5(content),
            "r6_graceful_degradation": self._r6(content),
        }
        total = sum(1 for v in checks.values() if v)
        return {
            "candidate": candidate,
            "score": total,
            "max_score": self._max_score,
            "checks": checks,
            "buildable": total >= self._pass_threshold,
        }

    def run(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Score all candidates, sort by score DESC, return all.

        Returns an empty list for empty input.
        All candidates are returned regardless of buildable status —
        TN-4 uses the score value (and D5 threshold < 4) to route.
        """
        if not candidates:
            return []
        scored = [self.score(c) for c in candidates]
        scored.sort(key=lambda s: s["score"], reverse=True)
        return scored

    # ── Check implementations ─────────────────────────────────────────────────

    def _extract_keywords(self, content: str) -> list[str]:
        """nex_core semantics: words len > 4, first 6."""
        return [w for w in content.lower().split() if len(w) > 4][:6]

    def _r1(self, content: str) -> bool:
        """R1 — wires to existing: count beliefs matching keywords,
        confidence > 0.5. Passes if count >= 5.

        nex_core threshold was count >= 2, calibrated against a sparser
        substrate. nex5 has ~7400 beliefs and 564 edges — trivially
        passable at count >= 2. Tuned to >= 5 based on 8-constraint
        production sanity (Phase 5 surface, 2026-05-10).
        """
        keywords = self._extract_keywords(content)
        if not keywords:
            return False
        try:
            where = " OR ".join("LOWER(content) LIKE ?" for _ in keywords)
            params = tuple(f"%{k}%" for k in keywords)
            rows = self._reader.read(
                f"SELECT COUNT(*) AS n FROM beliefs "
                f"WHERE confidence > 0.5 AND ({where})",
                params,
            )
            return bool(rows) and rows[0]["n"] >= 5
        except Exception as exc:
            errors.record(f"RefinementEngine._r1: {exc}", source=_LOG_SOURCE, exc=exc)
            return False

    def _r2(self, content: str) -> bool:
        """R2 — uses belief_edges: keyword JOIN on belief_edges source.
        nex5 adaptation (D1=α): any edge_type accepted; keyword JOIN
        replaces nex_core's topic JOIN. Passes if count >= 3.
        Returns True on DB error (nex_core default-pass semantics).

        nex_core threshold was count > 0; tuned to >= 3 for nex5's
        denser graph (same 8-constraint sanity as R1 calibration).
        """
        keywords = self._extract_keywords(content)
        if not keywords:
            return False
        try:
            where = " OR ".join("LOWER(b.content) LIKE ?" for _ in keywords)
            params = tuple(f"%{k}%" for k in keywords)
            rows = self._reader.read(
                f"SELECT COUNT(*) AS n FROM belief_edges be "
                f"JOIN beliefs b ON be.source_id = b.id "
                f"WHERE ({where})",
                params,
            )
            return bool(rows) and rows[0]["n"] >= 3
        except Exception as exc:
            errors.record(f"RefinementEngine._r2: {exc}", source=_LOG_SOURCE, exc=exc)
            return True  # default-pass on DB error, per nex_core semantics

    def _r3(self, content: str) -> bool:
        """R3 — safe for live service. Vestigial in nex5 (D3=A)."""
        low = content.lower()
        return not any(p in low for p in self._risky_patterns)

    def _r4(self, content: str) -> bool:
        """R4 — schema change safe. Vestigial in nex5 (D3=A)."""
        low = content.lower()
        return not any(p in low for p in self._unsafe_schema)

    def _r5(self, content: str) -> bool:
        """R5 — right size: fails if word_count > 80 AND
        compound-signal count >= 2. Only discriminating check for
        long compound candidates."""
        low = content.lower()
        signal_count = sum(1 for s in self._oversized_signals if s in low)
        word_count = len(content.split())
        return not (word_count > 80 and signal_count >= 2)

    def _r6(self, content: str) -> bool:
        """R6 — graceful degradation. Vestigial in nex5 (D3=A)."""
        low = content.lower()
        return not any(p in low for p in self._blocking)
