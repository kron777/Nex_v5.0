"""Koan beta belief tests.

Covers:
- All 19 koans seeded to beliefs.db at init
- source='koan', tier=1, locked=1 for all
- seed_koans() is idempotent (running twice yields 19 beliefs, not 38)
- koan_reads table exists after init
- _select_koan() returns a koan when koans are present
- _select_koan() returns None when no koans present
- Round-robin: koan not re-selected until others have been read
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_koan_")
    os.environ["NEX5_DATA_DIR"] = tmp
    os.environ["NEX5_ADMIN_HASH_FILE"] = str(Path(tmp) / "admin.argon2")
    from substrate.init_db import init_all
    init_all()
    from substrate import Reader, Writer, db_paths
    paths = db_paths()
    writers = {n: Writer(p, name=n) for n, p in paths.items()}
    readers = {n: Reader(p) for n, p in paths.items()}
    return writers, readers, tmp


def _cleanup(writers, tmp):
    for w in writers.values():
        try:
            w.close()
        except Exception:
            pass
    shutil.rmtree(tmp, ignore_errors=True)


class TestKoanSeeds(unittest.TestCase):

    def test_all_59_beliefs_seeded(self):
        writers, readers, tmp = _make_env()
        try:
            rows = readers["beliefs"].read(
                "SELECT COUNT(*) as cnt FROM beliefs WHERE source IN ('koan', 'tao')"
            )
            self.assertEqual(rows[0]["cnt"], 59)
        finally:
            _cleanup(writers, tmp)

    def test_koan_count(self):
        writers, readers, tmp = _make_env()
        try:
            rows = readers["beliefs"].read(
                "SELECT COUNT(*) as cnt FROM beliefs WHERE source = 'koan'"
            )
            self.assertEqual(rows[0]["cnt"], 39)
        finally:
            _cleanup(writers, tmp)

    def test_tao_count(self):
        writers, readers, tmp = _make_env()
        try:
            rows = readers["beliefs"].read(
                "SELECT COUNT(*) as cnt FROM beliefs WHERE source = 'tao'"
            )
            self.assertEqual(rows[0]["cnt"], 20)
        finally:
            _cleanup(writers, tmp)

    def test_all_tier1_locked(self):
        writers, readers, tmp = _make_env()
        try:
            rows = readers["beliefs"].read(
                "SELECT COUNT(*) as cnt FROM beliefs "
                "WHERE source IN ('koan', 'tao') AND tier = 1 AND locked = 1"
            )
            self.assertEqual(rows[0]["cnt"], 59)
        finally:
            _cleanup(writers, tmp)

    def test_seed_idempotent(self):
        writers, readers, tmp = _make_env()
        try:
            from substrate.koan_seeds import seed_koans
            seed_koans(writers["beliefs"])  # second call
            rows = readers["beliefs"].read(
                "SELECT COUNT(*) as cnt FROM beliefs WHERE source IN ('koan', 'tao')"
            )
            self.assertEqual(rows[0]["cnt"], 59)
        finally:
            _cleanup(writers, tmp)

    def test_koan_reads_table_exists(self):
        writers, readers, tmp = _make_env()
        try:
            rows = readers["beliefs"].read("SELECT COUNT(*) as cnt FROM koan_reads")
            self.assertEqual(rows[0]["cnt"], 0)
        finally:
            _cleanup(writers, tmp)

    def test_all_koans_have_content(self):
        writers, readers, tmp = _make_env()
        try:
            rows = readers["beliefs"].read(
                "SELECT content FROM beliefs WHERE source = 'koan'"
            )
            for row in rows:
                self.assertTrue(len(row["content"]) > 10)
        finally:
            _cleanup(writers, tmp)


class TestSelectKoan(unittest.TestCase):

    def _make_generator(self, writers, readers):
        from unittest.mock import MagicMock
        from theory_x.stage6_fountain.generator import FountainGenerator
        return FountainGenerator(
            sense_writer=writers["sense"],
            dynamic_writer=writers["dynamic"],
            voice_client=MagicMock(),
            dynamic_reader=readers["dynamic"],
            beliefs_writer=writers["beliefs"],
        )

    def test_select_koan_returns_one(self):
        writers, readers, tmp = _make_env()
        try:
            gen = self._make_generator(writers, readers)
            koan = gen._select_koan(readers["beliefs"])
            self.assertIsNotNone(koan)
            self.assertIn("id", koan)
            self.assertIn("content", koan)
            self.assertTrue(len(koan["content"]) > 10)
        finally:
            _cleanup(writers, tmp)

    def test_select_koan_returns_none_when_empty(self):
        writers, readers, tmp = _make_env()
        try:
            # Remove all koan beliefs
            writers["beliefs"].write(
                "DELETE FROM beliefs WHERE source = 'koan'", ()
            )
            gen = self._make_generator(writers, readers)
            koan = gen._select_koan(readers["beliefs"])
            self.assertIsNone(koan)
        finally:
            _cleanup(writers, tmp)

    def test_round_robin_avoids_recently_read(self):
        writers, readers, tmp = _make_env()
        try:
            gen = self._make_generator(writers, readers)

            # Read the first koan
            first = gen._select_koan(readers["beliefs"])
            self.assertIsNotNone(first)

            # Record it as read
            writers["beliefs"].write(
                "INSERT INTO koan_reads (gate_id, read_at) VALUES (?, ?)",
                (str(first["id"]), time.time()),
            )

            # Next selection should differ (18 unread remain)
            second = gen._select_koan(readers["beliefs"])
            self.assertIsNotNone(second)
            self.assertNotEqual(first["id"], second["id"])
        finally:
            _cleanup(writers, tmp)

    def test_least_recently_read_selected(self):
        writers, readers, tmp = _make_env()
        try:
            gen = self._make_generator(writers, readers)

            # Mark all but one koan as recently read
            all_koans = readers["beliefs"].read(
                "SELECT id FROM beliefs WHERE source = 'koan' ORDER BY id"
            )
            now = time.time()
            oldest_id = all_koans[0]["id"]
            for row in all_koans[1:]:
                writers["beliefs"].write(
                    "INSERT INTO koan_reads (gate_id, read_at) VALUES (?, ?)",
                    (str(row["id"]), now),
                )

            selected = gen._select_koan(readers["beliefs"])
            self.assertIsNotNone(selected)
            self.assertEqual(selected["id"], oldest_id)
        finally:
            _cleanup(writers, tmp)


if __name__ == "__main__":
    unittest.main()
