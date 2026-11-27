"""Regression tests for scheduled belief writers sharing canonical handles."""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_one_pen_belief_writers_")
    os.environ["NEX5_DATA_DIR"] = tmp
    os.environ["NEX5_ADMIN_HASH_FILE"] = str(Path(tmp) / "admin.argon2")
    from substrate.init_db import init_all
    init_all()
    from substrate import Reader, Writer, db_paths
    paths = db_paths()
    writers = {name: Writer(path, name=name) for name, path in paths.items()}
    readers = {name: Reader(path) for name, path in paths.items()}
    return writers, readers, tmp


def _cleanup(writers, tmp):
    for writer in writers.values():
        try:
            writer.close()
        except Exception:
            pass
    shutil.rmtree(tmp, ignore_errors=True)
    os.environ.pop("NEX5_DATA_DIR", None)
    os.environ.pop("NEX5_ADMIN_HASH_FILE", None)


class TestHotObserverWriter(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        from theory_x.stage_tom import hot_observer
        self.hot_observer = hot_observer
        self.hot_observer._state["counter"] = 2

    def tearDown(self):
        self.hot_observer._state["counter"] = 0
        _cleanup(self.writers, self.tmp)

    def test_runtime_observation_uses_shared_writer_and_keeps_it_open(self):
        thought = (
            "Bitcoin lending markets are changing as institutions adopt crypto "
            "collateral and new regulatory standards across global financial "
            "systems today."
        )
        with patch.object(self.hot_observer, "Writer") as writer_factory:
            written = self.hot_observer.observe(
                thought,
                "systems",
                beliefs_writer=self.writers["beliefs"],
            )
        self.assertTrue(written)
        writer_factory.assert_not_called()

        rows = self.readers["beliefs"].read(
            "SELECT id, source, tier, branch_id FROM beliefs "
            "WHERE source='hot_observer' ORDER BY id DESC LIMIT 1"
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source"], "hot_observer")
        self.assertEqual(rows[0]["tier"], 3)
        self.assertEqual(rows[0]["branch_id"], "systems")

        # An injected Writer remains owned by AppState and is not closed here.
        self.writers["beliefs"].write(
            "UPDATE beliefs SET confidence = confidence WHERE id = ?",
            (rows[0]["id"],),
        )

    def test_standalone_path_owns_and_closes_its_writer(self):
        thought = (
            "Bitcoin lending markets are changing as institutions adopt crypto "
            "collateral and new regulatory standards across global financial "
            "systems today."
        )
        owned = Mock()
        with patch.object(self.hot_observer, "Writer", return_value=owned) as factory:
            written = self.hot_observer.observe(thought, "systems", "/tmp/beliefs.db")
        self.assertTrue(written)
        factory.assert_called_once_with("/tmp/beliefs.db", name="hot_observer")
        owned.write.assert_called_once()
        owned.close.assert_called_once()


class TestGroundSelfBeliefWriter(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        import ground_self_belief
        self.gsb = ground_self_belief

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_refresh_updates_existing_identity_through_injected_writer(self):
        source = self.gsb.SELF_BELIEF_SOURCE
        self.writers["beliefs"].write(
            "INSERT INTO beliefs (content, tier, confidence, created_at, "
            "source, branch_id, locked) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("old scorecard statement", 1, 0.99, int(time.time()), source, "systems", 1),
        )
        before = self.readers["beliefs"].read_one(
            "SELECT id FROM beliefs WHERE source = ? AND tier = 1 AND locked = 1",
            (source,),
        )
        self.assertIsNotNone(before)

        with patch.object(self.gsb, "_get_writer", side_effect=AssertionError("opened second Writer")):
            self.gsb._write_self_belief(
                "refreshed scorecard statement",
                beliefs_writer=self.writers["beliefs"],
                beliefs_reader=self.readers["beliefs"],
            )

        after = self.readers["beliefs"].read_one(
            "SELECT id, content FROM beliefs WHERE source = ? AND tier = 1 AND locked = 1",
            (source,),
        )
        self.assertEqual(after["id"], before["id"])
        self.assertEqual(after["content"], "refreshed scorecard statement")

        # The scheduled loop does not close the canonical Writer.
        self.writers["beliefs"].write(
            "UPDATE beliefs SET confidence = confidence WHERE id = ?",
            (after["id"],),
        )

    def test_refresh_inserts_when_no_existing_row_through_injected_writer(self):
        with patch.object(self.gsb, "_get_writer", side_effect=AssertionError("opened second Writer")):
            self.gsb._write_self_belief(
                "first scorecard statement",
                beliefs_writer=self.writers["beliefs"],
                beliefs_reader=self.readers["beliefs"],
            )
        row = self.readers["beliefs"].read_one(
            "SELECT content, source, tier, locked FROM beliefs WHERE source = ?",
            (self.gsb.SELF_BELIEF_SOURCE,),
        )
        self.assertIsNotNone(row)
        self.assertEqual(row["content"], "first scorecard statement")
        self.assertEqual(row["tier"], 1)
        self.assertEqual(row["locked"], 1)

    def test_scorecard_loop_passes_appstate_handles(self):
        from theory_x.life import scorecard_loop
        state = SimpleNamespace(
            writers=self.writers,
            readers=self.readers,
        )
        expected = {"voice": {"correct": 1, "resolved": 2}, "random": {"correct": 1, "resolved": 2}}
        with patch.object(self.gsb, "refresh_self_belief", return_value=expected) as refresh:
            scorecard_loop._tick(state)
        refresh.assert_called_once_with(
            beliefs_writer=self.writers["beliefs"],
            beliefs_reader=self.readers["beliefs"],
        )


if __name__ == "__main__":
    unittest.main()
