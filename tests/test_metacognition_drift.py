"""Metacognition drift detection tests — Phase 40 + Phase 41.

Phase 40 (14 tests): slope math, four drift kinds, threshold gating,
fault tolerance, write-through to DB.

Phase 41 (8 tests): three value-drift signals — distance growth,
contradiction rate increase, abandonment / keystone-token overlap.
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


# ── Phase 41 value-drift tests ────────────────────────────────────────────────

import numpy as np
from unittest.mock import patch


import uuid as _uuid


def _seed_keystones(writers, n=5, tag=""):
    """Seed locked tier-1 beliefs as keystones."""
    import time as _t
    now = int(_t.time())
    uid = _uuid.uuid4().hex[:8]
    for i in range(n):
        writers["beliefs"].write(
            "INSERT OR IGNORE INTO beliefs (content, tier, confidence, source, "
            "created_at, tags, locked) VALUES (?, 1, 0.99, 'spectrum', ?, '[]', 1)",
            (f"attend {uid} wonder awareness presence existence {i} {tag}.", now - i * 10),
        )
    _t.sleep(0.05)


def _seed_recent_beliefs(writers, contents: list[str]):
    import time as _t
    now = int(_t.time())
    uid = _uuid.uuid4().hex[:8]
    for i, c in enumerate(contents):
        writers["beliefs"].write(
            "INSERT OR IGNORE INTO beliefs (content, tier, confidence, source, "
            "created_at, tags) VALUES (?, 7, 0.5, 'fountain_insight', ?, '[]')",
            (f"{c} {uid}{i}", now - i * 5),
        )
    _t.sleep(0.05)


def _seed_gate_decisions(writers, prior_count: int, recent_count: int):
    """Seed gate_decisions with anchor-contradiction rejects in two windows."""
    import time as _t
    now = _t.time()
    mid = now - 1800  # 30-min split

    def _seed_block(start_ts: float, count: int):
        for i in range(count):
            ts = start_ts - i * 0.1
            writers["beliefs"].write(
                "INSERT INTO gate_decisions "
                "(ts, source_node, outcome, reason, latency_ms, content_preview) "
                "VALUES (?, 'test_node', 'REJECT', "
                "'contradicts_anchor:locked_id_1', 0.0, 'test')",
                (ts,),
            )

    _seed_block(mid - 1, prior_count)     # prior window  (>start, <=mid)
    _seed_block(now - 1, recent_count)    # recent window (>mid, <=now)
    _t.sleep(0.05)


# ── 11. value_drift_distance fires when distance grows ────────────────────────

class TestValueDriftDistance(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        _seed_keystones(self.writers, n=3)
        # Recent beliefs with far-from-keystone content
        _seed_recent_beliefs(self.writers, [
            f"unrelated cryptocurrency market price action {i}" for i in range(10)
        ])

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _make_mc_with_distance_history(self, old_dist, new_dist):
        """MC pre-seeded so the distance increase triggers the threshold."""
        from theory_x.stage9_metacognition.metacognition import Metacognition, _VALUE_DRIFT_DISTANCE_DEQUE_LEN
        mc = Metacognition(
            self.writers["conversations"],
            self.readers["conversations"],
            self.readers["beliefs"],
        )
        # Pre-populate history so increase is detectable
        mc._distance_history.append(old_dist)
        # Pre-load keystone cache with a simple unit vector matrix
        mc._keystone_matrix = np.eye(384, dtype=np.float32)[:3]
        mc._keystone_tokens = frozenset(["wonder", "awareness", "presence"])
        return mc

    def test_distance_fires_when_distance_grows(self):
        from theory_x.stage9_metacognition.metacognition import _VALUE_DRIFT_DISTANCE_INCREASE
        mc = self._make_mc_with_distance_history(0.1, None)
        # Patch embed_belief to return a vector far from the keystone matrix
        far_vec = np.zeros(384, dtype=np.float32)
        far_vec[383] = 1.0  # orthogonal to eye[:3] rows

        with patch("theory_x.stage9_metacognition.metacognition.embed_belief",
                   return_value=far_vec):
            findings = mc._detect_value_drift()
        kinds = [f["event_type"] for f in findings]
        self.assertIn("value_drift_distance", kinds)

    def test_distance_stable_no_fire(self):
        mc = self._make_mc_with_distance_history(0.5, None)
        # Patch embed to return a vector identical to a keystone (distance ≈ 0)
        near_vec = np.eye(384, dtype=np.float32)[0]  # same as first keystone row

        with patch("theory_x.stage9_metacognition.metacognition.embed_belief",
                   return_value=near_vec):
            findings = mc._detect_value_drift()
        kinds = [f["event_type"] for f in findings]
        self.assertNotIn("value_drift_distance", kinds)


# ── 12. value_drift_contradiction fires on rate increase ──────────────────────

class TestValueDriftContradiction(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_contradiction_fires_on_rate_increase(self):
        from theory_x.stage9_metacognition.metacognition import _VALUE_DRIFT_CONTRADICTION_THRESHOLD
        # prior=threshold+1, recent=prior*2 (100% increase > 30% threshold)
        prior = _VALUE_DRIFT_CONTRADICTION_THRESHOLD + 1
        recent = prior * 2
        _seed_gate_decisions(self.writers, prior_count=prior, recent_count=recent)
        import time as _t; _t.sleep(0.1)

        from theory_x.stage9_metacognition.metacognition import Metacognition
        mc = Metacognition(
            self.writers["conversations"],
            self.readers["conversations"],
            self.readers["beliefs"],
        )
        mc._keystone_matrix = np.eye(384, dtype=np.float32)[:1]
        mc._keystone_tokens = frozenset(["test"])
        findings = mc._detect_value_drift()
        kinds = [f["event_type"] for f in findings]
        self.assertIn("value_drift_contradiction", kinds)

    def test_contradiction_no_fire_below_threshold(self):
        from theory_x.stage9_metacognition.metacognition import (
            Metacognition, _VALUE_DRIFT_CONTRADICTION_THRESHOLD
        )
        # prior below minimum floor → signal suppressed
        _seed_gate_decisions(self.writers, prior_count=2, recent_count=10)
        import time as _t; _t.sleep(0.1)

        mc = Metacognition(
            self.writers["conversations"],
            self.readers["conversations"],
            self.readers["beliefs"],
        )
        mc._keystone_matrix = np.eye(384, dtype=np.float32)[:1]
        mc._keystone_tokens = frozenset(["test"])
        findings = mc._detect_value_drift()
        kinds = [f["event_type"] for f in findings]
        self.assertNotIn("value_drift_contradiction", kinds)


# ── 13. value_drift_abandonment fires on low keystone-token overlap ───────────

class TestValueDriftAbandonment(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _make_mc_with_keystone_tokens(self, tokens: frozenset):
        from theory_x.stage9_metacognition.metacognition import Metacognition
        mc = Metacognition(
            self.writers["conversations"],
            self.readers["conversations"],
            self.readers["beliefs"],
        )
        mc._keystone_matrix = np.eye(384, dtype=np.float32)[:1]
        mc._keystone_tokens = tokens
        return mc

    def test_abandonment_fires_when_overlap_low(self):
        from theory_x.stage9_metacognition.metacognition import _VALUE_DRIFT_ABANDONMENT_OVERLAP_MAX
        # init_all seeds 76 tier=1 locked=1 beliefs whose content contains keystone
        # words like "wonder", "attend", "immutable". Delete ALL beliefs so the
        # recent-belief window only contains our unrelated seeds. _load_keystone_cache
        # exits early (mc._keystone_matrix is pre-set) so no reload from empty DB.
        self.writers["beliefs"].write("DELETE FROM beliefs")
        import time as _t; _t.sleep(0.05)
        # Seed only content guaranteed absent of any keystone-token vocabulary
        _seed_recent_beliefs(self.writers, [
            "cryptocurrency market price action trading volume" for _ in range(5)
        ])
        keystone_tokens = frozenset(["wonder", "awareness", "presence", "attend",
                                      "vantage", "membrane", "compress", "immutable"])
        mc = self._make_mc_with_keystone_tokens(keystone_tokens)
        findings = mc._detect_value_drift()
        kinds = [f["event_type"] for f in findings]
        self.assertIn("value_drift_abandonment", kinds)

    def test_abandonment_no_fire_when_overlap_healthy(self):
        # Recent beliefs full of keystone words → overlap high
        _seed_recent_beliefs(self.writers, [
            "wonder awareness presence attend vantage membrane compress" for _ in range(5)
        ])
        keystone_tokens = frozenset(["wonder", "awareness", "presence", "attend",
                                      "vantage", "membrane", "compress", "immutable"])
        mc = self._make_mc_with_keystone_tokens(keystone_tokens)
        findings = mc._detect_value_drift()
        kinds = [f["event_type"] for f in findings]
        self.assertNotIn("value_drift_abandonment", kinds)


# ── 14. All three signals robust when keystones empty ─────────────────────────

class TestValueDriftEmptyKeystones(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        # No keystones seeded — beliefs table has no tier=1 locked rows
        from substrate.init_db import init_all
        init_all()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_no_keystones_returns_empty(self):
        from theory_x.stage9_metacognition.metacognition import Metacognition
        mc = Metacognition(
            self.writers["conversations"],
            self.readers["conversations"],
            self.readers["beliefs"],
        )
        # Load cache — will find 76+ keystones from init_all seeds,
        # so test that even if we force-clear it with empty matrix, no crash
        mc._keystone_matrix = np.zeros((0, 384), dtype=np.float32)
        mc._keystone_tokens = frozenset()
        try:
            findings = mc._detect_value_drift()
        except Exception as exc:
            self.fail(f"_detect_value_drift raised with empty keystones: {exc}")
        # distance and abandonment should not fire with zero keystones
        kinds = [f["event_type"] for f in findings]
        self.assertNotIn("value_drift_distance", kinds)
        self.assertNotIn("value_drift_abandonment", kinds)


# ── 15. format_for_prompt covers each new event type ─────────────────────────

class TestValueDriftFormatForPrompt(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _prompt_for_type(self, etype: str) -> str:
        from theory_x.stage9_metacognition.metacognition import Metacognition
        mc = Metacognition(
            self.writers["conversations"],
            self.readers["conversations"],
            self.readers["beliefs"],
        )
        mc._cached_recent = [{"event_type": etype}]
        return mc.format_for_prompt()

    def test_format_value_drift_distance(self):
        result = self._prompt_for_type("value_drift_distance")
        self.assertIn("deepest beliefs", result)

    def test_format_value_drift_contradiction(self):
        result = self._prompt_for_type("value_drift_contradiction")
        self.assertIn("anchors", result)

    def test_format_value_drift_abandonment(self):
        result = self._prompt_for_type("value_drift_abandonment")
        self.assertIn("deepest beliefs", result)


if __name__ == "__main__":
    unittest.main()
