"""SelfPredictionLoop reuses the AppState database handles for every write path."""
from __future__ import annotations

import os
import sqlite3
import tempfile
import time
import unittest
from unittest import mock

from tests import _bootstrap  # noqa: F401

from substrate import Reader, Writer
from theory_x.stage_world import self_prediction as SP


class TestSelfPredictionOnePen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="nex5_selfpred_one_pen_")
        self.conv = os.path.join(self.tmp.name, "conversations.db")
        self.beliefs = os.path.join(self.tmp.name, "beliefs.db")
        self.dynamic = os.path.join(self.tmp.name, "dynamic.db")
        cx = sqlite3.connect(self.beliefs)
        cx.execute(
            "CREATE TABLE beliefs (id INTEGER PRIMARY KEY, created_at INTEGER, source TEXT)"
        )
        cx.commit()
        cx.close()
        self.conv_writer = Writer(self.conv, name="test_conversations")
        self.beliefs_writer = Writer(self.beliefs, name="test_beliefs")
        self.conv_reader = Reader(self.conv)
        self.beliefs_reader = Reader(self.beliefs)
        self.dynamic_reader = Reader(self.dynamic)

    def tearDown(self):
        self.conv_writer.close()
        self.beliefs_writer.close()
        self.tmp.cleanup()

    def test_fire_prediction_uses_injected_conversations_writer(self):
        with mock.patch.object(SP, "_read_status", return_value={
            "readiness_score": 0.8, "total_fires": 12,
        }), mock.patch.object(SP, "snapshot_stakes", return_value=(0.0, 0, 0.2)), \
             mock.patch.object(SP, "Writer", side_effect=AssertionError(
                 "self_prediction opened a second conversations Writer"
             )):
            out = SP.make_self_prediction(
                db_path=self.conv,
                conversations_writer=self.conv_writer,
            )

        self.assertEqual(out["self_pred"], "fire")
        self.assertEqual(self.conv_reader.read_one(
            "SELECT COUNT(*) FROM self_predictions"
        )[0], 2)

    def test_authored_prediction_uses_injected_writer_and_beliefs_reader(self):
        cx = sqlite3.connect(self.beliefs)
        cx.execute(
            "INSERT INTO beliefs (created_at, source) VALUES (?, ?)",
            (int(time.time() - 60), "fountain_insight"),
        )
        cx.commit()
        cx.close()
        with mock.patch.object(SP, "snapshot_stakes", return_value=(0.0, 0, 0.2)), \
             mock.patch.object(SP, "Writer", side_effect=AssertionError(
                 "self_prediction opened a second conversations Writer"
             )):
            out = SP.make_authored_prediction(
                db_path=self.conv,
                beliefs_db=self.beliefs,
                conversations_writer=self.conv_writer,
                beliefs_reader=self.beliefs_reader,
            )

        self.assertEqual(out["prior_count"], 1)
        self.assertEqual(self.conv_reader.read_one(
            "SELECT COUNT(*) FROM self_predictions WHERE kind='authored_30m'"
        )[0], 2)

    def test_loop_passes_appstate_handles_to_all_nested_writers(self):
        from theory_x.stage_world import commitments, expectations, owned_belief

        loop = SP.SelfPredictionLoop(
            conversations_writer=self.conv_writer,
            beliefs_writer=self.beliefs_writer,
            conversations_reader=self.conv_reader,
            dynamic_reader=self.dynamic_reader,
            beliefs_reader=self.beliefs_reader,
        )
        with mock.patch.object(SP, "resolve_due") as resolve_due, \
             mock.patch.object(SP, "adapt_threshold"), \
             mock.patch.object(SP, "make_self_prediction", return_value={"error": "fixture"}), \
             mock.patch.object(SP, "resolve_authored") as resolve_authored, \
             mock.patch.object(SP, "make_authored_prediction") as make_authored, \
             mock.patch.object(SP, "resolve_selfdesc") as resolve_selfdesc, \
             mock.patch.object(SP, "make_selfdesc_prediction") as make_selfdesc, \
             mock.patch.object(owned_belief, "enabled", return_value=True), \
             mock.patch.object(owned_belief, "due", return_value=True) as owned_due, \
             mock.patch.object(owned_belief, "make_owned_belief_expectation") as owned_make, \
             mock.patch.object(commitments, "enabled", return_value=True), \
             mock.patch.object(commitments, "scan") as commitments_scan, \
             mock.patch.object(expectations, "reconciler_on", return_value=True), \
             mock.patch.object(expectations, "reconcile") as reconcile:
            loop.tick()

        resolve_due.assert_called_once_with(
            conversations_writer=self.conv_writer, dynamic_reader=self.dynamic_reader
        )
        resolve_authored.assert_called_once_with(
            conversations_writer=self.conv_writer, beliefs_reader=self.beliefs_reader
        )
        make_authored.assert_called_once_with(
            conversations_writer=self.conv_writer, beliefs_reader=self.beliefs_reader
        )
        resolve_selfdesc.assert_called_once_with(
            conversations_writer=self.conv_writer, dynamic_reader=self.dynamic_reader
        )
        make_selfdesc.assert_called_once_with(
            conversations_writer=self.conv_writer, dynamic_reader=self.dynamic_reader
        )
        owned_due.assert_called_once_with(
            conversations_writer=self.conv_writer, conversations_reader=self.conv_reader
        )
        owned_make.assert_called_once_with(
            conversations_writer=self.conv_writer,
            conversations_reader=self.conv_reader,
            beliefs_reader=self.beliefs_reader,
        )
        commitments_scan.assert_called_once_with(
            conversations_writer=self.conv_writer, dynamic_reader=self.dynamic_reader
        )
        reconcile.assert_called_once_with(
            conversations_writer=self.conv_writer, beliefs_writer=self.beliefs_writer
        )


if __name__ == "__main__":
    unittest.main()
