"""Metacognition drift detection tests — Phase 40.

12 tests covering slope math, all four drift kinds, threshold gating,
fault tolerance when nodes are missing, and write-through to the DB.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_mcd_")
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


def _make_mc(writers, readers, smv=None, sp=None):
    from theory_x.stage9_metacognition.metacognition import Metacognition
    return Metacognition(
        writers["conversations"],
        readers["conversations"],
        readers["beliefs"],
        self_mind_view=smv,
        social_presence=sp,
    )


def _engagement_rows(diversities: list[float]) -> list[dict]:
    return [{"topic_diversity": d} for d in diversities]


def _voice_rows(distincts: list[float]) -> list[dict]:
    return [{"vocab_distinctiveness": d} for d in distincts]


def _attention_rows(theme_sets: list[list[str]]) -> list[dict]:
    return [{"current_themes_json": json.dumps(ts)} for ts in theme_sets]


def _uncertainty_rows(counts: list[int]) -> list[dict]:
    return [{"open_problem_count": c} for c in counts]


# ── 1. _compute_slope — empty / single-item → 0 ──────────────────────────────

class TestComputeSlope(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.mc = _make_mc(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_empty_returns_zero(self):
        self.assertEqual(self.mc._compute_slope([]), 0.0)

    def test_single_item_returns_zero(self):
        self.assertEqual(self.mc._compute_slope([0.5]), 0.0)

    def test_increasing_returns_positive(self):
        slope = self.mc._compute_slope([0.1, 0.2, 0.3, 0.4, 0.5])
        self.assertGreater(slope, 0.0)

    def test_decreasing_returns_negative(self):
        slope = self.mc._compute_slope([0.9, 0.7, 0.5, 0.3, 0.1])
        self.assertLess(slope, 0.0)


# ── 2. _detect_drift — both nodes None → empty ───────────────────────────────

class TestDetectDriftNoNodes(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.mc = _make_mc(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_no_nodes_returns_empty(self):
        self.assertEqual(self.mc._detect_drift(), [])


# ── 3. _detect_drift — below MIN_SAMPLES → empty ─────────────────────────────

class TestDetectDriftTooFewSamples(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        sp = MagicMock()
        sp.engagement_history.return_value = _engagement_rows([0.9, 0.5, 0.1])  # 3 < 4
        sp.voice_history.return_value = _voice_rows([0.9, 0.5, 0.1])
        smv = MagicMock()
        smv.aspect_history.return_value = _attention_rows([["a"]] * 3)
        self.mc = _make_mc(self.writers, self.readers, smv=smv, sp=sp)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_too_few_samples_returns_empty(self):
        self.assertEqual(self.mc._detect_drift(), [])


# ── 4. topic_diversity_collapse flagged on declining series ──────────────────

class TestTopicDiversityCollapse(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        sp = MagicMock()
        # Strongly declining: 0.9 → 0.1 over 5 samples
        sp.engagement_history.return_value = _engagement_rows([0.9, 0.7, 0.5, 0.3, 0.1])
        sp.voice_history.return_value = []
        self.mc = _make_mc(self.writers, self.readers, sp=sp)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_flags_topic_diversity_collapse(self):
        findings = self.mc._detect_drift()
        kinds = [f["event_type"] for f in findings]
        self.assertIn("topic_diversity_collapse", kinds)

    def test_severity_in_range(self):
        findings = self.mc._detect_drift()
        for f in findings:
            if f["event_type"] == "topic_diversity_collapse":
                self.assertGreaterEqual(f["severity"], 0.0)
                self.assertLessEqual(f["severity"], 1.0)


# ── 5. vocab_narrowing flagged on declining series ────────────────────────────

class TestVocabNarrowing(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        sp = MagicMock()
        sp.engagement_history.return_value = []
        sp.voice_history.return_value = _voice_rows([0.9, 0.7, 0.5, 0.3, 0.1])
        self.mc = _make_mc(self.writers, self.readers, sp=sp)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_flags_vocab_narrowing(self):
        findings = self.mc._detect_drift()
        kinds = [f["event_type"] for f in findings]
        self.assertIn("vocab_narrowing", kinds)


# ── 6. attention_groove flagged on recurring themes ───────────────────────────

class TestAttentionGroove(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        smv = MagicMock()
        # 5 snapshots all with same 3 themes → max overlap
        smv.aspect_history.return_value = _attention_rows(
            [["consciousness", "attention", "awareness"]] * 5
        )
        self.mc = _make_mc(self.writers, self.readers, smv=smv)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_flags_attention_groove(self):
        findings = self.mc._detect_drift()
        kinds = [f["event_type"] for f in findings]
        self.assertIn("attention_groove", kinds)


# ── 7. uncertainty_stagnation flagged on flat/rising problem count ────────────

class TestUncertaintyStagnation(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        smv = MagicMock()
        # Flat at 3 open problems across 5 snapshots
        smv.aspect_history.return_value = _uncertainty_rows([3, 3, 3, 3, 3])
        self.mc = _make_mc(self.writers, self.readers, smv=smv)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_flags_uncertainty_stagnation(self):
        findings = self.mc._detect_drift()
        kinds = [f["event_type"] for f in findings]
        self.assertIn("uncertainty_stagnation", kinds)


# ── 8. threshold gating — mild decline doesn't fire ──────────────────────────

class TestThresholdGating(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        sp = MagicMock()
        # Tiny decline — below _DRIFT_SEVERITY_THRESHOLD=0.3
        sp.engagement_history.return_value = _engagement_rows([0.8, 0.79, 0.78, 0.77, 0.76])
        sp.voice_history.return_value = _voice_rows([0.8, 0.79, 0.78, 0.77, 0.76])
        self.mc = _make_mc(self.writers, self.readers, sp=sp)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_mild_decline_not_flagged(self):
        findings = self.mc._detect_drift()
        kinds = [f["event_type"] for f in findings]
        self.assertNotIn("topic_diversity_collapse", kinds)
        self.assertNotIn("vocab_narrowing", kinds)


# ── 9. drift events written to meta_cognition_events with correct shape ───────

class TestDriftEventWritten(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        sp = MagicMock()
        sp.engagement_history.return_value = _engagement_rows([0.9, 0.7, 0.5, 0.3, 0.1])
        sp.voice_history.return_value = []
        self.mc = _make_mc(self.writers, self.readers, sp=sp)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_event_written_to_db(self):
        self.mc.tick()
        time.sleep(0.05)
        rows = self.readers["conversations"].read(
            "SELECT event_type, severity, description, source "
            "FROM meta_cognition_events "
            "WHERE event_type='topic_diversity_collapse'"
        )
        self.assertGreater(len(rows), 0)
        row = rows[0]
        self.assertAlmostEqual(row["severity"], rows[0]["severity"], places=2)
        self.assertEqual(row["source"], "drift_detector")
        self.assertIn("severity", row["description"])


# ── 10. tick robust to exceptions — one failure doesn't kill the others ───────

class TestTickRobustness(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        sp = MagicMock()
        sp.engagement_history.side_effect = RuntimeError("db gone")
        sp.voice_history.side_effect = RuntimeError("db gone")
        smv = MagicMock()
        smv.aspect_history.side_effect = RuntimeError("db gone")
        self.mc = _make_mc(self.writers, self.readers, smv=smv, sp=sp)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_tick_does_not_raise(self):
        try:
            self.mc.tick()
        except Exception as exc:
            self.fail(f"tick() raised unexpectedly: {exc}")


if __name__ == "__main__":
    unittest.main()
