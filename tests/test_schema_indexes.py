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


class TestAffinityProvenanceColumns(unittest.TestCase):
    """D-A: affinity_model/affinity_legacy are registered, additive, nullable."""

    def test_columns_registered_in_migrations(self):
        from substrate.init_db import _MIGRATIONS
        beliefs = " ".join(_MIGRATIONS["beliefs"])
        self.assertIn("ADD COLUMN affinity_model", beliefs)
        self.assertIn("ADD COLUMN affinity_legacy", beliefs)

    def test_columns_are_nullable_adds(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(str(Path(tmp) / "beliefs.db"))
            try:
                conn.executescript((_SCHEMA / "beliefs.sql").read_text())
                conn.execute("ALTER TABLE beliefs ADD COLUMN affinity_model TEXT")
                conn.execute("ALTER TABLE beliefs ADD COLUMN affinity_legacy REAL")
                cols = {r[1]: r for r in conn.execute("PRAGMA table_info(beliefs)")}
                self.assertIn("affinity_model", cols)
                self.assertIn("affinity_legacy", cols)
                # notnull flag (index 3) must be 0 — nullable, no default needed.
                self.assertEqual(cols["affinity_model"][3], 0)
                self.assertEqual(cols["affinity_legacy"][3], 0)
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
