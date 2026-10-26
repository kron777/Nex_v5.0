"""Tests for the carry-side topic gate (NEX5_CARRY_TOPIC_GATE).

The recent-striking feedback block (_build_recent_striking_block) feeds recent
STRIKING fires back verbatim; its existing groove filter is phrase/template-only, so
a TOPIC rut (e.g. Optimism/ETH-L2) passes straight through. This gate drops, from the
candidate pool before the 2-sample, fires on a topic that dominates recent output
(a token in >= _CARRY_TOPIC_DF of the last _CARRY_TOPIC_WINDOW fires), so a non-rut
STRIKING fire is surfaced instead. Default OFF -> byte-identical.

Covers: the pure _dominant_topic_terms detector (threshold, floor, diversity,
substring-match), and the block integration (flag ON drops the rut topic from the
pool; flag OFF is unchanged; an all-rut pool is never emptied).

See research log topic_rut_2026-10-07_var2_spec.
"""
from __future__ import annotations

import os
import unittest

from tests import _bootstrap  # noqa: F401

from theory_x.stage6_fountain import generator as G


class TestDominantTopicTerms(unittest.TestCase):
    """The pure detector — no DB, no generator."""

    def test_dominant_token_returned_above_bound(self):
        # 10 fires, 6 mention 'optimism' -> df 0.6 >= 0.40
        fires = ([f"optimism rollups note {i}" for i in range(6)]
                 + [f"the silence holds a weight {i}" for i in range(4)])
        terms = G._dominant_topic_terms(fires)
        self.assertIn("optimism", terms)

    def test_token_below_bound_not_returned(self):
        # 'optimism' in only 3 of 10 -> df 0.3 < 0.40
        fires = ([f"optimism rollups note {i}" for i in range(3)]
                 + [f"a distinct thought number {i} about trees and rivers" for i in range(7)])
        self.assertNotIn("optimism", G._dominant_topic_terms(fires))

    def test_diverse_window_returns_nothing(self):
        fires = [f"wholly unique subject {w}" for w in
                 ("alpha", "beta", "gamma", "delta", "epsilon",
                  "zeta", "eta", "theta", "iota", "kappa")]
        # every content token appears in ~1/10 fires; the shared words ('wholly',
        # 'unique', 'subject') are the same across all -> those WOULD dominate.
        # Use genuinely disjoint content to confirm no spurious term:
        fires = ["alpha ", "beta ", "gamma ", "delta ", "epsilon ",
                 "zeta ", "eta ", "theta ", "iota ", "kappa "]
        self.assertEqual(G._dominant_topic_terms(fires), [])

    def test_floor_small_window_returns_nothing(self):
        # Below _CARRY_TOPIC_MIN_FIRES the window is too small to call a rut.
        fires = ["optimism optimism"] * (G._CARRY_TOPIC_MIN_FIRES - 1)
        self.assertEqual(G._dominant_topic_terms(fires), [])

    def test_empty_input(self):
        self.assertEqual(G._dominant_topic_terms([]), [])
        self.assertEqual(G._dominant_topic_terms(None), [])

    def test_returned_term_substring_matches_raw_fire(self):
        fires = ["Optimism and Ethereum L2 scaling"] * 10
        terms = G._dominant_topic_terms(fires)
        self.assertTrue(terms)
        raw = fires[0].lower()
        for t in terms:
            self.assertIn(t, raw)   # usable by the block's substring drop


class _FakeReader:
    """Minimal stand-in: routes a query to rows by a distinctive SQL substring."""
    def __init__(self, routes):
        self._routes = routes          # list of (substr, rows)

    def read(self, sql, params=()):
        for sub, rows in self._routes:
            if sub in sql:
                return rows
        return []

    def read_one(self, sql, params=()):
        for sub, rows in self._routes:
            if sub in sql:
                return rows[0] if rows else None
        return None


class TestBlockIntegration(unittest.TestCase):
    """_build_recent_striking_block with stub readers; no real DB."""

    def _make_gen(self, pool_fires, recent_window):
        gen = G.FountainGenerator.__new__(G.FountainGenerator)
        # genius_tags: one STRIKING tag per pool fire (id i, descending score)
        tags = [{"fountain_event_id": i, "score": 1.0 - i * 0.01}
                for i in range(len(pool_fires))]
        cand = [{"id": i, "thought": t} for i, t in enumerate(pool_fires)]
        gen._conversations_reader = _FakeReader([("genius_tags", tags)])
        gen._dynamic_reader = _FakeReader([
            ("id IN", cand),                                   # candidate fetch
            ("ORDER BY id DESC", [{"thought": t} for t in recent_window]),  # window
        ])
        gen._beliefs_reader = _FakeReader([("groove_alerts", [])])  # no phrase groove
        return gen

    def tearDown(self):
        os.environ.pop("NEX5_CARRY_TOPIC_GATE", None)

    def test_flag_on_drops_rut_topic_from_pool(self):
        os.environ["NEX5_CARRY_TOPIC_GATE"] = "1"
        pool = ["Optimism rollups reshape how value settles",
                "The silence between thoughts carries its own weight"]
        recent = ["optimism scaling note " + str(i) for i in range(8)] + \
                 ["something else entirely " + str(i) for i in range(2)]  # 8/10 optimism
        gen = self._make_gen(pool, recent)
        block = "\n".join(gen._build_recent_striking_block())
        self.assertIn("silence", block)
        self.assertNotIn("Optimism", block)
        self.assertNotIn("optimism", block)

    def test_flag_off_keeps_rut_topic(self):
        # Default OFF: no gate; with a 2-of-2 pool both are surfaced (sample(2,2)).
        pool = ["Optimism rollups reshape how value settles",
                "The silence between thoughts carries its own weight"]
        recent = ["optimism scaling note " + str(i) for i in range(8)] + \
                 ["something else entirely " + str(i) for i in range(2)]
        gen = self._make_gen(pool, recent)
        block = "\n".join(gen._build_recent_striking_block())
        self.assertIn("Optimism", block)      # rut fire fed back, as on HEAD
        self.assertIn("silence", block)

    def test_flag_on_never_empties_all_rut_pool(self):
        # Every kept fire is on the rut topic -> fail-safe: pool kept, block renders.
        os.environ["NEX5_CARRY_TOPIC_GATE"] = "1"
        pool = ["Optimism rollups reshape how value settles",
                "Optimism bridges and the push toward cheaper settlement"]
        recent = ["optimism scaling note " + str(i) for i in range(10)]
        gen = self._make_gen(pool, recent)
        block = "\n".join(gen._build_recent_striking_block())
        self.assertIn("Optimism", block)      # not emptied


if __name__ == "__main__":
    unittest.main()
