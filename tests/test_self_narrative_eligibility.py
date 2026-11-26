"""Living self-narrative must be grounded in active belief state."""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest


class TestSelfNarrativeEligibility(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nex5_self_narrative_")
        os.environ["NEX5_DATA_DIR"] = self.tmp
        from substrate.init_db import init_all
        init_all()
        from substrate import Writer, db_paths
        self.path = str(db_paths()["beliefs"])
        self.writer = Writer(self.path, name="beliefs")

    def tearDown(self):
        self.writer.close()
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.pop("NEX5_DATA_DIR", None)

    def _insert(self, content, source, *, tier=6, paused=0, erosion_stage="external", created_at=None):
        return self.writer.write(
            "INSERT INTO beliefs (content, tier, confidence, created_at, source, paused, erosion_stage) "
            "VALUES (?, ?, 0.8, ?, ?, ?, ?)",
            (content, tier, int(created_at or time.time()), source, paused, erosion_stage),
        )

    def test_recent_t6_and_hot_reads_exclude_paused_and_retired(self):
        from theory_x.stage_tom.self_narrative import _recent_t6, _recent_hot

        now = time.time()
        self.writer.write("UPDATE beliefs SET paused=1 WHERE tier=6 OR source='hot_observer'")
        self._insert("active deep belief", "fountain_insight", tier=6, created_at=now - 30)
        self._insert("paused deep belief", "fountain_insight", tier=6, paused=1, created_at=now - 20)
        self._insert("retired marker deep belief", "fountain_insight", tier=6, erosion_stage="retired", created_at=now - 10)

        self._insert("active hot observation", "hot_observer", tier=3, created_at=now - 30)
        self._insert("paused hot observation", "hot_observer", tier=3, paused=1, created_at=now - 20)
        self._insert("retired marker hot observation", "hot_observer", tier=3, erosion_stage="retired", created_at=now - 10)

        self.assertEqual(_recent_t6(self.path, n=1), ["active deep belief"])
        self.assertEqual(_recent_hot(self.path), "active hot observation")

    def test_self_model_aggregation_does_not_count_inactive_hot_observations(self):
        from theory_x.stage_tom.self_model_aggregator import aggregate_self_model

        now = time.time()
        self.writer.write("UPDATE beliefs SET paused=1 WHERE source='hot_observer'")
        for i in range(4):
            self._insert(
                f"engaged the world directly (branch: systems) active {i}",
                "hot_observer",
                tier=3,
                created_at=now - i,
            )
        self._insert(
            "engaged the world directly (branch: systems) retired",
            "hot_observer",
            tier=3,
            erosion_stage="retired",
            created_at=now - 5,
        )

        self.assertIsNone(aggregate_self_model(self.path, lookback_secs=3600))

        self._insert(
            "engaged the world directly (branch: systems) active fifth",
            "hot_observer",
            tier=3,
            created_at=now - 6,
        )
        self.assertIsNotNone(aggregate_self_model(self.path, lookback_secs=3600))


if __name__ == "__main__":
    unittest.main()
