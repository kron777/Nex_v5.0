"""substrate.connect() — the canonical connection factory (H5/H4).

Proves the invariant every NEX connection must carry: WAL, busy_timeout,
and — the one that was silently off almost everywhere — foreign_keys
enforcement that actually rejects orphan rows.
"""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

from substrate import connect


class TestConnectFactory(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self._tmp.name) / "factory.db")

    def tearDown(self):
        self._tmp.cleanup()

    def test_read_write_pragmas(self):
        conn = connect(self.path)
        try:
            self.assertEqual(
                conn.execute("PRAGMA journal_mode").fetchone()[0].lower(), "wal"
            )
            self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertEqual(conn.execute("PRAGMA busy_timeout").fetchone()[0], 5000)
            self.assertEqual(conn.execute("PRAGMA synchronous").fetchone()[0], 1)  # NORMAL
        finally:
            conn.close()

    def test_custom_busy_timeout(self):
        conn = connect(self.path, busy_timeout_ms=1234)
        try:
            self.assertEqual(conn.execute("PRAGMA busy_timeout").fetchone()[0], 1234)
        finally:
            conn.close()

    def test_foreign_keys_reject_orphan(self):
        # The H4 proof: a declared FK must actually bite.
        conn = connect(self.path)
        try:
            conn.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
            conn.execute(
                "CREATE TABLE child (id INTEGER PRIMARY KEY, "
                "parent_id INTEGER REFERENCES parent(id))"
            )
            conn.execute("INSERT INTO parent (id) VALUES (1)")
            # Child pointing at an existing parent: fine.
            conn.execute("INSERT INTO child (id, parent_id) VALUES (1, 1)")
            # Orphan child: must be refused because foreign_keys is ON.
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO child (id, parent_id) VALUES (2, 999)")
        finally:
            conn.close()

    def test_read_only_refuses_writes_and_sets_fk(self):
        # Seed the file read-write first (mode=ro will not create it).
        seed = connect(self.path)
        seed.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
        seed.execute("INSERT INTO t (id, v) VALUES (1, 'x')")
        seed.close()

        ro = connect(self.path, read_only=True, row_factory=sqlite3.Row)
        try:
            # Opening ro with foreign_keys=ON must not raise, and the flag sticks.
            self.assertEqual(ro.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            row = ro.execute("SELECT v FROM t WHERE id=1").fetchone()
            self.assertEqual(row["v"], "x")  # row_factory honoured
            with self.assertRaises(sqlite3.OperationalError):
                ro.execute("INSERT INTO t (id, v) VALUES (2, 'y')")
        finally:
            ro.close()


if __name__ == "__main__":
    unittest.main()
