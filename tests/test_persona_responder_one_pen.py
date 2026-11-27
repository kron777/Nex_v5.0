"""PersonaResponder persistence is owned by the canonical per-database Writers."""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from tests import _bootstrap  # noqa: F401


class TestPersonaResponderOnePen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="nex5_persona_writer_")
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
        os.environ.pop("NEX5_SOCIAL_DEPTH", None)
        self.tmp.cleanup()

    def test_exchange_uses_shared_sense_and_conversations_handles(self):
        from theory_x.stage_tom import persona_responder as pr

        with patch.dict(os.environ, {"NEX5_SOCIAL_DEPTH": "1"}), \
             patch.object(pr, "_recent_thoughts", return_value=["NEX considered astronomy"]), \
             patch.object(pr, "_ask_persona", return_value="I wonder about astronomy?"), \
             patch.object(pr, "_check_reply", return_value=(False, "ok", "", 0.0)), \
             patch.object(
                 pr, "Writer",
                 side_effect=AssertionError("PersonaResponder opened a second Writer"),
             ):
            result = pr.one_exchange(
                dynamic_writer=self.writers["dynamic"],
                sense_writer=self.writers["sense"],
                conversations_writer=self.writers["conversations"],
                conversations_reader=self.readers["conversations"],
            )

        self.assertTrue(result["written"])
        event = self.readers["sense"].read_one(
            "SELECT stream, payload FROM sense_events "
            "WHERE stream='external.other_mind' ORDER BY id DESC LIMIT 1"
        )
        self.assertEqual(event["payload"], "I wonder about astronomy?")
        state = self.readers["conversations"].read_one(
            "SELECT focus, turn_count FROM interlocutor_state WHERE id=1"
        )
        self.assertEqual(state["turn_count"], 1)
        self.assertTrue(state["focus"])

    def test_discard_uses_shared_dynamic_writer(self):
        from theory_x.stage_tom import persona_responder as pr

        with patch.object(pr, "_recent_thoughts", return_value=["NEX considered systems"]), \
             patch.object(pr, "_ask_persona", return_value="An echoed response"), \
             patch.object(pr, "_check_reply", return_value=(True, "phrase_echo", "echo", 0.4)), \
             patch.object(
                 pr, "Writer",
                 side_effect=AssertionError("PersonaResponder opened a second Writer"),
             ):
            result = pr.one_exchange(
                dynamic_writer=self.writers["dynamic"],
                sense_writer=self.writers["sense"],
                conversations_writer=self.writers["conversations"],
                conversations_reader=self.readers["conversations"],
            )

        self.assertEqual(result["discarded"], "phrase_echo")
        row = self.readers["dynamic"].read_one(
            "SELECT reason, reply_excerpt FROM persona_rejects ORDER BY id DESC LIMIT 1"
        )
        self.assertEqual(row["reason"], "phrase_echo")
        self.assertEqual(row["reply_excerpt"], "An echoed response")

    def test_loop_passes_its_handles_to_each_exchange(self):
        from theory_x.stage_tom import persona_responder as pr

        loop = pr.PersonaResponderLoop(
            dynamic_writer=self.writers["dynamic"],
            sense_writer=self.writers["sense"],
            conversations_writer=self.writers["conversations"],
            conversations_reader=self.readers["conversations"],
        )
        with patch.object(pr, "one_exchange", return_value={"error": "fixture"}) as exchange:
            loop.tick()
        exchange.assert_called_once_with(
            dynamic_writer=self.writers["dynamic"],
            sense_writer=self.writers["sense"],
            conversations_writer=self.writers["conversations"],
            conversations_reader=self.readers["conversations"],
        )


if __name__ == "__main__":
    unittest.main()
