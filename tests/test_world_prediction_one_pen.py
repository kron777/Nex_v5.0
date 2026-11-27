"""AppState handle propagation tests for the gated WorldPredictionLoop.

Nested paths must reuse the supplied handles rather than opening fallback connections.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import time
import unittest
from unittest import mock

from tests import _bootstrap  # noqa: F401

from substrate import Reader, Writer
from theory_x.stage_world import (
    calibration_consult,
    prediction_generator as pg,
    world_loop,
    world_predictions as wp,
)


class TestWorldPredictionOnePen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="nex5_world_one_pen_")
        self.conversations = os.path.join(self.tmp.name, "conversations.db")
        self.beliefs = os.path.join(self.tmp.name, "beliefs.db")
        with sqlite3.connect(self.beliefs) as db:
            db.execute(
                "CREATE TABLE beliefs (id INTEGER PRIMARY KEY, content TEXT, "
                "source TEXT, tier INTEGER, locked INTEGER)"
            )
            db.execute(
                "INSERT INTO beliefs (content, source, tier, locked) VALUES (?, ?, 1, 1)",
                ("Measured world-prediction record", calibration_consult.SELF_BELIEF_SOURCE),
            )
        self.writer = Writer(self.conversations, name="world_predictions_test")
        self.reader = Reader(self.conversations)
        self.beliefs_reader = Reader(self.beliefs)
        wp.ensure_schema(self.conversations, conversations_writer=self.writer)

    def tearDown(self):
        self.writer.close()
        self.tmp.cleanup()

    def test_prediction_insert_resolution_and_scorecard_use_shared_handles(self):
        with mock.patch.object(wp, "fetch_price", return_value=100.0), \
             mock.patch.object(wp, "frozen_values", return_value=(
                 None, "none_stated", 0.0, "strict_direction",
                 0.0, 0, 0.0, "[]", 1, 1.0, "at_made",
             )), \
             mock.patch.object(wp, "Writer", side_effect=AssertionError(
                 "world_predictions opened a second conversations Writer"
             )), \
             mock.patch.object(wp, "Reader", side_effect=AssertionError(
                 "world_predictions opened a second conversations Reader"
             )):
            prediction_id = wp.make_prediction(
                asset="bitcoin",
                direction="up",
                horizon_seconds=10,
                db_path=self.conversations,
                conversations_writer=self.writer,
            )
        self.assertIsInstance(prediction_id, int)

        with mock.patch.object(wp, "fetch_price", return_value=110.0), \
             mock.patch.object(wp, "Writer", side_effect=AssertionError(
                 "world_predictions opened a second conversations Writer"
             )), \
             mock.patch.object(wp, "Reader", side_effect=AssertionError(
                 "world_predictions opened a second conversations Reader"
             )):
            result = wp.resolve_due(
                now=time.time() + 11,
                db_path=self.conversations,
                conversations_writer=self.writer,
                conversations_reader=self.reader,
            )
        self.assertEqual(result, {"resolved": 1, "correct": 1})
        row = self.reader.read_one(
            "SELECT outcome FROM world_predictions WHERE id=?", (prediction_id,)
        )
        self.assertEqual(row["outcome"], "correct")

        with mock.patch.object(wp, "Writer", side_effect=AssertionError(
            "scorecard opened a second conversations Writer"
        )), mock.patch.object(wp, "Reader", side_effect=AssertionError(
            "scorecard opened a second conversations Reader"
        )):
            card = pg.scorecard_by_source(
                db_path=self.conversations,
                conversations_writer=self.writer,
                conversations_reader=self.reader,
            )
        self.assertEqual(card["manual"]["resolved"], 1)
        self.assertEqual(card["manual"]["correct"], 1)

    def test_calibration_consult_uses_shared_beliefs_reader_and_conversations_handles(self):
        with mock.patch.object(wp, "Writer", side_effect=AssertionError(
            "calibration scorecard opened a second conversations Writer"
        )), mock.patch.object(wp, "Reader", side_effect=AssertionError(
            "calibration scorecard opened a second conversations Reader"
        )), mock.patch("substrate.writer.Writer", side_effect=AssertionError(
            "calibration consult opened a second conversations Writer"
        )), mock.patch("substrate.reader.Reader", side_effect=AssertionError(
            "calibration consult opened a second beliefs Reader"
        )):
            verdict = calibration_consult.consult_self_trust(
                conversations_writer=self.writer,
                conversations_reader=self.reader,
                beliefs_reader=self.beliefs_reader,
            )
        self.assertEqual(verdict["level"], "provisional")
        row = self.reader.read_one(
            "SELECT level, n FROM calibration_consults ORDER BY id DESC LIMIT 1"
        )
        self.assertEqual(row["level"], "provisional")
        self.assertEqual(row["n"], 0)

    def test_prediction_generator_passes_shared_handles_to_nested_calls(self):
        trust = {"level": "provisional", "reason": "small sample", "n": 4, "gap": 0.1}
        with mock.patch.object(pg.wp, "fetch_price", return_value=100.0), \
             mock.patch.object(pg, "_ask_voice_direction", return_value="up"), \
             mock.patch.object(calibration_consult, "consult_self_trust", return_value=trust) as consult, \
             mock.patch.object(pg.wp, "make_prediction", side_effect=[11, 12]) as make, \
             mock.patch.object(pg.wp, "stamp_trust") as stamp:
            result = pg.make_voice_prediction(
                "bitcoin",
                3600,
                db_path=self.conversations,
                conversations_writer=self.writer,
                conversations_reader=self.reader,
                beliefs_reader=self.beliefs_reader,
            )

        self.assertEqual(result["voice_id"], 11)
        self.assertEqual(result["random_id"], 12)
        consult.assert_called_once_with(
            conversations_writer=self.writer,
            conversations_reader=self.reader,
            beliefs_reader=self.beliefs_reader,
        )
        self.assertEqual(make.call_count, 2)
        for call in make.call_args_list:
            self.assertIs(call.kwargs["conversations_writer"], self.writer)
        stamp.assert_called_once()
        self.assertIs(stamp.call_args.kwargs["conversations_writer"], self.writer)

    def test_world_loop_passes_shared_handles_to_resolver_and_generator(self):
        loop = world_loop.WorldPredictionLoop(
            conversations_writer=self.writer,
            conversations_reader=self.reader,
            beliefs_reader=self.beliefs_reader,
        )
        with mock.patch.object(wp, "resolve_due", return_value={"resolved": 0, "correct": 0}) as resolve, \
             mock.patch.object(pg, "make_voice_prediction", return_value={
                 "voice_dir": "up", "random_dir": "down", "baseline": 100.0,
             }) as make:
            loop.tick()

        resolve.assert_called_once_with(
            conversations_writer=self.writer,
            conversations_reader=self.reader,
        )
        make.assert_called_once_with(
            loop.asset,
            loop._horizon,
            conversations_writer=self.writer,
            conversations_reader=self.reader,
            beliefs_reader=self.beliefs_reader,
        )


if __name__ == "__main__":
    unittest.main()
