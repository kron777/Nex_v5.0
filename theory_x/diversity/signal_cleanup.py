"""One-time cleanup: purge accumulated repeated fountain_insight beliefs."""
from __future__ import annotations

import logging

log = logging.getLogger("theory_x.diversity.signal_cleanup")


def purge_signal_repetitions(writer, reader, content: str, keep_n: int = 1) -> int:
    """Delete all but the most recent keep_n copies of a repeated belief.

    Works on any source, but intended for fountain_insight ruts.
    Returns number of beliefs deleted.
    """
    rows = reader.read(
        "SELECT id FROM beliefs "
        "WHERE source='fountain_insight' AND content=? "
        "ORDER BY created_at DESC",
        (content,),
    )
    if len(rows) <= keep_n:
        return 0
    to_delete = [r["id"] for r in rows[keep_n:]]
    placeholders = ",".join("?" * len(to_delete))
    writer.write(
        f"DELETE FROM beliefs WHERE id IN ({placeholders})",
        tuple(to_delete),
    )
    log.info("Purged %d duplicate fountain_insight beliefs: %r", len(to_delete), content[:60])
    return len(to_delete)
