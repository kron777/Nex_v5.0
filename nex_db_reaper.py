#!/usr/bin/env python3
"""nex_db_reaper.py — nightly retention reaper for NEX's high-churn tables.

WHY: pipeline_events / sense_events / tree_snapshots grow unbounded (~1.8 GB/mo)
and were the memory-pressure that forced the 2026-08-24 shutdown (see DB_AUDIT.md).
This bounds them to a 30-day window.

SAFE AGAINST A LIVE NEX (the hard requirement):
  * WAL mode → readers never block; only ONE writer at a time, so we take the
    write lock in SMALL batches and RELEASE it between batches (short txns +
    a brief sleep) so her fires interleave. busy_timeout waits politely if she
    holds it; we never hold a long lock.
  * The cutoff is computed ONCE at start; her fresh rows are always newer than
    it, so they are never selected — we only ever touch rows older than 30 days.
  * NO VACUUM here. auto_vacuum is OFF (0), so freed pages go to the freelist and
    are reused by her next inserts — no file shrink, no exclusive lock. Reclaim
    to the OS is a separate, off-only VACUUM (see --note).
  * Fail-safe: on lock/busy, back off and retry a few times, then exit CLEAN (0).
    Any unexpected error is logged and the run ends without crashing.

Usage:
  nex_db_reaper.py            # reap (batched deletes, freelist reclaim)
  nex_db_reaper.py --dry-run  # print what WOULD be deleted, delete nothing
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time

DATA = "/home/rr/Desktop/Desktop/nex5/data"
LOG = os.path.expanduser("~/.nex/reaper.log")

RETENTION_DAYS = 30
BATCH = 5000                 # rows per delete txn
BUSY_TIMEOUT_MS = 5000       # wait up to 5s for her write lock, then back off
SLEEP_BETWEEN_BATCHES = 0.2  # yield the write lock to NEX
CHECKPOINT_EVERY = 40        # PASSIVE wal checkpoint cadence (non-blocking)
MAX_LOCK_RETRIES = 5         # per batch, before backing off this table

# (db file, table, timestamp column)
TARGETS = [
    ("dynamic.db", "pipeline_events", "ts"),
    ("dynamic.db", "tree_snapshots",  "ts"),
    ("sense.db",   "sense_events",    "timestamp"),
]


def log(msg: str) -> None:
    line = f"{time.strftime('%F %T')} nex_db_reaper: {msg}"
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def _connect(db_file: str, readonly: bool) -> sqlite3.Connection:
    path = os.path.join(DATA, db_file)
    if readonly:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=BUSY_TIMEOUT_MS / 1000.0)
    else:
        con = sqlite3.connect(path, timeout=BUSY_TIMEOUT_MS / 1000.0, isolation_level=None)
        con.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
        # DO NOT change journal_mode/auto_vacuum — inherit the live DB's WAL.
    return con


def _freelist(con: sqlite3.Connection) -> int:
    try:
        return con.execute("PRAGMA freelist_count").fetchone()[0]
    except sqlite3.Error:
        return -1


def dry_run(cutoff: int) -> None:
    log(f"DRY-RUN — cutoff {time.strftime('%F %T', time.gmtime(cutoff))}Z "
        f"({RETENTION_DAYS}d). Deleting nothing.")
    total_would = 0
    for db_file, tbl, col in TARGETS:
        try:
            con = _connect(db_file, readonly=True)
            tot = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            old = con.execute(f"SELECT COUNT(*) FROM {tbl} WHERE {col} < ?", (cutoff,)).fetchone()[0]
            con.close()
            total_would += old
            pct = (100.0 * old / tot) if tot else 0.0
            log(f"  {db_file}:{tbl}: total={tot:,} WOULD DELETE={old:,} ({pct:.1f}%) keep={tot-old:,}")
        except sqlite3.Error as e:
            log(f"  {db_file}:{tbl}: read error (skipped): {e}")
    log(f"DRY-RUN total rows that WOULD be deleted: {total_would:,}")


def reap_table(db_file: str, tbl: str, col: str, cutoff: int) -> int:
    """Batched delete of rows older than cutoff. Returns rows reaped."""
    reaped = 0
    batches = 0
    fl_before = -1
    try:
        con = _connect(db_file, readonly=False)
        fl_before = _freelist(con)
        while True:
            # one short transaction per batch; rowid-subquery is the portable
            # equivalent of "DELETE ... LIMIT N" (stock SQLite has no DELETE LIMIT).
            retries = 0
            while True:
                try:
                    cur = con.execute(
                        f"DELETE FROM {tbl} WHERE rowid IN "
                        f"(SELECT rowid FROM {tbl} WHERE {col} < ? LIMIT {BATCH})",
                        (cutoff,),
                    )
                    n = cur.rowcount
                    break
                except sqlite3.OperationalError as e:
                    # locked/busy: NEX is mid-write. Back off and retry a few times.
                    retries += 1
                    if retries > MAX_LOCK_RETRIES:
                        log(f"  {tbl}: locked after {MAX_LOCK_RETRIES} retries — backing off, "
                            f"reaped {reaped:,} so far this table")
                        con.close()
                        return reaped
                    time.sleep(0.5 * retries)
            if n <= 0:
                break
            reaped += n
            batches += 1
            if batches % CHECKPOINT_EVERY == 0:
                try:
                    con.execute("PRAGMA wal_checkpoint(PASSIVE)")  # non-blocking
                except sqlite3.Error:
                    pass
            time.sleep(SLEEP_BETWEEN_BATCHES)  # let her write
        fl_after = _freelist(con)
        try:
            con.execute("PRAGMA wal_checkpoint(PASSIVE)")
        except sqlite3.Error:
            pass
        con.close()
        freed_pages = (fl_after - fl_before) if (fl_before >= 0 and fl_after >= 0) else -1
        freed_mb = (freed_pages * 4096 / 1048576.0) if freed_pages >= 0 else -1
        log(f"  {db_file}:{tbl}: reaped {reaped:,} rows in {batches} batches; "
            f"freelist {fl_before}->{fl_after} (~{freed_mb:.0f} MB reusable in-file)"
            if freed_pages >= 0 else
            f"  {db_file}:{tbl}: reaped {reaped:,} rows in {batches} batches")
        return reaped
    except sqlite3.Error as e:
        log(f"  {db_file}:{tbl}: ERROR (exiting clean for this table): {e}")
        return reaped


def reap(cutoff: int) -> None:
    log(f"START — cutoff {time.strftime('%F %T', time.gmtime(cutoff))}Z ({RETENTION_DAYS}d), "
        f"batch={BATCH}, busy_timeout={BUSY_TIMEOUT_MS}ms")
    grand = 0
    for db_file, tbl, col in TARGETS:
        grand += reap_table(db_file, tbl, col, cutoff)
    log(f"DONE — total rows reaped: {grand:,}. "
        f"(No VACUUM: freed pages are on the freelist, reused by NEX. "
        f"Run VACUUM only when NEX is OFF to return space to the OS.)")


def main() -> int:
    ap = argparse.ArgumentParser(description="NEX nightly DB retention reaper")
    ap.add_argument("--dry-run", action="store_true",
                    help="print what would be deleted; delete nothing")
    ap.add_argument("--days", type=int, default=RETENTION_DAYS,
                    help=f"retention window in days (default {RETENTION_DAYS})")
    args = ap.parse_args()
    cutoff = int(time.time()) - args.days * 86400
    try:
        if args.dry_run:
            dry_run(cutoff)
        else:
            reap(cutoff)
    except Exception as e:  # never crash a scheduled run
        log(f"FATAL (exiting clean): {e}")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
