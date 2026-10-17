"""nex_db_backup — online backup + restore drill (H7).

Backs up a seeded DB, integrity-checks the copy, then recovers from it after
the source is lost. Points NEX5_DATA_DIR / NEX5_BACKUP_DIR at a temp area so
nothing touches live data.
"""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

import nex_db_backup as backup


class TestBackupRestore(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.data = Path(self._tmp.name) / "data"
        self.data.mkdir()
        os.environ["NEX5_DATA_DIR"] = str(self.data)
        os.environ["NEX5_BACKUP_DIR"] = str(Path(self._tmp.name) / "backups")
        self.src = self.data / "beliefs.db"
        con = sqlite3.connect(str(self.src))
        con.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
        con.executemany("INSERT INTO t (v) VALUES (?)", [("a",), ("b",), ("c",)])
        con.commit()
        con.close()

    def tearDown(self):
        os.environ.pop("NEX5_DATA_DIR", None)
        os.environ.pop("NEX5_BACKUP_DIR", None)
        self._tmp.cleanup()

    def _count(self, path):
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            return con.execute("SELECT COUNT(*) FROM t").fetchone()[0]
        finally:
            con.close()

    def test_backup_is_integrity_checked_copy(self):
        out = backup.backup_all(keep=7)
        made = out["beliefs"]
        self.assertIsNotNone(made)
        self.assertTrue(made.exists())
        self.assertTrue(backup._integrity_ok(made))
        self.assertEqual(self._count(made), 3)
        self.assertIsNone(out["sense"])  # missing DB -> skipped

    def test_restore_recovers_after_loss(self):
        made = backup.backup_all()["beliefs"]
        self.src.unlink()                      # simulate loss
        backup.restore_db(made, self.src)
        self.assertTrue(self.src.exists())
        self.assertEqual(self._count(self.src), 3)

    def test_restore_refuses_overwrite_without_force(self):
        made = backup.backup_all()["beliefs"]
        with self.assertRaises(FileExistsError):
            backup.restore_db(made, self.src)   # source still present
        backup.restore_db(made, self.src, force=True)  # force permits it
        self.assertEqual(self._count(self.src), 3)

    def test_restore_rejects_corrupt_backup(self):
        bad = Path(self._tmp.name) / "bad.db"
        bad.write_bytes(b"not a database")
        with self.assertRaises(ValueError):
            backup.restore_db(bad, self.data / "elsewhere.db")

    def test_rotation_keeps_n_most_recent(self):
        root = backup.backup_root()
        root.mkdir(parents=True, exist_ok=True)
        for stamp in range(5):
            (root / f"beliefs-2026010{stamp}-000000.db").write_bytes(b"x")
        removed = backup.rotate("beliefs", root, keep=2)
        self.assertEqual(len(removed), 3)
        self.assertEqual(len(list(root.glob("beliefs-*.db"))), 2)


if __name__ == "__main__":
    unittest.main()
