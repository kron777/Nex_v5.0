"""Main ArcReader — orchestrates Type 1, 2, 3 detection."""
from __future__ import annotations

import logging
import time
from typing import Optional

import numpy as np

from theory_x.arcs.clustering import cluster_fires, cluster_centroid
from theory_x.arcs.progression import compute_progression_score, classify_member_roles
from theory_x.arcs.transformation import compute_transformation_score
from theory_x.arcs.meta_reflective import is_meta_reflective_content, find_closed_arc
from theory_x.diversity.embeddings import embed_belief

log = logging.getLogger("theory_x.arcs")

PROGRESSION_THRESHOLD = 0.5
TRANSFORMATION_THRESHOLD = 0.4
MIN_ARC_MEMBERS = 3
MAX_ARC_MEMBERS_AT_CREATION = 30

WINDOWS = [
    {"size": 20, "label": "recent"},
    {"size": 50, "label": "session"},
    {"size": 100, "label": "day"},
]


class ArcReader:
    def __init__(self, writer, reader):
        self._writer = writer
        self._reader = reader

    def scan(self) -> dict:
        total_new_arcs = 0

        for window_spec in WINDOWS:
            fires = self._fetch_recent_fires(window_spec["size"])
            if len(fires) < MIN_ARC_MEMBERS:
                continue
            total_new_arcs += self._detect_in_window(fires)

        broad_fires = self._fetch_recent_fires(100)
        members_added = self._check_extensions(broad_fires)
        closers = self._check_for_closers(broad_fires)

        log.info(
            "ArcReader scan: new_arcs=%d extensions=%d closers=%d",
            total_new_arcs, members_added, closers,
        )
        return {
            "arcs_detected": total_new_arcs,
            "members_added": members_added,
            "closers_found": closers,
        }

    def _detect_in_window(self, fires: list[dict]) -> int:
        new_arcs = 0
        for cluster in cluster_fires(fires):
            if len(cluster) < MIN_ARC_MEMBERS:
                continue
            if self._is_duplicate_arc(cluster):
                continue
            arc_type, score = self._classify_cluster(cluster)
            if arc_type:
                self._write_arc(cluster, arc_type, score)
                new_arcs += 1
        return new_arcs

    def _fetch_recent_fires(self, limit: int) -> list[dict]:
        rows = self._reader.read(
            "SELECT id, content, created_at FROM beliefs "
            "WHERE source='fountain_insight' "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return list(reversed([dict(r) for r in rows]))

    def _is_duplicate_arc(self, cluster: list[dict]) -> bool:
        """Return True if an arc with Jaccard similarity ≥ 0.7 already exists."""
        member_ids = {f["id"] for f in cluster}
        if not member_ids:
            return False
        cutoff = time.time() - 86400
        rows = self._reader.read(
            "SELECT arc_id, GROUP_CONCAT(belief_id) AS members "
            "FROM arc_members WHERE joined_at > ? GROUP BY arc_id",
            (cutoff,),
        )
        for r in rows:
            raw = r["members"] or ""
            existing = {int(x) for x in str(raw).split(",") if x.strip()}
            if not existing:
                continue
            intersection = len(member_ids & existing)
            union_size = len(member_ids | existing)
            if union_size > 0 and intersection / union_size >= 0.7:
                return True
        return False

    def _classify_cluster(self, cluster: list[dict]) -> tuple[Optional[str], float]:
        prog = compute_progression_score(cluster)
        trans = compute_transformation_score(cluster)
        if prog >= PROGRESSION_THRESHOLD and prog >= trans:
            return ("progression", prog)
        if trans >= TRANSFORMATION_THRESHOLD:
            return ("return_transformation", trans)
        return (None, 0.0)

    def _write_arc(self, cluster: list[dict], arc_type: str, score: float) -> None:
        if len(cluster) > MAX_ARC_MEMBERS_AT_CREATION:
            log.warning(
                "Cluster too large (%d members) — skipping. "
                "Tighten clustering threshold if this persists.",
                len(cluster),
            )
            return

        centroid = cluster_centroid(cluster)
        centroid_bytes = centroid.tobytes()
        theme = cluster[0]["content"][:80]
        now = time.time()

        arc_id = self._writer.write(
            "INSERT INTO arcs "
            "(arc_type, detected_at, window_start, window_end, "
            " theme_summary, member_count, progression_score, "
            " transformation_score, centroid_embedding, quality_grade, "
            " last_active_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                arc_type, now,
                cluster[0]["created_at"], cluster[-1]["created_at"],
                theme, len(cluster),
                score if arc_type == "progression" else None,
                score if arc_type == "return_transformation" else None,
                centroid_bytes, score, now,
            ),
        )
        if not arc_id:
            log.warning("Failed to write arc")
            return

        roles = (
            classify_member_roles(cluster)
            if arc_type == "progression"
            else ["variation"] * len(cluster)
        )
        roles[0] = "introduction"
        if arc_type == "progression":
            roles[-1] = "synthesis"

        norm_c = np.linalg.norm(centroid)
        for position, (fire, role) in enumerate(zip(cluster, roles), 1):
            e = embed_belief(fire["id"], fire["content"])
            norm_e = np.linalg.norm(e)
            denom = norm_e * norm_c + 1e-9
            dist = 1.0 - float(np.dot(e, centroid) / denom)
            try:
                self._writer.write(
                    "INSERT INTO arc_members "
                    "(arc_id, belief_id, position, role, distance_from_centroid, joined_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (arc_id, fire["id"], position, role, dist, now),
                )
            except Exception as exc:
                log.debug("arc_members insert skipped: %s", exc)

        log.info(
            "Arc written: id=%d type=%s score=%.2f members=%d theme='%s'",
            arc_id, arc_type, score, len(cluster), theme[:60],
        )

    def _check_extensions(self, fires: list[dict]) -> int:
        cutoff = time.time() - 7200
        active_arcs = self._reader.read(
            "SELECT id, centroid_embedding, member_count FROM arcs "
            "WHERE last_active_at > ? AND closed_by_belief_id IS NULL",
            (cutoff,),
        )
        if not active_arcs:
            return 0

        existing_ids = {r["belief_id"] for r in self._reader.read(
            "SELECT belief_id FROM arc_members WHERE joined_at > ?",
            (cutoff,),
        )}

        added = 0
        now = time.time()
        for fire in fires:
            if fire["id"] in existing_ids:
                continue
            fire_emb = embed_belief(fire["id"], fire["content"])
            for arc in active_arcs:
                raw = arc["centroid_embedding"]
                if raw is None:
                    continue
                centroid = np.frombuffer(raw, dtype=np.float32)
                norm_f = np.linalg.norm(fire_emb)
                norm_c = np.linalg.norm(centroid)
                if norm_f == 0 or norm_c == 0:
                    continue
                sim = float(np.dot(fire_emb, centroid) / (norm_f * norm_c))
                if sim > 0.75:
                    try:
                        self._writer.write(
                            "INSERT INTO arc_members "
                            "(arc_id, belief_id, position, role, "
                            " distance_from_centroid, joined_at) "
                            "VALUES (?, ?, ?, 'return', ?, ?)",
                            (arc["id"], fire["id"],
                             arc["member_count"] + 1, 1.0 - sim, now),
                        )
                        self._writer.write(
                            "UPDATE arcs SET member_count=member_count+1, "
                            "last_active_at=? WHERE id=?",
                            (now, arc["id"]),
                        )
                        existing_ids.add(fire["id"])
                        added += 1
                        break
                    except Exception:
                        pass
        return added

    def _check_for_closers(self, fires: list[dict]) -> int:
        recent_arcs = [
            dict(r) for r in self._reader.read(
                "SELECT id, centroid_embedding FROM arcs "
                "WHERE last_active_at > ? AND closed_by_belief_id IS NULL",
                (time.time() - 7200,),
            )
        ]
        found = 0
        for fire in fires[-10:]:
            is_meta, confidence = is_meta_reflective_content(fire["content"])
            if not is_meta:
                continue
            result = find_closed_arc(fire, recent_arcs, {})
            if result:
                arc_id, proximity = result
                now = time.time()
                try:
                    self._writer.write(
                        "INSERT INTO arc_closers "
                        "(arc_id, belief_id, detected_at, meta_confidence) "
                        "VALUES (?, ?, ?, ?)",
                        (arc_id, fire["id"], now, confidence * proximity),
                    )
                    self._writer.write(
                        "UPDATE arcs SET closed_by_belief_id=? WHERE id=?",
                        (fire["id"], arc_id),
                    )
                    found += 1
                    log.info(
                        "Arc closer: arc=%d fire=%d confidence=%.2f",
                        arc_id, fire["id"], confidence * proximity,
                    )
                except Exception:
                    pass
        return found
