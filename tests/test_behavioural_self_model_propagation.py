"""Characterize the recurrent BehaviouralSelfModel -> belief -> INSIDE prompt wire.

This is an isolated substrate test. It measures whether one controlled change
in recent NEX output propagates through the existing write/retrieval path.
It does not assert that the resulting feedback is desirable or enable a flag.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401


class TestBehaviouralSelfModelPropagation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nex5_bsm_wire_")
        os.environ["NEX5_DATA_DIR"] = self.tmp
        os.environ["NEX5_ADMIN_HASH_FILE"] = str(Path(self.tmp) / "admin.argon2")

        from substrate.init_db import init_all
        init_all()
        from substrate import Reader, Writer, db_paths

        paths = db_paths()
        self.writers = {name: Writer(path, name=name) for name, path in paths.items()}
        self.readers = {name: Reader(path) for name, path in paths.items()}

    def tearDown(self):
        for writer in getattr(self, "writers", {}).values():
            try:
                writer.close()
            except Exception:
                pass
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.pop("NEX5_DATA_DIR", None)
        os.environ.pop("NEX5_ADMIN_HASH_FILE", None)

    def test_observed_output_can_reenter_future_inside_prompt(self):
        from theory_x.stage3_world_model.retrieval import BeliefRetriever
        from theory_x.stage4_membrane.behavioural_self_model import BehaviouralSelfModel
        from theory_x.stage4_membrane.router import QueryRouter
        from theory_x.stage4_membrane.self_model import SelfModel

        now = int(time.time())
        session_id = "bsm-wire-characterization"
        self.writers["conversations"].write(
            "INSERT INTO sessions (id, started_at) VALUES (?, ?)",
            (session_id, now),
        )
        for index in range(10):
            self.writers["conversations"].write(
                "INSERT INTO messages "
                "(session_id, role, content, register, timestamp) "
                "VALUES (?, 'nex', ?, 'Philosophical', ?)",
                (session_id, f"Perhaps I might be uncertain about this point ({index}).",
                 now + index),
            )

        behavioural = BehaviouralSelfModel(self.readers["conversations"])
        metrics = behavioural.observe()
        self.assertEqual(metrics["sample_size"], 10)
        self.assertEqual(metrics["hedge_rate"], 1.0)
        self.assertEqual(metrics["belief_usage_rate"], 0.0)

        retriever = BeliefRetriever(self.readers["beliefs"])
        self_model = SelfModel(
            sense_reader=self.readers["sense"],
            beliefs_reader=self.readers["beliefs"],
        )
        router = QueryRouter()
        query = "what do you think about your hedge rate?"

        before = router.route(query, retriever, self_model)
        self.assertEqual(before["side"], "INSIDE")
        self.assertNotIn("seeded directness", before["belief_text"] or "")

        written = behavioural.write_behavioural_beliefs(
            self.writers["beliefs"], self.readers["beliefs"]
        )
        self.assertGreaterEqual(written, 1)

        persisted = self.readers["beliefs"].read(
            "SELECT id, content, tier, confidence, source FROM beliefs "
            "WHERE source = 'behavioural_observation' ORDER BY id"
        )
        self.assertTrue(persisted)
        self.assertTrue(all(row["tier"] == 6 for row in persisted))
        self.assertTrue(all(row["source"] == "behavioural_observation" for row in persisted))

        # The membrane must classify the newly persisted source as INSIDE.
        from theory_x.stage4_membrane.classifier import CLASSIFIER, MembraneSide
        self.assertEqual(
            CLASSIFIER.classify_belief(dict(persisted[0])),
            MembraneSide.INSIDE,
        )

        after = router.route(query, retriever, self_model)
        self.assertEqual(after["side"], "INSIDE")
        self.assertIn("seeded directness", after["belief_text"] or "")

        # Counterfactual subtraction: removing only the generated beliefs must
        # remove their contribution from the next assembled self-inquiry text.
        self.writers["beliefs"].write(
            "DELETE FROM beliefs WHERE source = 'behavioural_observation'"
        )
        without_feedback = router.route(query, retriever, self_model)
        self.assertNotIn("seeded directness", without_feedback["belief_text"] or "")


if __name__ == "__main__":
    unittest.main()
