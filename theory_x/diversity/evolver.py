"""Grading That Learns + Mismatch Detector — self-tuning grader weights."""
from __future__ import annotations

import logging
import time
from typing import Optional

log = logging.getLogger("theory_x.diversity.evolver")

CONSERVATIVE_BLEND = 0.3
MISMATCH_THRESHOLD = 0.3


class GraderEvolver:
    def __init__(self, beliefs_writer, beliefs_reader):
        self._writer = beliefs_writer
        self._reader = beliefs_reader

    def evolve(self) -> Optional[dict]:
        grades = self._reader.read(
            "SELECT g.belief_id, g.input_distance, g.output_distance, g.rarity, "
            "       g.grade, g.grader_version "
            "FROM collision_grades g "
            "ORDER BY g.graded_at ASC"
        )
        if len(grades) < 10:
            log.info("Evolver: not enough data (%d grades), skipping", len(grades))
            return None

        samples = []
        for g in grades:
            rv = self._retrospective_value(g["belief_id"])
            if rv is None:
                continue
            samples.append({
                "input_distance": g["input_distance"],
                "output_distance": g["output_distance"],
                "rarity": g["rarity"],
                "original_grade": g["grade"],
                "retrospective_value": rv,
                "belief_id": g["belief_id"],
                "grader_version": g["grader_version"],
            })

        if len(samples) < 5:
            return None

        self._detect_mismatches(samples)

        new_weights = self._fit_weights(samples)
        if new_weights is None:
            return None

        current = self._current_weights()
        blended = {
            k: (1 - CONSERVATIVE_BLEND) * current.get(k, v) + CONSERVATIVE_BLEND * v
            for k, v in new_weights.items()
        }

        version_rows = self._reader.read("SELECT MAX(version) AS v FROM grader_versions")
        next_version = (version_rows[0]["v"] or 1) + 1

        rationale = (
            f"input_distance {current.get('w_input_distance', 0):.2f}→{blended['w_input_distance']:.2f}, "
            f"output_distance {current.get('w_output_distance', 0):.2f}→{blended['w_output_distance']:.2f}, "
            f"rarity {current.get('w_rarity', 0):.2f}→{blended['w_rarity']:.2f}"
        )
        self._writer.write(
            "INSERT INTO grader_versions "
            "(version, w_input_distance, w_output_distance, w_rarity, rationale, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (next_version, blended["w_input_distance"],
             blended["w_output_distance"], blended["w_rarity"],
             rationale, time.time()),
        )
        log.info("Grader updated v%d: %s", next_version, rationale)
        return {"new_version": next_version, "weights": blended, "rationale": rationale}

    def _retrospective_value(self, belief_id: int) -> Optional[float]:
        desc = self._reader.read(
            "SELECT COUNT(*) AS n FROM belief_lineage WHERE parent_id=?", (belief_id,)
        )
        num_descendants = desc[0]["n"] if desc else 0

        boost = self._reader.read(
            "SELECT boost_value FROM belief_boost WHERE belief_id=?", (belief_id,)
        )
        boost_survival = min(1.0, (boost[0]["boost_value"] - 1.0) if boost else 0.0)

        refs = self._reader.read(
            "SELECT COUNT(*) AS n FROM belief_lineage WHERE parent_id=? AND relationship='reference'",
            (belief_id,),
        )
        ref_count = min(10, refs[0]["n"] if refs else 0)

        belief = self._reader.read(
            "SELECT tier FROM beliefs WHERE id=?", (belief_id,)
        )
        tier = belief[0]["tier"] if belief else 0
        tier_score = min(1.0, tier / 7.0)

        rv = (
            0.4 * min(1.0, num_descendants / 5.0) +
            0.3 * boost_survival +
            0.2 * (ref_count / 10.0) +
            0.1 * tier_score
        )
        return round(rv, 4)

    def _detect_mismatches(self, samples: list) -> None:
        now = time.time()
        for s in samples:
            diff = abs(s["original_grade"] - s["retrospective_value"])
            if diff <= MISMATCH_THRESHOLD:
                continue
            direction = (
                "under_graded" if s["retrospective_value"] > s["original_grade"]
                else "over_graded"
            )
            try:
                self._writer.write(
                    "INSERT INTO grade_mismatches "
                    "(belief_id, original_grade, retrospective_value, "
                    " mismatch_direction, detected_at, grader_version) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (s["belief_id"], s["original_grade"], s["retrospective_value"],
                     direction, now, s["grader_version"]),
                )
            except Exception:
                pass

    def _fit_weights(self, samples: list) -> Optional[dict]:
        try:
            import numpy as np
            X = np.array([
                [s["input_distance"], s["output_distance"], s["rarity"]]
                for s in samples
            ], dtype=float)
            y = np.array([s["retrospective_value"] for s in samples], dtype=float)
            coeff, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
            coeff = np.maximum(coeff, 0.0)
            total = coeff.sum()
            if total < 1e-6:
                return None
            coeff /= total
            return {
                "w_input_distance": float(coeff[0]),
                "w_output_distance": float(coeff[1]),
                "w_rarity": float(coeff[2]),
            }
        except Exception as e:
            log.warning("Weight fitting failed: %s", e)
            return None

    def _current_weights(self) -> dict:
        rows = self._reader.read(
            "SELECT w_input_distance, w_output_distance, w_rarity FROM grader_versions "
            "ORDER BY version DESC LIMIT 1"
        )
        return dict(rows[0]) if rows else {
            "w_input_distance": 0.4, "w_output_distance": 0.35, "w_rarity": 0.25
        }
