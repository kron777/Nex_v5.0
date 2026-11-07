"""SENTIENCE_PROGRAM Phase D — held tension instead of deletion
(`NEX5_HELD_TENSION`).

Dark by default. Covers:
- flag OFF: resolve() byte-identical to before (synthesized/both_deleted,
  tier 8, '[RETIRED]' prefix) -- already proven by the untouched
  test_harmonizer_fixes.py/test_world_model.py suites; this file adds the
  flag-ON behaviour and the cap/retention/surfacing machinery those don't
  cover.
- flag ON: both beliefs survive at their original tier, unpaused, content
  unchanged; a held_tensions row is written; harmonizer_events gets a
  'held_tension' resolution.
- cap: beyond _TENSION_CAP open tensions, a new escalation falls back to
  the original retire/synthesize path rather than growing unbounded.
- sweep_resolved_tensions(): closes a tension whose basis left the pool
  (one side promoted/retired elsewhere) or that aged past the stale-
  retention window, each with the right resolved_reason -- the spec's
  required "a resolution path clears them" proof.
- format_for_prompt(): with the flag on and an open tension, surfaces the
  actual belief contents ("I notice I hold both...") instead of the
  pre-existing generic count line; falls through to that generic line
  unchanged when the flag is on but no tension is open yet, and when the
  flag is off (already covered by test_harmonizer_fixes.py).
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from tests._bootstrap import *  # noqa: F401, F403

_FLAG = "NEX5_HELD_TENSION"


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_tension_")
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


def _make_harmonizer(writers, readers):
    from theory_x.stage3_world_model.promotion import BeliefPromoter
    from theory_x.stage3_world_model.harmonizer import Harmonizer
    p = BeliefPromoter(writers["beliefs"], readers["beliefs"])
    return Harmonizer(
        beliefs_writer=writers["beliefs"], beliefs_reader=readers["beliefs"],
        dynamic_writer=writers["dynamic"], dynamic_reader=readers["dynamic"],
        promoter=p,
    )


class TestFlagOnHoldsTension(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        os.environ[_FLAG] = "1"

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_both_beliefs_survive_unpaused_unchanged(self):
        h = _make_harmonizer(self.writers, self.readers)
        a_id = _seed_belief(self.writers, "Markets trend upward over decades")
        b_id = _seed_belief(self.writers, "Markets do not trend upward over decades")
        result = h.resolve(a_id, b_id)
        self.assertEqual(result, "held_tension")
        row_a = self.readers["beliefs"].read_one("SELECT * FROM beliefs WHERE id=?", (a_id,))
        row_b = self.readers["beliefs"].read_one("SELECT * FROM beliefs WHERE id=?", (b_id,))
        self.assertEqual(row_a["tier"], 5)
        self.assertEqual(row_b["tier"], 5)
        self.assertEqual(row_a["paused"], 0)
        self.assertEqual(row_b["paused"], 0)
        self.assertNotIn("[RETIRED]", row_a["content"])
        self.assertEqual(row_a["content"], "Markets trend upward over decades")

    def test_held_tensions_row_written(self):
        h = _make_harmonizer(self.writers, self.readers)
        a_id = _seed_belief(self.writers, "Markets trend upward over decades")
        b_id = _seed_belief(self.writers, "Markets do not trend upward over decades")
        h.resolve(a_id, b_id)
        row = self.readers["dynamic"].read_one(
            "SELECT * FROM held_tensions WHERE belief_id_a=? OR belief_id_a=?",
            (min(a_id, b_id), min(a_id, b_id)),
        )
        self.assertIsNotNone(row)
        self.assertIsNone(row["resolved_at"])

    def test_harmonizer_events_gets_held_tension_resolution(self):
        h = _make_harmonizer(self.writers, self.readers)
        a_id = _seed_belief(self.writers, "Markets trend upward over decades")
        b_id = _seed_belief(self.writers, "Markets do not trend upward over decades")
        h.resolve(a_id, b_id)
        row = self.readers["dynamic"].read_one(
            "SELECT resolution FROM harmonizer_events WHERE resolution='held_tension' "
            "AND belief_id_a=? AND belief_id_b=?", (a_id, b_id),
        )
        self.assertIsNotNone(row)

    def test_full_escalation_via_run_scan_and_resolve_holds_not_retires(self):
        """End-to-end through the normal escalation path, flag on."""
        from theory_x.stage3_world_model.harmonizer import PARADOX_INCUBATION_SECONDS
        h = _make_harmonizer(self.writers, self.readers)
        a_id = _seed_belief(self.writers, "Markets trend upward over decades")
        b_id = _seed_belief(self.writers, "Markets do not trend upward over decades")
        old_ts = time.time() - PARADOX_INCUBATION_SECONDS - 60
        self.writers["dynamic"].write(
            "INSERT INTO harmonizer_events (ts, belief_id_a, belief_id_b, resolution) "
            "VALUES (?, ?, ?, 'paradox')", (old_ts, a_id, b_id),
        )
        h.run_scan_and_resolve()
        row_a = self.readers["beliefs"].read_one("SELECT tier FROM beliefs WHERE id=?", (a_id,))
        self.assertEqual(row_a["tier"], 5, "must not be retired when held-tension is armed")


class TestCap(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        os.environ[_FLAG] = "1"

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_beyond_cap_falls_back_to_retire_both(self):
        from theory_x.stage3_world_model import harmonizer as hmod
        h = _make_harmonizer(self.writers, self.readers)
        with mock.patch.object(hmod, "_TENSION_CAP", 0):
            a_id = _seed_belief(self.writers, "Markets trend upward over decades")
            b_id = _seed_belief(self.writers, "Markets do not trend upward over decades")
            result = h.resolve(a_id, b_id)
        self.assertEqual(result, "both_deleted")
        row_a = self.readers["beliefs"].read_one("SELECT tier FROM beliefs WHERE id=?", (a_id,))
        self.assertEqual(row_a["tier"], 8, "cap-exceeded pair must still reach an outcome")

    def test_cap_not_exceeded_holds_normally(self):
        from theory_x.stage3_world_model import harmonizer as hmod
        h = _make_harmonizer(self.writers, self.readers)
        with mock.patch.object(hmod, "_TENSION_CAP", 5):
            a_id = _seed_belief(self.writers, "Markets trend upward over decades")
            b_id = _seed_belief(self.writers, "Markets do not trend upward over decades")
            result = h.resolve(a_id, b_id)
        self.assertEqual(result, "held_tension")


class TestSweepResolvedTensions(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        os.environ[_FLAG] = "1"

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_belief_left_pool_resolves_tension(self):
        h = _make_harmonizer(self.writers, self.readers)
        a_id = _seed_belief(self.writers, "Markets trend upward over decades")
        b_id = _seed_belief(self.writers, "Markets do not trend upward over decades")
        h.resolve(a_id, b_id)
        # One side promoted to a locked keystone by some OTHER path.
        self.writers["beliefs"].write("UPDATE beliefs SET tier=1, locked=1 WHERE id=?", (a_id,))
        resolved = h.sweep_resolved_tensions()
        self.assertEqual(resolved, 1)
        row = self.readers["dynamic"].read_one(
            "SELECT resolved_reason FROM held_tensions WHERE resolved_at IS NOT NULL")
        self.assertEqual(row["resolved_reason"], "belief_left_pool")

    def test_stale_retention_resolves_tension(self):
        from theory_x.stage3_world_model import harmonizer as hmod
        h = _make_harmonizer(self.writers, self.readers)
        a_id = _seed_belief(self.writers, "Markets trend upward over decades")
        b_id = _seed_belief(self.writers, "Markets do not trend upward over decades")
        h.resolve(a_id, b_id)
        old_ts = time.time() - (hmod._TENSION_STALE_DAYS + 1) * 86400
        self.writers["dynamic"].write(
            "UPDATE held_tensions SET created_at=? WHERE belief_id_a=? OR belief_id_a=?",
            (old_ts, min(a_id, b_id), min(a_id, b_id)),
        )
        resolved = h.sweep_resolved_tensions()
        self.assertEqual(resolved, 1)
        row = self.readers["dynamic"].read_one(
            "SELECT resolved_reason FROM held_tensions WHERE resolved_at IS NOT NULL")
        self.assertEqual(row["resolved_reason"], "stale_retention")

    def test_fresh_eligible_tension_not_resolved(self):
        h = _make_harmonizer(self.writers, self.readers)
        a_id = _seed_belief(self.writers, "Markets trend upward over decades")
        b_id = _seed_belief(self.writers, "Markets do not trend upward over decades")
        h.resolve(a_id, b_id)
        resolved = h.sweep_resolved_tensions()
        self.assertEqual(resolved, 0)

    def test_decay_calls_the_sweep_without_raising(self):
        h = _make_harmonizer(self.writers, self.readers)
        a_id = _seed_belief(self.writers, "Markets trend upward over decades")
        b_id = _seed_belief(self.writers, "Markets do not trend upward over decades")
        h.resolve(a_id, b_id)
        self.writers["beliefs"].write("UPDATE beliefs SET tier=1, locked=1 WHERE id=?", (a_id,))
        h.decay(now=time.time())  # must not raise
        row = self.readers["dynamic"].read_one(
            "SELECT COUNT(*) AS n FROM held_tensions WHERE resolved_at IS NOT NULL")
        self.assertEqual(row["n"], 1)


class TestFormatForPromptSurfacing(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_flag_on_surfaces_content_specific_line(self):
        os.environ[_FLAG] = "1"
        h = _make_harmonizer(self.writers, self.readers)
        a_id = _seed_belief(self.writers, "Markets trend upward over the long run")
        b_id = _seed_belief(self.writers, "Markets do not trend upward over the long run")
        h.resolve(a_id, b_id)
        text = h.format_for_prompt()
        self.assertIn("I notice I hold both", text)
        self.assertIn("Markets trend upward", text)

    def test_flag_on_no_open_tension_falls_through_to_generic(self):
        """Flag on, but nothing held yet -- must behave like the pre-existing
        generic path (quiet when no paradox events either)."""
        os.environ[_FLAG] = "1"
        h = _make_harmonizer(self.writers, self.readers)
        h.tick()
        self.assertEqual(h.format_for_prompt(), "")

    def test_flag_off_generic_path_unaffected(self):
        os.environ.pop(_FLAG, None)
        h = _make_harmonizer(self.writers, self.readers)
        a_id = _seed_belief(self.writers, "Order emerges from complexity and system design")
        b_id = _seed_belief(self.writers, "Order does not emerge from complexity alone")
        h.mark_paradox(a_id, b_id)
        h.tick()
        text = h.format_for_prompt()
        self.assertIn("tension", text.lower())
        self.assertNotIn("I notice I hold both", text)


if __name__ == "__main__":
    unittest.main()
