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


if __name__ == "__main__":
    unittest.main()
