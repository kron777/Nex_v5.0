"""Intake resonance probe — Carryx §8 Step 1.

Measures how strongly a newly-crystallized belief resonates with the
authored keystone library (T1-T3). Pure measurement; does not yet change
tier or behavior. Foundation for §8 Step 2 (tier mapping by resonance)
which we will build after observing actual resonance distribution.

Per carryx §8:
  - Compute: embed the incoming content (cheap, model already loaded)
  - Compare: cosine vs her existing belief graph (here: keystones)
  - HIGH resonance: "this is mine, I have a stance"
  - NO connection: most items (crypto prices, trailers)
  - LLM-per-item is NON-STARTER — only embedding work here.

This module is hot-path adjacent: hooked into Crystallizer._write_belief
before INSERT. Must never raise (probe is observational). Must be cheap
once keystones are cached (one embedding call + N cosines, N=~362).

Set NEX5_INTAKE_RESONANCE_OFF=1 to disable at runtime.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Optional

log = logging.getLogger("theory_x.stage2_dynamic.intake_resonance")

# Tiers considered "standing-points" for the comparison (the authored
# library). Per the substrate doctrine: depth lives in keystones.
_STANDING_TIERS = (1, 2, 3)

# How many recent striking T6 beliefs to also include in the standing set.
# These are her own crystallized voice (genuine Mode A) — also part of
# the standing-points she should be resonating with.
_STRIKING_T6_LIMIT = 200


class IntakeResonance:
    """Compute resonance score for incoming belief content.

    Lazy embedding: keystones are embedded on first access and cached in
    the diversity.embeddings LRU. Cold start is one-time work (~362
    embeddings, ~15-30s); subsequent calls are sub-millisecond.
    """

    def __init__(
        self,
        beliefs_reader,
        beliefs_writer,
        prewarm: bool = True,
    ) -> None:
        self._beliefs_reader = beliefs_reader
        self._beliefs_writer = beliefs_writer
        self._standing_ids: list[int] = []
        self._standing_content: dict[int, str] = {}
        self._standing_loaded: bool = False
        self._load_lock = threading.Lock()
        # Stats
        self._compute_count: int = 0
        self._error_count: int = 0
        self._last_resonance: Optional[float] = None
        if prewarm:
            # Load standing-points list (just IDs + content, embedding deferred)
            self._load_standing_points()

    def _load_standing_points(self) -> None:
        """Build the list of belief IDs and content for comparison."""
        if self._standing_loaded:
            return
        with self._load_lock:
            if self._standing_loaded:
                return
            import os as _os
            _tight = _os.environ.get("NEX5_INTAKE_TIGHT_CORE") == "1"
            _tiers = (1, 2) if _tight else _STANDING_TIERS
            try:
                tier_placeholders = ",".join("?" * len(_tiers))
                rows = self._beliefs_reader.read(
                    f"SELECT id, content FROM beliefs "
                    f"WHERE tier IN ({tier_placeholders}) AND content IS NOT NULL "
                    f"AND length(content) > 8",
                    _tiers,
                )
                for r in (rows or []):
                    self._standing_ids.append(int(r["id"]))
                    self._standing_content[int(r["id"])] = r["content"]
                # Also include T6 beliefs with high affinity (her crystallized voice)
                t6_rows = [] if _tight else self._beliefs_reader.read(
                    "SELECT id, content FROM beliefs "
                    "WHERE tier = 6 AND content IS NOT NULL "
                    "AND length(content) > 8 "
                    "ORDER BY COALESCE(affinity, 0) DESC, "
                    "         COALESCE(reinforce_count, 0) DESC "
                    "LIMIT ?",
                    (_STRIKING_T6_LIMIT,),
                )
                for r in (t6_rows or []):
                    self._standing_ids.append(int(r["id"]))
                    self._standing_content[int(r["id"])] = r["content"]
                self._standing_loaded = True
                log.info(
                    "intake_resonance: standing-points loaded "
                    "(mode=%s, %d total)",
                    "TIGHT(T1-T2)" if _tight else "BROAD(T1-T3+T6)",
                    len(self._standing_ids),
                )
            except Exception as exc:
                log.warning("intake_resonance: load standing-points failed: %s", exc)

    def compute(self, content: str) -> Optional[dict]:

        self._enter_count = getattr(self, '_enter_count', 0) + 1

        if self._enter_count <= 5 or self._enter_count % 50 == 0:

            log.info('intake_resonance: compute() called #%d (standing_loaded=%s)', self._enter_count, self._standing_loaded)
        """Return resonance dict for `content`, or None on failure / disabled.

        Result keys:
            resonance:        max cosine vs standing-points
            top_match_id:     belief id of the best-matching keystone
            top_match_score:  same as resonance (alias)
            standing_size:    how many beliefs we compared against
            ts:               wall-clock seconds when computed
        """
        if os.environ.get("NEX5_INTAKE_RESONANCE_OFF") == "1":
            return None
        if not content or len(content) < 8:
            return None
        self._load_standing_points()
        if not self._standing_ids:
            return None
        try:
            from theory_x.diversity.embeddings import embed, embed_belief, cosine
        except Exception as exc:
            self._error_count += 1
            log.warning("intake_resonance: embeddings unavailable: %s", exc)
            return None
        try:
            new_emb = embed(content)
        except Exception as exc:
            self._error_count += 1
            log.warning("intake_resonance: embed failed: %s", exc)
            return None

        best_id: Optional[int] = None
        best_cos: float = -1.0
        for bid in self._standing_ids:
            try:
                bemb = embed_belief(bid, self._standing_content[bid])
                c = cosine(new_emb, bemb)
                if c > best_cos:
                    best_cos = c
                    best_id = bid
            except Exception:
                continue

        self._compute_count += 1
        self._last_resonance = best_cos
        # Persist a log row (low priority — never block on this)
        try:
            self._beliefs_writer.write(
                "INSERT INTO intake_resonance_log "
                "(content, resonance, top_match_belief_id, ts) "
                "VALUES (?, ?, ?, ?)",
                (content[:500], float(best_cos), best_id, time.time()),
            )
            self._write_count = getattr(self, "_write_count", 0) + 1
            if self._write_count <= 5 or self._write_count % 25 == 0:
                log.info("intake_resonance: WROTE row #%d (res=%.3f) for: %s",
                         self._write_count, float(best_cos), content[:50])
        except Exception as exc:
            self._error_count += 1
            self._last_error = repr(exc)
            log.warning("intake_resonance: WRITE FAILED (#%d): %r | content=%s",
                        self._error_count, exc, content[:50])
        return {
            "resonance": float(best_cos),
            "top_match_id": best_id,
            "top_match_score": float(best_cos),
            "standing_size": len(self._standing_ids),
            "ts": time.time(),
        }

    def status(self) -> dict:
        return {
            "standing_size": len(self._standing_ids),
            "compute_count": self._compute_count,
            "error_count": self._error_count,
            "last_resonance": self._last_resonance,
            "disabled": (
                os.environ.get("NEX5_INTAKE_RESONANCE_OFF") == "1"
            ),
        }
