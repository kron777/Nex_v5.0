"""Passive-mode safety — the single choke point for all data access.

The Watcher must never be able to write to NEX or its databases. Guarantees here:

  * SQLite is opened read-only (`mode=ro` URI). A write attempt raises at the
    SQLite layer, and a connection authorizer DENIES every mutating action as a
    second, independent barrier.
  * `guard_sql` rejects any statement that looks mutating, before it runs.
  * If read-only cannot be established, the operation is REFUSED — never
    silently downgraded to read-write.

Nothing in this package opens a writable handle to any NEX file or database.
"""
from __future__ import annotations

import re
import sqlite3
from typing import Iterable

_MUTATING = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|VACUUM|ATTACH|REINDEX|"
    r"PRAGMA\s+\w+\s*=)\b",
    re.IGNORECASE,
)

# SQLite authorizer action codes that represent a write/schema change.
_DENY_ACTIONS = {
    sqlite3.SQLITE_CREATE_INDEX, sqlite3.SQLITE_CREATE_TABLE,
    sqlite3.SQLITE_CREATE_TEMP_INDEX, sqlite3.SQLITE_CREATE_TEMP_TABLE,
    sqlite3.SQLITE_CREATE_TEMP_TRIGGER, sqlite3.SQLITE_CREATE_TEMP_VIEW,
    sqlite3.SQLITE_CREATE_TRIGGER, sqlite3.SQLITE_CREATE_VIEW,
    sqlite3.SQLITE_DELETE, sqlite3.SQLITE_DROP_INDEX, sqlite3.SQLITE_DROP_TABLE,
    sqlite3.SQLITE_DROP_TEMP_INDEX, sqlite3.SQLITE_DROP_TEMP_TABLE,
    sqlite3.SQLITE_DROP_TEMP_TRIGGER, sqlite3.SQLITE_DROP_TEMP_VIEW,
    sqlite3.SQLITE_DROP_TRIGGER, sqlite3.SQLITE_DROP_VIEW,
    sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_ALTER_TABLE,
}


class PassiveViolation(RuntimeError):
    """Raised when something tries to leave passive (read-only) mode."""


def guard_sql(sql: str) -> str:
    """Return `sql` unchanged if it is read-only; raise PassiveViolation otherwise."""
    if _MUTATING.search(sql or ""):
        raise PassiveViolation(f"refused mutating SQL in passive mode: {sql!r}")
    return sql


def _ro_authorizer(action, *_args):
    return sqlite3.SQLITE_DENY if action in _DENY_ACTIONS else sqlite3.SQLITE_OK


def read_only_connect(db_path) -> sqlite3.Connection:
    """Open `db_path` strictly read-only, with a write-denying authorizer.

    Raises sqlite3.OperationalError if the file cannot be opened read-only
    (e.g. missing). It is never opened read-write.
    """
    uri = f"file:{db_path}?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=5)
    con.row_factory = sqlite3.Row
    con.set_authorizer(_ro_authorizer)
    return con


def read_only_query(db_path, sql: str, params: Iterable = ()) -> list:
    """Run one read-only query and return rows. Refuses mutating SQL twice over
    (guard_sql + the mode=ro connection + the authorizer)."""
    guard_sql(sql)
    con = read_only_connect(db_path)
    try:
        return list(con.execute(sql, tuple(params)))
    finally:
        con.close()
