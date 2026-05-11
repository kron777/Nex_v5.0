"""DriveEmergence — Phase 29 (DOCTRINE §5 row 13).

Substrate-resident emergent drive detector. Detects when NEX has been
repeatedly returning to the same topic across multiple belief branches —
without having declared it as a goal or problem.

Background tick (600s) reads the belief field, clusters by cosine similarity,
scores each cluster on BOTH repetition (sustained reinforce_count) AND
convergence (multiple distinct branch_ids). Neither signal alone is sufficient.

Single-row table: drives.id = 1 always (INSERT OR REPLACE).
Row deleted when no drive qualifies — never stale. format_for_prompt()
returns "" when the row is absent. §0 aligned: substrate solves, LLM speaks.

Detection math (§2 of DRIVE_EMERGENCE_SPEC):
  repetition_score  = (sum use_counts / cluster_size) × recency_weight
  convergence_score = distinct_branch_ids / total_beliefs_in_cluster
  drive_strength    = 0.6 × rep + 0.4 × conv
  Decay: drive_strength *= 0.92 each tick; delete when below 0.25.

Topic synthesis is deterministic (§3): confidence-weighted word frequencies
from source beliefs. No LLM call.
"""
from __future__ import annotations

import json
import re
import sys
import threading
import time
from collections import Counter
from typing import Any, Optional

import errors
from substrate import Reader, Writer

__all__ = ["DriveEmergence"]

THEORY_X_STAGE = "drives"

_LOG_SOURCE = "drive_emergence"
_DRIVE_LOG  = "/tmp/nex5_drive_emergence.log"

# Detection windows and thresholds
_WINDOW_DAYS         = 14     # how far back to scan beliefs
_RECENCY_WINDOW_DAYS = 7      # window for recency weight in repetition_score
_MIN_CLUSTER_SIZE    = 4      # smallest qualifying cluster
_MIN_REPETITION      = 0.3    # minimum repetition_score
_MIN_CONVERGENCE     = 0.25   # minimum convergence_score (fraction of distinct branches)
_MIN_BRANCH_COUNT    = 2      # at least 2 distinct branches required
_MIN_DRIVE_STRENGTH  = 0.25   # delete drive below this after decay

# Clustering
_CLUSTER_SIMILARITY = 0.70    # cosine threshold for centroid-based grouping
_CANDIDATE_LIMIT    = 200     # cap on beliefs pulled per tick

# Weights
_W_REP  = 0.6
_W_CONV = 0.4

# Lifecycle
_DECAY_RATE      = 0.92   # per tick
_TICK_INTERVAL_S = 600    # 10 minutes

_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "not", "this",
    "that", "these", "those", "it", "its", "i", "we", "you", "they",
    "he", "she", "as", "if", "so", "no", "my", "our", "their",
})


def _tokens(text: str) -> list[str]:
    words = re.sub(r"[^\w\s]", " ", text.lower()).split()
    return [w for w in words if w not in _STOPWORDS and len(w) > 2]


def _repetition_score(cluster: list[dict], now: float) -> float:
    recency_cutoff = now - _RECENCY_WINDOW_DAYS * 86400
    recent_n = sum(1 for b in cluster if (b.get("created_at") or 0) > recency_cutoff)
    recency_weight = recent_n / len(cluster)
    total_uc = sum(int(b.get("use_count") or 0) for b in cluster)
    return (total_uc / len(cluster)) * recency_weight


def _convergence_score(cluster: list[dict]) -> float:
    distinct = {b["branch_id"] for b in cluster if b.get("branch_id")}
    return len(distinct) / len(cluster)


def _cosine(a: Any, b: Any) -> float:
    import numpy as np
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0 or nb == 0:
        return 0.0
    sim = float(np.dot(a, b) / (na * nb))
    return (sim + 1.0) / 2.0


def _cluster(
    candidates: list[dict],
    embeddings: dict[int, Any],
    threshold: float,
) -> list[list[dict]]:
    """Centroid-based clustering. Each belief joins the cluster whose centroid
    cosine similarity is highest and meets threshold. Prevents single-linkage
    chaining — centroid always represents the semantic mean of all members."""
    import numpy as np
    clusters:  list[list[dict]] = []
    centroids: list[Any]        = []

    for cand in candidates:
        cid = cand["id"]
        emb = embeddings.get(cid)
        if emb is None:
            continue
        best_i   = -1
        best_sim = threshold  # must exceed threshold to join
        for i, cent in enumerate(centroids):
            sim = _cosine(emb, cent)
            if sim > best_sim:
                best_sim = sim
                best_i   = i
        if best_i >= 0:
            n = len(clusters[best_i])
            centroids[best_i] = (centroids[best_i] * n + emb) / (n + 1)
            clusters[best_i].append(cand)
        else:
            clusters.append([cand])
            centroids.append(np.array(emb, dtype=np.float32))

    return clusters


def _synthesize_topic(cluster: list[dict]) -> str:
    """Confidence-weighted word frequency topic. No LLM. Deterministic."""
    word_weights: Counter = Counter()
    for b in cluster:
        conf = float(b.get("confidence") or 0.5)
        for tok in _tokens(b.get("content") or ""):
            word_weights[tok] += conf

    top_words = [w for w, _ in word_weights.most_common(5)]
    if len(top_words) >= 2:
        return " ".join(top_words)[:80]

    # Fallback: first 80 chars of highest-confidence belief
    best = max(cluster, key=lambda b: float(b.get("confidence") or 0.0))
    return (best.get("content") or "")[:80]


class DriveEmergence:
    """Substrate-resident emergent drive detector. Daemon thread drives 600s tick.

    Implements SentienceNode protocol (DOCTRINE §4):
        name, tick(context), decay(now), state(now=None)
    Per-chat tick() is a no-op — returns current in-memory state. All
    computation happens in the background daemon thread.
    """

    name: str = "drive_emergence"

    def __init__(
        self,
        conversations_writer: Writer,
        conversations_reader: Reader,
        beliefs_reader: Reader,
        tick_interval_s: int = _TICK_INTERVAL_S,
    ) -> None:
        self._cw       = conversations_writer
        self._cr       = conversations_reader
        self._br       = beliefs_reader
        self._interval = tick_interval_s
        self._lock     = threading.Lock()

        # In-memory state — mirrors DB row (or None when no drive)
        self._topic:              Optional[str]   = None
        self._drive_strength:     Optional[float] = None
        self._repetition_score:   Optional[float] = None
        self._convergence_score:  Optional[float] = None
        self._reinforce_count:    int             = 0
        self._formed_at:          Optional[float] = None
        self._last_reinforced_at: Optional[float] = None

        self._load_from_db()

    # ── Startup ───────────────────────────────────────────────────────────────

    def _load_from_db(self) -> None:
        """Restore in-memory state from existing DB row on boot."""
        try:
            row = self._cr.read_one("SELECT * FROM drives WHERE id = 1")
            if row:
                with self._lock:
                    self._topic              = str(row["topic"])
                    self._drive_strength     = float(row["drive_strength"])
                    self._repetition_score   = float(row["repetition_score"])
                    self._convergence_score  = float(row["convergence_score"])
                    self._reinforce_count    = int(row["reinforce_count"])
                    self._formed_at          = float(row["formed_at"])
                    self._last_reinforced_at = float(row["last_reinforced_at"])
        except Exception:
            pass

    def start_loop(self) -> None:
        """Start the 600s daemon tick thread."""
        t = threading.Thread(
            target=self._loop, daemon=True, name="drive_emergence_tick"
        )
        t.start()

    # ── Background loop ───────────────────────────────────────────────────────

    def _loop(self) -> None:
        while True:
            try:
                self._background_tick()
            except Exception as exc:
                errors.record(
                    f"drive_emergence tick error: {exc}",
                    source=_LOG_SOURCE, exc=exc,
                )
            time.sleep(self._interval)

    def _background_tick(self) -> None:
        now = time.time()

        # 1. Decay existing drive
        existing = self._cr.read_one("SELECT * FROM drives WHERE id = 1")
        if existing:
            existing = dict(existing)
            new_strength = existing["drive_strength"] * _DECAY_RATE
            if new_strength < _MIN_DRIVE_STRENGTH:
                self._cw.write("DELETE FROM drives WHERE id = 1", ())
                existing = None
                self._clear_state()
            else:
                existing["drive_strength"] = new_strength

        # 2. Pull candidates
        cutoff = now - _WINDOW_DAYS * 86400
        rows = self._br.read(
            "SELECT id, content, confidence, branch_id, use_count, created_at "
            "FROM beliefs "
            "WHERE confidence >= 0.15 AND paused = 0 AND created_at >= ? "
            "ORDER BY created_at DESC LIMIT ?",
            (cutoff, _CANDIDATE_LIMIT),
        )
        candidates = [dict(r) for r in rows] if rows else []

        if len(candidates) < _MIN_CLUSTER_SIZE:
            if existing:
                self._persist_decay(existing, now)
            return

        # 3. Embed candidates
        try:
            from theory_x.diversity.embeddings import embed_belief
            embeddings = {
                c["id"]: embed_belief(c["id"], c["content"] or "")
                for c in candidates
            }
        except Exception as exc:
            errors.record(
                f"drive_emergence embed error: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )
            if existing:
                self._persist_decay(existing, now)
            return

        # 4. Cluster by cosine similarity
        clusters = _cluster(candidates, embeddings, _CLUSTER_SIMILARITY)

        # 5. Score each cluster; keep strongest qualifier
        best: Optional[dict] = None
        _obs_all_scored: list = []
        _obs_rejections: dict = {
            "below_repetition": 0, "below_convergence": 0,
            "no_cluster_match": 0, "time_window_miss": 0, "other": 0,
        }
        for cluster in clusters:
            if len(cluster) < _MIN_CLUSTER_SIZE:
                _obs_rejections["no_cluster_match"] += 1
                continue
            rep_score  = _repetition_score(cluster, now)
            conv_score = _convergence_score(cluster)
            _obs_all_scored.append({
                "theme_label":       _synthesize_topic(cluster)[:40],
                "member_count":      len(cluster),
                "repetition_score":  round(rep_score, 4),
                "convergence_score": round(conv_score, 4),
                "combined_strength": round(_W_REP * rep_score + _W_CONV * conv_score, 4),
            })
            if rep_score < _MIN_REPETITION or conv_score < _MIN_CONVERGENCE:
                if rep_score < _MIN_REPETITION:
                    _obs_rejections["below_repetition"] += 1
                else:
                    _obs_rejections["below_convergence"] += 1
                continue
            n_branches = len({b["branch_id"] for b in cluster if b.get("branch_id")})
            if n_branches < _MIN_BRANCH_COUNT:
                _obs_rejections["time_window_miss"] += 1
                continue
            strength = _W_REP * rep_score + _W_CONV * conv_score
            if best is None or strength > best["drive_strength"]:
                best = {
                    "cluster":          cluster,
                    "drive_strength":   strength,
                    "repetition_score": rep_score,
                    "convergence_score": conv_score,
                }

        # Observability log — post-scoring, pre-emergence (Phase 29b)
        try:
            _tick_duration_ms = round((time.time() - now) * 1000, 1)
            _top5 = sorted(
                _obs_all_scored,
                key=lambda x: x["combined_strength"],
                reverse=True,
            )[:5]
            _thresholds_snap = {
                "min_cluster_size":    _MIN_CLUSTER_SIZE,
                "min_repetition":      _MIN_REPETITION,
                "min_convergence":     _MIN_CONVERGENCE,
                "min_branch_count":    _MIN_BRANCH_COUNT,
                "min_drive_strength":  _MIN_DRIVE_STRENGTH,
                "cluster_similarity":  _CLUSTER_SIMILARITY,
                "window_days":         _WINDOW_DAYS,
                "recency_window_days": _RECENCY_WINDOW_DAYS,
            }
            self._cw.write(
                "INSERT INTO drive_emergence_log "
                "(tick_at, candidates_examined, top_candidates, rejection_reasons, "
                "thresholds_snapshot, drive_formed_id, tick_duration_ms) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    now,
                    len(clusters),
                    json.dumps(_top5),
                    json.dumps(_obs_rejections),
                    json.dumps(_thresholds_snap),
                    None,
                    _tick_duration_ms,
                ),
            )
        except Exception as _obs_exc:
            print(f"drive_emergence_log write failed: {_obs_exc}", file=sys.stderr)

        # 6. Replace, reinforce, or persist decayed state
        if best is not None and best["drive_strength"] >= _MIN_DRIVE_STRENGTH:
            topic         = _synthesize_topic(best["cluster"])
            source_ids    = [b["id"] for b in best["cluster"]]
            formed_at     = existing["formed_at"] if existing else now
            reinforce_cnt = (int(existing["reinforce_count"]) + 1) if existing else 1
            self._cw.write(
                "INSERT OR REPLACE INTO drives "
                "(id, topic, source_beliefs, drive_strength, repetition_score, "
                "convergence_score, formed_at, last_reinforced_at, reinforce_count) "
                "VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    topic,
                    json.dumps(source_ids),
                    best["drive_strength"],
                    best["repetition_score"],
                    best["convergence_score"],
                    formed_at,
                    now,
                    reinforce_cnt,
                ),
            )
            with self._lock:
                self._topic              = topic
                self._drive_strength     = best["drive_strength"]
                self._repetition_score   = best["repetition_score"]
                self._convergence_score  = best["convergence_score"]
                self._reinforce_count    = reinforce_cnt
                self._formed_at          = formed_at
                self._last_reinforced_at = now
        elif existing:
            self._persist_decay(existing, now)

        try:
            with open(_DRIVE_LOG, "a") as _f:
                _f.write(json.dumps({
                    "ts":               now,
                    "topic":            self._topic,
                    "drive_strength":   self._drive_strength,
                    "repetition_score": self._repetition_score,
                    "convergence_score": self._convergence_score,
                    "reinforce_count":  self._reinforce_count,
                }) + "\n")
        except Exception:
            pass

    def _clear_state(self) -> None:
        with self._lock:
            self._topic              = None
            self._drive_strength     = None
            self._repetition_score   = None
            self._convergence_score  = None
            self._reinforce_count    = 0
            self._formed_at          = None
            self._last_reinforced_at = None

    def _persist_decay(self, existing: dict, now: float) -> None:
        strength = existing["drive_strength"]
        if strength >= _MIN_DRIVE_STRENGTH:
            self._cw.write(
                "UPDATE drives SET drive_strength = ?, last_reinforced_at = ? "
                "WHERE id = 1",
                (strength, now),
            )
            with self._lock:
                self._drive_strength     = strength
                self._last_reinforced_at = now
        else:
            self._cw.write("DELETE FROM drives WHERE id = 1", ())
            self._clear_state()

    # ── SentienceNode protocol ────────────────────────────────────────────────

    def tick(self, context: Optional[dict] = None) -> dict:
        """Per-chat-turn no-op. Returns current in-memory state."""
        return self.state()

    def decay(self, now: float = None) -> None:
        pass  # decay runs inside _background_tick

    def state(self, now: Optional[float] = None) -> dict:
        with self._lock:
            return {
                "name":              self.name,
                "topic":             self._topic,
                "drive_strength":    self._drive_strength,
                "repetition_score":  self._repetition_score,
                "convergence_score": self._convergence_score,
                "reinforce_count":   self._reinforce_count,
                "formed_at":         self._formed_at,
                "last_reinforced_at": self._last_reinforced_at,
            }

    # ── Output surface ────────────────────────────────────────────────────────

    def format_for_prompt(self, context: Any = None) -> str:
        """Read current drives row. Zero output-time computation per §0."""
        try:
            row = self._cr.read_one("SELECT topic FROM drives WHERE id = 1")
            if not row:
                return ""
            return f"Drawn lately to: {row['topic']}"
        except Exception:
            return ""

    def drive_topic_embedding(self) -> Optional[Any]:
        """Embedding of current drive topic for VoiceEngine drive_alignment axis."""
        with self._lock:
            topic = self._topic
        if not topic:
            return None
        try:
            from theory_x.diversity.embeddings import embed
            return embed(topic)
        except Exception:
            return None
