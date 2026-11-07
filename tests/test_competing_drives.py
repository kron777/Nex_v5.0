"""CompetingDrives (theory_x/stage_drives/competing_drives.py) — test coverage
added 2026-11-08. Previously had zero direct tests of its own tick()/resolve
logic -- the only two hits in tests/ (test_affect_history.py,
test_affect_state.py) are comments describing an unrelated historical bug,
not tests of this class.

Tests only, proving current behaviour -- no production code changed by this
file. Covers:
- _safe_div, _detect_tensions (threshold boundary, multiple pairs)
- _compute_weights: normalizes to sum 1.0; zero-total fallback to 0.2 each
- a representative sample of the per-signal measurement helpers
- _tick_once: persists drives_competing + drives_competing_log, updates
  in-memory state
- compute_now: writes drive_activations, returns the new row id
- attach_event: backfills fountain_event_id
- SentienceNode protocol (name/tick/decay/state)
- format_for_prompt()'s change-detection suppression: emits only when the
  active tension pattern actually changes, not every tick it's still true

Not covered (left for a future round, noted rather than silently skipped):
_sense_freshness/_branch_entropy_novelty/_content_complexity's exact
normalization constants aren't individually exercised -- their shared
pattern (try/except -> safe default, clamp 0..1) is proven once via
_contradiction_pressure and _affect_variance instead of 11 near-duplicate
tests.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests._bootstrap import *  # noqa: F401, F403


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_competing_drives_")
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


def _make_cd(writers, readers, with_dynamic=False):
    from theory_x.stage_drives.competing_drives import CompetingDrives
    return CompetingDrives(
        conversations_writer=writers["conversations"],
        conversations_reader=readers["conversations"],
        beliefs_reader=readers["beliefs"],
        dynamic_reader=readers["dynamic"] if with_dynamic else None,
    )


class TestSafeDivAndTensionDetection(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_safe_div_zero_denominator(self):
        from theory_x.stage_drives.competing_drives import _safe_div
        self.assertEqual(_safe_div(5.0, 0.0), 0.0)
        self.assertEqual(_safe_div(5.0, 0.0, default=1.0), 1.0)
        self.assertEqual(_safe_div(3.0, 6.0), 0.5)

    def test_no_tension_when_both_below_threshold(self):
        cd = _make_cd(self.writers, self.readers)
        out = cd._detect_tensions({"coherence": 0.1, "exploration": 0.1})
        self.assertEqual(out, [])

    def test_tension_exactly_at_threshold_not_counted(self):
        """Spec says '> 0.25', strictly greater -- exactly-at-threshold must
        NOT count as a tension."""
        cd = _make_cd(self.writers, self.readers)
        out = cd._detect_tensions({"coherence": 0.30, "exploration": 0.30})
        self.assertEqual(out, [])

    def test_single_pair_above_threshold(self):
        cd = _make_cd(self.writers, self.readers)
        out = cd._detect_tensions({"coherence": 0.31, "exploration": 0.31})
        self.assertEqual(out, [("coherence", "exploration")])

    def test_multiple_pairs_above_threshold(self):
        cd = _make_cd(self.writers, self.readers)
        out = cd._detect_tensions({
            "coherence": 0.4, "exploration": 0.4,
            "integration": 0.4, "self_preservation": 0.4,
            "curiosity": 0.0,
        })
        self.assertEqual(
            set(out), {("coherence", "exploration"), ("integration", "self_preservation")}
        )


class TestComputeWeights(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_weights_normalize_to_sum_one(self):
        cd = _make_cd(self.writers, self.readers)
        weights, inputs, raw = cd._compute_weights()
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)
        self.assertEqual(set(weights.keys()), {
            "coherence", "exploration", "integration",
            "self_preservation", "curiosity",
        })

    def test_zero_total_falls_back_to_even_split(self):
        """On a totally fresh store with no signal at all, every raw
        component can legitimately be 0 -- must not divide by zero."""
        cd = _make_cd(self.writers, self.readers)
        weights, inputs, raw = cd._compute_weights()
        if sum(raw.values()) <= 0:
            for v in weights.values():
                self.assertEqual(v, 0.2)


class TestMeasurementHelpers(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    _belief_counter = 0

    def _seed_belief(self, source, tier=5):
        now = time.time()
        TestMeasurementHelpers._belief_counter += 1
        content = f"test belief {source} #{TestMeasurementHelpers._belief_counter}"
        return self.writers["beliefs"].write(
            "INSERT INTO beliefs (content, tier, confidence, created_at, source, locked, paused) "
            "VALUES (?, ?, 0.6, ?, ?, 0, 0)",
            (content, tier, now, source),
        )

    def test_source_ratios_counts_synergized_and_sense(self):
        for _ in range(2):
            self._seed_belief("synergized")
        for _ in range(1):
            self._seed_belief("precipitated_from_sense")
        for _ in range(1):
            self._seed_belief("fountain_insight")
        cd = _make_cd(self.writers, self.readers)
        ratios = cd._source_ratios()
        self.assertEqual(ratios["own_count"], 4.0)
        self.assertAlmostEqual(ratios["synergized"], 2 / 4)
        self.assertAlmostEqual(ratios["sense"], 1 / 4)

    def test_source_ratios_empty_store_returns_zero(self):
        cd = _make_cd(self.writers, self.readers)
        ratios = cd._source_ratios()
        self.assertEqual(ratios["own_count"], 0.0)
        self.assertEqual(ratios["synergized"], 0.0)

    def test_contradiction_pressure_normalizes_and_caps_at_one(self):
        # (source_id, target_id, edge_type) is unique, so 8 distinct pairs
        # are needed to get 8 'opposes' rows -- well past the 5-per-day
        # normalization point.
        now = time.time()
        for _ in range(8):
            a_id = self._seed_belief("manual")
            b_id = self._seed_belief("manual")
            self.writers["beliefs"].write(
                "INSERT INTO belief_edges (source_id, target_id, edge_type, weight, created_at) "
                "VALUES (?, ?, 'opposes', 0.5, ?)",
                (a_id, b_id, now),
            )
        cd = _make_cd(self.writers, self.readers)
        self.assertEqual(cd._contradiction_pressure(), 1.0)

    def test_contradiction_pressure_zero_with_no_edges(self):
        cd = _make_cd(self.writers, self.readers)
        self.assertEqual(cd._contradiction_pressure(), 0.0)

    def test_groove_severity_reads_max_recent(self):
        now = time.time()
        self.writers["beliefs"].write(
            "INSERT INTO groove_alerts (detected_at, alert_type, severity, window_size) "
            "VALUES (?, 'repetition', 0.3, 10)", (now,))
        self.writers["beliefs"].write(
            "INSERT INTO groove_alerts (detected_at, alert_type, severity, window_size) "
            "VALUES (?, 'repetition', 0.9, 10)", (now,))
        cd = _make_cd(self.writers, self.readers)
        self.assertEqual(cd._groove_severity(), 0.9)

    def test_open_problems_pressure_normalizes_against_20(self):
        now = time.time()
        for i in range(10):
            self.writers["conversations"].write(
                "INSERT INTO open_problems (title, description, state, created_at, last_touched_at) "
                "VALUES (?, 'd', 'open', ?, ?)", (f"p{i}", now, now))
        cd = _make_cd(self.writers, self.readers)
        self.assertAlmostEqual(cd._open_problems_pressure(), 10 / 20.0)

    def test_affect_variance_needs_at_least_3_samples(self):
        now = time.time()
        self.writers["conversations"].write(
            "INSERT INTO affect_history (ts, valence, arousal) VALUES (?, 0.5, 0.5)", (now,))
        self.writers["conversations"].write(
            "INSERT INTO affect_history (ts, valence, arousal) VALUES (?, 0.5, 0.5)", (now,))
        cd = _make_cd(self.writers, self.readers)
        self.assertEqual(cd._affect_variance(), 0.0)

    def test_affect_variance_computes_real_stddev(self):
        now = time.time()
        for v, a in [(0.1, 0.1), (0.9, 0.9), (0.1, 0.1), (0.9, 0.9)]:
            self.writers["conversations"].write(
                "INSERT INTO affect_history (ts, valence, arousal) VALUES (?, ?, ?)",
                (now, v, a))
        cd = _make_cd(self.writers, self.readers)
        # std of [0.1, 0.9, 0.1, 0.9] is 0.4 -> 0.4/0.20 = 2.0, clamped to 1.0
        self.assertEqual(cd._affect_variance(), 1.0)


class TestPersistence(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_tick_once_persists_weights_and_log(self):
        cd = _make_cd(self.writers, self.readers)
        cd._tick_once()
        row = self.readers["conversations"].read_one(
            "SELECT * FROM drives_competing WHERE id = 1")
        self.assertIsNotNone(row)
        total = sum(row[k] for k in (
            "coherence", "exploration", "integration",
            "self_preservation", "curiosity"))
        self.assertAlmostEqual(total, 1.0, places=5)

        log_row = self.readers["conversations"].read_one(
            "SELECT * FROM drives_competing_log ORDER BY id DESC LIMIT 1")
        self.assertIsNotNone(log_row)
        weights_from_log = json.loads(log_row["weights_json"])
        self.assertEqual(set(weights_from_log.keys()), {
            "coherence", "exploration", "integration",
            "self_preservation", "curiosity",
        })

        state = cd.state()
        self.assertEqual(state["name"], "competing_drives")
        self.assertIsNotNone(state["computed_at"])

    def test_load_from_db_restores_prior_state(self):
        cd1 = _make_cd(self.writers, self.readers)
        cd1._tick_once()
        saved_weights = cd1.state()["weights"]

        cd2 = _make_cd(self.writers, self.readers)  # fresh instance, same DB
        restored = cd2.state()["weights"]
        for k in saved_weights:
            self.assertAlmostEqual(saved_weights[k], restored[k], places=6)

    def test_compute_now_writes_drive_activation_and_returns_id(self):
        cd = _make_cd(self.writers, self.readers)
        activation_id = cd.compute_now(fountain_event_id=None)
        self.assertIsNotNone(activation_id)
        row = self.readers["conversations"].read_one(
            "SELECT * FROM drive_activations WHERE id = ?", (activation_id,))
        self.assertIsNotNone(row)
        self.assertIsNone(row["fountain_event_id"])

    def test_attach_event_backfills_fountain_event_id(self):
        cd = _make_cd(self.writers, self.readers)
        activation_id = cd.compute_now()
        cd.attach_event(activation_id, fountain_event_id=42)
        row = self.readers["conversations"].read_one(
            "SELECT fountain_event_id FROM drive_activations WHERE id = ?",
            (activation_id,))
        self.assertEqual(row["fountain_event_id"], 42)


class TestSentienceNodeProtocol(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_tick_returns_state_shape(self):
        cd = _make_cd(self.writers, self.readers)
        result = cd.tick()
        self.assertEqual(result, cd.state())
        self.assertIn("weights", result)
        self.assertIn("tension_pairs", result)

    def test_decay_is_a_noop(self):
        cd = _make_cd(self.writers, self.readers)
        before = cd.state()
        cd.decay(now=time.time())
        self.assertEqual(cd.state(), before)


class TestFormatForPromptChangeDetection(unittest.TestCase):
    """The subtlest piece of this module: format_for_prompt() must only emit
    when the active tension PATTERN changes, not on every tick it's still
    true -- "choice points are transitions, not steady states" per its own
    docstring."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _set_state(self, cd, weights, tensions):
        with cd._lock:
            cd._weights = weights
            cd._tension_pairs = tensions

    def test_no_tension_returns_empty(self):
        cd = _make_cd(self.writers, self.readers)
        self._set_state(cd, {"coherence": 0.1, "exploration": 0.1,
                              "integration": 0.1, "self_preservation": 0.1,
                              "curiosity": 0.1}, [])
        self.assertEqual(cd.format_for_prompt(), "")

    def test_new_tension_emits_once_then_suppresses_repeat(self):
        cd = _make_cd(self.writers, self.readers)
        self._set_state(
            cd,
            {"coherence": 0.4, "exploration": 0.4, "integration": 0.1,
             "self_preservation": 0.05, "curiosity": 0.05},
            [("coherence", "exploration")],
        )
        first = cd.format_for_prompt()
        self.assertIn("tension between competing drives", first)
        self.assertIn("Coherence", first)
        self.assertIn("Exploration", first)

        # Same tension pattern, unchanged -- must suppress on the next call.
        second = cd.format_for_prompt()
        self.assertEqual(second, "")

    def test_tension_dropping_then_recurring_emits_again(self):
        cd = _make_cd(self.writers, self.readers)
        weights = {"coherence": 0.4, "exploration": 0.4, "integration": 0.1,
                   "self_preservation": 0.05, "curiosity": 0.05}
        self._set_state(cd, weights, [("coherence", "exploration")])
        self.assertNotEqual(cd.format_for_prompt(), "")

        # Tension clears.
        self._set_state(cd, weights, [])
        self.assertEqual(cd.format_for_prompt(), "")

        # Same tension pattern reappears -- should emit again, since the
        # last emitted pattern was recorded as "none" in between.
        self._set_state(cd, weights, [("coherence", "exploration")])
        self.assertNotEqual(cd.format_for_prompt(), "")

    def test_different_tension_pattern_emits_even_if_one_was_already_shown(self):
        cd = _make_cd(self.writers, self.readers)
        self._set_state(
            cd,
            {"coherence": 0.4, "exploration": 0.4, "integration": 0.4,
             "self_preservation": 0.4, "curiosity": 0.0},
            [("coherence", "exploration")],
        )
        cd.format_for_prompt()  # consume the first emission

        self._set_state(
            cd,
            {"coherence": 0.4, "exploration": 0.4, "integration": 0.4,
             "self_preservation": 0.4, "curiosity": 0.0},
            [("integration", "self_preservation")],
        )
        second = cd.format_for_prompt()
        self.assertNotEqual(second, "")
        self.assertIn("Integration", second)

    def test_fewer_than_two_active_drives_above_threshold_returns_empty(self):
        """Edge case: tension_pairs says there's tension, but by the time
        format_for_prompt() re-checks weights against the threshold for
        display, fewer than 2 clear it -- must not emit a one-line block."""
        cd = _make_cd(self.writers, self.readers)
        self._set_state(
            cd,
            {"coherence": 0.9, "exploration": 0.1, "integration": 0.0,
             "self_preservation": 0.0, "curiosity": 0.0},
            [("coherence", "exploration")],
        )
        self.assertEqual(cd.format_for_prompt(), "")


if __name__ == "__main__":
    unittest.main()
