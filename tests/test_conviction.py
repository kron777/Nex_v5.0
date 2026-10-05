"""Tests for conviction — śraddhā re-expressed by structure (NEX5_CONVICTION).

Directions tested: the support score reads tier as DEPTH (T1 > T6, the fix for
śraddhā's inverted `tier >= 6`); regroup() keeps every belief line byte-for-byte
and only adds the two group headers; any unresolvable line, empty block or DB
error returns the block unchanged (fail-safe to the flat block); ordering keeps
every line and drops none.

RECORDED NULL (2026-09-26): neither the grouping nor the ordering moved her voice
on qwen2.5:3b or 7b, so both chat-path hooks were removed. This module and its
harnesses are kept as the record; nothing calls it live.
"""
from __future__ import annotations

import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

from theory_x.stage_affect import conviction as cv

_NOW = 1_790_000_000.0


def _fixture_db(path: str) -> None:
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE beliefs (id INTEGER PRIMARY KEY, content TEXT, tier INTEGER, "
                "confidence REAL, last_referenced_at INTEGER)")
    con.execute("CREATE TABLE belief_edges (id INTEGER PRIMARY KEY, source_id INTEGER, "
                "target_id INTEGER, edge_type TEXT, last_traversed_at REAL)")
    rows = [
        (1, "a deep keystone about attention being a kind of care and consent", 1, 0.95, None),
        (2, "a thin fresh impression about a feed item that barely connects", 6, 0.60, None),
        (3, "a well connected body belief that she keeps traversing lately", 3, 0.80, None),
    ]
    con.executemany("INSERT INTO beliefs VALUES (?,?,?,?,?)", rows)
    # belief 3: many dense edges, traversed an hour ago; belief 1: a few, stale
    for k in range(40):
        con.execute("INSERT INTO belief_edges (source_id, target_id, edge_type, last_traversed_at) "
                    "VALUES (3, ?, 'synthesises', ?)", (100 + k, _NOW - 3600))
    for k in range(3):
        con.execute("INSERT INTO belief_edges (source_id, target_id, edge_type, last_traversed_at) "
                    "VALUES (1, ?, 'cross_domain', ?)", (200 + k, _NOW - 200 * 3600))
    # opposes edges must NOT count toward centrality
    for k in range(50):
        con.execute("INSERT INTO belief_edges (source_id, target_id, edge_type, last_traversed_at) "
                    "VALUES (2, ?, 'opposes', ?)", (300 + k, _NOW))
    con.commit()
    con.close()


def _block(*rows):
    lines = ["Her current beliefs relevant to this topic:"]
    for tier, conf, text in rows:
        lines.append(f"- [Tier {tier} | {conf:.2f}] {text}")
    return "\n".join(lines)


class TestSupport(unittest.TestCase):
    def test_tier_is_depth_not_height(self):
        # same everything else: T1 must outscore T6 (śraddhā reads the reverse)
        self.assertGreater(cv.support(1, 0.7, 10, 5.0), cv.support(6, 0.7, 10, 5.0))

    def test_monotone_in_each_primitive(self):
        base = cv.support(3, 0.7, 10, 10.0)
        self.assertGreater(cv.support(3, 0.9, 10, 10.0), base)
        self.assertGreater(cv.support(3, 0.7, 80, 10.0), base)
        self.assertGreater(cv.support(3, 0.7, 10, 1.0), base)

    def test_bounded(self):
        self.assertLessEqual(cv.support(1, 1.0, 10_000, 0.0), 1.0)
        self.assertGreaterEqual(cv.support(7, 0.0, 0, None), 0.0)


class TestRegroup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "beliefs.db")
        _fixture_db(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_groups_and_keeps_lines_verbatim(self):
        blk = _block(
            (6, 0.60, "a thin fresh impression about a feed item that barely connects"),
            (3, 0.80, "a well connected body belief that she keeps traversing lately"),
        )
        out = cv.regroup(blk, now=_NOW, db_path=self.db)
        self.assertNotEqual(out, blk)
        lines = out.split("\n")
        self.assertEqual(lines[0], "Her current beliefs relevant to this topic:")
        self.assertEqual(lines[1], cv.HELD_HEADER)
        self.assertIn("well connected body belief", lines[2])
        self.assertEqual(lines[3], cv.UNSETTLED_HEADER)
        self.assertIn("thin fresh impression", lines[4])
        # nothing but the two headers is added; every belief line survives byte-for-byte
        self.assertEqual(sorted(set(lines) - set(blk.split("\n"))),
                         sorted([cv.HELD_HEADER, cv.UNSETTLED_HEADER]))
        self.assertEqual(len(lines), len(blk.split("\n")) + 2)

    def test_opposes_edges_do_not_confer_support(self):
        sig = cv.signatures(
            ["a thin fresh impression about a feed item that barely connects"],
            now=_NOW, db_path=self.db)[0]
        self.assertEqual(sig["deg"], 0)
        self.assertFalse(sig["held"])

    def test_invert_swaps_groups(self):
        blk = _block(
            (6, 0.60, "a thin fresh impression about a feed item that barely connects"),
            (3, 0.80, "a well connected body belief that she keeps traversing lately"),
        )
        out = cv.regroup(blk, now=_NOW, db_path=self.db, invert=True).split("\n")
        self.assertIn("thin fresh impression", out[out.index(cv.HELD_HEADER) + 1])

    def test_preamble_lines_keep_their_place(self):
        blk = "SELF STATE: steady\n\n" + _block(
            (1, 0.95, "a deep keystone about attention being a kind of care and consent"))
        out = cv.regroup(blk, now=_NOW, db_path=self.db)
        self.assertTrue(out.startswith("SELF STATE: steady\n\nHer current beliefs"))

    def test_unresolvable_line_returns_block_unchanged(self):
        blk = _block(
            (3, 0.80, "a well connected body belief that she keeps traversing lately"),
            (6, 0.50, "a belief that is not in the graph at all"),
        )
        self.assertEqual(cv.regroup(blk, now=_NOW, db_path=self.db), blk)

    def test_no_belief_lines_unchanged(self):
        self.assertEqual(cv.regroup("just text", db_path=self.db), "just text")
        self.assertEqual(cv.regroup("", db_path=self.db), "")
        self.assertIsNone(cv.regroup(None, db_path=self.db))

    def test_db_error_returns_block_unchanged(self):
        blk = _block((3, 0.80, "a well connected body belief that she keeps traversing lately"))
        self.assertEqual(cv.regroup(blk, db_path="/nonexistent/beliefs.db"), blk)

    def test_truncated_last_line_resolves_by_prefix(self):
        full = "a well connected body belief that she keeps traversing lately"
        blk = _block((3, 0.80, full[:45] + " …"))
        self.assertNotEqual(cv.regroup(blk, now=_NOW, db_path=self.db), blk)


class TestOrderBySupport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "beliefs.db")
        _fixture_db(self.db)
        self.blk = "SELF STATE: steady\n\n" + _block(
            (6, 0.60, "a thin fresh impression about a feed item that barely connects"),
            (3, 0.80, "a well connected body belief that she keeps traversing lately"),
            (1, 0.95, "a deep keystone about attention being a kind of care and consent"),
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_orders_high_support_first_without_labels_or_drops(self):
        out = cv.order_by_support(self.blk, now=_NOW, db_path=self.db)
        self.assertNotEqual(out, self.blk)
        # same multiset of lines: nothing added, nothing dropped
        self.assertEqual(sorted(out.split("\n")), sorted(self.blk.split("\n")))
        self.assertNotIn(cv.HELD_HEADER, out)
        beliefs = [ln for ln in out.split("\n") if ln.startswith("- [Tier")]
        self.assertIn("thin fresh impression", beliefs[-1])     # lowest support last
        self.assertTrue(out.startswith("SELF STATE: steady\n\nHer current beliefs"))

    def test_reverse_is_lowest_first(self):
        out = cv.order_by_support(self.blk, now=_NOW, db_path=self.db, reverse=True)
        beliefs = [ln for ln in out.split("\n") if ln.startswith("- [Tier")]
        self.assertIn("thin fresh impression", beliefs[0])

    def test_precomputed_supports_and_stable_ties(self):
        blk = _block((6, 0.6, "x one belief line text"), (6, 0.6, "y two belief line text"),
                     (6, 0.6, "z three belief line text"))
        out = cv.order_by_support(blk, supports=[0.5, 0.9, 0.5]).split("\n")
        self.assertIn("y two", out[1])
        self.assertIn("x one", out[2])      # tie with z keeps retrieval order
        self.assertIn("z three", out[3])

    def test_fail_safe(self):
        bad = self.blk + "\n- [Tier 6 | 0.50] a belief that is not in the graph at all"
        self.assertEqual(cv.order_by_support(bad, now=_NOW, db_path=self.db), bad)
        self.assertEqual(cv.order_by_support(self.blk, db_path="/nonexistent/x.db"), self.blk)
        one = _block((3, 0.8, "a well connected body belief that she keeps traversing lately"))
        self.assertEqual(cv.order_by_support(one, db_path=self.db), one)
        self.assertEqual(cv.order_by_support(self.blk, supports=[0.1]), self.blk)
        self.assertIsNone(cv.order_by_support(None))


if __name__ == "__main__":
    unittest.main()
