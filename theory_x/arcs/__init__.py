"""Arc Reader — temporal progression detection in fountain output."""
from __future__ import annotations

import logging

from theory_x.arcs.loop import ArcLoop, build_arc_loop
from theory_x.arcs.detector import ArcReader

log = logging.getLogger("theory_x.arcs")

__all__ = ["ArcLoop", "ArcReader", "build_arc_loop", "reset_oversized_arcs"]


def reset_oversized_arcs(writer, reader) -> int:
    """One-time cleanup: delete arcs with member_count > 25 detected before
    tighter thresholds landed. Idempotent — safe to call repeatedly."""
    rows = reader.read(
        "SELECT id, member_count, theme_summary FROM arcs WHERE member_count > 25"
    )
    for r in rows:
        writer.write("DELETE FROM arc_members WHERE arc_id=?", (r["id"],))
        writer.write("DELETE FROM arc_closers WHERE arc_id=?", (r["id"],))
        writer.write("DELETE FROM arcs WHERE id=?", (r["id"],))
        log.info(
            "Reset oversized arc id=%d (%d members): %s",
            r["id"], r["member_count"], (r["theme_summary"] or "")[:60],
        )
    return len(rows)
