"""belief_boost HEADROOM pre-screen (tools/check_belief_headroom).

Read-only. eff = created_at + (bv-1)*3.5d; boost REPLACES, max grade ~0.42 => ~1.47d lift. The fetch
takes top own_n by eff with BOTH caps (per-source 3 / sense 5, per-branch 2), so the pre-screen is
cap-aware: a sense belief can clear the rank cutoff yet be locked out by a full branch/source (a false
GO the pre-cap test would miss). GO gates on sense.promotable_effective. ANALOGUE, no flag.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import time
import unittest

from tests._bootstrap import *  # noqa: F401, F403


class TestBeliefHeadroom(unittest.TestCase):

    def _db(self, beliefs, boosts=None):
        """beliefs: list of (source, days_ago, branch). Returns a temp beliefs.db path."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        con = sqlite3.connect(path)
        con.execute("CREATE TABLE beliefs (id INTEGER PRIMARY KEY, content TEXT, source TEXT, "
                    "tier INTEGER, confidence REAL, created_at REAL, branch_id TEXT)")
        con.execute("CREATE TABLE belief_boost (belief_id INTEGER PRIMARY KEY, boost_value REAL)")
        now = time.time()
        for i, (src, days_ago, br) in enumerate(beliefs, 1):
            con.execute("INSERT INTO beliefs VALUES (?,?,?,?,?,?,?)",
                        (i, "x", src, 1, 0.5, now - days_ago * 86400.0, br))
        for bid, bv in (boosts or []):
            con.execute("INSERT INTO belief_boost VALUES (?,?)", (bid, bv))
        con.commit()
        con.close()
        return path

    def test_constants_match_generator(self):
        from theory_x.stage6_fountain import generator as g
        from tools import check_belief_headroom as t
        self.assertEqual(tuple(t._OWN_CONTENT_SOURCES), tuple(g._OWN_CONTENT_SOURCES))
        self.assertEqual(t._OWN_PER_SOURCE_MAX, g._OWN_PER_SOURCE_MAX)
        self.assertEqual(t._OWN_PER_SOURCE_OVERRIDES, g._OWN_PER_SOURCE_OVERRIDES)

    def test_sense_path_dead_when_no_sense(self):
        from tools.check_belief_headroom import measure, _verdict
        beliefs = [("fountain_insight", i * 0.1, f"b{i}") for i in range(8)]
        path = self._db(beliefs)
        try:
            m = measure(path, own_n=3)
        finally:
            os.unlink(path)
        self.assertEqual(m["sense"]["in_pool"], 0)
        self.assertIn("SENSE PATH DEAD", _verdict(m))

    def test_sense_headroom_present_go(self):
        from tools.check_belief_headroom import measure, _verdict
        fetched = [("fountain_insight", 0.0, "b1"), ("fountain_insight", 0.1, "b2"),
                   ("fountain_insight", 0.2, "b3")]
        sense = [("precipitated_from_sense", 0.3, "s1"), ("precipitated_from_sense", 0.4, "s2"),
                 ("precipitated_from_sense", 0.5, "s3")]
        path = self._db(fetched + sense)
        try:
            m = measure(path, own_n=3, max_grade=0.42)
        finally:
            os.unlink(path)
        self.assertEqual(m["sense"]["promotable_effective"], 3)
        self.assertEqual(m["sense"]["in_fetch"], 0)
        self.assertTrue(_verdict(m).startswith("GO / HEADROOM PRESENT"))

    def test_sense_headroom_absent_gap_too_large(self):
        from tools.check_belief_headroom import measure, _verdict
        fetched = [("fountain_insight", 0.0, "b1"), ("fountain_insight", 0.1, "b2"),
                   ("fountain_insight", 0.2, "b3")]
        sense = [("precipitated_from_sense", 10.0 + i, f"s{i}") for i in range(3)]
        path = self._db(fetched + sense)
        try:
            m = measure(path, own_n=3, max_grade=0.42)
        finally:
            os.unlink(path)
        self.assertEqual(m["sense"]["promotable_clears_cutoff"], 0)
        self.assertEqual(m["sense"]["promotable_effective"], 0)
        self.assertTrue(_verdict(m).startswith("NO-GO / HEADROOM ABSENT"))

    def test_cap_blocked_is_not_a_false_go(self):
        # the Q1b gap: sense beliefs CLEAR the rank cutoff but their branch is full in the fetch.
        # pre-cap test would call them promotable (false GO); cap-aware must not.
        from tools.check_belief_headroom import measure, _verdict
        fetched = [("fountain_insight", 0.0, "hot"), ("fountain_insight", 0.0, "hot"),  # branch 'hot' full
                   ("fountain_insight", 2.0, "b2")]                                      # cutoff = -2d
        sense = [("precipitated_from_sense", 3.0, "hot"), ("precipitated_from_sense", 3.1, "hot"),
                 ("precipitated_from_sense", 3.2, "hot")]   # boosted eff -1.53d clears -2d, but 'hot' full
        path = self._db(fetched + sense)
        try:
            m = measure(path, own_n=3, max_grade=0.42)
        finally:
            os.unlink(path)
        self.assertEqual(m["sense"]["promotable_clears_cutoff"], 3)   # pre-cap WOULD have said GO
        self.assertEqual(m["sense"]["promotable_effective"], 0)       # cap-aware: locked out
        self.assertEqual(m["sense"]["cap_blocked"], 3)
        v = _verdict(m)
        self.assertTrue(v.startswith("NO-GO"))
        self.assertIn("cap", v)

    def test_in_fetch_is_ceiling_reducer(self):
        from tools.check_belief_headroom import measure, _verdict
        fetched = [("precipitated_from_sense", 0.0, "b1"), ("fountain_insight", 0.1, "b2"),
                   ("fountain_insight", 0.2, "b3")]                 # a sense belief already in-fetch
        sense_below = [("precipitated_from_sense", 0.3, "s1"), ("precipitated_from_sense", 0.4, "s2"),
                       ("precipitated_from_sense", 0.5, "s3")]
        path = self._db(fetched + sense_below)
        try:
            m = measure(path, own_n=3, max_grade=0.42)
        finally:
            os.unlink(path)
        self.assertEqual(m["sense"]["in_fetch"], 1)
        self.assertIn("ceiling REDUCER", _verdict(m))

    def test_boost_lifts_effective_recency(self):
        from tools.check_belief_headroom import measure
        beliefs = [("fountain_insight", 0.1, "b1"), ("fountain_insight", 0.2, "b2"),
                   ("fountain_insight", 5.0, "b3")]
        path = self._db(beliefs, boosts=[(3, 2.5)])    # id 3 (5d old) boosted +1.5*3.5d = +5.25d -> future
        try:
            m = measure(path, own_n=1, max_grade=0.42)
        finally:
            os.unlink(path)
        self.assertLess(m["cutoff_age_days"], 0.0)      # the boosted old belief is the single fetched one

    def test_insufficient(self):
        from tools.check_belief_headroom import measure
        path = self._db([("fountain_insight", 0.0, "b1"), ("fountain_insight", 0.1, "b2")])
        try:
            m = measure(path, own_n=12)
        finally:
            os.unlink(path)
        self.assertIn("error", m)


if __name__ == "__main__":
    unittest.main()
