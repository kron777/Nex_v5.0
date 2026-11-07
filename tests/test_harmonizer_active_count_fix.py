"""Harmonizer active_paradox miscount fix (`NEX5_HARMONIZER_TENSION_COUNT_FIX`).

tick()'s "active_paradox" counted ALL-TIME rows with resolution='paradox',
including pairs that have since escalated to synthesized/both_deleted/
held_tension -- a later row for the same pair never superseded the earlier
count. Measured live: 73 all-time vs 40 actually still open. This directly
feeds the already-live, unflagged format_for_prompt() "Holding N unresolved
tensions" line.

Dark by default. Covers:
- flag OFF: tick()'s active_paradox reproduces the old (buggy) all-time
  count exactly -- byte-identical to today.
- flag ON: active_paradox reflects only pairs whose MOST RECENT event is
  still 'paradox' -- an escalated pair is correctly excluded even though
  an earlier 'paradox' row for it still exists in the log.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests._bootstrap import *  # noqa: F401, F403

_FLAG = "NEX5_HARMONIZER_TENSION_COUNT_FIX"


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_harm_count_")
    os.environ["NEX5_DATA_DIR"] = tmp
    os.environ["NEX5_ADMIN_HASH_FILE"] = str(Path(tmp) / "admin.argon2")
    from substrate.init_db import init_all
    init_all()
    from substrate import Reader, Writer, db_paths
    paths = db_paths()
    writers = {n: Writer(p, name=n) for n, p in paths.items()}
    readers = {n: Reader(p) for n, p in paths.items()}
    return writers, readers, tmp


def _cleanup(writers, tmp):
    for w in writers.values():
        try:
            w.close()
        except Exception:
            pass
    shutil.rmtree(tmp, ignore_errors=True)
    os.environ.pop("NEX5_DATA_DIR", None)
    os.environ.pop("NEX5_ADMIN_HASH_FILE", None)


def _seed_belief(writers, content, tier=5):
    now = int(time.time())
    return writers["beliefs"].write(
        "INSERT INTO beliefs (content, tier, confidence, created_at, source, locked, paused) "
        "VALUES (?, ?, 0.65, ?, 'test', 0, 0)", (content, tier, now),
    )


def _seed_event(writers, a_id, b_id, resolution, ts=None):
    ts = ts if ts is not None else time.time()
    writers["dynamic"].write(
        "INSERT INTO harmonizer_events (ts, belief_id_a, belief_id_b, resolution) "
        "VALUES (?, ?, ?, ?)", (ts, a_id, b_id, resolution),
    )


def _make_harmonizer(writers, readers):
    from theory_x.stage3_world_model.promotion import BeliefPromoter
    from theory_x.stage3_world_model.harmonizer import Harmonizer
    p = BeliefPromoter(writers["beliefs"], readers["beliefs"])
    return Harmonizer(
        beliefs_writer=writers["beliefs"], beliefs_reader=readers["beliefs"],
        dynamic_writer=writers["dynamic"], dynamic_reader=readers["dynamic"],
        promoter=p,
    )


class TestFlagOffUnchanged(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        os.environ.pop(_FLAG, None)

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_reproduces_the_old_alltime_count(self):
        """2 pairs: one still open, one escalated (2 rows: paradox then
        both_deleted). Old behaviour counts BOTH paradox rows = 2, even
        though only 1 pair is actually still open."""
        h = _make_harmonizer(self.writers, self.readers)
        a1, b1 = _seed_belief(self.writers, "x1"), _seed_belief(self.writers, "y1")
        a2, b2 = _seed_belief(self.writers, "x2"), _seed_belief(self.writers, "y2")
        _seed_event(self.writers, a1, b1, "paradox", ts=time.time() - 300)
        _seed_event(self.writers, a2, b2, "paradox", ts=time.time() - 300)
        _seed_event(self.writers, a2, b2, "both_deleted", ts=time.time() - 100)
        state = h.tick()
        self.assertEqual(state["active_paradox"], 2,
                          "flag off must reproduce the old all-time miscount")


class TestFlagOnCorrectCount(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        os.environ[_FLAG] = "1"

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_escalated_pair_excluded_from_count(self):
        h = _make_harmonizer(self.writers, self.readers)
        a1, b1 = _seed_belief(self.writers, "x1"), _seed_belief(self.writers, "y1")
        a2, b2 = _seed_belief(self.writers, "x2"), _seed_belief(self.writers, "y2")
        _seed_event(self.writers, a1, b1, "paradox", ts=time.time() - 300)
        _seed_event(self.writers, a2, b2, "paradox", ts=time.time() - 300)
        _seed_event(self.writers, a2, b2, "both_deleted", ts=time.time() - 100)
        state = h.tick()
        self.assertEqual(state["active_paradox"], 1,
                          "only the still-open pair should count")

    def test_matches_live_shape_73_vs_40(self):
        """Same shape as the live measurement: several pairs paradox-only,
        several more escalated later -- count must equal only the open set."""
        h = _make_harmonizer(self.writers, self.readers)
        open_pairs = [(_seed_belief(self.writers, f"o{i}a"),
                       _seed_belief(self.writers, f"o{i}b")) for i in range(4)]
        escalated_pairs = [(_seed_belief(self.writers, f"e{i}a"),
                            _seed_belief(self.writers, f"e{i}b")) for i in range(3)]
        for a, b in open_pairs:
            _seed_event(self.writers, a, b, "paradox", ts=time.time() - 300)
        for a, b in escalated_pairs:
            _seed_event(self.writers, a, b, "paradox", ts=time.time() - 300)
            _seed_event(self.writers, a, b, "synthesized", ts=time.time() - 100)
        state = h.tick()
        self.assertEqual(state["active_paradox"], 4)

    def test_format_for_prompt_reports_the_corrected_number(self):
        h = _make_harmonizer(self.writers, self.readers)
        a1, b1 = _seed_belief(self.writers, "x1"), _seed_belief(self.writers, "y1")
        a2, b2 = _seed_belief(self.writers, "x2"), _seed_belief(self.writers, "y2")
        _seed_event(self.writers, a1, b1, "paradox", ts=time.time() - 300)
        _seed_event(self.writers, a2, b2, "paradox", ts=time.time() - 300)
        _seed_event(self.writers, a2, b2, "both_deleted", ts=time.time() - 100)
        h.tick()
        text = h.format_for_prompt()
        self.assertIn("1", text)
        self.assertNotIn("2 unresolved tensions", text)


if __name__ == "__main__":
    unittest.main()
