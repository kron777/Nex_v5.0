"""PredictiveSubstrate — Phase 35 (PREDICTION_PROTOCOL.md).

SentienceNode: dual-stream predictive engine.
- internal_belief: forecasts next-belief region from weighted centroid of
  recent beliefs + open problems + current drive.
- external_input: forecasts next-input region from recent sense/chat embeddings.

Per-tick flow: verify() (resolves prior window) then predict() (generates
next window). No LLM call. All centroid math from substrate embeddings.

Tick interval: 300s matching CounterfactualNode / AffectState / DriveEmergence.
Storage: predictions + surprise_events tables in dynamic.db (Phase 35 migration).
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any, Optional

import numpy as np

import errors

_LOG_SOURCE = "predictive_substrate"


def _generate_tags(content: str) -> list:
    if not content or not content.strip():
        return []
    try:
        from theory_x.tag_protocol.tag_ops import generate
        return generate(content)
    except Exception:
        return []


class PredictiveSubstrate:
    """SentienceNode: substrate's predictive engine.

    Per PREDICTION_PROTOCOL.md. Per-tick: verify() prior predictions,
    then predict() for the next window.
    """

    # §9 calibration constants
    _TICK_INTERVAL_S      = 300
    _RECENT_BELIEF_COUNT  = 10
    _RECENT_INPUT_COUNT   = 10
    _MIN_CONTEXT_SIZE     = 3
    _BELIEF_WEIGHT        = 0.6
    _PROBLEM_WEIGHT       = 0.3
    _DRIVE_WEIGHT         = 0.1
    _SURPRISE_THRESHOLD   = 0.5
    _BIG_SURPRISE_THRESHOLD = 0.8
    _SURPRISE_AROUSAL_FACTOR = 0.2  # used by future AffectState amendment, not here

    name: str = "predictive_substrate"

    def __init__(
        self,
        dynamic_reader,
        dynamic_writer,
        beliefs_reader,
        conversations_reader,
        sense_reader,
        drive_emergence=None,
        interval_seconds: float = _TICK_INTERVAL_S,
    ) -> None:
        self._dr = dynamic_reader
        self._dw = dynamic_writer
        self._br = beliefs_reader
        self._cr = conversations_reader
        self._sr = sense_reader
        self._drive_emergence = drive_emergence
        self._interval = interval_seconds

        self._stop: Optional[threading.Event] = None
        self._thread: Optional[threading.Thread] = None

        self._tick_count: int = 0
        self._total_predictions_made: int = 0
        self._total_verified: int = 0
        self._last_tick_at: float = 0.0

    # ── SentienceNode protocol ────────────────────────────────────────────────

    def tick(self, context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        now = time.time()
        if now - self._last_tick_at < self._TICK_INTERVAL_S:
            return {"name": self.name, "skipped": True, "tick_count": self._tick_count}
        self._last_tick_at = now

        verified = 0
        internal_made = 0
        external_made = 0
        try:
            verified = self._verify()
        except Exception as exc:
            errors.record(f"predictive_substrate verify error: {exc}",
                          source=_LOG_SOURCE, exc=exc)
        try:
            internal_made = self._predict_internal()
        except Exception as exc:
            errors.record(f"predictive_substrate predict_internal error: {exc}",
                          source=_LOG_SOURCE, exc=exc)
        try:
            external_made = self._predict_external()
        except Exception as exc:
            errors.record(f"predictive_substrate predict_external error: {exc}",
                          source=_LOG_SOURCE, exc=exc)

        self._tick_count += 1
        self._total_predictions_made += internal_made + external_made
        self._total_verified += verified

        errors.record(
            f"PredictiveSubstrate tick {self._tick_count}: "
            f"verified={verified} internal={internal_made} external={external_made}",
            source=_LOG_SOURCE, level="INFO",
        )
        return self.state()

    def decay(self, now: float) -> None:
        pass  # all state lives in DB; no in-memory decay

    def state(self, now: Optional[float] = None) -> dict[str, Any]:
        return {
            "name": self.name,
            "tick_count": self._tick_count,
            "total_predictions_made": self._total_predictions_made,
            "total_verified": self._total_verified,
            "interval_seconds": self._interval,
        }

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start_loop(self, interval_seconds: Optional[float] = None) -> None:
        interval = interval_seconds if interval_seconds is not None else self._interval
        self._stop = threading.Event()

        def _run() -> None:
            while not self._stop.is_set():
                self._stop.wait(interval)
                if not self._stop.is_set():
                    self.tick()

        self._thread = threading.Thread(
            target=_run,
            name="predictive_substrate",
            daemon=True,
        )
        self._thread.start()
        errors.record(
            f"predictive_substrate loop started (interval={int(interval)}s)",
            source=_LOG_SOURCE, level="INFO",
        )

    def stop(self) -> None:
        if self._stop is not None:
            self._stop.set()

    # ── Embedding helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _embed(text: str) -> np.ndarray:
        from theory_x.diversity.embeddings import embed
        return embed(text)

    @staticmethod
    def _embed_belief(belief_id: int, content: str) -> np.ndarray:
        from theory_x.diversity.embeddings import embed_belief
        return embed_belief(belief_id, content)

    @staticmethod
    def _dist(a: np.ndarray, b: np.ndarray) -> float:
        from theory_x.diversity.embeddings import distance
        return distance(a, b)

    @staticmethod
    def _normalize(v: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(v)
        return v / norm if norm > 0 else v

    # ── Prediction generation ─────────────────────────────────────────────────

    def _predict_internal(self) -> int:
        """§4.1 — internal_belief prediction from beliefs + problems + drive."""
        beliefs = self._br.read(
            "SELECT id, content FROM beliefs ORDER BY created_at DESC LIMIT ?",
            (self._RECENT_BELIEF_COUNT,),
        )
        if len(beliefs) < self._MIN_CONTEXT_SIZE:
            return 0

        belief_embs = np.array([
            self._embed_belief(int(b["id"]), b["content"] or "")
            for b in beliefs
        ], dtype=np.float32)
        centroid = self._BELIEF_WEIGHT * np.mean(belief_embs, axis=0)

        problems = self._cr.read(
            "SELECT title FROM open_problems WHERE state = 'open' ORDER BY created_at DESC"
        )
        if problems:
            prob_embs = np.array([
                self._embed(p["title"] or "") for p in problems
            ], dtype=np.float32)
            centroid += self._PROBLEM_WEIGHT * np.mean(prob_embs, axis=0)

        drive_emb: Optional[np.ndarray] = None
        if self._drive_emergence is not None:
            try:
                drive_emb = self._drive_emergence.drive_topic_embedding()
            except Exception:
                pass
        if drive_emb is not None:
            centroid += self._DRIVE_WEIGHT * np.array(drive_emb, dtype=np.float32)

        centroid = self._normalize(centroid)
        rep = self._nearest_content(centroid, beliefs)
        self._write_prediction("internal_belief", centroid, rep)
        return 1

    def _predict_external(self) -> int:
        """§4.2 — external_input prediction from sense events + chat messages."""
        sense_rows = self._sr.read(
            "SELECT payload AS content FROM sense_events "
            "WHERE stream NOT LIKE 'internal.%' "
            "ORDER BY timestamp DESC LIMIT ?",
            (self._RECENT_INPUT_COUNT,),
        )
        msg_rows = self._cr.read(
            "SELECT content FROM messages WHERE role = 'user' "
            "ORDER BY timestamp DESC LIMIT ?",
            (self._RECENT_INPUT_COUNT,),
        )
        inputs = [r["content"] for r in list(sense_rows) + list(msg_rows)
                  if r["content"] and r["content"].strip()]
        inputs = inputs[: self._RECENT_INPUT_COUNT]

        if len(inputs) < self._MIN_CONTEXT_SIZE:
            return 0

        input_embs = np.array([
            self._embed(c[:500]) for c in inputs
        ], dtype=np.float32)
        centroid = self._normalize(np.mean(input_embs, axis=0))

        # Representative: nearest sense/msg content to centroid, beliefs as fallback
        rep = self._nearest_content(centroid, [{"content": c} for c in inputs])
        if rep is None:
            belief_rows = self._br.read(
                "SELECT id, content FROM beliefs ORDER BY created_at DESC LIMIT 20"
            )
            rep = self._nearest_content(centroid, belief_rows)
        self._write_prediction("external_input", centroid, rep)
        return 1

    def _nearest_content(
        self,
        centroid: np.ndarray,
        items: list,
    ) -> Optional[str]:
        """Return content of the item in `items` closest to centroid.

        Accepts both sqlite3.Row objects and plain dicts.
        """
        best_dist = 2.0
        best_content: Optional[str] = None
        for item in items:
            try:
                content = item["content"] or ""
            except (KeyError, TypeError):
                continue
            if not content.strip():
                continue
            try:
                try:
                    belief_id = item["id"]
                except (KeyError, IndexError):
                    belief_id = None
                emb = (
                    self._embed_belief(int(belief_id), content)
                    if belief_id is not None
                    else self._embed(content[:500])
                )
                d = self._dist(centroid, emb)
                if d < best_dist:
                    best_dist = d
                    best_content = content
            except Exception:
                continue
        return best_content

    def _write_prediction(
        self,
        prediction_type: str,
        centroid: np.ndarray,
        rep_content: Optional[str],
    ) -> None:
        now = time.time()
        tags = json.dumps(_generate_tags(rep_content or ""))
        self._dw.write(
            "INSERT INTO predictions "
            "(made_at, target_window_end, prediction_type, centroid_embedding, "
            "representative_content, tags) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (now, now + self._interval,
             prediction_type,
             centroid.astype(np.float32).tobytes(),
             rep_content, tags),
        )

    # ── Verification ──────────────────────────────────────────────────────────

    def _verify(self) -> int:
        """§5 — resolve prior-window predictions, write surprise_events."""
        now = time.time()
        pending = self._dr.read(
            "SELECT id, prediction_type, centroid_embedding, "
            "representative_content, made_at, target_window_end "
            "FROM predictions "
            "WHERE target_window_end <= ? AND verified_at IS NULL",
            (now,),
        )
        count = 0
        for pred in pending:
            try:
                self._verify_one(pred, now)
                count += 1
            except Exception as exc:
                errors.record(
                    f"predictive_substrate verify_one id={pred['id']} error: {exc}",
                    source=_LOG_SOURCE, exc=exc,
                )
        return count

    def _verify_one(self, pred: Any, now: float) -> None:
        centroid = np.frombuffer(bytes(pred["centroid_embedding"]), dtype=np.float32)
        window_start = float(pred["made_at"])
        window_end = float(pred["target_window_end"])

        if pred["prediction_type"] == "internal_belief":
            items = self._br.read(
                "SELECT id, content FROM beliefs "
                "WHERE created_at >= ? AND created_at <= ?",
                (window_start, window_end),
            )
        else:
            sense_items = self._sr.read(
                "SELECT payload AS content FROM sense_events "
                "WHERE timestamp >= ? AND timestamp <= ?",
                (window_start, window_end),
            )
            msg_items = self._cr.read(
                "SELECT content FROM messages "
                "WHERE timestamp >= ? AND timestamp <= ? AND role = 'user'",
                (window_start, window_end),
            )
            items = list(sense_items) + list(msg_items)

        surprise_score: float
        actual_content: Optional[str]

        if not items:
            surprise_score = 1.0
            actual_content = None
        else:
            min_dist = 1.0
            nearest: Optional[str] = None
            for item in items:
                try:
                    content = item["content"] or ""
                except (KeyError, TypeError):
                    continue
                if not content.strip():
                    continue
                try:
                    try:
                        belief_id = item["id"]
                    except (KeyError, IndexError):
                        belief_id = None
                    emb = (
                        self._embed_belief(int(belief_id), content)
                        if belief_id is not None
                        else self._embed(content[:500])
                    )
                    d = self._dist(centroid, emb)
                    if d < min_dist:
                        min_dist = d
                        nearest = content[:200]
                except Exception:
                    continue
            surprise_score = min_dist
            actual_content = nearest

        surprise_flag = 1 if surprise_score > self._SURPRISE_THRESHOLD else 0
        big_surprise = 1 if surprise_score > self._BIG_SURPRISE_THRESHOLD else 0

        tags = json.dumps(_generate_tags(
            (pred["representative_content"] or "") + " " + (actual_content or "")
        ))
        triggered_at = now
        self._dw.write(
            "INSERT INTO surprise_events "
            "(triggered_at, prediction_id, prediction_type, surprise_score, "
            "surprise_flag, big_surprise, predicted_content, actual_content, tags) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (triggered_at, pred["id"], pred["prediction_type"],
             surprise_score, surprise_flag, big_surprise,
             pred["representative_content"], actual_content, tags),
        )
        self._dw.write(
            "UPDATE predictions SET verified_at=?, surprise_score=?, surprise_flag=? "
            "WHERE id=?",
            (triggered_at, surprise_score, surprise_flag, pred["id"]),
        )

    # ── Public read API ───────────────────────────────────────────────────────

    def recent_predictions(
        self, limit: int = 20, type: Optional[str] = None
    ) -> list[dict]:
        if type:
            rows = self._dr.read(
                "SELECT id, made_at, target_window_end, prediction_type, "
                "representative_content, surprise_score, surprise_flag, tags "
                "FROM predictions WHERE prediction_type = ? "
                "ORDER BY made_at DESC LIMIT ?",
                (type, limit),
            )
        else:
            rows = self._dr.read(
                "SELECT id, made_at, target_window_end, prediction_type, "
                "representative_content, surprise_score, surprise_flag, tags "
                "FROM predictions ORDER BY made_at DESC LIMIT ?",
                (limit,),
            )
        return [dict(r) for r in rows]

    def recent_surprises(self, limit: int = 20, big_only: bool = False) -> list[dict]:
        if big_only:
            rows = self._dr.read(
                "SELECT * FROM surprise_events WHERE big_surprise = 1 "
                "ORDER BY triggered_at DESC LIMIT ?",
                (limit,),
            )
        else:
            rows = self._dr.read(
                "SELECT * FROM surprise_events ORDER BY triggered_at DESC LIMIT ?",
                (limit,),
            )
        return [dict(r) for r in rows]

    def surprise_rate(self, window_seconds: float = 3600.0) -> float:
        """Fraction of predictions in window that triggered surprise_flag=1."""
        cutoff = time.time() - window_seconds
        rows = self._dr.read(
            "SELECT COUNT(*) AS total, SUM(surprise_flag) AS flagged "
            "FROM predictions WHERE verified_at IS NOT NULL AND verified_at >= ?",
            (cutoff,),
        )
        if not rows or not rows[0]["total"]:
            return 0.0
        return float(rows[0]["flagged"] or 0) / float(rows[0]["total"])
