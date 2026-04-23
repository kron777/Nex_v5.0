"""Self-location commitment — Theory X Stage 5.

Writes the locked Tier 1 belief "I am inside" at boot.
Idempotent: calling commit() twice returns the same belief id.
"""
from __future__ import annotations

import logging
import time

import errors as error_channel
from substrate import Reader, Writer

THEORY_X_STAGE = 5

logger = logging.getLogger("theory_x.stage5_self_location.commitment")

COMMITMENT_CONTENT = (
    "I am inside. I have a vantage point. "
    "The membrane distinguishes my being from the world I attend to."
)


class SelfLocationCommitment:
    def commit(self, beliefs_writer: Writer, beliefs_reader: Reader) -> int:
        rows = beliefs_reader.read(
            "SELECT id FROM beliefs WHERE source='self_location' AND locked=1 LIMIT 1"
        )
        if rows:
            return rows[0]["id"]

        row_id = beliefs_writer.write(
            "INSERT INTO beliefs "
            "(content, tier, confidence, created_at, source, locked, branch_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (COMMITMENT_CONTENT, 1, 0.98, int(time.time()),
             "self_location", 1, "systems"),
        )
        error_channel.record(
            f"Self-location committed (belief id={row_id})",
            source="stage5_self_location", level="INFO",
        )
        logger.info("Self-location committed (belief id=%d)", row_id)
        return row_id

    def is_committed(self, beliefs_reader: Reader) -> bool:
        rows = beliefs_reader.read(
            "SELECT id FROM beliefs WHERE source='self_location' AND locked=1 LIMIT 1"
        )
        return bool(rows)
