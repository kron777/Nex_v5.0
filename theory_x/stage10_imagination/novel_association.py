"""Novel Association — cross-branch synthesises edge generation.

Realizes §5 row 10a: detects semantically similar belief pairs that
cross branch boundaries (cosine >= _SIMILARITY_THRESHOLD) and writes
synthesises edges to grow T7 cross-domain topology. Surfaces fresh
associations into belief_text via format_for_prompt().

Known gap (queued Phase 18): BeliefRetriever filters tier <= 6;
synthesises edges connect T7 beliefs. The cognitive-effect path
through retrieval is incomplete. NovelAssociation still produces:
  - Graph topology growth in the T7 plane
  - Self-awareness annotation via belief_text injection
  - Activation propagation through synthesises edges (1.2× multiplier)

T6 promotion path is effectively single-branch in the current
substrate (all T1-T6 beliefs are branch='systems' or NULL). Cross-
domain content lives exclusively in T7. Diagnosis of the promotion
pipeline is queued as Phase 18 investigation.

10b (Counterfactual Simulation) deferred pending §7 amendment
(§7 prohibits nodes from writing beliefs; 10b's counterfactual path
requires new belief content, not just edges).

PHASE 17 reversion: drop novel_association_log table, remove module
+ tests + wiring. synthesises edges written to belief_edges are
permanent graph topology and survive reversion.

Implements SentienceNode protocol (DOCTRINE §4):
  name, tick(context), decay(now), state(now=None)
"""
from __future__ import annotations

import threading
import time
from itertools import combinations
from typing import Optional

import errors
from substrate import Writer, Reader

THEORY_X_STAGE = 10

_LOG_SOURCE = "novel_association"

_SIMILARITY_THRESHOLD  = 0.72    # normalized cosine; raw ~0.44, above noise floor (~0.30)
_NARRATIVE_THRESHOLD   = 0.85    # higher bar for SelfNarrative write — strongly significant pairs only
_LOOP_INTERVAL_S       = 1800    # scan cadence (30 min)
_ANNOTATION_LOOKBACK_S = 7200   # staleness gate: how old an unannotated entry can be
_BATCH_SIZE            = 10      # total candidates; per_branch = batch // n_branches
_STALE_DAYS            = 14      # decay cutoff for unannotated log entries


class NovelAssociation:
    name: str = "novel_association"

    def __init__(
        self,
        beliefs_writer: Writer,
        beliefs_reader: Reader,
        self_narrative=None,     # Phase 26: SelfNarrative instance
    ) -> None:
        self._writer = beliefs_writer
        self._reader = beliefs_reader
        self._self_narrative = self_narrative
        self._lock = threading.Lock()
        self._last_scan_at: float = 0.0
        self._edges_written_total: int = 0

    # ── SentienceNode protocol ────────────────────────────────────────────────

    def tick(self, context: Optional[dict] = None) -> dict:
        """Run one scan cycle if interval has elapsed. Returns state."""
        now = time.time()
        if now - self._last_scan_at < _LOOP_INTERVAL_S:
            return self.state(now=now)

        with self._lock:
            self._last_scan_at = now
        written = self._scan(now)
        with self._lock:
            self._edges_written_total += written
        return self.state(now=now)

    def decay(self, now: float) -> None:
        """Mark unannotated log entries older than _STALE_DAYS as annotated."""
        cutoff = now - _STALE_DAYS * 86400
        self._writer.write(
            "UPDATE novel_association_log SET annotated_at = ? "
            "WHERE annotated_at IS NULL AND detected_at < ?",
            (now, cutoff),
        )

    def state(self, now: Optional[float] = None) -> dict:
        now = now or time.time()
        with self._lock:
            last = self._last_scan_at
            total = self._edges_written_total
        return {
            "name": self.name,
            "last_scan_at": round(last, 1),
            "edges_written_total": total,
            "next_scan_in": max(0, round(last + _LOOP_INTERVAL_S - now, 0)),
        }

    # ── public API ───────────────────────────────────────────────────────────

    def format_for_prompt(self) -> str:
        """Return 1-line annotation for the most recent unannotated association.

        Marks the entry annotated immediately after read so the same association
        is not injected twice. Returns empty string when nothing fresh exists.
        """
        now = time.time()
        cutoff = now - _ANNOTATION_LOOKBACK_S
        try:
            row = self._reader.read_one(
                "SELECT id, branch_id_a, branch_id_b, similarity "
                "FROM novel_association_log "
                "WHERE annotated_at IS NULL AND detected_at > ? "
                "ORDER BY detected_at DESC LIMIT 1",
                (cutoff,),
            )
        except Exception as exc:
            errors.record(
                f"novel_association_log read failed: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )
            return ""

        if row is None:
            return ""

        self._writer.write(
            "UPDATE novel_association_log SET annotated_at = ? WHERE id = ?",
            (now, row["id"]),
        )
        br_a = row["branch_id_a"]
        br_b = row["branch_id_b"]
        sim  = float(row["similarity"])
        return (
            f"Self-observation: I notice a cross-domain connection between "
            f"{br_a} and {br_b} thinking (similarity {sim:.2f})."
        )

    def start_loop(self) -> None:
        """Start background scan thread. Call once from run.py at boot."""
        t = threading.Thread(
            target=self._loop, daemon=True, name="novel_association_loop"
        )
        t.start()

    # ── internal ─────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        while True:
            time.sleep(_LOOP_INTERVAL_S)
            try:
                # Force scan regardless of interval (loop already sleeps the interval)
                with self._lock:
                    self._last_scan_at = 0.0
                self.tick()
            except Exception as exc:
                errors.record(f"loop error: {exc}", source=_LOG_SOURCE, exc=exc)

    def _scan(self, now: float) -> int:
        """Pull candidates, find cross-branch pairs, write edges + log. Returns edge count."""
        candidates = self._pull_candidates()
        if len(candidates) < 2:
            return 0

        try:
            from theory_x.diversity.embeddings import embed_belief, cosine
        except Exception as exc:
            errors.record(
                f"embedding import failed: {exc}", source=_LOG_SOURCE, exc=exc
            )
            return 0

        written = 0
        for a, b in combinations(candidates, 2):
            if a["branch_id"] == b["branch_id"]:
                continue
            try:
                emb_a = embed_belief(a["id"], a["content"])
                emb_b = embed_belief(b["id"], b["content"])
                sim = cosine(emb_a, emb_b)
            except Exception as exc:
                errors.record(f"embedding failed: {exc}", source=_LOG_SOURCE, exc=exc)
                continue

            if sim < _SIMILARITY_THRESHOLD:
                continue

            self._write_association(a, b, sim, now)
            written += 1

            if self._self_narrative is not None and sim >= _NARRATIVE_THRESHOLD:
                try:
                    self._self_narrative.write_narrative(
                        f"Strong cross-domain connection: "
                        f"{a['branch_id']} ↔ {b['branch_id']} "
                        f"(similarity {sim:.2f})",
                        "novel_association_crossing",
                        None,
                    )
                except Exception as exc:
                    errors.record(
                        f"self_narrative novel_association trigger: {exc}",
                        source=_LOG_SOURCE, exc=exc,
                    )

        return written

    def _pull_candidates(self) -> list[dict]:
        """Per-branch sample: fully include small branches, cap large ones at _BATCH_SIZE.

        # PHASE 17 fix 2026-05-09: per-branch cap is conditional.
        # Original 2-per-branch cap under-sampled small branches (13-16 beliefs
        # each) while only meaningfully capping the systems branch (1447 beliefs).
        # Surfaced when belief id=9468 (cognition_science, 3rd most recent) paired
        # above threshold with multiple emerging_tech beliefs but never appeared in
        # the candidate set. Fix: branches with < _BATCH_SIZE beliefs are fully
        # sampled; branches with >= _BATCH_SIZE beliefs are capped at _BATCH_SIZE.
        """
        try:
            rows = self._reader.read(
                "SELECT id, content, branch_id FROM beliefs "
                "WHERE confidence >= 0.15 AND branch_id IS NOT NULL AND paused = 0 "
                "ORDER BY branch_id, id DESC",
                (),
            )
        except Exception as exc:
            errors.record(f"candidate pull failed: {exc}", source=_LOG_SOURCE, exc=exc)
            return []

        by_branch: dict[str, list[dict]] = {}
        for row in rows:
            br = row["branch_id"]
            if br not in by_branch:
                by_branch[br] = []
            by_branch[br].append(dict(row))

        if not by_branch:
            return []

        result: list[dict] = []
        for branch_rows in by_branch.values():
            # Fully sample small branches; cap large ones at _BATCH_SIZE.
            cap = len(branch_rows) if len(branch_rows) < _BATCH_SIZE else _BATCH_SIZE
            result.extend(branch_rows[:cap])
        return result

    def _write_association(
        self, a: dict, b: dict, sim: float, now: float
    ) -> None:
        try:
            self._writer.write(
                "INSERT OR IGNORE INTO belief_edges "
                "(source_id, target_id, edge_type, weight, created_at) "
                "VALUES (?, ?, 'synthesises', ?, ?)",
                (a["id"], b["id"], sim, now),
            )
            self._writer.write(
                "INSERT OR IGNORE INTO novel_association_log "
                "(detected_at, belief_id_a, belief_id_b, "
                "branch_id_a, branch_id_b, similarity) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (now, a["id"], b["id"], a["branch_id"], b["branch_id"], sim),
            )
            errors.record(
                f"novel association: {a['branch_id']} ↔ {b['branch_id']} "
                f"(sim {sim:.2f})",
                source=_LOG_SOURCE, level="INFO",
            )
        except Exception as exc:
            errors.record(
                f"write_association failed: {exc}", source=_LOG_SOURCE, exc=exc
            )
