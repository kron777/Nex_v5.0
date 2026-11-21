"""Regression guard for the arc_closers.closure_type migration.

Context: `substrate/schema/beliefs.sql` creates arc_closers WITH
`closure_type TEXT NOT NULL DEFAULT 'template'`, and `substrate/init_db.py`
_apply_migrations also carries an idempotent `ALTER TABLE arc_closers ADD COLUMN
closure_type ...` for legacy databases that predate the column. Either path must
leave the column present; `theory_x/arcs` writes closure_type, so its absence is a
real defect. This was a WHATS_NEXT.md open-question migration bug that had been
fixed but left UNGUARDED — surfaced by the RDO's defect-remediation cycle as the
one eligible, net-new work item. This test is that guard.

Isolated: it does not modify NEX runtime or migration code. (tests/ is exempt from
the no-raw-sqlite3 architecture invariant, so sqlite3 is used directly for
read-only introspection.)
"""
import os
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401


def _init_real_beliefs_db() -> tuple[str, str]:
    tmp = tempfile.mkdtemp(prefix="nex5_arc_closers_")
    os.environ["NEX5_DATA_DIR"] = tmp
    os.environ["NEX5_ADMIN_HASH_FILE"] = str(Path(tmp) / "admin.argon2")
    from substrate.init_db import init_all
    init_all()
    from substrate import db_paths
    return tmp, str(db_paths()["beliefs"])


def _table_info(con: sqlite3.Connection, table: str) -> dict:
    # PRAGMA rows: (cid, name, type, notnull, dflt_value, pk)
    return {r[1]: {"type": r[2], "notnull": r[3], "dflt": r[4]}
            for r in con.execute(f"PRAGMA table_info({table})")}


def _closure_type_invariant_holds(con: sqlite3.Connection) -> bool:
    """The invariant this test protects. Kept as a function so the test can prove
    it FAILS on a pre-migration table (i.e. the guard is not vacuous)."""
    info = _table_info(con, "arc_closers")
    col = info.get("closure_type")
    if col is None:
        return False
    return col["notnull"] == 1 and str(col["dflt"] or "").strip("'\"") == "template"


class TestArcClosersClosureTypeMigration(unittest.TestCase):
    def test_closure_type_present_after_init_all(self):
        """Acceptance 1-3: real init_all() leaves closure_type NOT NULL default 'template'."""
        tmp, db = _init_real_beliefs_db()
        try:
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            try:
                self.assertTrue(_closure_type_invariant_holds(con),
                                "arc_closers.closure_type missing/incorrect after init_all()")
                info = _table_info(con, "arc_closers")["closure_type"]
                self.assertEqual(info["notnull"], 1)
                self.assertEqual(str(info["dflt"]).strip("'\""), "template")
            finally:
                con.close()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
            os.environ.pop("NEX5_DATA_DIR", None)
            os.environ.pop("NEX5_ADMIN_HASH_FILE", None)

    def test_default_applied_on_insert(self):
        """Acceptance 4 (behavioural, isolated): an insert omitting closure_type gets 'template'."""
        con = sqlite3.connect(":memory:")
        con.execute(
            "CREATE TABLE arc_closers (id INTEGER PRIMARY KEY AUTOINCREMENT, arc_id INTEGER, "
            "belief_id INTEGER, detected_at REAL, meta_confidence REAL, "
            "closure_type TEXT NOT NULL DEFAULT 'template')")
        con.execute("INSERT INTO arc_closers (arc_id, belief_id, detected_at, meta_confidence) "
                    "VALUES (1, 1, 0.0, 0.5)")
        self.assertEqual(con.execute("SELECT closure_type FROM arc_closers").fetchone()[0],
                         "template")
        con.close()

    def test_invariant_check_catches_the_regression(self):
        """Acceptance 5: the guard FAILS on a pre-migration arc_closers (non-vacuous)."""
        good = sqlite3.connect(":memory:")
        good.execute("CREATE TABLE arc_closers (id INTEGER PRIMARY KEY, "
                     "closure_type TEXT NOT NULL DEFAULT 'template')")
        self.assertTrue(_closure_type_invariant_holds(good))
        good.close()

        pre_migration = sqlite3.connect(":memory:")  # the regressed shape: no closure_type
        pre_migration.execute("CREATE TABLE arc_closers (id INTEGER PRIMARY KEY, "
                              "arc_id INTEGER, belief_id INTEGER)")
        self.assertFalse(_closure_type_invariant_holds(pre_migration),
                         "guard must catch a pre-migration arc_closers lacking closure_type")
        pre_migration.close()


class TestArcClosersLegacyUpgrade(unittest.TestCase):
    """The REAL legacy upgrade path: a pre-migration arc_closers (no closure_type)
    run through the actual `_apply_migrations` runner — not the fresh-schema path and
    not the invariant helper. Builds a minimal legacy beliefs.db so only the
    arc_closers ALTER fires (other migrations target absent tables -> skipped)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nex5_arc_legacy_")
        self.db = str(Path(self.tmp) / "legacy_beliefs.db")
        con = sqlite3.connect(self.db)
        # pre-migration shape: arc_closers WITHOUT closure_type, with one legacy row
        con.execute("CREATE TABLE arc_closers (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    "arc_id INTEGER NOT NULL, belief_id INTEGER NOT NULL, "
                    "detected_at REAL NOT NULL, meta_confidence REAL NOT NULL)")
        con.execute("INSERT INTO arc_closers (arc_id, belief_id, detected_at, meta_confidence) "
                    "VALUES (7, 7, 1.0, 0.9)")
        con.commit()
        con.close()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run_real_migration(self):
        from substrate import Writer
        from substrate.init_db import _apply_migrations
        w = Writer(self.db, name="beliefs")
        try:
            _apply_migrations({"beliefs": w})
        finally:
            w.close()

    def test_legacy_upgrade_adds_column_with_constraint_and_backfills(self):
        # pre-state: column genuinely absent
        con = sqlite3.connect(f"file:{self.db}?mode=ro", uri=True)
        self.assertNotIn("closure_type", _table_info(con, "arc_closers"))
        con.close()

        self._run_real_migration()   # the ACTUAL runner

        con = sqlite3.connect(f"file:{self.db}?mode=ro", uri=True)
        try:
            info = _table_info(con, "arc_closers")
            self.assertIn("closure_type", info, "real migration did not add closure_type")
            self.assertEqual(info["closure_type"]["notnull"], 1)                 # NOT NULL
            self.assertEqual(str(info["closure_type"]["dflt"]).strip("'\""), "template")
            # the pre-existing legacy row was backfilled by the DEFAULT
            self.assertEqual(
                con.execute("SELECT closure_type FROM arc_closers WHERE arc_id=7").fetchone()[0],
                "template")
        finally:
            con.close()

    def test_default_applied_on_insert_after_legacy_upgrade(self):
        self._run_real_migration()
        con = sqlite3.connect(self.db)
        try:
            con.execute("INSERT INTO arc_closers (arc_id, belief_id, detected_at, meta_confidence) "
                        "VALUES (8, 8, 2.0, 0.5)")
            con.commit()
            self.assertEqual(
                con.execute("SELECT closure_type FROM arc_closers WHERE arc_id=8").fetchone()[0],
                "template")
        finally:
            con.close()

    def test_repeated_migration_is_idempotent(self):
        self._run_real_migration()
        self._run_real_migration()   # second run must be a safe no-op (column-exists skip)
        con = sqlite3.connect(f"file:{self.db}?mode=ro", uri=True)
        try:
            cols = [r for r in _table_info(con, "arc_closers") if r == "closure_type"]
            self.assertEqual(len(cols), 1, "repeated migration must not duplicate the column")
        finally:
            con.close()


if __name__ == "__main__":
    unittest.main()
