"""Crossbreed Grader — scores synergized beliefs. Weights versioned + self-tuning."""
from __future__ import annotations

import logging
import time
from typing import Optional

from theory_x.diversity.embeddings import embed_belief, distance

log = logging.getLogger("theory_x.diversity.grader")

DEFAULT_WEIGHTS = {
    "w_input_distance": 0.4,
    "w_output_distance": 0.35,
    "w_rarity": 0.25,
}


class CrossbreedGrader:
    def __init__(self, beliefs_writer, beliefs_reader):
        self._writer = beliefs_writer
        self._reader = beliefs_reader
        self._current_version = self._load_or_create_version()

    def _load_or_create_version(self) -> int:
        rows = self._reader.read("SELECT MAX(version) AS v FROM grader_versions")
        if rows and dict(rows[0]).get("v"):
            return rows[0]["v"]
        self._writer.write(
            "INSERT INTO grader_versions "
            "(version, w_input_distance, w_output_distance, w_rarity, rationale, created_at) "
            "VALUES (1, ?, ?, ?, ?, ?)",
            (DEFAULT_WEIGHTS["w_input_distance"],
             DEFAULT_WEIGHTS["w_output_distance"],
             DEFAULT_WEIGHTS["w_rarity"],
             "initial weights", time.time()),
        )
        return 1

    def current_weights(self) -> dict:
        rows = self._reader.read(
            "SELECT w_input_distance, w_output_distance, w_rarity "
            "FROM grader_versions WHERE version=?",
            (self._current_version,),
        )
        return dict(rows[0]) if rows else dict(DEFAULT_WEIGHTS)

    def grade(self, child_id: int, parent_a_id: int, parent_b_id: int) -> Optional[float]:
        child = self._fetch_belief(child_id)
        pa = self._fetch_belief(parent_a_id)
        pb = self._fetch_belief(parent_b_id)
        if not (child and pa and pb):
            return None

        e_child = embed_belief(child_id, child["content"])
        e_a = embed_belief(parent_a_id, pa["content"])
        e_b = embed_belief(parent_b_id, pb["content"])

        input_dist = distance(e_a, e_b)
        output_dist = min(distance(e_child, e_a), distance(e_child, e_b))
        rarity = self._estimate_rarity(pa.get("branch_id"), pb.get("branch_id"))

        w = self.current_weights()
        grade = (
            w["w_input_distance"] * input_dist +
            w["w_output_distance"] * output_dist +
            w["w_rarity"] * rarity
        )

        self._writer.write(
            "INSERT INTO collision_grades "
            "(belief_id, parent_a_id, parent_b_id, input_distance, "
            " output_distance, rarity, grade, grader_version, graded_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (child_id, parent_a_id, parent_b_id, input_dist,
             output_dist, rarity, grade, self._current_version, time.time()),
        )
        log.info("Graded collision %d: grade=%.3f (in_d=%.2f out_d=%.2f rarity=%.2f)",
                 child_id, grade, input_dist, output_dist, rarity)
        return grade

    def _fetch_belief(self, bid: int) -> Optional[dict]:
        rows = self._reader.read(
            "SELECT id, content, branch_id FROM beliefs WHERE id=?", (bid,)
        )
        return dict(rows[0]) if rows else None

    def _estimate_rarity(self, branch_a: Optional[str], branch_b: Optional[str]) -> float:
        if not branch_a or not branch_b:
            return 0.5
        rows = self._reader.read(
            """SELECT COUNT(*) AS n FROM collision_grades g
               JOIN beliefs pa ON g.parent_a_id = pa.id
               JOIN beliefs pb ON g.parent_b_id = pb.id
               WHERE (pa.branch_id = ? AND pb.branch_id = ?)
                  OR (pa.branch_id = ? AND pb.branch_id = ?)""",
            (branch_a, branch_b, branch_b, branch_a),
        )
        n = rows[0]["n"] if rows else 0
        return min(1.0, 1.0 / (1.0 + n / 5.0))
