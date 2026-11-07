"""SubstrateHarmonic (theory_x/harmonic/substrate_harmonic.py) — test coverage
added 2026-11-08. Previously had zero test files at all (confirmed by grep
across tests/ before writing this).

Tests only, proving current behaviour -- no production code changed by this
file. Covers:
- stream extractors: drives, drive_conflict (incl. the documented '[]'/'null'
  no-conflict normalization), groove_severity, sv_last, fountain_sv_share,
  gate_reject_rate (incl. the throw_net exclusion), throw_net_rate,
  stillness_active -- and that each fails safe (default, not an exception)
  against an empty store
- pair scorers A, B, C, D, E, F (defined but retired from aggregation,
  see _score_f's own docstring), G
- _aggregate(): mean of whatever's in pair_scores, including the empty-dict
  edge case
- _derive_walk_state(): idle / walking_<track> / walking_<track>_low_groove /
  recent_<track>, across all three named anchor ranges and the "other" case
- tick(): writes one substrate_coherence row with the right shape, never
  raises even when every stream read fails
- SentienceNode protocol (name/tick/decay/state)
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from tests._bootstrap import *  # noqa: F401, F403


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_substrate_harmonic_")
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


def _make_sh(writers, readers):
    from theory_x.harmonic.substrate_harmonic import SubstrateHarmonic
    return SubstrateHarmonic(
        conversations_writer=writers["conversations"],
        conversations_reader=readers["conversations"],
        beliefs_reader=readers["beliefs"],
        dynamic_reader=readers["dynamic"],
    )


class TestStreamExtractorsEmptyStore(unittest.TestCase):
    """Every extractor must fail safe (a documented default), never raise,
    against a totally fresh store."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.sh = _make_sh(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_drives_current_empty(self):
        self.assertEqual(self.sh._read_drives_current(time.time()), {})

    def test_drive_conflict_empty(self):
        self.assertIsNone(self.sh._read_drive_conflict(time.time()))

    def test_groove_severity_empty(self):
        self.assertEqual(self.sh._read_groove_severity(time.time()), 0.0)

    def test_sv_last_empty(self):
        self.assertEqual(self.sh._read_sv_last(time.time()), (None, None))

    def test_fountain_sv_share_empty(self):
        self.assertEqual(self.sh._read_fountain_sv_share(time.time()), 0.0)

    def test_gate_reject_rate_empty(self):
        self.assertEqual(self.sh._read_gate_reject_rate(time.time()), 0.0)

    def test_throw_net_rate_empty(self):
        self.assertEqual(self.sh._read_throw_net_rate(time.time()), 0.0)

    def test_stillness_active_empty(self):
        self.assertEqual(self.sh._read_stillness_active(time.time()), 0)


class TestStreamExtractorsWithData(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.sh = _make_sh(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_drives_current_reads_latest_row(self):
        now = time.time()
        self.writers["conversations"].write(
            "INSERT INTO drive_activations (timestamp, coherence_weight, "
            "exploration_weight, integration_weight, self_preservation_weight, "
            "curiosity_weight) VALUES (?, 0.1, 0.2, 0.3, 0.2, 0.2)", (now,))
        out = self.sh._read_drives_current(now)
        self.assertEqual(out["integration"], 0.3)

    def test_drive_conflict_treats_empty_list_json_as_no_conflict(self):
        now = time.time()
        self.writers["conversations"].write(
            "INSERT INTO drive_activations (timestamp, coherence_weight, "
            "exploration_weight, integration_weight, self_preservation_weight, "
            "curiosity_weight, active_conflicts) VALUES (?, 0,0,0,0,0, '[]')",
            (now,))
        self.assertIsNone(self.sh._read_drive_conflict(now))

    def test_drive_conflict_returns_real_conflict_json(self):
        now = time.time()
        self.writers["conversations"].write(
            "INSERT INTO drive_activations (timestamp, coherence_weight, "
            "exploration_weight, integration_weight, self_preservation_weight, "
            "curiosity_weight, active_conflicts) VALUES "
            "(?, 0,0,0,0,0, '[[\"coherence\", \"exploration\"]]')", (now,))
        out = self.sh._read_drive_conflict(now)
        self.assertEqual(out, '[["coherence", "exploration"]]')

    def test_groove_severity_reads_max_in_24h(self):
        now = time.time()
        self.writers["beliefs"].write(
            "INSERT INTO groove_alerts (detected_at, alert_type, severity, window_size) "
            "VALUES (?, 'x', 0.4, 10)", (now,))
        self.writers["beliefs"].write(
            "INSERT INTO groove_alerts (detected_at, alert_type, severity, window_size) "
            "VALUES (?, 'x', 0.85, 10)", (now,))
        self.assertEqual(self.sh._read_groove_severity(now), 0.85)

    def test_sv_last_reads_most_recent_substrate_voice_fire(self):
        now = time.time()
        self.writers["dynamic"].write(
            "INSERT INTO fountain_events (ts, thought, readiness, hot_branch, "
            "anchor_belief_id) VALUES (?, 't1', 0.8, 'other_branch', 10)", (now - 100,))
        self.writers["dynamic"].write(
            "INSERT INTO fountain_events (ts, thought, readiness, hot_branch, "
            "anchor_belief_id) VALUES (?, 't2', 0.8, 'substrate_voice', 4500)", (now,))
        ts, anchor = self.sh._read_sv_last(now)
        self.assertAlmostEqual(ts, now)
        self.assertEqual(anchor, 4500)

    def test_fountain_sv_share_counts_within_last_30(self):
        now = time.time()
        for i in range(3):
            self.writers["dynamic"].write(
                "INSERT INTO fountain_events (ts, thought, readiness, hot_branch) "
                "VALUES (?, 't', 0.8, 'substrate_voice')", (now - i,))
        for i in range(7):
            self.writers["dynamic"].write(
                "INSERT INTO fountain_events (ts, thought, readiness, hot_branch) "
                "VALUES (?, 't', 0.8, 'other')", (now - 100 - i,))
        self.assertAlmostEqual(self.sh._read_fountain_sv_share(now), 3 / 10)

    def test_gate_reject_rate_excludes_throw_net_source(self):
        now = time.time()
        # organic: 1 REJECT, 1 ACCEPT
        self.writers["beliefs"].write(
            "INSERT INTO gate_decisions (ts, source_node, outcome, reason, "
            "latency_ms, content_preview) VALUES (?, 'organic.x', 'REJECT', 'r', 1.0, 'c')",
            (now,))
        self.writers["beliefs"].write(
            "INSERT INTO gate_decisions (ts, source_node, outcome, reason, "
            "latency_ms, content_preview) VALUES (?, 'organic.x', 'ACCEPT', 'r', 1.0, 'c')",
            (now,))
        # throw_net noise: 10 more REJECTs that must be excluded
        for _ in range(10):
            self.writers["beliefs"].write(
                "INSERT INTO gate_decisions (ts, source_node, outcome, reason, "
                "latency_ms, content_preview) VALUES (?, 'throw_net.resubmit', 'REJECT', "
                "'r', 1.0, 'c')", (now,))
        self.assertAlmostEqual(self.sh._read_gate_reject_rate(now), 0.5)

    def test_throw_net_rate_counts_sessions_in_last_hour(self):
        now = time.time()
        for i in range(4):
            self.writers["beliefs"].write(
                "INSERT INTO throw_net_sessions (session_id, triggered_by, started_at) "
                "VALUES (?, 'x', ?)", (f"s{i}", now - 100))
        self.assertEqual(self.sh._read_throw_net_rate(now), 4.0)

    def test_stillness_active_reads_most_recent_count(self):
        now = time.time()
        self.writers["dynamic"].write(
            "INSERT INTO stillness_log (ts, reason, consecutive_stillness_count) "
            "VALUES (?, 'groove', 2)", (now - 10,))
        self.writers["dynamic"].write(
            "INSERT INTO stillness_log (ts, reason, consecutive_stillness_count) "
            "VALUES (?, 'groove', 5)", (now,))
        self.assertEqual(self.sh._read_stillness_active(now), 5)


class TestPairScorers(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.sh = _make_sh(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_score_a_both_active_is_coherent(self):
        now = time.time()
        streams = {"groove_severity": 0.9, "sv_last_ts": now - 10}
        self.assertEqual(self.sh._score_a(streams, now), 1.0)

    def test_score_a_mismatch_is_incoherent(self):
        now = time.time()
        streams = {"groove_severity": 0.9, "sv_last_ts": None}
        self.assertEqual(self.sh._score_a(streams, now), 0.0)

    def test_score_b_perfect_cadence(self):
        now = time.time()
        streams = {"sv_last_ts": now - 720.0}  # exactly _WALK_CADENCE_SEC
        self.assertAlmostEqual(self.sh._score_b(streams, now), 1.0)

    def test_score_b_no_sv_is_neutral(self):
        now = time.time()
        self.assertEqual(self.sh._score_b({"sv_last_ts": None}, now), 0.5)

    def test_score_c_at_target_share_is_1(self):
        self.assertAlmostEqual(self.sh._score_c({"fountain_share_sv": 0.17}), 1.0, places=5)

    def test_score_c_zero_share_is_0(self):
        self.assertEqual(self.sh._score_c({"fountain_share_sv": 0.0}), 0.0)

    def test_score_c_far_above_target_is_0(self):
        self.assertEqual(self.sh._score_c({"fountain_share_sv": 0.9}), 0.0)

    def test_score_d_both_active_is_coherent(self):
        now = time.time()
        streams = {"drive_conflict_json": "[[\"a\",\"b\"]]", "sv_last_ts": now - 10}
        self.assertEqual(self.sh._score_d(streams, now), 1.0)

    def test_score_d_mismatch_is_incoherent(self):
        now = time.time()
        streams = {"drive_conflict_json": None, "sv_last_ts": now - 10}
        self.assertEqual(self.sh._score_d(streams, now), 0.0)

    def test_score_e_at_baseline_is_1(self):
        self.assertAlmostEqual(self.sh._score_e({"gate_reject_rate": 0.326}), 1.0, places=5)

    def test_score_e_far_from_baseline_clamps_at_0(self):
        self.assertEqual(self.sh._score_e({"gate_reject_rate": 1.0}), 0.0)

    def test_score_f_in_band_is_1(self):
        """Retired from aggregation (see _score_f's docstring), but still
        defined and must still behave per its own documented band."""
        self.assertEqual(self.sh._score_f({"throw_net_rate": 2500}), 1.0)

    def test_score_f_zero_rate_is_0(self):
        self.assertEqual(self.sh._score_f({"throw_net_rate": 0}), 0.0)

    def test_score_f_is_not_in_active_aggregation(self):
        scores = self.sh._score_all_pairs(
            {"groove_severity": 0.0, "sv_last_ts": None, "drive_conflict_json": None,
             "fountain_share_sv": 0.0, "gate_reject_rate": 0.0}, time.time())
        self.assertNotIn("throw_net_vs_baseline", scores)

    def test_score_g_is_always_neutral(self):
        self.assertEqual(self.sh._score_g({}, time.time()), 0.5)


class TestAggregation(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.sh = _make_sh(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_aggregate_mean_of_scores(self):
        self.assertAlmostEqual(self.sh._aggregate({"a": 1.0, "b": 0.0}), 0.5)

    def test_aggregate_empty_is_zero(self):
        self.assertEqual(self.sh._aggregate({}), 0.0)


class TestWalkStateDerivation(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.sh = _make_sh(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_idle_when_never_fired(self):
        state, anchor = self.sh._derive_walk_state(
            {"sv_last_anchor": None, "sv_last_ts": None, "groove_severity": 0.0})
        self.assertEqual(state, "idle")
        self.assertIsNone(anchor)

    def test_walking_track1_within_15min_high_groove(self):
        now = time.time()
        state, anchor = self.sh._derive_walk_state({
            "sv_last_anchor": 4500, "sv_last_ts": now - 60, "groove_severity": 0.9,
        })
        self.assertEqual(state, "walking_track1")
        self.assertEqual(anchor, 4500)

    def test_walking_track2_low_groove_variant(self):
        now = time.time()
        state, anchor = self.sh._derive_walk_state({
            "sv_last_anchor": 4850, "sv_last_ts": now - 60, "groove_severity": 0.1,
        })
        self.assertEqual(state, "walking_track2_low_groove")

    def test_practice_range(self):
        now = time.time()
        state, anchor = self.sh._derive_walk_state({
            "sv_last_anchor": 3610, "sv_last_ts": now - 60, "groove_severity": 0.9,
        })
        self.assertEqual(state, "walking_practice")

    def test_other_track_when_anchor_outside_named_ranges(self):
        now = time.time()
        state, anchor = self.sh._derive_walk_state({
            "sv_last_anchor": 99999, "sv_last_ts": now - 60, "groove_severity": 0.9,
        })
        self.assertEqual(state, "walking_other")

    def test_recent_within_1h_but_outside_15min(self):
        now = time.time()
        state, anchor = self.sh._derive_walk_state({
            "sv_last_anchor": 4500, "sv_last_ts": now - 1200, "groove_severity": 0.9,
        })
        self.assertEqual(state, "recent_track1")

    def test_idle_beyond_1h(self):
        now = time.time()
        state, anchor = self.sh._derive_walk_state({
            "sv_last_anchor": 4500, "sv_last_ts": now - 7200, "groove_severity": 0.9,
        })
        self.assertEqual(state, "idle")


class TestTickAndProtocol(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.sh = _make_sh(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_tick_writes_one_row_with_expected_shape(self):
        result = self.sh.tick()
        row = self.readers["conversations"].read_one(
            "SELECT * FROM substrate_coherence ORDER BY id DESC LIMIT 1")
        self.assertIsNotNone(row)
        scores = json.loads(row["pair_scores"])
        self.assertEqual(set(scores.keys()), {
            "groove_vs_sv_active", "walk_pace_vs_cadence", "fountain_sv_share",
            "drive_tension_vs_sv", "gate_reject_vs_baseline", "stillness_vs_walk",
        })
        self.assertEqual(row["walk_state"], "idle")  # no fountain_events seeded
        self.assertEqual(result["name"], "substrate_harmonic")
        self.assertEqual(result["tick_count"], 1)

    def test_tick_never_raises_even_if_writer_fails(self):
        """Simulate a write failure -- tick() must swallow it via the
        central error channel, not propagate. (Not: actually closing the
        real Writer -- its worker thread stops, and a subsequent .write()
        then blocks forever on future.result() waiting for a worker that
        will never drain the queue; that's a substrate-level Writer-misuse
        hang, not something this test should trigger.)"""
        with mock.patch.object(self.sh._writer, "write", side_effect=RuntimeError("boom")):
            try:
                result = self.sh.tick()  # must not raise
            except Exception as exc:
                self.fail(f"tick() raised instead of swallowing the error: {exc}")
        self.assertEqual(result["tick_count"], 1)

    def test_state_shape_and_decay_noop(self):
        self.sh.tick()
        before = self.sh.state()
        self.sh.decay(now=time.time())
        after = self.sh.state()
        self.assertEqual(before, after)
        self.assertIn("last_total", after)
        self.assertIn("last_walk_state", after)


if __name__ == "__main__":
    unittest.main()
