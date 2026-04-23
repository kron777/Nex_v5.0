"""Writer — the one-pen scribe for a single SQLite database.

Every write to the database goes through Writer. Direct writes from
anywhere else are a bug by definition (see SPECIFICATION.md §8).

Design carry-forward from NEX 4.0 (gatekeeper contention post-mortem,
2026-04-20): open the write connection with isolation_level=None so
Python's sqlite3 library does not auto-begin deferred transactions
and hold the WAL write lock across statement boundaries. Transactions
are driven explicitly with BEGIN IMMEDIATE / COMMIT (or ROLLBACK on
error). This closes the exact failure mode that caused 4.0's
contention pathology.

One Writer per database, one worker thread per Writer. The worker
consumes a queue.Queue of WriteRequest objects. Callers may submit
asynchronously and wait on the returned Future, or use the
synchronous convenience methods `write()` / `write_many()`.
"""
from __future__ import annotations

import logging
import queue
import sqlite3
import threading
from concurrent.futures import Future
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

import errors as error_channel

THEORY_X_STAGE = None

logger = logging.getLogger("substrate.writer")


@dataclass
class WriteRequest:
    """A unit of work for the writer.

    Single statement: pass `sql` and `params`.
    Atomic multi-statement block: pass `statements`.
    """
    sql: Optional[str] = None
    params: Sequence[Any] = ()
    statements: Optional[list[tuple[str, Sequence[Any]]]] = None
    future: Future = field(default_factory=Future)


_SENTINEL = object()


class Writer:
    """One database, one write connection, one worker thread."""

    def __init__(
        self,
        db_path: str | Path,
        *,
        busy_timeout_ms: int = 5000,
        name: Optional[str] = None,
    ):
        self.db_path = str(db_path)
        self.name = name or Path(self.db_path).stem
        self._queue: "queue.Queue" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._conn: Optional[sqlite3.Connection] = None
        self._started = threading.Event()
        self._open_error: Optional[BaseException] = None
        self._busy_timeout_ms = busy_timeout_ms
        self.start()

    # --- lifecycle --------------------------------------------------------

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._started.clear()
        self._thread = threading.Thread(
            target=self._run,
            name=f"Writer({self.name})",
            daemon=True,
        )
        self._thread.start()
        self._started.wait()
        if self._open_error is not None:
            raise RuntimeError(
                f"Writer failed to open {self.db_path}"
            ) from self._open_error

    def close(self) -> None:
        """Graceful shutdown — drain the queue, close the connection."""
        if self._thread is None:
            return
        self._queue.put(_SENTINEL)
        self._thread.join(timeout=10.0)
        self._thread = None

    # --- submission -------------------------------------------------------

    def submit(self, req: WriteRequest) -> Future:
        self._queue.put(req)
        return req.future

    def write(self, sql: str, params: Sequence[Any] = ()) -> Any:
        """Single-statement synchronous write. Returns cursor.lastrowid."""
        req = WriteRequest(sql=sql, params=tuple(params))
        self.submit(req)
        return req.future.result()

    def write_many(self, statements: Iterable[tuple[str, Sequence[Any]]]) -> list[Any]:
        """Atomic multi-statement synchronous write. Returns [lastrowid, ...]."""
        req = WriteRequest(statements=[(s, tuple(p)) for s, p in statements])
        self.submit(req)
        return req.future.result()

    def queue_depth(self) -> int:
        return self._queue.qsize()

    # --- worker -----------------------------------------------------------

    def _open(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.db_path,
            isolation_level=None,          # no implicit BEGIN — we drive txns
            check_same_thread=False,
            timeout=self._busy_timeout_ms / 1000.0,
        )
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute(f"PRAGMA busy_timeout={self._busy_timeout_ms}")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _run(self) -> None:
        try:
            self._conn = self._open()
        except BaseException as e:
            self._open_error = e
            logger.exception("Writer failed to open %s", self.db_path)
            error_channel.record(
                f"Writer failed to open {self.db_path}",
                source=f"substrate.writer[{self.name}]",
                exc=e,
            )
            self._started.set()
            return
        self._started.set()
        while True:
            item = self._queue.get()
            if item is _SENTINEL:
                break
            try:
                item.future.set_result(self._execute(item))
            except BaseException as e:
                logger.exception("Writer error on %s", self.db_path)
                error_channel.record(
                    f"Writer error on {self.db_path}: {e}",
                    source=f"substrate.writer[{self.name}]",
                    exc=e,
                )
                item.future.set_exception(e)
        try:
            if self._conn is not None:
                self._conn.close()
        except Exception as e:
            logger.exception("Writer failed to close %s", self.db_path)
            error_channel.record(
                f"Writer close error on {self.db_path}: {e}",
                source=f"substrate.writer[{self.name}]",
                exc=e,
            )

    def _execute(self, req: WriteRequest):
        assert self._conn is not None
        conn = self._conn
        if req.statements is not None:
            conn.execute("BEGIN IMMEDIATE")
            try:
                results = [conn.execute(s, p).lastrowid for s, p in req.statements]
                conn.execute("COMMIT")
                return results
            except BaseException:
                try:
                    conn.execute("ROLLBACK")
                except Exception:
                    pass
                raise
        if req.sql is None:
            raise ValueError("WriteRequest has neither sql nor statements")
        conn.execute("BEGIN IMMEDIATE")
        try:
            cur = conn.execute(req.sql, req.params)
            conn.execute("COMMIT")
            return cur.lastrowid
        except BaseException:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            raise
