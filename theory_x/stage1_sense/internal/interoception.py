"""Feed 22 — Interoception.

Belief graph state: counts per tier, locked belief count, most recent
entry timestamp. NEX sees the shape of her own belief graph.

Reads beliefs.db via substrate.Reader — never direct sqlite3.
Always enabled. Poll interval: 30s.
"""
from __future__ import annotations

from typing import Optional

import errors as error_channel
from substrate import Reader, Writer
from theory_x.stage1_sense.base import Adapter, RequestFn, SenseEvent

THEORY_X_STAGE = 1


class Interoception(Adapter):
    id = "interoception"
    stream = "internal.interoception"
    poll_interval_seconds = 30
    provenance = "substrate://beliefs.db"
    is_internal = True

    def __init__(
        self,
        writer: Writer,
        *,
        beliefs_reader: Reader,
        request_fn: Optional[RequestFn] = None,
    ) -> None:
        super().__init__(writer, request_fn=request_fn)
        self._beliefs_reader = beliefs_reader

    def poll(self) -> list[SenseEvent]:
        try:
            tier_counts = {str(t): 0 for t in range(9)}
            rows = self._beliefs_reader.read(
                "SELECT tier, COUNT(*) AS n FROM beliefs GROUP BY tier"
            )
            for row in rows:
                tier_counts[str(row["tier"])] = row["n"]

            locked_count_row = self._beliefs_reader.read_one(
                "SELECT COUNT(*) AS n FROM beliefs WHERE locked = 1"
            )
            locked_count = int(locked_count_row["n"]) if locked_count_row else 0

            total_row = self._beliefs_reader.read_one(
                "SELECT COUNT(*) AS n FROM beliefs"
            )
            total = int(total_row["n"]) if total_row else 0

            last_row = self._beliefs_reader.read_one(
                "SELECT MAX(created_at) AS t FROM beliefs"
            )
            last_created = last_row["t"] if last_row else None

            payload = self.pack(
                total_beliefs=total,
                locked_beliefs=locked_count,
                tier_counts=tier_counts,
                last_created_at=last_created,
            )
            return [SenseEvent(
                stream=self.stream,
                payload=payload,
                provenance=self.provenance,
                timestamp=self.now(),
            )]
        except Exception as e:
            error_channel.record(
                f"interoception.poll error: {e}",
                source="adapter[interoception]",
                exc=e,
            )
            return []
