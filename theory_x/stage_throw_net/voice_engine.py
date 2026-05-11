"""VoiceEngine — substrate-as-voice (Phase 30, DOCTRINE §5 row 14).

Replaces the LLM in the chat reply path when in use_substrate mode.
Retrieves the highest-relevance candidate from NEX's belief substrate,
scores it against the user query using a five-axis grader, and returns
it as NEX's reply. The LLM is not called for that turn.

Five-axis grader (Phase 29 §4):
  semantic       0.45 — cosine similarity between query and candidate
  confidence     0.23 — beliefs.confidence; non-belief sources default 0.5
  tier           0.14 — T3-T6 score 1.0; non-belief sources default 0.7
  recency        0.08 — min(1.0, reinforce_count / 10); non-belief default 0.3
  drive_alignment 0.10 — cosine(candidate_emb, drive_topic_emb); 0.0 if no drive

min_score = 0.6 (conservative v1). Returns None when no candidate
clears the threshold — chat handler falls through to LLM unchanged.
"""
from __future__ import annotations

import json
import time
from typing import Any, Optional

import numpy as np

import errors
from substrate import Reader, Writer
from theory_x.stage_throw_net.time_fetch import TimeFetch

__all__ = ["VoiceEngine"]

THEORY_X_STAGE = "voice_engine"

_LOG_SOURCE = "voice_engine"

_SEMANTIC_W       = 0.45
_CONFIDENCE_W     = 0.23
_TIER_W           = 0.14
_RECENCY_W        = 0.08
_DRIVE_ALIGN_W    = 0.10

# T3-T6 are the productive insight tiers.
_GOOD_TIERS = frozenset({3, 4, 5, 6})


class VoiceEngine:
    """Retrieve-and-score reply engine using NEX's belief substrate.

    Implements SentienceNode protocol (DOCTRINE §4).
    tick() is called inline from the chat handler — no daemon thread.
    """

    name: str = "voice_engine"

    def __init__(
        self,
        beliefs_reader: Reader,
        problem_memory,
        beliefs_writer: Writer,
        min_score: float = 0.6,
        drive_emergence=None,
    ) -> None:
        self._reader = beliefs_reader
        self._writer = beliefs_writer
        self._time_fetch = TimeFetch(beliefs_reader, problem_memory)
        self.min_score = min_score
        self._drive_emergence = drive_emergence
        self._reply_count: int = 0
        self._miss_count: int = 0
        self._last_score: Optional[float] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def query_reply(
        self,
        query: str,
        session_id: Optional[str] = None,
        turn_n: int = 0,
    ) -> Optional[dict[str, Any]]:
        """Retrieve highest-relevance candidate for the user query.

        Returns {"content", "score", "source", "belief_id"} or None.
        Never raises.
        """
        try:
            candidates = self._retrieve_candidates(query)
            if not candidates:
                self._miss_count += 1
                self._record_query_trigger(
                    query, session_id, turn_n, None, 0.0, False
                )
                return None

            query_emb = self._embed(query)

            best_candidate = None
            best_score = 0.0
            for c in candidates:
                s = self._score_candidate(c, query_emb)
                if s > best_score:
                    best_score = s
                    best_candidate = c

            self._last_score = best_score
            used = best_score >= self.min_score and best_candidate is not None

            self._record_query_trigger(
                query, session_id, turn_n, best_candidate, best_score, used
            )

            if used:
                self._reply_count += 1
                return {
                    "content": best_candidate["content"],
                    "score": best_score,
                    "source": best_candidate.get("source", "unknown"),
                    "belief_id": best_candidate.get("origin_id"),
                }

            self._miss_count += 1
            return None

        except Exception as exc:
            errors.record(
                f"voice_engine.query_reply: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )
            self._miss_count += 1
            return None

    # ── SentienceNode protocol ────────────────────────────────────────────────

    def tick(self, context=None) -> dict[str, Any]:
        return self.state()

    def decay(self, now: float) -> None:
        pass

    def state(self, now: float = None) -> dict[str, Any]:
        return {
            "name": self.name,
            "reply_count": self._reply_count,
            "miss_count": self._miss_count,
            "last_score": self._last_score,
            "min_score": self.min_score,
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _retrieve_candidates(self, query: str) -> list[dict[str, Any]]:
        """TimeFetch.run(query) → enriched candidate pool."""
        try:
            raw = self._time_fetch.run(query)
        except Exception as exc:
            errors.record(
                f"voice_engine._retrieve_candidates: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )
            return []

        if not raw:
            return []

        # Enrich belief-source candidates with tier + reinforce_count.
        belief_ids = [
            c["origin_id"]
            for c in raw
            if c.get("source") == "belief" and c.get("origin_id") is not None
        ]
        tier_map: dict[int, int] = {}
        reinforce_map: dict[int, int] = {}
        if belief_ids:
            try:
                placeholders = ",".join("?" * len(belief_ids))
                rows = self._reader.read(
                    f"SELECT id, tier, reinforce_count FROM beliefs WHERE id IN ({placeholders})",
                    tuple(belief_ids),
                )
                for r in rows:
                    tier_map[r["id"]] = r["tier"]
                    reinforce_map[r["id"]] = r["reinforce_count"] or 0
            except Exception as exc:
                errors.record(
                    f"voice_engine tier enrichment: {exc}",
                    source=_LOG_SOURCE, exc=exc,
                )

        enriched = []
        for c in raw:
            ec = dict(c)
            if c.get("source") == "belief" and c.get("origin_id") is not None:
                oid = c["origin_id"]
                ec["tier"] = tier_map.get(oid)
                ec["reinforce_count"] = reinforce_map.get(oid, 0)
            enriched.append(ec)

        return enriched

    def _embed(self, text: str) -> np.ndarray:
        """Embed text; return zero vector on failure."""
        try:
            from theory_x.diversity.embeddings import embed
            return embed(text)
        except Exception:
            return np.zeros(384, dtype=np.float32)

    def _score_candidate(
        self,
        candidate: dict[str, Any],
        query_emb: np.ndarray,
        candidate_emb: Optional[np.ndarray] = None,
    ) -> float:
        """Five-axis weighted score. Returns 0.0 on any error."""
        try:
            # Semantic axis
            try:
                from theory_x.diversity.embeddings import embed, cosine
                if candidate_emb is None:
                    candidate_emb = embed(candidate["content"])
                semantic = cosine(query_emb, candidate_emb)
            except Exception:
                semantic = 0.0

            # Confidence axis
            conf = candidate.get("confidence")
            if conf is None:
                conf = 0.5
            confidence = float(conf)

            # Tier axis
            tier = candidate.get("tier")
            if tier is None:
                tier_score = 0.7
            else:
                tier_score = 1.0 if int(tier) in _GOOD_TIERS else 0.5

            # Recency axis
            rc = candidate.get("reinforce_count")
            if rc is None:
                recency = 0.3
            else:
                recency = min(1.0, int(rc) / 10.0)

            # Drive alignment axis (Phase 29)
            drive_alignment = 0.0
            if self._drive_emergence is not None:
                try:
                    drive_emb = self._drive_emergence.drive_topic_embedding()
                    if drive_emb is not None and candidate_emb is not None:
                        from theory_x.diversity.embeddings import cosine
                        drive_alignment = cosine(candidate_emb, drive_emb)
                except Exception:
                    pass

            return (
                _SEMANTIC_W    * semantic
                + _CONFIDENCE_W  * confidence
                + _TIER_W        * tier_score
                + _RECENCY_W     * recency
                + _DRIVE_ALIGN_W * drive_alignment
            )
        except Exception as exc:
            errors.record(
                f"voice_engine._score_candidate: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )
            return 0.0

    def _record_query_trigger(
        self,
        query: str,
        session_id: Optional[str],
        turn_n: int,
        best_candidate: Optional[dict[str, Any]],
        best_score: float,
        used_as_reply: bool,
    ) -> None:
        """Fire-and-forget write to throw_net_triggers. Never raises."""
        try:
            self._writer.write(
                "INSERT INTO throw_net_triggers "
                "(ts, trigger_type, topic, source_event_id, "
                "threshold_state, fired, session_id) "
                "VALUES (?, 'user_query', ?, ?, ?, ?, ?)",
                (
                    time.time(),
                    query[:120],
                    f"{session_id or 'unknown'}:turn_{turn_n}",
                    json.dumps({
                        "score": round(best_score, 4),
                        "candidate_source": best_candidate.get("source") if best_candidate else None,
                        "used_as_reply": used_as_reply,
                    }),
                    1 if used_as_reply else 0,
                    session_id if used_as_reply else None,
                ),
            )
        except Exception as exc:
            errors.record(
                f"voice_engine._record_query_trigger: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )
