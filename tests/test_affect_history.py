"""affect_history is actually created and a real tick appends to it.

Regression guard for a closed loop: affect_history had no CREATE TABLE anywhere,
so affect_state.py's INSERT was swallowed and CompetingDrives' affect_variance
(theory_x/stage_drives/competing_drives.py) read an empty table since 2026-05-20.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from tests._bootstrap import *  # noqa: F401, F403


class TestAffectHistoryLoop(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nex5_afh_")
        os.environ["NEX5_DATA_DIR"] = self.tmp
        from substrate.init_db import init_all
        init_all()

    def tearDown(self):
        os.environ.pop("NEX5_DATA_DIR", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _conv_conn(self):
        from substrate import db_paths
        return sqlite3.connect(str(db_paths()["conversations"]))

    def test_init_all_creates_affect_history(self):
        c = self._conv_conn()
        try:
            cols = [r[1] for r in c.execute("PRAGMA table_info(affect_history)")]
            self.assertEqual(
                cols, ["id", "ts", "valence", "arousal", "stability", "mood_label"])
        finally:
            c.close()

    def test_real_tick_appends_and_consumer_reads(self):
        from substrate import Writer, Reader, db_paths
        from theory_x.stage_affect.affect_state import AffectState
        p = db_paths()
        cw = Writer(str(p["conversations"]), name="conversations")
        cr = Reader(str(p["conversations"]))
        br = Reader(str(p["beliefs"]))
        node = AffectState(conversations_writer=cw, conversations_reader=cr,
                           beliefs_reader=br)
        try:
            with patch.object(node, "_compute_valence_delta", return_value=0.1), \
                 patch.object(node, "_compute_arousal_delta", return_value=0.05), \
                 patch.object(node, "_compute_stability", return_value=0.9):
                node._background_tick()
            time.sleep(0.1)  # let the writer thread flush
        finally:
            cw.close()

        c = self._conv_conn()
        try:
            n = c.execute("SELECT COUNT(*) FROM affect_history").fetchone()[0]
            self.assertGreaterEqual(n, 1, "real tick did not append to affect_history")
            # the affect_variance consumer's own query shape returns rows now.
            rows = c.execute(
                "SELECT valence, arousal FROM affect_history WHERE ts > ?", (0,)
            ).fetchall()
            self.assertTrue(rows)
        finally:
            c.close()


if __name__ == "__main__":
    unittest.main()
