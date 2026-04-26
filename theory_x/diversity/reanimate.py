"""Wake Up Sleeping — surfaces dormant beliefs into the retrieval pool."""
from __future__ import annotations

import logging
import time
from typing import Optional

log = logging.getLogger("theory_x.diversity.reanimate")

_pending_reanimation: Optional[dict] = None


def wake_one(writer, reader) -> Optional[dict]:
    """Pick one high-dormancy belief, mark it reanimated, return it for injection."""
    global _pending_reanimation
    rows = reader.read(
        "SELECT d.belief_id, b.content FROM dormant_beliefs d "
        "JOIN beliefs b ON d.belief_id = b.id "
        "WHERE d.reanimated_at IS NULL "
        "ORDER BY d.dormancy_score DESC LIMIT 1"
    )
    if not rows:
        return None
    row = dict(rows[0])
    writer.write(
        "UPDATE dormant_beliefs SET reanimated_at=? WHERE belief_id=?",
        (time.time(), row["belief_id"]),
    )
    _pending_reanimation = row
    log.info("Reanimated dormant belief_id=%d", row["belief_id"])
    return row


def pop_reanimated() -> Optional[dict]:
    """Retrieve and clear the pending reanimation candidate."""
    global _pending_reanimation
    result = _pending_reanimation
    _pending_reanimation = None
    return result
