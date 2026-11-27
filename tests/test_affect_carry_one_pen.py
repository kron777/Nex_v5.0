"""Affect-carry uses the Chat-owned conversations Writer and Reader."""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from tests import _bootstrap  # noqa: F401


class TestAffectCarryOnePen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="nex5_affect_carry_")
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
        os.environ.pop("NEX5_AFFECT_CARRY", None)
        os.environ.pop("NEX5_AFFECT_CARRY_OPENBEAT", None)
        self.tmp.cleanup()

    def test_stance_uses_shared_writer_and_reader(self):
        from theory_x.stage_affect import affect_carry as ac

        with patch.dict(os.environ, {
            "NEX5_AFFECT_CARRY": "1",
            "NEX5_AFFECT_CARRY_OPENBEAT": "0",
        }), patch.object(ac, "_this_turn_weight", return_value=0.7), \
             patch("substrate.Writer", side_effect=AssertionError(
                 "affect_carry opened a second conversations Writer"
             )):
            stance = ac.stance_for(
                "session-one", "hard news",
                conversations_writer=self.writers["conversations"],
                conversations_reader=self.readers["conversations"],
            )

        self.assertIn("Carried tone", stance)
        row = self.readers["conversations"].read_one(
            "SELECT weight FROM affect_carry WHERE session_id=?", ("session-one",)
        )
        self.assertAlmostEqual(row["weight"], 0.7)

    def test_openbeat_state_uses_same_shared_writer(self):
        from theory_x.stage_affect import affect_carry as ac

        with patch.dict(os.environ, {
            "NEX5_AFFECT_CARRY": "1",
            "NEX5_AFFECT_CARRY_OPENBEAT": "1",
        }), patch.object(ac, "_this_turn_weight", return_value=0.7), \
             patch("substrate.Writer", side_effect=AssertionError(
                 "affect_carry openbeat opened a second conversations Writer"
             )):
            stance = ac.stance_for(
                "session-two", "hard news",
                conversations_writer=self.writers["conversations"],
                conversations_reader=self.readers["conversations"],
            )

        self.assertIn("Carried tone", stance)
        row = self.readers["conversations"].read_one(
            "SELECT last_turn_was_spike FROM affect_carry_openbeat WHERE session_id=?",
            ("session-two",),
        )
        self.assertEqual(row["last_turn_was_spike"], 1)


if __name__ == "__main__":
    unittest.main()
