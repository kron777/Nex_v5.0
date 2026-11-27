"""WorldBridge selection logging uses AppState database handles."""
from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from unittest.mock import patch

from tests import _bootstrap  # noqa: F401


class TestWorldBridgeOnePen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="nex5_world_bridge_")
        os.environ["NEX5_DATA_DIR"] = self.tmp.name
        from substrate.init_db import init_all
        init_all()
        from substrate import Reader, Writer, db_paths
        paths = db_paths()
        self.paths = paths
        self.writers = {name: Writer(path, name=name) for name, path in paths.items()}
        self.readers = {name: Reader(path) for name, path in paths.items()}

    def tearDown(self):
        for writer in self.writers.values():
            writer.close()
        os.environ.pop("NEX5_DATA_DIR", None)
        self.tmp.cleanup()

    def test_selection_uses_shared_sense_reader_and_beliefs_writer(self):
        from theory_x.world_bridge import selector as wb

        now = time.time()
        payload = json.dumps({
            "title": "A new world event",
            "summary": "A substantive report about a new scientific observation.",
        })
        self.writers["sense"].write(
            "INSERT INTO sense_events (stream, payload, provenance, timestamp) "
            "VALUES (?, ?, ?, ?)",
            ("news.test", payload, "test://world-bridge", now - 5),
        )
        selector = wb.WorldBridgeSelector(
            sense_db_path=str(self.paths["sense"]),
            beliefs_db_path=str(self.paths["beliefs"]),
            sense_reader=self.readers["sense"],
            beliefs_writer=self.writers["beliefs"],
        )

        with patch.object(
            wb, "Reader",
            side_effect=AssertionError("WorldBridge opened a second sense Reader"),
        ), patch.object(
            wb, "Writer",
            side_effect=AssertionError("WorldBridge opened a second beliefs Writer"),
        ):
            selected = selector.select_and_log(fountain_event_id=7)

        self.assertIsNotNone(selected)
        self.assertEqual(len(selected), 1)
        self.assertIn("A new world event", selected[0]["formatted_text"])
        row = self.readers["beliefs"].read_one(
            "SELECT fountain_event_id, selection_count, injected, notes "
            "FROM world_bridge_log ORDER BY id DESC LIMIT 1"
        )
        self.assertEqual(row["fountain_event_id"], 7)
        self.assertEqual(row["selection_count"], 1)
        self.assertEqual(row["injected"], 0)
        self.assertEqual(row["notes"], "ok")


if __name__ == "__main__":
    unittest.main()
