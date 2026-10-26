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

import logging
import os
import sqlite3
from pathlib import Path
from typing import Any, Callable, Optional

# Re-exported so callers can `from substrate import connect, Row, ...` and drop
# their own `import sqlite3` (the one-pen compliance ratchet forbids importing
# sqlite3 outside this package).
from sqlite3 import (  # noqa: F401
    Connection,
    Cursor,
    DatabaseError,
    Error,
    IntegrityError,
    OperationalError,
    Row,
)

THEORY_X_STAGE = None

DEFAULT_BUSY_TIMEOUT_MS = 5000

_tripwire_log = logging.getLogger("substrate.schema_tripwire")
_SCHEMA_ERRORS = ("no such table", "no such column", "has no column named")


def _trip(exc: sqlite3.OperationalError, sql: str) -> None:
    msg = str(exc)
    if any(m in msg for m in _SCHEMA_ERRORS):
        _tripwire_log.error("SCHEMA TRIPWIRE: %s | sql: %s", msg,
                            " ".join(str(sql).split())[:300])


class _TripwireCursor(sqlite3.Cursor):
    def execute(self, sql, *args):
        try:
            return super().execute(sql, *args)
        except sqlite3.OperationalError as e:
            _trip(e, sql)
            raise

    def executemany(self, sql, *args):
        try:
            return super().executemany(sql, *args)
        except sqlite3.OperationalError as e:
            _trip(e, sql)
            raise

    def executescript(self, sql):
        try:
            return super().executescript(sql)
        except sqlite3.OperationalError as e:
            _trip(e, sql)
            raise


class _TripwireConnection(sqlite3.Connection):
    """NEX5_SCHEMA_TRIPWIRE=1: log every schema error (unknown table/column)
    with its SQL at the moment it is raised, then re-raise it unchanged. Many
    callers swallow these errors, so a missing column otherwise fails without
    a trace. Observation only: control flow is identical with it on or off.
    Connection.execute/executemany do NOT route through cursor() (CPython
    builds the cursor in C), so each entry point is wrapped explicitly."""

    def cursor(self, factory=_TripwireCursor):
        return super().cursor(factory)

    def execute(self, sql, *args):
        try:
            return super().execute(sql, *args)
        except sqlite3.OperationalError as e:
            _trip(e, sql)
            raise

    def executemany(self, sql, *args):
        try:
            return super().executemany(sql, *args)
        except sqlite3.OperationalError as e:
            _trip(e, sql)
            raise

    def executescript(self, sql):
        try:
            return super().executescript(sql)
        except sqlite3.OperationalError as e:
            _trip(e, sql)
            raise


def connect(
    db_path: str | Path,
    *,
    read_only: bool = False,
    busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS,
    row_factory: Optional[Callable[[sqlite3.Cursor, Any], Any]] = None,
    timeout: Optional[float] = None,
    uri: bool = False,
    isolation_level: Optional[str] = "",
    check_same_thread: bool = False,
) -> sqlite3.Connection:
    """Open a SQLite connection with NEX's standard pragmas (WAL on read-write,
    busy_timeout, foreign_keys=ON).

    Also a drop-in for the sqlite3.connect call shapes used across the codebase,
    so the connect()-factory migration is a mechanical swap:
      * a pre-formed `file:...?mode=ro` URI (with uri=True) is accepted as-is,
        and `mode=ro` is recognised as read-only;
      * `timeout` (seconds) overrides the busy_timeout-derived default;
      * `isolation_level` defaults to "" — sqlite3's own default (implicit
        deferred transactions), so a migrated raw caller behaves exactly as it
        did on sqlite3.connect. The Writer passes isolation_level=None to get
        the autocommit/explicit-BEGIN mode its one-pen txn control needs (the
        4.0 contention post-mortem, see writer.py).
    """
    s = str(db_path)
    if uri or s.startswith("file:"):
        target, use_uri = s, True
        if "mode=ro" in s:
            read_only = True
    elif read_only:
        target, use_uri = f"file:{s}?mode=ro", True
    else:
        target, use_uri = s, False

    if timeout is None:
        timeout = busy_timeout_ms / 1000.0
    else:
        busy_timeout_ms = int(float(timeout) * 1000)

    extra = {}
    if os.environ.get("NEX5_SCHEMA_TRIPWIRE") == "1":
        extra["factory"] = _TripwireConnection
    conn = sqlite3.connect(
        target,
        uri=use_uri,
        isolation_level=isolation_level,
        check_same_thread=check_same_thread,
        timeout=timeout,
        **extra,
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
