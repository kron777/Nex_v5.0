"""Schema invariants — fire-path indexes (H2) and no duplicate tables (M3)."""
import tempfile
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

from substrate import connect

_SCHEMA = Path(__file__).resolve().parent.parent / "substrate" / "schema"


class TestFirePathIndexes(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.conn = connect(str(Path(self._tmp.name) / "beliefs.db"))
        self.conn.executescript((_SCHEMA / "beliefs.sql").read_text())

    def tearDown(self):
        self.conn.close()
        self._tmp.cleanup()

    def test_fire_path_indexes_present(self):
        idx = {r[1] for r in self.conn.execute("PRAGMA index_list(beliefs)")}
        self.assertIn("idx_beliefs_created_at", idx)
        self.assertIn("idx_beliefs_source_created", idx)

    def test_recency_order_served_by_index(self):
        # The recency pool orders by created_at DESC with a LIMIT; with the
        # index that must not fall back to a transient sort.
        for i in range(200):
            self.conn.execute(
                "INSERT INTO beliefs (content, tier, confidence, created_at, source) "
                "VALUES (?, 2, 0.5, ?, 'fountain')",
                (f"b{i}", i),
            )
        plan = " ".join(
            str(r[-1])
            for r in self.conn.execute(
                "EXPLAIN QUERY PLAN "
                "SELECT id FROM beliefs ORDER BY created_at DESC LIMIT 50"
            )
        )
        self.assertIn("idx_beliefs_created_at", plan)
        self.assertNotIn("TEMP B-TREE FOR ORDER BY", plan.upper())


class TestAffinityColumns(unittest.TestCase):
    """D-A: affinity columns are registered as migrations, additive, nullable.

    Also pins the fresh-init fix: affinity / affinity_updated_at were read and
    written by affinity_loop but created in no schema or migration, so a fresh
    beliefs table lacked them and affinity_tick raised 'no such column'.
    """

    _AFFINITY_COLS = ("affinity", "affinity_updated_at",
                      "affinity_model", "affinity_legacy")

    def _affinity_alters(self):
        from substrate.init_db import _MIGRATIONS
        return [s for s in _MIGRATIONS["beliefs"]
                if "ADD COLUMN affinity" in s]

    def test_columns_registered_in_migrations(self):
        alters = " ".join(self._affinity_alters())
        for col in self._AFFINITY_COLS:
            self.assertIn(f"ADD COLUMN {col} ", alters + " ")

    def test_columns_created_nullable_and_query_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(str(Path(tmp) / "beliefs.db"))
            try:
                conn.executescript((_SCHEMA / "beliefs.sql").read_text())
                for stmt in self._affinity_alters():
                    conn.execute(stmt)
                cols = {r[1]: r for r in conn.execute("PRAGMA table_info(beliefs)")}
                for col in self._AFFINITY_COLS:
                    self.assertIn(col, cols)
                    self.assertEqual(cols[col][3], 0, f"{col} should be nullable")
                # The affinity_loop SELECT must not raise 'no such column' now.
                conn.execute(
                    "SELECT id, affinity, affinity_updated_at, affinity_model, "
                    "affinity_legacy FROM beliefs "
                    "WHERE affinity IS NULL OR affinity_updated_at < ?", (0,)
                ).fetchall()
            finally:
                conn.close()

    def test_affinity_loop_real_queries_run_on_migrated_db(self):
        """Generalise the drift fix: build a beliefs DB via the real migration
        list and run affinity_loop's actual SELECT and UPDATE. A column that any
        schema/migration forgot surfaces here, not on the next fresh deploy."""
        from substrate.init_db import _MIGRATIONS
        from theory_x.life import affinity_loop
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(str(Path(tmp) / "beliefs.db"))
            try:
                conn.executescript((_SCHEMA / "beliefs.sql").read_text())
                for stmt in _MIGRATIONS["beliefs"]:
                    try:
                        conn.execute(stmt)
                    except Exception:
                        pass  # CREATE IF NOT EXISTS / duplicate ALTER — idempotent
                conn.commit()
                # The candidate SELECT reads every affinity-path column.
                affinity_loop._pick_candidates(conn, 5)          # must not raise
                # The write path's columns must exist too.
                conn.execute("UPDATE beliefs SET affinity=?, affinity_updated_at=? "
                             "WHERE id=?", (0.5, 0.0, -1))
            finally:
                conn.close()


class TestDynamicSchemaNoDupes(unittest.TestCase):
    def test_substrate_snapshots_single_definition(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(str(Path(tmp) / "dynamic.db"))
            try:
                conn.executescript((_SCHEMA / "dynamic.sql").read_text())
                n = conn.execute(
                    "SELECT COUNT(*) FROM sqlite_master "
                    "WHERE type='table' AND name='substrate_snapshots'"
                ).fetchone()[0]
                self.assertEqual(n, 1)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
