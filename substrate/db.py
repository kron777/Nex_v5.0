"""Canonical SQLite connection factory.

One place that opens a connection with the settings every connection to a
NEX database must have, so the invariant cannot drift across call sites:

    * WAL journalling + synchronous=NORMAL — many readers never block the
      one writer and vice versa (SPECIFICATION.md §8). These are database-
      level and can only be set on a read-write connection; a read-only
      connection inherits whatever the writer established and must not try
      to change them.
    * busy_timeout — wait on a lock instead of failing immediately.
    * foreign_keys=ON — SQLite leaves FK enforcement OFF per connection by
      default, so a schema's FOREIGN KEY clauses are inert unless each
      connection turns it on. Enforcing it here means a stray write through
      any connection built by this factory still rejects orphans.

Reader and Writer both build their connections here. New code that needs a
raw connection should call substrate.connect() rather than sqlite3.connect
so it picks up the same guarantees.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Callable, Optional

THEORY_X_STAGE = None

DEFAULT_BUSY_TIMEOUT_MS = 5000


def connect(
    db_path: str | Path,
    *,
    read_only: bool = False,
    busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS,
    row_factory: Optional[Callable[[sqlite3.Cursor, Any], Any]] = None,
) -> sqlite3.Connection:
    """Open a SQLite connection with NEX's standard pragmas.

    read_only opens via the `mode=ro` URI so an accidental write fails loudly
    rather than silently taking a write lock. isolation_level is None on every
    connection: callers drive transactions explicitly (BEGIN IMMEDIATE/COMMIT)
    so the library never auto-begins and holds the WAL write lock across
    statement boundaries (the 4.0 contention post-mortem — see writer.py).
    """
    if read_only:
        target, uri = f"file:{db_path}?mode=ro", True
    else:
        target, uri = str(db_path), False

    conn = sqlite3.connect(
        target,
        uri=uri,
        isolation_level=None,
        check_same_thread=False,
        timeout=busy_timeout_ms / 1000.0,
    )
    if row_factory is not None:
        conn.row_factory = row_factory

    # WAL + synchronous are database-level: only settable read-write.
    if not read_only:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(f"PRAGMA busy_timeout={int(busy_timeout_ms)}")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
