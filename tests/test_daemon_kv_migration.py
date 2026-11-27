"""Regression coverage for the shared dynamic daemon_kv schema/migration."""

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests import _bootstrap  # noqa: F401

from substrate import connect


class TestDaemonKVMigration(unittest.TestCase):
    def _initialise(self, legacy: bool):
        from substrate.init_db import init_all
        from substrate.paths import db_paths

        tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.dict(os.environ, {"NEX5_DATA_DIR": tmp.name})
        patcher.start()
        try:
            db_path = db_paths()["dynamic"]
            if legacy:
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
                with sqlite3.connect(str(db_path)) as conn:
                    conn.execute(
                        "CREATE TABLE daemon_kv (key TEXT PRIMARY KEY, value TEXT)"
                    )
                    conn.execute(
                        "INSERT INTO daemon_kv (key, value) VALUES (?, ?)",
                        ("legacy-checkpoint", "preserve-me"),
                    )
            init_all()
            return tmp, patcher, str(db_path)
        except BaseException:
            patcher.stop()
            tmp.cleanup()
            raise

    def test_fresh_database_has_complete_daemon_kv_schema(self):
        tmp, patcher, db_path = self._initialise(legacy=False)
        try:
            conn = connect(db_path)
            try:
                columns = {
                    row[1] for row in conn.execute("PRAGMA table_info(daemon_kv)")
                }
                self.assertEqual(columns, {"key", "value", "updated_at"})
                conn.execute(
                    "INSERT INTO daemon_kv (key, value, updated_at) VALUES (?, ?, ?)",
                    ("fresh-checkpoint", "value", 123.0),
                )
                conn.commit()
            finally:
                conn.close()
        finally:
            patcher.stop()
            tmp.cleanup()

    def test_existing_daemon_kv_gets_updated_at_without_losing_rows(self):
        tmp, patcher, db_path = self._initialise(legacy=True)
        try:
            conn = connect(db_path)
            try:
                columns = {
                    row[1] for row in conn.execute("PRAGMA table_info(daemon_kv)")
                }
                self.assertEqual(columns, {"key", "value", "updated_at"})
                row = conn.execute(
                    "SELECT key, value, updated_at FROM daemon_kv "
                    "WHERE key = ?",
                    ("legacy-checkpoint",),
                ).fetchone()
                self.assertEqual(tuple(row), ("legacy-checkpoint", "preserve-me", None))
                conn.execute(
                    "UPDATE daemon_kv SET updated_at = ? WHERE key = ?",
                    (456.0, "legacy-checkpoint"),
                )
                conn.commit()
            finally:
                conn.close()
        finally:
            patcher.stop()
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
