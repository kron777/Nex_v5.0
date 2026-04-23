"""Reader — WAL-mode read connections for a SQLite database.

Readers are free and concurrent. Each `.read(...)` call opens a
fresh connection, runs the query, and closes. For hotter paths,
callers can use `.connection()` as a context manager to reuse a
connection across several queries.

WAL mode guarantees readers never block the writer and are never
blocked by the writer. Connections are opened in read-only mode
via the `mode=ro` URI parameter — an accidental write attempt
fails loudly rather than silently acquiring a write lock.

See SPECIFICATION.md §8 — Many Readers, No Wait.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional, Sequence

THEORY_X_STAGE = None


class Reader:
    def __init__(self, db_path: str | Path, *, busy_timeout_ms: int = 5000):
        self.db_path = str(db_path)
        self._busy_timeout_ms = busy_timeout_ms

    def _open(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            f"file:{self.db_path}?mode=ro",
            uri=True,
            isolation_level=None,
            check_same_thread=False,
            timeout=self._busy_timeout_ms / 1000.0,
        )
        conn.row_factory = sqlite3.Row
        conn.execute(f"PRAGMA busy_timeout={self._busy_timeout_ms}")
        return conn

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = self._open()
        try:
            yield conn
        finally:
            conn.close()

    def read(self, sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
        with self.connection() as conn:
            return list(conn.execute(sql, params).fetchall())

    def read_one(
        self, sql: str, params: Sequence[Any] = ()
    ) -> Optional[sqlite3.Row]:
        with self.connection() as conn:
            return conn.execute(sql, params).fetchone()

    def count(self, table: str) -> int:
        row = self.read_one(f"SELECT COUNT(*) AS n FROM {table}")
        return int(row["n"]) if row is not None else 0
