"""Commitments scans and releases use the canonical conversations Writer."""
from __future__ import annotations

import os
import tempfile
import time
import unittest
from unittest.mock import patch

from tests import _bootstrap  # noqa: F401


class TestCommitmentsOnePen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="nex5_commitments_writer_")
        os.environ["NEX5_DATA_DIR"] = self.tmp.name
        from substrate.init_db import init_all
        init_all()
        from substrate import Reader, Writer, db_paths
        paths = db_paths()
        self.writers = {name: Writer(path, name=name) for name, path in paths.items()}
        self.readers = {name: Reader(path) for name, path in paths.items()}

    def tearDown(self):
        for writer in self.writers.values():
            writer.close()
        os.environ.pop("NEX5_DATA_DIR", None)
        self.tmp.cleanup()

    def test_scan_uses_injected_conversations_writer_and_dynamic_reader(self):
        from theory_x.stage_world import commitments as C

        self.writers["dynamic"].write(
            "INSERT INTO fountain_events (ts, thought, readiness, hot_branch, word_count) "
            "VALUES (?, ?, ?, ?, ?)",
            (time.time(), "I will investigate the astronomy engine tomorrow", 0.8,
             "systems", 8),
        )
        with patch.object(
            C, "Writer",
            side_effect=AssertionError("commitments scan opened a second Writer"),
        ):
            stats = C.scan(
                conversations_writer=self.writers["conversations"],
                dynamic_reader=self.readers["dynamic"],
            )

        self.assertGreater(stats["commitments"] + stats["intentions"], 0)
        row = self.readers["conversations"].read_one(
            "SELECT id, released_by FROM commitments ORDER BY id DESC LIMIT 1"
        )
        self.assertIsNotNone(row)
        self.assertIsNone(row["released_by"])

        with patch.object(
            C, "Writer",
            side_effect=AssertionError("commitment release opened a second Writer"),
        ):
            C.record_release(
                row["id"], "self", time.time(), "test:release",
                conversations_writer=self.writers["conversations"],
            )
        released = self.readers["conversations"].read_one(
            "SELECT released_by, release_ref FROM commitments WHERE id=?",
            (row["id"],),
        )
        self.assertEqual(released["released_by"], "self")
        self.assertEqual(released["release_ref"], "test:release")


if __name__ == "__main__":
    unittest.main()
