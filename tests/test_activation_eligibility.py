"""Spreading activation must not traverse paused or retired belief nodes."""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest


class TestActivationEligibility(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nex5_activation_")
        os.environ["NEX5_DATA_DIR"] = self.tmp
        from substrate.init_db import init_all
        init_all()
        from substrate import Reader, Writer, db_paths
        paths = db_paths()
        self.writer = Writer(paths["beliefs"], name="beliefs")
        self.reader = Reader(paths["beliefs"])

    def tearDown(self):
        self.writer.close()
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.pop("NEX5_DATA_DIR", None)

    def _belief(self, content, *, tier=5, paused=0, erosion_stage="external"):
        return self.writer.write(
            "INSERT INTO beliefs (content, tier, confidence, created_at, paused, erosion_stage) "
            "VALUES (?, ?, 0.9, ?, ?, ?)",
            (content, tier, int(time.time()), paused, erosion_stage),
        )

    def _edge(self, source_id, target_id):
        self.writer.write(
            "INSERT INTO belief_edges (source_id, target_id, edge_type, weight, created_at) "
            "VALUES (?, ?, 'supports', 0.9, ?)",
            (source_id, target_id, time.time()),
        )

    def test_activation_does_not_traverse_paused_or_retired_nodes(self):
        from theory_x.stage3_world_model.activation import ActivationEngine

        seed = self._belief("Active seed belief")
        paused = self._belief("Paused intermediate belief", paused=1)
        retired = self._belief("Retired intermediate belief", erosion_stage="retired")
        tombstone = self._belief("Tier eight intermediate belief", tier=8)
        active_target = self._belief("Active downstream belief")

        self._edge(seed, paused)
        self._edge(paused, active_target)
        self._edge(seed, retired)
        self._edge(retired, active_target)
        self._edge(seed, tombstone)
        self._edge(tombstone, active_target)

        scores = ActivationEngine(self.reader).activate([seed], hops=3)

        self.assertEqual(set(scores), {seed})
        self.assertNotIn(paused, scores)
        self.assertNotIn(retired, scores)
        self.assertNotIn(tombstone, scores)
        self.assertNotIn(active_target, scores)


if __name__ == "__main__":
    unittest.main()
