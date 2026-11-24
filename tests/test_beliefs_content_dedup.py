"""Regression coverage for the beliefs.content partial unique indexes.

The migration deliberately permits the same content for different problem IDs,
while preventing duplicates within one problem and among orphan beliefs.
Exercise the production migration statements, not a copied approximation.
"""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

from substrate.init_db import _MIGRATIONS


_SCHEMA = (Path(__file__).resolve().parent.parent /
           "substrate" / "schema" / "beliefs.sql")


class TestBeliefsContentDedup(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = sqlite3.connect(str(Path(self.tmp.name) / "beliefs.db"))
        self.conn.executescript(_SCHEMA.read_text())

        # Apply only the production migration statements required by these
        # indexes. The problem_id column is introduced by this same migration.
        relevant = [
            stmt for stmt in _MIGRATIONS["beliefs"]
            if stmt.startswith("ALTER TABLE beliefs ADD COLUMN problem_id ")
            or "idx_beliefs_content_problem_uniq" in stmt
            or "idx_beliefs_content_orphan_uniq" in stmt
        ]
        self.assertEqual(len(relevant), 3)
        for stmt in relevant:
            self.conn.execute(stmt)

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def _insert(self, content, problem_id):
        self.conn.execute(
            "INSERT INTO beliefs (content, tier, confidence, created_at, problem_id) "
            "VALUES (?, 2, 0.5, 1, ?)",
            (content, problem_id),
        )

    def test_partial_unique_indexes_reject_duplicates_and_allow_distinct_problems(self):
        indexes = {row[1] for row in self.conn.execute("PRAGMA index_list(beliefs)")}
        self.assertIn("idx_beliefs_content_problem_uniq", indexes)
        self.assertIn("idx_beliefs_content_orphan_uniq", indexes)

        # Same content within one problem is a duplicate.
        self._insert("same problem content", 10)
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert("same problem content", 10)

        # Similar content belonging to different problems is permitted.
        self._insert("same problem content", 11)

        # Orphan beliefs (problem_id IS NULL) are unique by content too.
        self._insert("orphan content", None)
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert("orphan content", None)

        # The orphan and problem-scoped partial indexes are independent.
        self._insert("orphan content", 12)
        self.conn.commit()


if __name__ == "__main__":
    unittest.main()
