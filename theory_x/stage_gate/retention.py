"""gate_decisions / throw_net_sessions retention — periodic age-based pruning.

Neither table has ever had a cleanup mechanism. gate_decisions reached
25.8M rows and throw_net_sessions 2.97M by 2026-07-27, both still growing
(~123K/day and ~12.7K/day respectively even after the 2026-07-26
contradicts_anchor false-positive fix and the throw_net_triggers backlog
prune -- see journal/CARRY_OVER.md). Both are pure INSERT-only logging
tables read exclusively via recent-time-window SELECTs; nothing reads an
old row for anything but a bounded lookback.

RETENTION WINDOWS -- derived from surveying every live reader, not guessed:

  gate_decisions consumers and their windows:
    self_mind_view.py      _ATTENTION_WINDOW_S = 300s (5 min)
    affect_state.py        _GATE_WINDOW_S = 3600s (1h)
    substrate_harmonic.py   24h (86400s)
    scripts/snapshot.py,
    scripts/nexsnap_extract.py   24h (86400s, manual/CLI tools)
    metacognition.py       _VALUE_DRIFT_CONTRADICTION_WINDOW_S = 7 days;
                            compares two consecutive 7-day windows
                            (mid=now-7d, start=now-14d) -- the furthest
                            actual read reaches 14 days back. This is the
                            longest need found anywhere.
  GATE_DECISIONS_RETENTION_DAYS = 21: the 14-day maximum need plus a
  7-day margin (matches the week-unit already used by the constant it's
  derived from), so a daily prune tick can never race past a row a
  consumer still needs.

  throw_net_sessions consumers:
    substrate_harmonic.py  _read_throw_net_rate: 3600s (1h) -- the only
                            reader anywhere in the codebase.
  THROW_NET_SESSIONS_RETENTION_DAYS = 7: vastly more than the 1h actual
  need; kept at a full week (rather than e.g. 1 day) purely for
  investigative headroom, since the table is cheap at this volume and a
  few days of history has repeatedly been useful for debugging this
  session.

NULL-BYPASS FAILURE MODE -- explicitly ruled out, not just avoided.
decay_pass()'s original bug (theory_x/stage3_world_model/promotion.py,
fixed 2026-07-26) was `last_referenced_at IS NULL OR last_referenced_at
< cutoff` -- the IS NULL clause made an unreferenced belief (the default
state) bypass the age check entirely and qualify immediately, not after
the intended idle period. That failure mode requires a nullable
timestamp column. Verified directly against the live schema:
gate_decisions.ts and throw_net_sessions.started_at are both
`REAL NOT NULL` (confirmed via sqlite_master, 2026-07-27) -- a row is
schema-guaranteed to have a real timestamp or the INSERT itself would
have failed. `_prune_table()` below uses a plain `ts_column < cutoff`
comparison with no OR/COALESCE; there is no null case for it to bypass.

FIRST-TICK BEHAVIOUR, stated explicitly per the same discipline: on the
first run against the current live data (2026-07-27), gate_decisions
has ~23.3M of 25.8M rows (90%) older than 21 days, and this is EXPECTED
and CORRECT, not a bug -- the table has never been pruned and the bulk
of its history is the now-fixed contradicts_anchor flood. This is the
same shape as the throw_net_triggers backlog prune (2026-07-26): a
one-time large catch-up followed by a small steady-state trickle
forever after (~123K/day / 21 = a bounded, roughly constant table size
in the low millions, not unbounded growth). Batched via the same
LIMIT-subquery pattern used for that prune, to avoid holding one long
write lock against the live shared Writer.

VACUUM -- deliberately NOT done here, and not something this loop should
ever call. SQLite's auto_vacuum is off on beliefs.db (confirmed via
PRAGMA, 2026-07-27); DELETE frees pages onto SQLite's internal freelist
for reuse by future writes (bounding future file growth) but does not
shrink the file on disk. Reclaiming the ~23M rows' worth of freed space
requires a manual VACUUM, which takes an exclusive lock for its full
duration and needs roughly the DB's own size again in free disk space
(74GB free vs ~9GB beliefs.db -- space is not the constraint). Given the
live service shares this exact DB through a single Writer, VACUUM would
stall it for an unknown but plausibly multi-minute duration. That is a
separate, deliberately-scheduled maintenance decision, not something to
fold into an automatic periodic loop.
"""
from __future__ import annotations

import threading
import time

import errors

_LOG_SOURCE = "gate_retention"

GATE_DECISIONS_RETENTION_DAYS = 21
THROW_NET_SESSIONS_RETENTION_DAYS = 7

_BATCH_SIZE = 250000
_TICK_SECONDS = 86400  # daily -- both retention windows are measured in weeks


def _prune_table(writer, reader, table: str, ts_column: str,
                  retention_days: int, batch_size: int = _BATCH_SIZE) -> int:
    """Delete rows in `table` older than retention_days, batched.

    Loops until no more rows match rather than assuming a single batch
    suffices -- correct and safe whether this is the first, large
    catch-up run or a routine small daily delta; the same code path
    handles both without a special case.
    """
    cutoff = time.time() - retention_days * 86400
    total_deleted = 0
    while True:
        remaining = reader.read(
            f"SELECT COUNT(*) AS n FROM {table} WHERE {ts_column} < ?",
            (cutoff,),
        )
        n = remaining[0]["n"] if remaining else 0
        if n == 0:
            break
        writer.write(
            f"DELETE FROM {table} WHERE id IN "
            f"(SELECT id FROM {table} WHERE {ts_column} < ? LIMIT ?)",
            (cutoff, batch_size),
        )
        total_deleted += min(n, batch_size)
    return total_deleted


def prune_gate_decisions(writer, reader) -> int:
    return _prune_table(
        writer, reader, "gate_decisions", "ts", GATE_DECISIONS_RETENTION_DAYS
    )


def prune_throw_net_sessions(writer, reader) -> int:
    return _prune_table(
        writer, reader, "throw_net_sessions", "started_at",
        THROW_NET_SESSIONS_RETENTION_DAYS,
    )


def retention_loop(state, stop: threading.Event) -> None:
    """Daemon entrypoint matching stage2_dynamic's (state, stop) contract."""
    while not stop.is_set():
        stop.wait(_TICK_SECONDS)
        if stop.is_set():
            break
        try:
            writer = state.writers["beliefs"]
            reader = state.readers["beliefs"]
            gd_count = prune_gate_decisions(writer, reader)
            tns_count = prune_throw_net_sessions(writer, reader)
            if gd_count or tns_count:
                errors.record(
                    f"gate_retention pruned gate_decisions={gd_count} "
                    f"throw_net_sessions={tns_count}",
                    source=_LOG_SOURCE, level="INFO",
                )
        except Exception as exc:
            errors.record(
                f"gate_retention_loop error: {exc}", source=_LOG_SOURCE, exc=exc
            )
