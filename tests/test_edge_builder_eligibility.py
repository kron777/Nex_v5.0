"""Diversity edge construction must ignore inactive belief nodes."""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np


class TestDiversityEdgeBuilderEligibility(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nex5_edge_builder_")
        os.environ["NEX5_DATA_DIR"] = self.tmp
        from substrate.init_db import init_all
        init_all()
        from substrate import connect, db_paths
        self.path = db_paths()["beliefs"]
        self.cx = connect(self.path, timeout=5)
        # Isolate the test from init-time seed beliefs.
        self.cx.execute("UPDATE beliefs SET paused=1")

    def tearDown(self):
        self.cx.close()
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.pop("NEX5_DATA_DIR", None)

    def _insert(self, content, *, tier=5, paused=0, erosion_stage="external"):
        cur = self.cx.execute(
            "INSERT INTO beliefs (content, tier, confidence, created_at, source, "
            "paused, erosion_stage, locked) VALUES (?, ?, 0.8, ?, 'auto_growth', ?, ?, 0)",
            (content, tier, int(time.time()), paused, erosion_stage),
        )
        return cur.lastrowid

    def test_candidate_and_comparison_pools_exclude_paused_retired_and_tier_eight(self):
        active_a = self._insert("Active belief about attention and cognition")
        active_b = self._insert("Active belief about cognition and attention")
        paused = self._insert("Paused belief about attention and cognition", paused=1)
        retired = self._insert(
            "Retired marker belief about attention and cognition",
            erosion_stage="retired",
        )
        tombstone = self._insert("Tier eight belief about attention and cognition", tier=8)
        self.cx.commit()

        from theory_x.diversity.edge_builder import edge_builder_tick
        with patch(
            "theory_x.diversity.edge_builder.embed_belief",
            return_value=np.array([1.0, 0.0], dtype=np.float32),
        ):
            stats = edge_builder_tick(Path(self.path))

        self.assertEqual(stats["considered"], 2)
        edges = self.cx.execute(
            "SELECT source_id, target_id FROM belief_edges"
        ).fetchall()
        endpoints = {value for edge in edges for value in edge}
        self.assertTrue(endpoints.issubset({active_a, active_b}))
        self.assertNotIn(paused, endpoints)
        self.assertNotIn(retired, endpoints)
        self.assertNotIn(tombstone, endpoints)


if __name__ == "__main__":
    unittest.main()
