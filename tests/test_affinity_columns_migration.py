"""Regression guard for the beliefs.affinity schema-drift migration.

Context (substrate/init_db.py:239-248): `affinity` and `affinity_updated_at` are
read and written by `theory_x/life/affinity_loop.py` but were defined in NO schema
file — they existed only in the live DB, added out-of-band, so a fresh `init_all()`
once produced a beliefs table WITHOUT them and the first affinity_tick raised
"no such column: affinity". The fix is a migration (init_db.py:247-248). Both
columns are nullable on purpose: `affinity IS NULL` is the "not-yet-rated" state the
loop's SELECT depends on.

Unlike arc_closers (dual schema+migration), these columns are MIGRATION-ONLY, so a
single fresh `init_all()` test genuinely exercises the migration — no separate
legacy fixture is needed. Isolated; no runtime/migration code changed. (tests/ is
exempt from the no-raw-sqlite3 architecture invariant.)
"""
import os
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401


def _init_real_beliefs_db() -> tuple[str, str]:
    tmp = tempfile.mkdtemp(prefix="nex5_affinity_")
    os.environ["NEX5_DATA_DIR"] = tmp
    os.environ["NEX5_ADMIN_HASH_FILE"] = str(Path(tmp) / "admin.argon2")
    from substrate.init_db import init_all
    init_all()
    from substrate import db_paths
    return tmp, str(db_paths()["beliefs"])


class TestAffinityColumnsMigration(unittest.TestCase):
    def setUp(self):
        self.tmp, self.db = _init_real_beliefs_db()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.pop("NEX5_DATA_DIR", None)
        os.environ.pop("NEX5_ADMIN_HASH_FILE", None)

    def test_init_all_provisions_affinity_columns(self):
        """A fresh init_all() must leave beliefs with affinity + affinity_updated_at,
        both NULLABLE — guarding the 'no such column: affinity' schema drift."""
        con = sqlite3.connect(f"file:{self.db}?mode=ro", uri=True)
        try:
            info = {r[1]: {"type": r[2], "notnull": r[3]}
                    for r in con.execute("PRAGMA table_info(beliefs)")}
            self.assertIn("affinity", info, "fresh init_all() did not provision beliefs.affinity")
            self.assertIn("affinity_updated_at", info)
            self.assertEqual(info["affinity"]["notnull"], 0, "affinity must be nullable")
            self.assertEqual(info["affinity_updated_at"]["notnull"], 0)
            # the exact query affinity_loop depends on must run (no 'no such column')
            con.execute("SELECT id FROM beliefs WHERE affinity IS NULL LIMIT 1").fetchall()
        finally:
            con.close()

    def test_newly_seeded_beliefs_are_unrated(self):
        """`affinity IS NULL` = not-yet-rated: nothing is rated at init."""
        con = sqlite3.connect(f"file:{self.db}?mode=ro", uri=True)
        try:
            total = con.execute("SELECT COUNT(*) FROM beliefs").fetchone()[0]
            rated = con.execute("SELECT COUNT(*) FROM beliefs "
                                "WHERE affinity IS NOT NULL").fetchone()[0]
            self.assertGreater(total, 0, "init_all should seed some beliefs")
            self.assertEqual(rated, 0, "no belief should be pre-rated at init (affinity IS NULL)")
        finally:
            con.close()


if __name__ == "__main__":
    unittest.main()
