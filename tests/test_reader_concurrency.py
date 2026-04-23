"""Reader concurrency — N readers run while the writer is active.

This is the 4.0 regression guard. In deferred-mode (4.0's bug), an
open write transaction would hold the WAL write lock and block other
connections up to busy_timeout. With isolation_level=None + explicit
BEGIN IMMEDIATE/COMMIT, readers should never block.
"""
import concurrent.futures as cf
import tempfile
import threading
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

from substrate import Reader, Writer


SCHEMA = "CREATE TABLE t (id INTEGER PRIMARY KEY AUTOINCREMENT, v INTEGER NOT NULL);"


class TestReaderConcurrency(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Path(self._tmp.name) / "conc.db"
        self.writer = Writer(self.db, name="conc")
        self.writer.write(SCHEMA, ())

    def tearDown(self):
        self.writer.close()
        self._tmp.cleanup()

    def test_many_readers_with_active_writer(self):
        stop = threading.Event()

        def writer_loop():
            n = 0
            while not stop.is_set():
                self.writer.write("INSERT INTO t (v) VALUES (?)", (n,))
                n += 1
                time.sleep(0.001)

        def reader_loop(tag: int) -> int:
            reader = Reader(self.db)
            reads = 0
            deadline = time.monotonic() + 0.5
            while time.monotonic() < deadline:
                rows = reader.read("SELECT COUNT(*) AS n FROM t")
                self.assertGreaterEqual(rows[0]["n"], 0)
                reads += 1
            return reads

        t = threading.Thread(target=writer_loop, daemon=True)
        t.start()
        try:
            with cf.ThreadPoolExecutor(max_workers=8) as ex:
                results = list(ex.map(reader_loop, range(8)))
        finally:
            stop.set()
            t.join(timeout=2.0)

        # Every reader should have completed many reads — the exact number
        # depends on scheduling, but "stuck on a write lock" would show up
        # as near-zero reads from some workers.
        for reads in results:
            self.assertGreater(reads, 10, f"a reader stalled ({reads} reads)")
        # And the writer must have written something.
        self.assertGreater(Reader(self.db).count("t"), 10)


if __name__ == "__main__":
    unittest.main()
