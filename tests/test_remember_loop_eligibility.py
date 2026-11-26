"""RememberLoop must only pair active, non-retired beliefs."""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest


class TestRememberLoopEligibility(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nex5_remember_")
        os.environ["NEX5_DATA_DIR"] = self.tmp
        from substrate.init_db import init_all
        init_all()
        from substrate import Writer, db_paths
        paths = db_paths()
        self.path = paths["beliefs"]
        self.writer = Writer(self.path, name="beliefs")

    def tearDown(self):
        self.writer.close()
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.pop("NEX5_DATA_DIR", None)

    def _insert(self, content, created_at, *, tier=6, paused=0, erosion_stage="external"):
        return self.writer.write(
            "INSERT INTO beliefs (content, tier, confidence, created_at, source, paused, erosion_stage) "
            "VALUES (?, ?, 0.8, ?, 'auto_growth', ?, ?)",
            (content, tier, int(created_at), paused, erosion_stage),
        )

    def test_old_and_recent_pair_pools_exclude_inactive_and_retired_rows(self):
        from substrate import connect
        from theory_x.life.remember_loop import _pick_old_belief, _pick_recent_belief

        now = time.time()
        old_active = self._insert("eligible old belief", now - 10 * 86400)
        self._insert("paused old belief", now - 11 * 86400, paused=1)
        self._insert("retired old belief", now - 12 * 86400, erosion_stage="retired")
        self._insert("tier eight old belief", now - 13 * 86400, tier=8)

        recent_active = self._insert("eligible recent belief", now - 60)
        self._insert("paused recent belief", now - 120, paused=1)
        self._insert("retired recent belief", now - 180, erosion_stage="retired")
        self._insert("tier eight recent belief", now - 240, tier=8)

        cx = connect(str(self.path), timeout=5)
        try:
            self.assertEqual(_pick_old_belief(cx)["id"], old_active)
            self.assertEqual(_pick_recent_belief(cx)["id"], recent_active)
        finally:
            cx.close()


if __name__ == "__main__":
    unittest.main()
