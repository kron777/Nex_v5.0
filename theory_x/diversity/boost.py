"""Retrieval boost (Helper 5) + Deliberate Forgetting (Evolver 14)."""
from __future__ import annotations

import logging
import time

log = logging.getLogger("theory_x.diversity.boost")

BOOST_THRESHOLD = 0.7
DECAY_RATE_PER_DAY = 0.02
NEUTRAL_THRESHOLD = 1.05


def apply_boost(writer, belief_id: int, grade: float) -> None:
    boost_value = 1.0 + grade
    writer.write(
        "INSERT INTO belief_boost (belief_id, boost_value, boosted_at, source_grade, decay_rate) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(belief_id) DO UPDATE SET "
        "  boost_value=excluded.boost_value, "
        "  boosted_at=excluded.boosted_at, "
        "  source_grade=excluded.source_grade",
        (belief_id, boost_value, time.time(), grade, DECAY_RATE_PER_DAY),
    )
    log.info("Boost applied: belief_id=%d boost=%.2f (grade=%.3f)", belief_id, boost_value, grade)


def apply_decay(writer, reader) -> int:
    """Reduce all active boosts by their daily decay rate. Remove neutral ones."""
    rows = reader.read(
        "SELECT belief_id, boost_value, boosted_at, decay_rate FROM belief_boost"
    )
    now = time.time()
    removed = 0
    for row in rows:
        days_elapsed = (now - row["boosted_at"]) / 86400.0
        new_boost = row["boost_value"] - row["decay_rate"] * days_elapsed
        if new_boost <= NEUTRAL_THRESHOLD:
            writer.write("DELETE FROM belief_boost WHERE belief_id=?", (row["belief_id"],))
            removed += 1
        elif abs(new_boost - row["boost_value"]) > 0.001:
            writer.write(
                "UPDATE belief_boost SET boost_value=?, boosted_at=? WHERE belief_id=?",
                (new_boost, now, row["belief_id"]),
            )
    if removed:
        log.info("Deliberate forgetting: removed %d expired boosts", removed)
    return removed
