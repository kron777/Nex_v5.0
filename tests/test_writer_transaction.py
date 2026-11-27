"""Writer transaction callbacks execute on the one-pen connection."""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from substrate import Writer, connect


class WriterTransactionTests(unittest.TestCase):
    def test_callback_reads_and_writes_in_one_committed_transaction(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "writer.db"
            cx = connect(path)
            cx.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, value TEXT)")
            cx.commit()
            cx.close()

            writer = Writer(path, name="transaction-commit-test")
            try:
                row_id = writer.transaction(lambda db: db.execute(
                    "INSERT INTO items(value) VALUES ('committed')"
                ).lastrowid)
            finally:
                writer.close()

            cx = connect(path)
            try:
                self.assertEqual(cx.execute(
                    "SELECT value FROM items WHERE id=?", (row_id,)
                ).fetchone()[0], "committed")
            finally:
                cx.close()

    def test_callback_exception_rolls_back_every_statement(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "writer.db"
            cx = connect(path)
            cx.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, value TEXT)")
            cx.commit()
            cx.close()

            writer = Writer(path, name="transaction-rollback-test")
            try:
                def fail(db):
                    db.execute("INSERT INTO items(value) VALUES ('must roll back')")
                    raise RuntimeError("injected failure")

                with self.assertRaisesRegex(RuntimeError, "injected failure"):
                    writer.transaction(fail)
                writer.write("INSERT INTO items(value) VALUES ('after rollback')")
            finally:
                writer.close()

            cx = connect(path)
            try:
                values = [r[0] for r in cx.execute("SELECT value FROM items ORDER BY id")]
                self.assertEqual(values, ["after rollback"])
            finally:
                cx.close()


if __name__ == "__main__":
    unittest.main()
