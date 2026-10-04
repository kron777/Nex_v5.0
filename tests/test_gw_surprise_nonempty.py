"""Workspace surprise candidate must not let an EMPTY prediction window win
(NEX5_GW_SURPRISE_NONEMPTY). Empty window = score 1.0, actual_content NULL."""
from __future__ import annotations

import os
import sqlite3
import time
import unittest

from tests import _bootstrap  # noqa: F401
from theory_x.stage_tom import global_workspace as gw


def _db(rows):
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE surprise_events (triggered_at REAL, surprise_score REAL, actual_content TEXT)")
    con.executemany("INSERT INTO surprise_events VALUES (?,?,?)", rows)
    return con


class TestSurpriseNonEmpty(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("NEX5_GW_SURPRISE_NONEMPTY", None)

    def test_empty_window_wins_when_off_and_is_skipped_when_on(self):
        now = time.time()
        con = _db([(now - 30, 0.42, "a real belief that surprised her"), (now - 5, 1.0, None)])
        old = gw._surprise_candidate(con)
        self.assertEqual(old[0], 1.0)
        self.assertIn("'...'", old[1])                      # the empty quote
        os.environ["NEX5_GW_SURPRISE_NONEMPTY"] = "1"
        new = gw._surprise_candidate(con)
        self.assertAlmostEqual(new[0], 0.42)
        self.assertIn("a real belief", new[1])

    def test_only_empty_window_gives_no_candidate(self):
        con = _db([(time.time() - 5, 1.0, None)])
        os.environ["NEX5_GW_SURPRISE_NONEMPTY"] = "1"
        self.assertIsNone(gw._surprise_candidate(con))

    def test_non_empty_unchanged(self):
        now = time.time()
        con = _db([(now - 40, 0.35, "older"), (now - 10, 0.61, "newest real surprise")])
        old = gw._surprise_candidate(con)
        os.environ["NEX5_GW_SURPRISE_NONEMPTY"] = "1"
        self.assertEqual(gw._surprise_candidate(con), old)


if __name__ == "__main__":
    unittest.main()
