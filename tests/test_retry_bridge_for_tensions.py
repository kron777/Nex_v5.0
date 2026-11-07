"""Candidate 3 (2026-11-07 round) — periodic bridge retry for held tensions.

A Phase D tension (`NEX5_HELD_TENSION`) previously only ever closed two ways:
its basis left the pool (sweep_resolved_tensions' 'belief_left_pool'), or it
aged past _TENSION_STALE_DAYS ('stale_retention'). Neither path ever looked
for a bridging belief the way the normal escalation path
(_retire_both_or_synthesize) does -- so a tension whose pair could now be
bridged, because the belief pool grew after the tension opened, just sat
there anyway. retry_bridge_for_tensions() re-runs that same search against
every still-eligible open tension and, on a hit, applies the normal
synthesis treatment (retire both to tier 8, edges to the bridge) and closes
the tension with reason 'bridge_found'.

Like sweep_resolved_tensions, this has no explicit NEX5_HELD_TENSION check of
its own -- it operates on whatever is actually in held_tensions, same
reasoning: with the flag off, no rows ever get written there in the first
place, so there is nothing for this to find regardless.

Not currently invoked by any live loop (see Harmonizer.decay()'s docstring).
This file proves the method itself, not reachability.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests._bootstrap import *  # noqa: F401, F403

_FLAG = "NEX5_HELD_TENSION"


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_bridge_retry_")
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


def _seed_belief(writers, content, tier=5, locked=0, paused=0):
    now = int(time.time())
    return writers["beliefs"].write(
        "INSERT INTO beliefs (content, tier, confidence, created_at, source, locked, paused) "
        "VALUES (?, ?, 0.65, ?, 'test', ?, ?)",
        (content, tier, now, locked, paused),
    )


def _clear_keystone_noise(writers):
    """init_all() seeds ~76 pre-existing tier<=5 unpaused keystone beliefs.
    _find_synthesis_candidate()'s search is capped at LIMIT 50 with no
    ORDER BY, so a freshly-seeded bridge belief (a higher id, inserted
    after those keystones) never gets reached within that cap. Clearing
    them isolates the mechanism under test from that pre-existing,
    unrelated seed-data artifact -- the same LIMIT-50 behaviour already
    exists in _retire_both_or_synthesize, unchanged by this candidate."""
    writers["beliefs"].write("DELETE FROM beliefs WHERE tier <= 5")


def _seed_tension(writers, a_id, b_id, days_ago=0.0):
    created_at = time.time() - days_ago * 86400
    return writers["dynamic"].write(
        "INSERT INTO held_tensions (belief_id_a, belief_id_b, created_at) "
        "VALUES (?, ?, ?)",
        (min(a_id, b_id), max(a_id, b_id), created_at),
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


_A_CONTENT = "Markets trend upward over decades"
_B_CONTENT = "Markets do not trend upward over decades"
_BRIDGE_CONTENT = "Markets trend upward in some decades but not every decade"


class TestBridgeFound(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        os.environ[_FLAG] = "1"

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_bridge_found_retires_both_and_resolves_tension(self):
        _clear_keystone_noise(self.writers)
        a_id = _seed_belief(self.writers, _A_CONTENT)
        b_id = _seed_belief(self.writers, _B_CONTENT)
        tension_id = _seed_tension(self.writers, a_id, b_id)
        # bridge didn't exist when the tension opened -- added afterwards.
        bridge_id = _seed_belief(self.writers, _BRIDGE_CONTENT)

        h = _make_harmonizer(self.writers, self.readers)
        bridged = h.retry_bridge_for_tensions()
        self.assertEqual(bridged, 1)

        tension = self.readers["dynamic"].read_one(
            "SELECT resolved_at, resolved_reason FROM held_tensions WHERE id = ?",
            (tension_id,),
        )
        self.assertIsNotNone(tension["resolved_at"])
        self.assertEqual(tension["resolved_reason"], "bridge_found")

        row_a = self.readers["beliefs"].read_one(
            "SELECT tier, content, paused FROM beliefs WHERE id = ?", (a_id,))
        row_b = self.readers["beliefs"].read_one(
            "SELECT tier, content, paused FROM beliefs WHERE id = ?", (b_id,))
        self.assertEqual(row_a["tier"], 8)
        # belief_id_b: _apply_synthesis sets tier=8, then (same as the
        # original, unextracted code) decisive_contradiction(belief_id_b)
        # runs after and demotes it 2 further tiers, capped at 7 -- a
        # pre-existing asymmetry in the normal synthesis path, unchanged by
        # this candidate's refactor.
        self.assertEqual(row_b["tier"], 7)
        self.assertTrue(row_a["content"].startswith("[RETIRED]"))
        self.assertTrue(row_b["content"].startswith("[RETIRED]"))

        event = self.readers["dynamic"].read_one(
            "SELECT resolution, synthesis_belief_id FROM harmonizer_events "
            "WHERE belief_id_a = ? AND belief_id_b = ? ORDER BY ts DESC LIMIT 1",
            (a_id, b_id),
        )
        self.assertEqual(event["resolution"], "synthesized")
        self.assertEqual(event["synthesis_belief_id"], bridge_id)

    def test_multiple_open_tensions_processed_independently(self):
        _clear_keystone_noise(self.writers)
        a1, b1 = _seed_belief(self.writers, _A_CONTENT), _seed_belief(self.writers, _B_CONTENT)
        t1 = _seed_tension(self.writers, a1, b1)
        _seed_belief(self.writers, _BRIDGE_CONTENT)  # bridges t1 only

        a2 = _seed_belief(self.writers, "Completely unrelated topic alpha")
        b2 = _seed_belief(self.writers, "Completely unrelated topic beta")
        t2 = _seed_tension(self.writers, a2, b2)  # no bridge for this pair

        h = _make_harmonizer(self.writers, self.readers)
        bridged = h.retry_bridge_for_tensions()
        self.assertEqual(bridged, 1)

        t1_row = self.readers["dynamic"].read_one(
            "SELECT resolved_at FROM held_tensions WHERE id = ?", (t1,))
        t2_row = self.readers["dynamic"].read_one(
            "SELECT resolved_at FROM held_tensions WHERE id = ?", (t2,))
        self.assertIsNotNone(t1_row["resolved_at"])
        self.assertIsNone(t2_row["resolved_at"])


class TestNoBridgeFound(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        os.environ[_FLAG] = "1"

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_no_matching_belief_leaves_tension_open_and_untouched(self):
        a_id = _seed_belief(self.writers, _A_CONTENT)
        b_id = _seed_belief(self.writers, _B_CONTENT)
        tension_id = _seed_tension(self.writers, a_id, b_id)

        h = _make_harmonizer(self.writers, self.readers)
        bridged = h.retry_bridge_for_tensions()
        self.assertEqual(bridged, 0)

        tension = self.readers["dynamic"].read_one(
            "SELECT resolved_at FROM held_tensions WHERE id = ?", (tension_id,))
        self.assertIsNone(tension["resolved_at"])

        row_a = self.readers["beliefs"].read_one(
            "SELECT tier, content FROM beliefs WHERE id = ?", (a_id,))
        self.assertEqual(row_a["tier"], 5)
        self.assertEqual(row_a["content"], _A_CONTENT)


class TestIneligibleBasisSkipped(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        os.environ[_FLAG] = "1"

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_paused_belief_skipped_left_for_sweep(self):
        """If a side is no longer eligible, this is sweep_resolved_tensions'
        job, not retry_bridge_for_tensions' -- must not crash, resolve, or
        otherwise act on it."""
        a_id = _seed_belief(self.writers, _A_CONTENT, paused=1)
        b_id = _seed_belief(self.writers, _B_CONTENT)
        tension_id = _seed_tension(self.writers, a_id, b_id)
        _seed_belief(self.writers, _BRIDGE_CONTENT)  # a bridge exists, but shouldn't be used

        h = _make_harmonizer(self.writers, self.readers)
        bridged = h.retry_bridge_for_tensions()
        self.assertEqual(bridged, 0)

        tension = self.readers["dynamic"].read_one(
            "SELECT resolved_at FROM held_tensions WHERE id = ?", (tension_id,))
        self.assertIsNone(tension["resolved_at"])


class TestAlreadyResolvedTensionsIgnored(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        os.environ[_FLAG] = "1"

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_already_resolved_tension_not_reprocessed(self):
        a_id = _seed_belief(self.writers, _A_CONTENT)
        b_id = _seed_belief(self.writers, _B_CONTENT)
        self.writers["dynamic"].write(
            "INSERT INTO held_tensions (belief_id_a, belief_id_b, created_at, "
            "resolved_at, resolved_reason) VALUES (?, ?, ?, ?, 'stale_retention')",
            (a_id, b_id, time.time() - 1000, time.time()),
        )
        _seed_belief(self.writers, _BRIDGE_CONTENT)

        h = _make_harmonizer(self.writers, self.readers)
        bridged = h.retry_bridge_for_tensions()
        self.assertEqual(bridged, 0)

        row_a = self.readers["beliefs"].read_one(
            "SELECT tier FROM beliefs WHERE id = ?", (a_id,))
        self.assertEqual(row_a["tier"], 5)  # untouched -- already-closed tension, not re-opened


class TestDecayWiresSweepThenRetry(unittest.TestCase):
    """Harmonizer.decay() isn't reachable from the live process (verified by
    grep, see its own docstring) -- this proves the two Phase D pieces are
    wired together correctly for whenever a future, separately-decided call
    site invokes it."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        os.environ[_FLAG] = "1"

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_decay_sweeps_stale_and_bridges_findable_in_one_pass(self):
        _clear_keystone_noise(self.writers)
        # Tension 1: stale -- should be swept, not searched for a bridge.
        a1 = _seed_belief(self.writers, "Stale topic one")
        b1 = _seed_belief(self.writers, "Stale topic two")
        t1 = _seed_tension(self.writers, a1, b1, days_ago=31.0)

        # Tension 2: bridgeable -- should be resolved via retry_bridge.
        a2 = _seed_belief(self.writers, _A_CONTENT)
        b2 = _seed_belief(self.writers, _B_CONTENT)
        t2 = _seed_tension(self.writers, a2, b2)
        _seed_belief(self.writers, _BRIDGE_CONTENT)

        h = _make_harmonizer(self.writers, self.readers)
        h.decay(now=time.time())

        t1_row = self.readers["dynamic"].read_one(
            "SELECT resolved_reason FROM held_tensions WHERE id = ?", (t1,))
        t2_row = self.readers["dynamic"].read_one(
            "SELECT resolved_reason FROM held_tensions WHERE id = ?", (t2,))
        self.assertEqual(t1_row["resolved_reason"], "stale_retention")
        self.assertEqual(t2_row["resolved_reason"], "bridge_found")


if __name__ == "__main__":
    unittest.main()
