"""Provenance Erosion — beliefs become NEX's own over time.

A belief starts as 'external'. Through use and reinforcement it advances:
  external → nex_absorbed → nex_integrated → nex_core

Protected sources never erode (keystone, heart_sutra, etc.).
Each stage advance gives a small confidence boost (+0.02).
"""
from __future__ import annotations

import time

import errors
from substrate import Writer, Reader

THEORY_X_STAGE = 3

_LOG_SOURCE = "erosion"

EROSION_STAGES = ["external", "nex_absorbed", "nex_integrated", "nex_core"]

PROTECTED_SOURCES = {
    "keystone_seed",
    "self_location",
    "heart_sutra",
    "precipitated_from_dynamic",
    "manual",
    "reification_recognition",
}

THRESHOLDS: dict[str, int | None] = {
    "external":      10,
    "nex_absorbed":  30,
    "nex_integrated": 80,
    "nex_core":      None,
}


class ProvenanceErosion:
    def __init__(self, beliefs_writer: Writer, beliefs_reader: Reader) -> None:
        self._writer = beliefs_writer
        self._reader = beliefs_reader

    def record_use(self, belief_id: int) -> None:
        """Increment use_count then check for stage advance."""
        try:
            self._writer.write(
                "UPDATE beliefs SET use_count = use_count + 1 WHERE id = ?",
                (belief_id,),
            )
            self._erosion_check(belief_id)
        except Exception as exc:
            errors.record(f"record_use error: {exc}", source=_LOG_SOURCE, exc=exc)

    def record_reinforce(self, belief_id: int) -> None:
        """Increment reinforce_count then check for stage advance."""
        try:
            self._writer.write(
                "UPDATE beliefs SET reinforce_count = reinforce_count + 1 WHERE id = ?",
                (belief_id,),
            )
            self._erosion_check(belief_id)
        except Exception as exc:
            errors.record(f"record_reinforce error: {exc}", source=_LOG_SOURCE, exc=exc)

    def _erosion_check(self, belief_id: int) -> None:
        """Advance erosion stage if threshold reached. Skip protected sources."""
        try:
            row = self._reader.read_one(
                "SELECT id, source, erosion_stage, reinforce_count, locked FROM beliefs "
                "WHERE id = ?",
                (belief_id,),
            )
        except Exception as exc:
            errors.record(f"erosion_check read error: {exc}", source=_LOG_SOURCE, exc=exc)
            return

        if row is None:
            return
        if row["source"] in PROTECTED_SOURCES:
            return
        if row["locked"]:
            return

        stage = row["erosion_stage"] or "external"
        threshold = THRESHOLDS.get(stage)
        if threshold is None:
            return  # already at nex_core

        if row["reinforce_count"] >= threshold:
            current_idx = EROSION_STAGES.index(stage) if stage in EROSION_STAGES else 0
            next_idx = min(current_idx + 1, len(EROSION_STAGES) - 1)
            new_stage = EROSION_STAGES[next_idx]
            try:
                self._writer.write(
                    "UPDATE beliefs SET erosion_stage = ?, reinforce_count = 0, "
                    "confidence = MIN(1.0, confidence + 0.02) WHERE id = ?",
                    (new_stage, belief_id),
                )
                errors.record(
                    f"belief {belief_id} eroded to stage '{new_stage}'",
                    source=_LOG_SOURCE, level="INFO",
                )
            except Exception as exc:
                errors.record(f"erosion_check write error: {exc}", source=_LOG_SOURCE, exc=exc)

    def erosion_pass(self) -> int:
        """Run a full pass checking all eligible beliefs. Returns count advanced."""
        try:
            rows = self._reader.read(
                "SELECT id, source, erosion_stage, reinforce_count, locked FROM beliefs "
                "WHERE locked = 0 AND erosion_stage != 'nex_core' LIMIT 500"
            )
        except Exception as exc:
            errors.record(f"erosion_pass read error: {exc}", source=_LOG_SOURCE, exc=exc)
            return 0

        advanced = 0
        for row in rows:
            if row["source"] in PROTECTED_SOURCES:
                continue
            stage = row["erosion_stage"] or "external"
            threshold = THRESHOLDS.get(stage)
            if threshold is None:
                continue
            if row["reinforce_count"] >= threshold:
                current_idx = EROSION_STAGES.index(stage) if stage in EROSION_STAGES else 0
                next_idx = min(current_idx + 1, len(EROSION_STAGES) - 1)
                new_stage = EROSION_STAGES[next_idx]
                try:
                    self._writer.write(
                        "UPDATE beliefs SET erosion_stage = ?, reinforce_count = 0, "
                        "confidence = MIN(1.0, confidence + 0.02) WHERE id = ?",
                        (new_stage, row["id"]),
                    )
                    advanced += 1
                except Exception:
                    pass

        if advanced:
            errors.record(
                f"erosion_pass advanced {advanced} beliefs",
                source=_LOG_SOURCE, level="INFO",
            )
        return advanced
