"""belief_boost HEADROOM pre-screen (tools/check_belief_headroom).

Read-only. Measures whether a within-range boost (eff = created_at + (bv-1)*3.5d, max grade ~0.42
=> ~1.47d lift, boost REPLACES not stacks) could move a below-cutoff belief into the top own_n fetch.
HEADROOM ABSENT => belief_boost is decision-inert (saturated-gate analogue). ANALOGUE, no flag.
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
        """beliefs: list of (source, created_at_offset_days_ago). Returns a temp beliefs.db path."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        con = sqlite3.connect(path)
        con.execute("CREATE TABLE beliefs (id INTEGER PRIMARY KEY, content TEXT, source TEXT, "
                    "tier INTEGER, confidence REAL, created_at REAL, branch_id TEXT)")
        con.execute("CREATE TABLE belief_boost (belief_id INTEGER PRIMARY KEY, boost_value REAL)")
        now = time.time()
        for i, (src, days_ago) in enumerate(beliefs, 1):
            con.execute("INSERT INTO beliefs VALUES (?,?,?,?,?,?,?)",
                        (i, "x", src, 1, 0.5, now - days_ago * 86400.0, "b"))
        for bid, bv in (boosts or []):
            con.execute("INSERT INTO belief_boost VALUES (?,?)", (bid, bv))
        con.commit()
        con.close()
        return path

    def test_sources_match_generator(self):
        # drift guard: the local mirror must equal generator._OWN_CONTENT_SOURCES
        from theory_x.stage6_fountain.generator import _OWN_CONTENT_SOURCES as gen_src
        from tools.check_belief_headroom import _OWN_CONTENT_SOURCES as tool_src
        self.assertEqual(tuple(tool_src), tuple(gen_src))

    def test_headroom_absent_when_gap_exceeds_lift(self):
        from tools.check_belief_headroom import measure, _verdict
        # 3 recent + 5 far-older: the 10-day gap exceeds the ~1.47d max lift
        beliefs = [("fountain_insight", 0.0), ("fountain_insight", 0.04), ("fountain_insight", 0.08)]
        beliefs += [("fountain_insight", 10.0 + i) for i in range(5)]
        path = self._db(beliefs)
        try:
            m = measure(path, own_n=3, max_grade=0.42)
        finally:
            os.unlink(path)
        self.assertEqual(m["promotable_count"], 0)
        self.assertGreater(m["grade_to_promote_marginal"], 0.42)
        self.assertTrue(_verdict(m).startswith("HEADROOM ABSENT"))

    def test_headroom_present_when_densely_packed(self):
        from tools.check_belief_headroom import measure, _verdict
        # below-cutoff beliefs sit within the ~1.47d lift of the cutoff
        beliefs = [("fountain_insight", 0.0), ("fountain_insight", 0.1), ("fountain_insight", 0.2)]
        beliefs += [("fountain_insight", 0.3), ("fountain_insight", 0.4),
                    ("fountain_insight", 0.5), ("fountain_insight", 0.6)]
        path = self._db(beliefs)
        try:
            m = measure(path, own_n=3, max_grade=0.42)
        finally:
            os.unlink(path)
        self.assertGreaterEqual(m["promotable_count"], 3)
        self.assertTrue(_verdict(m).startswith("HEADROOM PRESENT"))

    def test_sense_path_dead_when_no_sense_beliefs(self):
        from tools.check_belief_headroom import measure, _verdict
        beliefs = [("fountain_insight", i * 0.1) for i in range(8)]   # all own-fire, no sense
        path = self._db(beliefs)
        try:
            m = measure(path, own_n=3)
        finally:
            os.unlink(path)
        self.assertEqual(m["sense"]["in_pool"], 0)
        self.assertIn("SENSE PATH DEAD", _verdict(m))

    def test_sense_promotable_reported(self):
        from tools.check_belief_headroom import measure, _verdict
        # dense pool, below-cutoff beliefs are sense-derived and promotable
        beliefs = [("fountain_insight", 0.0), ("fountain_insight", 0.1), ("fountain_insight", 0.2)]
        beliefs += [("precipitated_from_sense", 0.3), ("precipitated_from_sense", 0.4),
                    ("precipitated_from_sense", 0.5)]
        path = self._db(beliefs)
        try:
            m = measure(path, own_n=3, max_grade=0.42)
        finally:
            os.unlink(path)
        self.assertEqual(m["sense"]["below_cutoff"], 3)
        self.assertEqual(m["sense"]["promotable"], 3)
        self.assertNotIn("SENSE PATH DEAD", _verdict(m))

    def test_boost_lifts_effective_recency(self):
        from tools.check_belief_headroom import measure
        # an old belief with a big boost should rank into the top own_n (eff uses the boost)
        beliefs = [("fountain_insight", 0.1), ("fountain_insight", 0.2), ("fountain_insight", 5.0)]
        m = None
        path = self._db(beliefs, boosts=[(3, 2.5)])   # id 3 (5d old) boosted: +1.5*3.5d = +5.25d
        try:
            m = measure(path, own_n=1, max_grade=0.42)
        finally:
            os.unlink(path)
        # id 3 eff = -5d + 5.25d = +0.25d (future-dated), so it is the single fetched belief; the
        # cutoff is therefore younger than 'now' -> negative age
        self.assertLess(m["cutoff_age_days"], 0.0)

    def test_insufficient(self):
        from tools.check_belief_headroom import measure
        path = self._db([("fountain_insight", 0.0), ("fountain_insight", 0.1)])
        try:
            m = measure(path, own_n=12)
        finally:
            os.unlink(path)
        self.assertIn("error", m)


if __name__ == "__main__":
    unittest.main()
