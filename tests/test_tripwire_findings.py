"""Swallowed schema errors NEX5_SCHEMA_TRIPWIRE surfaced on the first soak of
the fresh store (2026-10-26). Each is pinned by its observable here; the raga
perseveration query is covered by the static-SQL compile guard."""
import os
import tempfile
import time
import unittest
from unittest import mock

from tests import _bootstrap  # noqa: F401

from substrate import connect


class TestTripwireFindings(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"NEX5_DATA_DIR": self.tmp.name})
        self.env.start()
        from substrate.init_db import init_all
        init_all()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_pattern_and_witness_logs_exist_before_first_compose(self):
        # The decoder's daemon counts read these before the loops' first
        # compose-hour tick would have created them.
        from substrate.paths import db_paths
        c = connect(str(db_paths()["dynamic"]))
        try:
            for t in ("pattern_log", "witness_log"):
                self.assertEqual(c.execute(
                    f"SELECT COUNT(*), MAX(composed_at) FROM {t} WHERE composed_at <= ?",
                    (time.time(),)).fetchone(), (0, None))
        finally:
            c.close()

    def test_compositional_emotion_reads_affect_without_a_failed_query(self):
        from substrate.paths import db_paths
        from theory_x.stage_affect import compositional_emotion as ce
        c = connect(str(db_paths()["conversations"]))
        c.execute("INSERT INTO affect_state (id, valence, arousal, stability, "
                  "mood_label, updated_at) VALUES (1, 0.3, 0.4, 0.8, 'calm', ?)",
                  (time.time(),))
        c.commit(); c.close()
        with mock.patch.dict(os.environ, {"NEX5_SCHEMA_TRIPWIRE": "1"}):
            with self.assertNoLogs("substrate.schema_tripwire", "ERROR"):
                got = ce._read_affect()
        self.assertEqual(got["mood_label"], "calm")


if __name__ == "__main__":
    unittest.main()
