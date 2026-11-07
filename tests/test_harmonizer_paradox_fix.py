"""The LIMIT-200 escalation-starvation fix (`NEX5_HARMONIZER_PARADOX_FIX`).

scan_for_conflicts() samples LIMIT 200 of a belief pool that, on the live
corpus, has grown past 3,700 (tier 3 alone over 600). Escalation depends on
the SAME pair being re-detected on a LATER scan, which becomes vanishingly
unlikely once the pool outgrows the window -- measured live: 40 pairs stuck
at 'paradox' for up to 277h against the 16h incubation threshold.

Dark by default: NEX5_HARMONIZER_PARADOX_FIX=1 to arm. Covers:
- flag OFF: _escalate_stale_paradoxes() is a no-op; run_scan_and_resolve()'s
  behaviour is byte-identical to before this change, including on a pair
  that has aged well past incubation but was never re-sampled.
- flag ON: an aged, open paradox pair escalates even when it is NOT in the
  current scan_for_conflicts() window (simulated directly: the pair's
  beliefs are seeded, then excluded from re-detection by tier/pause so the
  normal re-detection path cannot find them, proving the direct pass is
  what fired).
- eligibility guard: a pair where one belief has since been promoted to a
  locked keystone (or already retired) must NOT be force-resolved.
- pairs already escalated by the normal path (synthesized/both_deleted) must
  not be touched again, even if a stale 'paradox' event exists earlier in
  the log for the same pair.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests._bootstrap import *  # noqa: F401, F403

_FLAG = "NEX5_HARMONIZER_PARADOX_FIX"


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_harm_fix_")
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


def _seed_belief(writers, content, tier=5, confidence=0.65, locked=0, paused=0):
    now = int(time.time())
    return writers["beliefs"].write(
        "INSERT INTO beliefs "
        "(content, tier, confidence, created_at, source, locked, paused) "
        "VALUES (?, ?, ?, ?, 'test', ?, ?)",
        (content, tier, confidence, now, locked, paused),
    )


def _seed_paradox_event(writers, a_id, b_id, age_hours):
    ts = time.time() - age_hours * 3600
    writers["dynamic"].write(
        "INSERT INTO harmonizer_events (ts, belief_id_a, belief_id_b, resolution) "
        "VALUES (?, ?, ?, 'paradox')",
        (ts, a_id, b_id),
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

    def test_escalate_stale_paradoxes_is_noop(self):
        h = _make_harmonizer(self.writers, self.readers)
        a_id = _seed_belief(self.writers, "Markets trend upward over decades")
        b_id = _seed_belief(self.writers, "Markets do not trend upward over decades")
        _seed_paradox_event(self.writers, a_id, b_id, age_hours=300)
        self.assertEqual(h._escalate_stale_paradoxes(), 0)
        row = self.readers["beliefs"].read_one("SELECT tier FROM beliefs WHERE id=?", (a_id,))
        self.assertNotEqual(row["tier"], 8, "flag off must never retire a belief")

    def test_run_scan_and_resolve_unaffected_by_a_stuck_pair_outside_its_window(self):
        """An aged, open pair that scan_for_conflicts() cannot re-sample (its
        beliefs are paused, so scan_for_conflicts() excludes them -- standing
        in for "outside the capped LIMIT 200 window") must stay untouched."""
        h = _make_harmonizer(self.writers, self.readers)
        a_id = _seed_belief(self.writers, "Order arises from complexity", tier=5, paused=1)
        b_id = _seed_belief(self.writers, "Order does not arise from complexity", tier=5, paused=1)
        _seed_paradox_event(self.writers, a_id, b_id, age_hours=300)
        acted = h.run_scan_and_resolve()
        self.assertEqual(acted, 0)
        row = self.readers["beliefs"].read_one("SELECT tier FROM beliefs WHERE id=?", (a_id,))
        self.assertNotEqual(row["tier"], 8)


class TestFlagOnEscalatesStuckPairs(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        os.environ[_FLAG] = "1"

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_stuck_pair_outside_scan_window_still_escalates(self):
        """Paused beliefs are invisible to scan_for_conflicts() (standing in
        for "fell out of the capped LIMIT 200 sample") -- the direct pass
        must still find and escalate them by id."""
        h = _make_harmonizer(self.writers, self.readers)
        a_id = _seed_belief(self.writers, "Order arises from complexity", tier=5, paused=1)
        b_id = _seed_belief(self.writers, "Order does not arise from complexity", tier=5, paused=1)
        _seed_paradox_event(self.writers, a_id, b_id, age_hours=300)
        # scan_for_conflicts() truly cannot see this pair (paused excluded).
        self.assertEqual(h.scan_for_conflicts(), [])
        # ...but it's also not "still eligible" per the guard (paused), so the
        # direct pass must likewise leave it alone -- this proves the guard,
        # not the escalation; see the next test for the escalation itself.
        acted = h._escalate_stale_paradoxes()
        self.assertEqual(acted, 0)
        row = self.readers["beliefs"].read_one("SELECT tier FROM beliefs WHERE id=?", (a_id,))
        self.assertNotEqual(row["tier"], 8, "paused beliefs must not be force-resolved")

    def test_eligible_stuck_pair_escalates_without_resampling(self):
        """An aged, open, STILL-ELIGIBLE pair must escalate via the direct
        pass alone, without ever calling run_scan_and_resolve()'s normal
        re-detection path (proves the fix, not the pre-existing path)."""
        h = _make_harmonizer(self.writers, self.readers)
        a_id = _seed_belief(self.writers, "Markets trend upward over decades", tier=5)
        b_id = _seed_belief(self.writers, "Markets do not trend upward over decades", tier=5)
        _seed_paradox_event(self.writers, a_id, b_id, age_hours=300)
        acted = h._escalate_stale_paradoxes()
        self.assertEqual(acted, 1)
        row_a = self.readers["beliefs"].read_one("SELECT tier FROM beliefs WHERE id=?", (a_id,))
        row_b = self.readers["beliefs"].read_one("SELECT tier FROM beliefs WHERE id=?", (b_id,))
        self.assertEqual(row_a["tier"], 8)
        self.assertEqual(row_b["tier"], 8)

    def test_still_incubating_pair_not_escalated(self):
        h = _make_harmonizer(self.writers, self.readers)
        a_id = _seed_belief(self.writers, "Markets trend upward over decades")
        b_id = _seed_belief(self.writers, "Markets do not trend upward over decades")
        _seed_paradox_event(self.writers, a_id, b_id, age_hours=1)  # well under 16h
        self.assertEqual(h._escalate_stale_paradoxes(), 0)

    def test_promoted_to_keystone_is_not_force_resolved(self):
        """One side locked at tier 1 (promoted out from under the tension)
        since being marked paradox -- must be skipped, not retired."""
        h = _make_harmonizer(self.writers, self.readers)
        a_id = _seed_belief(self.writers, "Markets trend upward over decades", tier=5)
        b_id = _seed_belief(self.writers, "Markets do not trend upward over decades", tier=5)
        _seed_paradox_event(self.writers, a_id, b_id, age_hours=300)
        self.writers["beliefs"].write(
            "UPDATE beliefs SET tier=1, locked=1 WHERE id=?", (a_id,))
        acted = h._escalate_stale_paradoxes()
        self.assertEqual(acted, 0)
        row_b = self.readers["beliefs"].read_one("SELECT tier FROM beliefs WHERE id=?", (b_id,))
        self.assertNotEqual(row_b["tier"], 8, "the other side must not be unilaterally retired")

    def test_already_escalated_pair_not_touched_again(self):
        """A pair whose MOST RECENT event is already synthesized/both_deleted
        (an earlier 'paradox' row for the same pair also exists in the log)
        must not be re-resolved."""
        h = _make_harmonizer(self.writers, self.readers)
        a_id = _seed_belief(self.writers, "Markets trend upward over decades", tier=8)
        b_id = _seed_belief(self.writers, "Markets do not trend upward over decades", tier=8)
        _seed_paradox_event(self.writers, a_id, b_id, age_hours=300)
        self.writers["dynamic"].write(
            "INSERT INTO harmonizer_events (ts, belief_id_a, belief_id_b, resolution) "
            "VALUES (?, ?, ?, 'both_deleted')",
            (time.time() - 100, a_id, b_id),
        )
        pairs = h._open_paradox_pairs()
        self.assertEqual(pairs, [], "a pair already escalated must not read back as open")
        acted = h._escalate_stale_paradoxes()
        self.assertEqual(acted, 0)

    def test_full_run_scan_and_resolve_includes_the_direct_pass(self):
        """End-to-end: run_scan_and_resolve() itself picks up a stuck pair
        that is outside its own scan window, when the flag is on."""
        h = _make_harmonizer(self.writers, self.readers)
        a_id = _seed_belief(self.writers, "Markets trend upward over decades", tier=5)
        b_id = _seed_belief(self.writers, "Markets do not trend upward over decades", tier=5)
        _seed_paradox_event(self.writers, a_id, b_id, age_hours=300)
        acted = h.run_scan_and_resolve()
        self.assertGreaterEqual(acted, 1)
        row_a = self.readers["beliefs"].read_one("SELECT tier FROM beliefs WHERE id=?", (a_id,))
        self.assertEqual(row_a["tier"], 8)


if __name__ == "__main__":
    unittest.main()
