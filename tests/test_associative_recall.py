"""Tests for FountainGenerator._associative_recall (R52 associative recall).

The retrieval core selects context by recency only — never by relevance to what
is being thought about (R52: 59.2% of fires got zero relevant context). This adds
dedicated relevance slots: own-content beliefs ranked by content-token overlap
with the current thread (the prior fire's focal item), computed at query time,
tier<8, with a 6h per-thread already-shown damper. Fail-safe to [].

Tested by binding the method onto a light shim with a real Reader over an
isolated tempdir DB (NEX5_DATA_DIR) — never the live soak DBs.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_assoc_")
    os.environ["NEX5_DATA_DIR"] = tmp
    from substrate.init_db import init_all
    init_all()
    from substrate import Reader, Writer, db_paths
    paths = db_paths()
    return tmp, Writer(paths["beliefs"], name="beliefs"), Reader(paths["beliefs"])


def _cleanup(tmp, writer):
    try:
        writer.close()
    except Exception:
        pass
    shutil.rmtree(tmp, ignore_errors=True)
    os.environ.pop("NEX5_DATA_DIR", None)


class _Shim:
    """Minimal stand-in exposing only what _associative_recall reads."""
    def __init__(self, reader, focal):
        self._beliefs_reader = reader
        self._last_focal_item = focal


def _assoc(shim, n):
    from theory_x.stage6_fountain.generator import FountainGenerator
    return FountainGenerator._associative_recall.__get__(shim, _Shim)(n)


class TestAssociativeRecall(unittest.TestCase):

    def setUp(self):
        self.tmp, self.w, self.r = _make_env()

    def tearDown(self):
        _cleanup(self.tmp, self.w)

    def _add(self, content, source="fountain_insight", tier=6, offset=60):
        self.w.write(
            "INSERT INTO beliefs (content, tier, confidence, created_at, source, branch_id, locked) "
            "VALUES (?, ?, 0.6, ?, ?, 'x', 0)",
            (content, tier, time.time() - offset, source),
        )
        time.sleep(0.01)

    def test_returns_relevant_over_recent(self):
        # relevant-but-older vs irrelevant-but-newer: relevance must win
        self._add("The Large Hadron Collider measured a new particle resonance", offset=9000)
        self._add("Sourdough starter hydration and crumb structure", offset=30)
        self._add("Collider particle detectors and resonance calibration methods", offset=6000)
        shim = _Shim(self.r, "Large Hadron Collider particle resonance")
        got = _assoc(shim, 2)
        self.assertEqual(len(got), 2)
        blob = " ".join(b["content"].lower() for b in got)
        self.assertIn("collider", blob)
        self.assertNotIn("sourdough", blob)  # irrelevant recent belief excluded

    def test_no_thread_returns_empty(self):
        self._add("Anything relevant to nothing in particular")
        self.assertEqual(_assoc(_Shim(self.r, None), 3), [])
        self.assertEqual(_assoc(_Shim(self.r, ""), 3), [])

    def test_no_overlap_returns_empty(self):
        self._add("Sourdough starter hydration and crumb structure")
        self.assertEqual(_assoc(_Shim(self.r, "quantum chromodynamics lattice gauge"), 3), [])

    def test_ranked_by_overlap_and_capped(self):
        self._add("bitcoin ethereum solana markets rally")   # 4 overlap
        self._add("bitcoin markets dip")                      # 2 overlap
        self._add("bitcoin")                                  # 1 overlap
        shim = _Shim(self.r, "bitcoin ethereum solana markets")
        got = _assoc(shim, 2)
        self.assertEqual(len(got), 2)
        # top pick must be the highest-overlap belief
        self.assertIn("solana", got[0]["content"].lower())

    def test_excludes_tier_8_retired(self):
        self._add("Retired conclusion about bitcoin markets and ethereum", tier=8)
        self._add("Live note on bitcoin markets and ethereum flows", tier=6)
        got = _assoc(_Shim(self.r, "bitcoin ethereum markets"), 5)
        self.assertEqual(len(got), 1)
        self.assertIn("live note", got[0]["content"].lower())

    def test_6h_burst_dedup(self):
        self._add("bitcoin ethereum markets one")
        self._add("bitcoin ethereum markets two")
        shim = _Shim(self.r, "bitcoin ethereum markets")
        first = _assoc(shim, 2)
        self.assertEqual(len(first), 2)
        # same thread again within 6h: both already shown -> nothing new
        second = _assoc(shim, 2)
        self.assertEqual(second, [])

    def test_fail_safe_on_reader_error(self):
        class _Boom:
            def read(self, *a, **k):
                raise RuntimeError("db down")
        self.assertEqual(_assoc(_Shim(_Boom(), "bitcoin markets"), 3), [])

    def test_lazy_shown_state_created(self):
        self._add("bitcoin ethereum markets note")
        shim = _Shim(self.r, "bitcoin ethereum markets")
        self.assertFalse(hasattr(shim, "_assoc_shown"))
        _assoc(shim, 1)
        self.assertTrue(hasattr(shim, "_assoc_shown"))  # created on first use


if __name__ == "__main__":
    unittest.main()
