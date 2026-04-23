"""Writer roundtrip — submit a write, verify it persisted."""
import tempfile
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

from substrate import Reader, Writer


SCHEMA = """
CREATE TABLE t (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL
);
"""


class TestWriterRoundtrip(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Path(self._tmp.name) / "round.db"
        self.writer = Writer(self.db, name="round")
        # Apply schema via the Writer.
        for stmt in [s.strip() for s in SCHEMA.split(";") if s.strip()]:
            self.writer.write(stmt, ())

    def tearDown(self):
        self.writer.close()
        self._tmp.cleanup()

    def test_single_statement_roundtrip(self):
        rowid = self.writer.write(
            "INSERT INTO t (content) VALUES (?)", ("hello",)
        )
        self.assertEqual(rowid, 1)

        reader = Reader(self.db)
        rows = reader.read("SELECT id, content FROM t")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["content"], "hello")

    def test_multi_statement_atomic(self):
        rowids = self.writer.write_many([
            ("INSERT INTO t (content) VALUES (?)", ("a",)),
            ("INSERT INTO t (content) VALUES (?)", ("b",)),
            ("INSERT INTO t (content) VALUES (?)", ("c",)),
        ])
        self.assertEqual(len(rowids), 3)

        reader = Reader(self.db)
        self.assertEqual(reader.count("t"), 3)

    def test_multi_statement_rollback_on_error(self):
        with self.assertRaises(Exception):
            self.writer.write_many([
                ("INSERT INTO t (content) VALUES (?)", ("ok1",)),
                ("INSERT INTO nonexistent_table (x) VALUES (?)", (1,)),
            ])
        reader = Reader(self.db)
        # ok1 must NOT have landed — the BEGIN IMMEDIATE / ROLLBACK on error
        # guarantees atomicity.
        self.assertEqual(reader.count("t"), 0)

    def test_error_does_not_kill_worker(self):
        with self.assertRaises(Exception):
            self.writer.write("INSERT INTO nope VALUES (1)", ())
        # Next write should still succeed — the worker thread survived.
        self.writer.write("INSERT INTO t (content) VALUES (?)", ("survivor",))
        self.assertEqual(Reader(self.db).count("t"), 1)


if __name__ == "__main__":
    unittest.main()
