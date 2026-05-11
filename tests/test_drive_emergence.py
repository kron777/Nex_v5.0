"""Unit tests for DriveEmergence (Phase 29, DOCTRINE §5 row 13).

14 tests per §9 of DRIVE_EMERGENCE_SPEC:
  1  - Both signals (rep + conv) → drive written
  2  - Repetition only (single branch) → no drive
  3  - Convergence only (low reinforce_count) → no drive
  4  - Second tick no new beliefs → drive_strength decreases, reinforce_count unchanged
  5  - Decay below threshold → drive deleted
  6  - Weaker drive replaced by stronger candidate
  7  - format_for_prompt() with no drives row → ""
  8  - format_for_prompt() with drives row → "Drawn lately to: {topic}"
  9  - state() shape — all required keys present
  10 - VoiceEngine drive_alignment axis boosts aligned candidate
  11 - Fountain probe spawned when no recent open problem
  12 - Fountain probe NOT spawned within cooldown window
  13 - /api/system/status includes drives_info (null when no drive)
  14 - SentienceNode protocol conformance
"""
from __future__ import annotations

import json
import time
import unittest
from unittest.mock import MagicMock, patch
import numpy as np

from theory_x.stage_drives.drive_emergence import (
    DriveEmergence,
    _repetition_score,
    _convergence_score,
    _synthesize_topic,
    _cluster,
    _DECAY_RATE,
    _MIN_DRIVE_STRENGTH,
    _W_REP,
    _W_CONV,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _belief(
    id: int,
    content: str = "emergence complexity pattern",
    confidence: float = 0.7,
    branch_id: str = "systems",
    use_count: int = 3,
    created_at: float = None,
) -> dict:
    return {
        "id":        id,
        "content":   content,
        "confidence": confidence,
        "branch_id": branch_id,
        "use_count": use_count,
        "created_at": created_at or time.time(),
    }


def _make_node(
    *,
    drives_row=None,
    candidate_beliefs=None,
    tick_interval_s=600,
):
    """Build a DriveEmergence backed entirely by mocks."""
    cw = MagicMock()
    cw.write.return_value = 1
    cw.db_path = ":memory:"

    cr = MagicMock()
    cr.read_one.return_value = drives_row

    br = MagicMock()
    if candidate_beliefs is None:
        candidate_beliefs = []

    def _br_read(sql, params=()):
        return candidate_beliefs

    def _br_read_one(sql, params=()):
        return None

    br.read.side_effect = _br_read
    br.read_one.side_effect = _br_read_one

    node = DriveEmergence(cw, cr, br, tick_interval_s=tick_interval_s)
    node._mock_cw = cw
    node._mock_cr = cr
    node._mock_br = br
    return node


def _emb(seed: int) -> np.ndarray:
    """Reproducible unit-vector embedding from integer seed."""
    rng = np.random.default_rng(seed)
    v = rng.normal(size=384).astype(np.float32)
    return v / np.linalg.norm(v)


def _multi_branch_beliefs(n: int = 5, branches=("alpha", "beta", "gamma")) -> list[dict]:
    """Return n beliefs spread across multiple branches with use_count > 0."""
    beliefs = []
    for i in range(n):
        beliefs.append(_belief(
            id=i + 1,
            content=f"emergence complexity pattern idea {i}",
            branch_id=branches[i % len(branches)],
            use_count=4,
        ))
    return beliefs


# ── Test 1 — both signals → drive written ────────────────────────────────────

class TestBothSignalsDriveWritten(unittest.TestCase):
    def test_drive_written_with_repetition_and_convergence(self):
        beliefs = _multi_branch_beliefs(8, branches=("alpha", "beta", "gamma"))
        node = _make_node(candidate_beliefs=beliefs)

        # Patch embeddings so all beliefs are similar (same cluster)
        similar_emb = _emb(42)
        embeddings_map = {b["id"]: similar_emb for b in beliefs}

        with patch(
            "theory_x.diversity.embeddings.embed_belief",
            side_effect=lambda bid, content: embeddings_map.get(bid, similar_emb),
        ), patch(
            "theory_x.stage_drives.drive_emergence._cosine",
            return_value=0.80,
        ):
            node._background_tick()

        node._mock_cw.write.assert_called()
        # At least one call should be INSERT OR REPLACE INTO drives
        calls_sql = [str(c.args[0]) for c in node._mock_cw.write.call_args_list]
        assert any("INSERT OR REPLACE INTO drives" in s for s in calls_sql), (
            f"Expected INSERT into drives; calls were: {calls_sql}"
        )


# ── Test 2 — repetition only (single branch) → no drive ──────────────────────

class TestRepetitionOnlyNoDrive(unittest.TestCase):
    def test_single_branch_cluster_not_written(self):
        # All beliefs same branch → convergence_score = 1/n < _MIN_CONVERGENCE will
        # actually be high for 1 branch. But distinct/total = 1/8 = 0.125 < 0.25.
        beliefs = [_belief(id=i + 1, branch_id="alpha", use_count=5) for i in range(8)]
        node = _make_node(candidate_beliefs=beliefs)

        similar_emb = _emb(1)
        with patch(
            "theory_x.diversity.embeddings.embed_belief",
            return_value=similar_emb,
        ), patch(
            "theory_x.stage_drives.drive_emergence._cosine",
            return_value=0.90,
        ):
            node._background_tick()

        calls_sql = [str(c.args[0]) for c in node._mock_cw.write.call_args_list]
        assert not any("INSERT OR REPLACE INTO drives" in s for s in calls_sql), (
            "Drive should NOT be written for single-branch cluster"
        )


# ── Test 3 — convergence only (low reinforce_count) → no drive ───────────────

class TestConvergenceOnlyNoDrive(unittest.TestCase):
    def test_multi_branch_low_reinforce_not_written(self):
        # Multiple branches but use_count = 0 → repetition_score = 0 < _MIN_REPETITION
        beliefs = [
            _belief(id=i + 1, branch_id=f"branch_{i}", use_count=0)
            for i in range(8)
        ]
        node = _make_node(candidate_beliefs=beliefs)

        similar_emb = _emb(2)
        with patch(
            "theory_x.diversity.embeddings.embed_belief",
            return_value=similar_emb,
        ), patch(
            "theory_x.stage_drives.drive_emergence._cosine",
            return_value=0.90,
        ):
            node._background_tick()

        calls_sql = [str(c.args[0]) for c in node._mock_cw.write.call_args_list]
        assert not any("INSERT OR REPLACE INTO drives" in s for s in calls_sql), (
            "Drive should NOT be written for zero-reinforce_count cluster"
        )


# ── Test 4 — second tick decays, reinforce_count unchanged ───────────────────

class TestSecondTickDecaysStrength(unittest.TestCase):
    def test_decay_second_tick_no_candidates(self):
        existing_strength = 0.50
        existing_row = {
            "drive_strength":    existing_strength,
            "topic":             "emergence",
            "source_beliefs":    json.dumps([1, 2, 3]),
            "repetition_score":  0.40,
            "convergence_score": 0.35,
            "formed_at":         time.time() - 1200,
            "last_reinforced_at": time.time() - 600,
            "reinforce_count":   2,
        }

        cw = MagicMock()
        cw.db_path = ":memory:"
        cr = MagicMock()
        cr.read_one.return_value = existing_row
        br = MagicMock()
        br.read.return_value = []  # no candidates

        node = DriveEmergence(cw, cr, br)

        node._background_tick()

        # Should write UPDATE (persist decayed) not INSERT OR REPLACE
        calls_sql = [str(c.args[0]) for c in cw.write.call_args_list]
        assert any("UPDATE drives" in s for s in calls_sql), (
            f"Expected UPDATE drives; got: {calls_sql}"
        )
        # Strength written should be less than original
        for c in cw.write.call_args_list:
            if "UPDATE drives" in str(c.args[0]):
                written_strength = c.args[1][0]
                self.assertLess(written_strength, existing_strength)
                break


# ── Test 5 — decay below threshold → drive deleted ───────────────────────────

class TestDecayBelowThresholdDeletes(unittest.TestCase):
    def test_drive_deleted_when_strength_below_min(self):
        # Set strength just above min; one decay step brings it below
        # _MIN_DRIVE_STRENGTH=0.25, _DECAY_RATE=0.92 → 0.27 * 0.92 = 0.2484 < 0.25
        existing_strength = 0.27
        existing_row = {
            "drive_strength":    existing_strength,
            "topic":             "emergence",
            "source_beliefs":    json.dumps([1]),
            "repetition_score":  0.30,
            "convergence_score": 0.26,
            "formed_at":         time.time() - 1200,
            "last_reinforced_at": time.time() - 600,
            "reinforce_count":   1,
        }

        cw = MagicMock()
        cw.db_path = ":memory:"
        cr = MagicMock()
        cr.read_one.return_value = existing_row
        br = MagicMock()
        br.read.return_value = []

        node = DriveEmergence(cw, cr, br)
        node._background_tick()

        calls_sql = [str(c.args[0]) for c in cw.write.call_args_list]
        assert any("DELETE FROM drives" in s for s in calls_sql), (
            f"Expected DELETE FROM drives; got: {calls_sql}"
        )
        # In-memory state should be cleared
        s = node.state()
        self.assertIsNone(s["topic"])
        self.assertIsNone(s["drive_strength"])


# ── Test 6 — weaker drive replaced by stronger ───────────────────────────────

class TestWeakerDriveReplaced(unittest.TestCase):
    def test_stronger_candidate_replaces_existing(self):
        existing_strength = 0.35
        existing_row = {
            "drive_strength":    existing_strength,
            "topic":             "old topic",
            "source_beliefs":    json.dumps([1, 2]),
            "repetition_score":  0.30,
            "convergence_score": 0.28,
            "formed_at":         time.time() - 1200,
            "last_reinforced_at": time.time() - 600,
            "reinforce_count":   3,
        }

        beliefs = _multi_branch_beliefs(8, branches=("x", "y", "z", "w"))
        # High use_count → high rep_score; multiple branches → high conv_score
        for b in beliefs:
            b["use_count"] = 10

        cw = MagicMock()
        cw.db_path = ":memory:"
        cr = MagicMock()
        cr.read_one.return_value = existing_row
        br = MagicMock()
        br.read.return_value = beliefs

        node = DriveEmergence(cw, cr, br)

        similar_emb = _emb(7)
        with patch(
            "theory_x.diversity.embeddings.embed_belief",
            return_value=similar_emb,
        ), patch(
            "theory_x.stage_drives.drive_emergence._cosine",
            return_value=0.90,
        ):
            node._background_tick()

        calls_sql = [str(c.args[0]) for c in cw.write.call_args_list]
        assert any("INSERT OR REPLACE INTO drives" in s for s in calls_sql), (
            "Stronger candidate should replace existing drive"
        )


# ── Test 7 — format_for_prompt() no row → "" ─────────────────────────────────

class TestFormatForPromptEmpty(unittest.TestCase):
    def test_returns_empty_when_no_drive(self):
        node = _make_node(drives_row=None)
        # ensure cr.read_one returns None for SELECT topic
        node._mock_cr.read_one.return_value = None
        result = node.format_for_prompt()
        self.assertEqual(result, "")


# ── Test 8 — format_for_prompt() row present ─────────────────────────────────

class TestFormatForPromptPresent(unittest.TestCase):
    def test_returns_drawn_lately(self):
        node = _make_node()
        node._mock_cr.read_one.return_value = {"topic": "emergence complexity patterns"}
        result = node.format_for_prompt()
        self.assertEqual(result, "Drawn lately to: emergence complexity patterns")


# ── Test 9 — state() shape ───────────────────────────────────────────────────

class TestStateShape(unittest.TestCase):
    def test_all_keys_present(self):
        node = _make_node()
        s = node.state()
        required = {
            "name", "topic", "drive_strength", "repetition_score",
            "convergence_score", "reinforce_count", "formed_at",
            "last_reinforced_at",
        }
        for key in required:
            self.assertIn(key, s, f"Missing key: {key}")

    def test_name_value(self):
        node = _make_node()
        self.assertEqual(node.state()["name"], "drive_emergence")


# ── Test 10 — VoiceEngine drive_alignment axis ───────────────────────────────

class TestVoiceEngineDriveAlignment(unittest.TestCase):
    def test_aligned_candidate_scores_higher(self):
        from theory_x.stage_throw_net.voice_engine import VoiceEngine

        reader = MagicMock()
        writer = MagicMock()
        writer.write.return_value = 1
        problem_memory = MagicMock()
        problem_memory.get_open_problems.return_value = []

        # Drive embedding pointing toward "emergence"
        drive_emb = _emb(42)
        drive_node = MagicMock()
        drive_node.drive_topic_embedding.return_value = drive_emb
        drive_node._drive_strength = 0.5
        drive_node._topic = "emergence patterns"

        ve = VoiceEngine(reader, problem_memory, writer, drive_emergence=drive_node)

        query_emb = _emb(10)

        # Candidate A: aligned with drive (high cosine to drive_emb)
        candidate_aligned = {
            "content":        "emergence patterns complexity",
            "confidence":     0.6,
            "tier":           4,
            "reinforce_count": 3,
            "source":         "belief",
            "origin_id":      1,
        }
        # Candidate B: same semantic/confidence/tier/recency but NOT aligned with drive
        candidate_unaligned = {
            "content":        "emergence patterns complexity",
            "confidence":     0.6,
            "tier":           4,
            "reinforce_count": 3,
            "source":         "belief",
            "origin_id":      2,
        }

        aligned_emb = drive_emb.copy()  # maximally aligned
        orthogonal_emb = _emb(999)       # different direction

        from theory_x.diversity.embeddings import cosine as real_cosine

        def _mock_embed(text):
            return query_emb

        with patch("theory_x.diversity.embeddings.embed", side_effect=_mock_embed), \
             patch("theory_x.diversity.embeddings.cosine", side_effect=real_cosine):
            score_aligned = ve._score_candidate(
                candidate_aligned, query_emb, candidate_emb=aligned_emb
            )
            score_unaligned = ve._score_candidate(
                candidate_unaligned, query_emb, candidate_emb=orthogonal_emb
            )

        self.assertGreater(
            score_aligned, score_unaligned,
            "Drive-aligned candidate must score higher than unaligned"
        )


# ── Test 11 — Fountain probe spawned when no recent open problem ──────────────

class TestFountainProbeSpawns(unittest.TestCase):
    def test_drive_probe_spawned_no_recent_problem(self):
        from theory_x.stage6_fountain import build_fountain
        from voice.llm import VoiceClient

        writers = {k: MagicMock() for k in ("sense", "dynamic", "beliefs", "conversations")}
        for w in writers.values():
            w.write.return_value = 1
        readers = {k: MagicMock() for k in ("sense", "dynamic", "beliefs", "conversations")}

        # No recent open problems
        readers["conversations"].read_one.return_value = None
        readers["conversations"].read.return_value = []
        readers["beliefs"].read.return_value = []
        readers["beliefs"].read_one.return_value = None
        readers["dynamic"].read.return_value = []
        readers["dynamic"].read_one.return_value = None
        readers["sense"].read.return_value = []

        drive_node = MagicMock()
        drive_node._topic = "emergence patterns"
        drive_node._drive_strength = 0.45
        drive_node.state.return_value = {"topic": "emergence patterns", "drive_strength": 0.45}

        gate = MagicMock()
        gate_decision = MagicMock()
        gate_decision.outcome.name = "ACCEPT"
        gate.check.return_value = gate_decision
        gate_calls = []
        gate.check.side_effect = lambda pkt: gate_calls.append(pkt) or gate_decision

        voice_client = MagicMock(spec=VoiceClient)

        with patch("theory_x.stage6_fountain.generator.FountainGenerator.generate", return_value=None):
            state = build_fountain(
                writers=writers,
                readers=readers,
                voice_client=voice_client,
                drive_emergence=drive_node,
                coherence_gate=gate,
            )
            # Manually trigger a single probe check
            state.generator._maybe_spawn_drive_probe()

        # At least one probe through gate mentioning drive topic
        probe_contents = [str(p.content) for p in gate_calls if hasattr(p, "content")]
        self.assertTrue(
            any("emergence patterns" in c for c in probe_contents),
            f"Expected drive probe with topic in gate calls; got: {probe_contents}",
        )


# ── Test 12 — Fountain probe NOT spawned within cooldown ─────────────────────

class TestFountainProbeRespectsCooldown(unittest.TestCase):
    def test_probe_not_fired_within_cooldown(self):
        from theory_x.stage6_fountain.generator import FountainGenerator, _DRIVE_PROBE_COOLDOWN_TICKS

        writer = MagicMock()
        writer.write.return_value = 1
        reader = MagicMock()
        reader.read.return_value = []
        reader.read_one.return_value = None

        drive_node = MagicMock()
        drive_node._topic = "emergence patterns"
        drive_node._drive_strength = 0.45

        gate = MagicMock()
        gate_decision = MagicMock()
        gate_decision.outcome.name = "ACCEPT"
        gate.check.return_value = gate_decision

        gen = FountainGenerator(
            sense_writer=writer,
            dynamic_writer=writer,
            voice_client=MagicMock(),
            dynamic_reader=reader,
            beliefs_writer=writer,
            beliefs_reader=reader,
            conversations_reader=reader,
            drive_emergence=drive_node,
            coherence_gate=gate,
        )

        # Fire once — sets cooldown
        gen._maybe_spawn_drive_probe()
        first_fire_count = gate.check.call_count

        # Fire again immediately — still within cooldown
        gen._maybe_spawn_drive_probe()
        second_fire_count = gate.check.call_count

        self.assertEqual(
            first_fire_count, second_fire_count,
            "Second probe should not fire within cooldown window",
        )


# ── Test 13 — drives_info shape (mirrors /api/system/status logic) ────────────

class TestDrivesInfoShape(unittest.TestCase):
    """Verifies the drives_info shape expected by the status endpoint.
    Avoids importing gui.server (requires argon2) — tests the data contract."""

    def _build_drives_info(self, state_dict: dict):
        """Replicate the endpoint logic from gui/server.py."""
        if state_dict.get("topic") is None:
            return None
        return {
            "topic":             state_dict["topic"],
            "drive_strength":    round(float(state_dict["drive_strength"]), 3),
            "repetition_score":  round(float(state_dict["repetition_score"]), 3),
            "convergence_score": round(float(state_dict["convergence_score"]), 3),
            "reinforce_count":   state_dict["reinforce_count"],
            "formed_at":         state_dict["formed_at"],
            "last_reinforced_at": state_dict["last_reinforced_at"],
        }

    def test_drives_info_null_when_no_drive(self):
        drive_node = MagicMock()
        drive_node.state.return_value = {
            "topic":            None,
            "drive_strength":   None,
            "repetition_score": None,
            "convergence_score": None,
            "reinforce_count":  0,
            "formed_at":        None,
            "last_reinforced_at": None,
        }
        drives_info = self._build_drives_info(drive_node.state())
        self.assertIsNone(drives_info)

    def test_drives_info_present_with_drive(self):
        drive_node = MagicMock()
        drive_node.state.return_value = {
            "topic":             "emergence complexity",
            "drive_strength":    0.41,
            "repetition_score":  0.38,
            "convergence_score": 0.46,
            "reinforce_count":   3,
            "formed_at":         1778501965.7,
            "last_reinforced_at": 1778502565.7,
        }
        drives_info = self._build_drives_info(drive_node.state())
        self.assertIsNotNone(drives_info)
        self.assertEqual(drives_info["topic"], "emergence complexity")
        self.assertIn("drive_strength", drives_info)
        required = {
            "topic", "drive_strength", "repetition_score", "convergence_score",
            "reinforce_count", "formed_at", "last_reinforced_at",
        }
        for key in required:
            self.assertIn(key, drives_info, f"Missing key: {key}")


# ── Test 14 — SentienceNode protocol conformance ─────────────────────────────

class TestSentienceNodeProtocol(unittest.TestCase):
    def setUp(self):
        self.node = _make_node()

    def test_implements_sentience_node_protocol(self):
        from theory_x import SentienceNode
        self.assertIsInstance(self.node, SentienceNode)

    def test_name(self):
        self.assertEqual(self.node.name, "drive_emergence")

    def test_tick_returns_dict(self):
        result = self.node.tick()
        self.assertIsInstance(result, dict)

    def test_decay_is_callable_no_error(self):
        self.node.decay(now=time.time())


if __name__ == "__main__":
    unittest.main()
