"""Affinity maintenance and identity snapshots must ignore inactive beliefs."""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest


class TestAffinityEligibility(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nex5_affinity_")
        os.environ["NEX5_DATA_DIR"] = self.tmp
        os.environ["NEX5_AFFINITY_PROVENANCE"] = "on"
        from substrate.init_db import init_all
        init_all()
        from substrate import Writer, db_paths
        self.path = db_paths()["beliefs"]
        self.writer = Writer(self.path, name="beliefs")

    def tearDown(self):
        self.writer.close()
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.pop("NEX5_DATA_DIR", None)
        os.environ.pop("NEX5_AFFINITY_PROVENANCE", None)

    def _insert(self, content, *, tier=5, paused=0, erosion_stage="external", affinity=None):
        return self.writer.write(
            "INSERT INTO beliefs "
            "(content, tier, confidence, created_at, source, paused, erosion_stage, affinity) "
            "VALUES (?, ?, 0.8, ?, 'fountain_insight', ?, ?, ?)",
            (content, tier, int(time.time()), paused, erosion_stage, affinity),
        )

    def test_affinity_scoring_excludes_paused_retired_and_tier_eight(self):
        from substrate import connect
        from theory_x.life.affinity_loop import affinity_tick

        active = self._insert("active affinity candidate")
        paused = self._insert("paused affinity candidate", paused=1)
        retired = self._insert("retired marker affinity candidate", erosion_stage="retired")
        tombstone = self._insert("tier eight affinity candidate", tier=8)

        result = affinity_tick(voice=None)
        self.assertEqual(result["candidates"], 1)
        self.assertEqual(result["scored"], 1)

        cx = connect(str(self.path), timeout=5)
        try:
            rows = cx.execute(
                "SELECT id, affinity FROM beliefs WHERE id IN (?, ?, ?, ?)",
                (active, paused, retired, tombstone),
            ).fetchall()
            values = {row[0]: row[1] for row in rows}
        finally:
            cx.close()

        self.assertIsNotNone(values[active])
        self.assertIsNone(values[paused])
        self.assertIsNone(values[retired])
        self.assertIsNone(values[tombstone])

    def test_identity_top_affinity_ignores_inactive_rows(self):
        from theory_x.life.identity_loop import _gather_metrics

        active = self._insert("active affinity snapshot", affinity=0.4)
        self._insert("paused high-affinity snapshot", paused=1, affinity=0.99)
        self._insert("retired high-affinity snapshot", erosion_stage="retired", affinity=0.98)
        self._insert("tier eight high-affinity snapshot", tier=8, affinity=0.97)

        metrics = _gather_metrics(time.time())
        self.assertEqual(metrics["top_affinity"], "active affinity snapshot")


if __name__ == "__main__":
    unittest.main()
