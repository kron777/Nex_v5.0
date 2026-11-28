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
from typing import Any, Callable, Iterable, Optional, Sequence

import errors as error_channel

from .db import connect

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
    include_rowcounts: bool = False
    continue_on_integrity_error: bool = False
    future: Future = field(default_factory=Future)
    transaction: Optional[Callable[[sqlite3.Connection], Any]] = None


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
        # Submission and shutdown share one lock so every accepted request is
        # queued before the shutdown sentinel, and every later request fails
        # synchronously instead of being stranded behind it.
        self._lifecycle_lock = threading.Lock()
        self._accepting = True
        self._sentinel_enqueued = False
        self.start()

    # --- lifecycle --------------------------------------------------------

    def start(self) -> None:
        with self._lifecycle_lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._started.clear()
            self._open_error = None
            self._accepting = True
            self._sentinel_enqueued = False
            thread = threading.Thread(
                target=self._run,
                name=f"Writer({self.name})",
                daemon=True,
            )
            self._thread = thread
            try:
                thread.start()
            except BaseException:
                # Thread.start can fail after the OS thread has been created.
                # The constructor will not return an owner to run.py, so this
                # Writer must quiesce its own partially-started worker.
                self._accepting = False
                if thread.ident is not None:
                    self._queue.put(_SENTINEL)
                    self._sentinel_enqueued = True
                    try:
                        thread.join(timeout=1.0)
                    except Exception:
                        logger.exception(
                            "Writer %s join failed during startup rollback", self.name
                        )
                    if not thread.is_alive():
                        self._thread = None
                        self._queue = queue.Queue()
                        self._sentinel_enqueued = False
                    else:
                        logger.error(
                            "Writer %s survived startup rollback; sentinel remains queued",
                            self.name,
                        )
                else:
                    self._thread = None
                    self._queue = queue.Queue()
                    self._sentinel_enqueued = False
                raise
        self._started.wait()
        if self._open_error is not None:
            raise RuntimeError(
                f"Writer failed to open {self.db_path}"
            ) from self._open_error

    def close(self, timeout: float = 10.0) -> None:
        """Stop accepting work, drain accepted requests, then close the connection.

        A timeout leaves the worker reference intact and raises TimeoutError;
        callers must not assume the connection has closed. Repeated close calls
        wait on the same shutdown sentinel. A later explicit start may reopen a
        fully stopped Writer.
        """
        with self._lifecycle_lock:
            thread = self._thread
            if thread is None:
                return
            if self._accepting:
                self._accepting = False
            if not self._sentinel_enqueued:
                self._queue.put(_SENTINEL)
                self._sentinel_enqueued = True

        thread.join(timeout=max(0.0, timeout))
        if thread.is_alive():
            raise TimeoutError(
                f"Writer {self.name} did not stop within {timeout:.3f}s"
            )
        with self._lifecycle_lock:
            if self._thread is thread:
                self._thread = None

    # --- submission -------------------------------------------------------

    def submit(self, req: WriteRequest) -> Future:
        with self._lifecycle_lock:
            if not self._accepting or self._thread is None or not self._thread.is_alive():
                raise RuntimeError(f"Writer {self.name} is closed or not running")
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

    def transaction(self, callback: Callable[[sqlite3.Connection], Any]) -> Any:
        """Run a read/write callback on this Writer's connection in one transaction.

        The callback executes on the Writer worker thread after BEGIN IMMEDIATE.
        It may read and write through the supplied connection, but must not call
        this same Writer's synchronous methods (that would deadlock its worker).
        Calls to other database Writers are allowed; their commits remain
        separate transactions and are not made atomically with this one.
        The connection/cursors must not escape the callback.
        """
        if not callable(callback):
            raise TypeError("transaction callback must be callable")
        req = WriteRequest(transaction=callback)
        self.submit(req)
        return req.future.result()

    def write_many_with_counts(
        self,
        statements: Iterable[tuple[str, Sequence[Any]]],
        *,
        continue_on_integrity_error: bool = False,
    ) -> list[tuple[Any, int]]:
        """Atomically execute statements and return (lastrowid, rowcount) per statement.

        Rowcounts are captured from each cursor before the next statement runs.
        This is useful for INSERT OR IGNORE batches where connection.total_changes
        is cumulative and cannot identify which individual statement inserted a row.

        When continue_on_integrity_error is true, an IntegrityError on one statement
        records (None, 0) for that statement and the transaction continues. Other
        error types still roll back the complete batch.
        """
        req = WriteRequest(
            statements=[(s, tuple(p)) for s, p in statements],
            include_rowcounts=True,
            continue_on_integrity_error=continue_on_integrity_error,
        )
        self.submit(req)
        return req.future.result()

    def queue_depth(self) -> int:
        return self._queue.qsize()

    # --- worker -----------------------------------------------------------

    def _open(self) -> sqlite3.Connection:
        # isolation_level=None (no implicit BEGIN — we drive txns explicitly),
        # plus WAL, synchronous=NORMAL, busy_timeout and foreign_keys=ON from
        # the shared factory; see substrate/db.py. (The factory default is "";
        # the Writer is the one caller that needs None.)
        return connect(self.db_path, busy_timeout_ms=self._busy_timeout_ms,
                       isolation_level=None)

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
            except sqlite3.IntegrityError as e:
                # UNIQUE constraint on beliefs.content is EXPECTED, not an error:
                # the store is correctly refusing a duplicate belief. Log quietly
                # at debug level (no traceback, no error-channel spam) so genuine
                # errors stay visible in the log. Still propagate to the caller.
                if "UNIQUE constraint" in str(e):
                    logger.debug("Writer duplicate skipped on %s: %s",
                                 self.db_path, e)
                else:
                    logger.exception("Writer integrity error on %s", self.db_path)
                    error_channel.record(
                        f"Writer integrity error on {self.db_path}: {e}",
                        source=f"substrate.writer[{self.name}]",
                        exc=e,
                    )
                item.future.set_exception(e)
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
        if req.transaction is not None:
            if req.sql is not None or req.statements is not None:
                raise ValueError("WriteRequest transaction cannot be combined with SQL statements")
            conn.execute("BEGIN IMMEDIATE")
            try:
                result = req.transaction(conn)
                conn.execute("COMMIT")
                return result
            except BaseException:
                try:
                    conn.execute("ROLLBACK")
                except Exception:
                    pass
                raise
        if req.statements is not None:
            conn.execute("BEGIN IMMEDIATE")
            try:
                results = []
                for statement, params in req.statements:
                    try:
                        cursor = conn.execute(statement, params)
                    except sqlite3.IntegrityError:
                        if not req.continue_on_integrity_error:
                            raise
                        results.append((None, 0))
                        continue
                    if req.include_rowcounts:
                        results.append((cursor.lastrowid, cursor.rowcount))
                    else:
                        results.append(cursor.lastrowid)
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
