"""NEX5_SCHEMA_TRIPWIRE — schema errors are logged where raised, then re-raised.

Many callers swallow OperationalError, so an unknown table or column fails
without a trace. With the flag on, substrate.connect() connections log each one
with its SQL and re-raise it unchanged; with it off they are plain connections.
"""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests import _bootstrap  # noqa: F401

from substrate import Row, connect


class TestSchemaTripwire(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "t.db")

    def tearDown(self):
        self.tmp.cleanup()

    def _conn(self, on):
        env = {"NEX5_SCHEMA_TRIPWIRE": "1"} if on else {}
        with mock.patch.dict(os.environ, env, clear=False):
            if not on:
                os.environ.pop("NEX5_SCHEMA_TRIPWIRE", None)
            c = connect(self.db)
        c.execute("CREATE TABLE IF NOT EXISTS t (a INTEGER)")
        return c

    _PATHS = {
        "conn.execute": lambda c: c.execute("SELECT missing_col FROM t"),
        "conn.executemany": lambda c: c.executemany(
            "INSERT INTO t (missing_col) VALUES (?)", [(1,)]),
        "cursor.execute": lambda c: c.cursor().execute("SELECT * FROM missing_tbl"),
        "cursor.executemany": lambda c: c.cursor().executemany(
            "INSERT INTO missing_tbl VALUES (?)", [(1,)]),
        "conn.executescript": lambda c: c.executescript("SELECT * FROM missing_tbl;"),
    }

    def test_every_entry_point_logs_and_reraises(self):
        c = self._conn(on=True)
        try:
            for label, fn in self._PATHS.items():
                with self.subTest(path=label):
                    with self.assertLogs("substrate.schema_tripwire", "ERROR") as cm:
                        with self.assertRaises(sqlite3.OperationalError):
                            fn(c)
                    self.assertIn("SCHEMA TRIPWIRE", cm.output[0])
                    self.assertIn("missing_", cm.output[0])   # the SQL is included
        finally:
            c.close()

    def test_off_by_default_plain_connection_no_log(self):
        c = self._conn(on=False)
        try:
            self.assertIs(type(c), sqlite3.Connection)
            for label, fn in self._PATHS.items():
                with self.subTest(path=label):
                    with self.assertNoLogs("substrate.schema_tripwire", "ERROR"):
                        with self.assertRaises(sqlite3.OperationalError):
                            fn(c)
        finally:
            c.close()

    def test_non_schema_errors_are_not_logged(self):
        c = self._conn(on=True)
        try:
            with self.assertNoLogs("substrate.schema_tripwire", "ERROR"):
                with self.assertRaises(sqlite3.OperationalError):
                    c.execute("SELEC nonsense")          # syntax, not schema
        finally:
            c.close()

    def test_normal_use_unchanged(self):
        c = self._conn(on=True)
        try:
            c.row_factory = Row
            c.executemany("INSERT INTO t (a) VALUES (?)", [(1,), (2,)])
            c.commit()
            rows = c.execute("SELECT a FROM t ORDER BY a").fetchall()
            self.assertEqual([r["a"] for r in rows], [1, 2])
        finally:
            c.close()


if __name__ == "__main__":
    unittest.main()
