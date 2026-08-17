"""Signals reaper — bounded retention for the `signals` table.

Same pattern as the round-27 residue reaper (`theory_x/diversity/residue.py`):
a module-level retention constant, an hourly throttle, and a fire-and-forget
`_reap()` that must never raise into its caller.

WHY THIS EXISTS (round 70, measured in round 69)
------------------------------------------------
`signals` had 1,316,570 rows spanning 115.2 days and 329.0 MB of a 762.7 MB
`beliefs.db` — 43% of the file the crystallizer writes crystallizations into.
No `DELETE FROM signals` existed anywhere in the tree. 1,316,570 of those rows
are `branch_silence_anomaly`, which `signal_to_problem.py:33` deliberately
excludes from `_PROMOTABLE_TYPES`, so they are written forever and read never.

WHY 7 DAYS IS SAFE — every reader is time-bounded, and the widest window is 24h
------------------------------------------------------------------------------
All four readers of `signals` were enumerated before this was written:

  theory_x/signals/signal_to_problem.py:250   detected_at > now - 21600   (6h)
  theory_x/stage_drives/competing_drives.py:174
                                              detected_at > now - 86400   (24h)
  theory_x/probes/context_snapshot.py:87      detected_at > now - 600     (10m)
  gui/server.py:3139                          ORDER BY detected_at DESC LIMIT<=100

The binding constraint is `competing_drives.py` at **24 hours** — and that file
is ON THE FIRE PATH, so it is the one that matters. 7 days leaves a 7x margin:
no reader can observe a row this reaper is eligible to delete.

`gui/server.py` is unbounded in time but reads only the newest <=100 rows, which
are never 7 days old while the detectors are running at ~1,300/day.

`patterns.signal_ids` stores signal ids as a JSON blob (`signals/loop.py:114`),
but nothing joins it back to `signals` — `gui/server.py:3143` selects the column
for display only. Reaping orphans no dereferenced ref.

DEVIATION FROM THE RESIDUE REAPER, AND WHY
------------------------------------------
`residue._reap()` issues one unbounded DELETE. That is fine for its table; it is
not fine here. The first pass has a ~1.3M-row backlog to clear, and a single
DELETE would hold a write lock on `beliefs.db` — the crystallizer's write target
— for as long as it takes. So this reaper deletes in bounded batches and stops
after `_REAP_BATCH` rows, letting the next hourly pass continue.

`_REAP_BATCH` is measured, not guessed. Timed on a byte copy of the live 763 MB
`beliefs.db` (never on the live file): the DELETE costs ~2.5 us/row, so

    batch    5,000 ->   14 ms
    batch   50,000 ->  124 ms      <- chosen
    batch  100,000 ->  266 ms

At 50,000 the lock is ~124 ms once per hour, against a fountain that fires every
~2.7 minutes — negligible contention. The ~1.32M backlog drains in ~27 passes,
about 27 hours, after which the table sits at its ~7-day steady state.

NOT REAPED: unconsumed promotable signals. The filter deliberately keeps any row
that `signal_to_problem` could still act on, independent of age, so a reap can
never remove work that was merely waiting.
"""
from __future__ import annotations

import logging
import time

log = logging.getLogger("theory_x.signals.reaper")

_REAP_AFTER_SECONDS = 7 * 86400   # rows older than this are eligible
_REAP_INTERVAL = 3600.0           # at most one reap pass per hour
_REAP_BATCH = 50_000              # rows per pass — measured ~124 ms lock
_last_reap = 0.0

# Types signal_to_problem can still promote. An unconsumed row of one of these
# is never reaped regardless of age, so the reaper can only ever remove rows
# that are either already actioned or of a type nothing consumes.
_PROMOTABLE_TYPES = (
    "2_branch", "3_branch", "t6_promotion_burst", "pattern_recognition_burst",
    "cross_branch_convergence", "novel_arc", "concept_emergence",
)


def reap(writer, now: float | None = None, force: bool = False) -> int:
    """Delete aged signals in one bounded batch. Returns rows deleted.

    Throttled to one pass per hour unless `force`. Fire-and-forget: callers run
    on live loops, so this never raises.
    """
    global _last_reap
    now = time.time() if now is None else now
    if not force and now - _last_reap < _REAP_INTERVAL:
        return 0
    _last_reap = now

    cutoff = now - _REAP_AFTER_SECONDS
    placeholders = ",".join("?" * len(_PROMOTABLE_TYPES))
    try:
        writer.write(
            f"DELETE FROM signals WHERE id IN ("
            f"  SELECT id FROM signals"
            f"  WHERE detected_at < ?"
            f"    AND (actioned_at IS NOT NULL"
            f"         OR signal_type NOT IN ({placeholders}))"
            f"  LIMIT ?"
            f")",
            (cutoff, *_PROMOTABLE_TYPES, _REAP_BATCH),
        )
        return _REAP_BATCH
    except Exception as exc:
        log.warning("signals reap failed (non-fatal): %s", exc)
        return 0
