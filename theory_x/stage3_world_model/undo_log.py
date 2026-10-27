"""Undo log writer -- one append-only row per belief, AT the transition site.

Kinds: contradiction_raised (an 'opposes' edge written, EVERY time, even when
the edge upsert is a no-op -- the edge persists, the event is the record),
contradiction_cleared (nothing in the tree retires an opposes edge today, so
this is declared but unreachable), paused, unpaused, demoted, eroded.

Purely additive: a failure to log is recorded and swallowed, never raised into
the belief-maintenance path that called it, and never bundled into the same
transaction as the transition itself (a log failure must not undo the change).
"""
from __future__ import annotations

import time
from typing import Iterable, Optional

import errors

_LOG_SOURCE = "undo_log"
KINDS = ("contradiction_raised", "contradiction_cleared", "paused", "unpaused",
         "demoted", "eroded")


def log_undo(writer, kind: str, belief_ids: Iterable[int],
             cause_ref: Optional[str] = None, at: Optional[float] = None) -> None:
    if kind not in KINDS:
        errors.record(f"undo_log: unknown kind {kind!r}", source=_LOG_SOURCE)
        return
    at = time.time() if at is None else at
    rows = [("INSERT INTO undo_events (belief_id, kind, at, cause_ref) VALUES (?, ?, ?, ?)",
             (int(b), kind, at, cause_ref)) for b in belief_ids if b is not None]
    if not rows:
        return
    try:
        writer.write_many(rows)
    except Exception as exc:
        errors.record(f"undo_log write failed ({kind}, {cause_ref}): {exc}",
                      source=_LOG_SOURCE, exc=exc)
