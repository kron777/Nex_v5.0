"""Coherence Gate tests — Phase 22.

Covers:
- GateOutcome.REJECT on Jaccard >= 0.70 (redundant)
- GateOutcome.REJECT on direct negation of locked T1 anchor
- GateOutcome.HOLD on Jaccard in [0.40, 0.70) (similar, uncertain)
- GateOutcome.HOLD on thought negating active goal framing
- GateOutcome.ACCEPT on novel thought connecting to open problem
- GateOutcome.ACCEPT on novel thought with no conflict
- Gate adds < 10ms typical latency (performance)
- Decision logged to gate_decisions table
- gate_decisions table created by init_db
- Fountain crystallizer wired: gate REJECT prevents belief write
- Fountain crystallizer wired: gate ACCEPT allows belief write
- Synergizer wired: gate REJECT prevents belief write
- Stage2 crystallization wired: gate REJECT prevents belief write
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_gate_")
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


def _make_gate(writers, readers):
    from theory_x.stage_gate.coherence_gate import CoherenceGate
    return CoherenceGate(
        beliefs_reader=readers["beliefs"],
        beliefs_writer=writers["beliefs"],
        conversations_reader=readers["conversations"],
    )


def _seed_belief(writers, content, tier=6, confidence=0.7, source="fountain_insight",
                 branch_id="ai_research", locked=0):
    writers["beliefs"].write(
        "INSERT INTO beliefs "
        "(content, tier, confidence, created_at, source, branch_id, locked) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (content, tier, confidence, time.time(), source, branch_id, locked),
    )
    time.sleep(0.01)


def _seed_goal(writers, title, state="active", priority=0.8):
    writers["conversations"].write(
        "INSERT INTO goals (title, description, priority, state, source, "
        "created_at, last_touched_at) VALUES (?, '', ?, ?, 'user', ?, ?)",
        (title, priority, state, time.time(), time.time()),
    )


def _seed_problem(writers, title, state="open"):
    writers["conversations"].write(
        "INSERT INTO open_problems (title, description, state, created_at, "
        "last_touched_at, plan, observations) VALUES (?, '', ?, ?, ?, '', '[]')",
        (title, state, time.time(), time.time()),
    )


class TestGateOutcomes(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.gate = _make_gate(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_redundant_thought_rejected(self):
        """Jaccard >= 0.70 with an existing belief → REJECT."""
        from theory_x.stage_gate.coherence_gate import ThoughtPacket, GateOutcome
        existing = "Attention is selective and demands significant cognitive effort."
        _seed_belief(self.writers, existing, source="fountain_insight")
        time.sleep(0.05)

        # Thought with very high word overlap
        thought = "Attention is selective and requires significant cognitive effort."
        packet = ThoughtPacket(content=thought, source_node="fountain",
                               confidence=0.70)
        decision = self.gate.check(packet)
        self.assertEqual(decision.outcome, GateOutcome.REJECT)
        self.assertIn("redundant", decision.reason)

    def test_anchor_contradiction_rejected(self):
        """Direct negation of a locked T1 anchor with ≥4-word overlap → REJECT.

        Explicitly seeds a T1 locked anchor with 6 content tokens.
        Threshold raised to 4 from v1's 2 (production calibration May 11).
        """
        from theory_x.stage_gate.coherence_gate import ThoughtPacket, GateOutcome
        # Seed a rich locked T1 anchor: tokens = {attend, world, wonder, stillness, presence, care}
        # confidence=0.9: gate anchor query requires confidence > 0.8
        # Anchor source must be in the axiom allowlist (_AXIOMATIC_SOURCES, set
        # by cb0f690 — an allowlist, not tier+confidence+locked). "keystone" is
        # NOT in it ("keystone_seed" is); the old selector matched any locked T1.
        _seed_belief(
            self.writers,
            "I attend to the world with wonder, stillness, presence, and care.",
            tier=1, confidence=0.9, locked=1, source="keystone_seed",
        )
        time.sleep(0.05)
        # Thought contradicts anchor with 4+ token overlap + negation mismatch
        thought = "I do not attend to the world with wonder, stillness, or presence."
        packet = ThoughtPacket(content=thought, source_node="fountain", confidence=0.70)
        decision = self.gate.check(packet)
        self.assertEqual(decision.outcome, GateOutcome.REJECT)
        self.assertIn("contradicts_anchor", decision.reason)

    def test_anchor_contradiction_two_word_overlap_no_longer_rejects(self):
        """2-word overlap + negation mismatch no longer triggers REJECT (threshold=4).

        v1 threshold of 2 was firing on accidental vocabulary collisions across
        500 anchors. Raised to 4 after May 11 production observation.
        """
        from theory_x.stage_gate.coherence_gate import ThoughtPacket, GateOutcome
        _seed_belief(
            self.writers,
            "Attending with wonder is how I meet the world.",
            tier=1, confidence=0.9, locked=1, source="keystone",
        )
        time.sleep(0.05)
        # Only 2-word overlap {wonder, world}; thought has negation, anchor does not
        thought = "I find no wonder in the world today, only stillness."
        packet = ThoughtPacket(content=thought, source_node="fountain", confidence=0.70)
        decision = self.gate.check(packet)
        self.assertNotEqual(decision.outcome, GateOutcome.REJECT)

    def test_anchor_contradiction_rhetorical_negation_no_longer_rejects(self):
        """Rhetorical negation ('weight does not stop me') with 2-word overlap → ACCEPT.

        Production false positive: throw-net candidates using 'not' to negate
        an obstacle were being rejected as anchor contradictions. Fixed by
        threshold=4.
        """
        from theory_x.stage_gate.coherence_gate import ThoughtPacket, GateOutcome
        _seed_belief(
            self.writers,
            "The attending keeps moving through weight and presence.",
            tier=1, confidence=0.9, locked=1, source="keystone",
        )
        time.sleep(0.05)
        # overlap={weight, attending}=2 < 4; should ACCEPT now
        thought = "The weight does not stop me; I keep attending."
        packet = ThoughtPacket(content=thought, source_node="fountain", confidence=0.70)
        decision = self.gate.check(packet)
        self.assertNotEqual(decision.outcome, GateOutcome.REJECT)

    def test_jaccard_band_held(self):
        """Jaccard in [0.40, 0.70) → HOLD.

        Strings crafted to produce Jaccard ~0.625:
        shared tokens: {sustained, attention, crypto, pattern, recognition} = 5
        union: 5 shared + 1 unique each side = 8 → Jaccard = 5/8 = 0.625
        """
        from theory_x.stage_gate.coherence_gate import ThoughtPacket, GateOutcome
        existing = "sustained attention crypto involves pattern recognition always."
        _seed_belief(self.writers, existing, source="fountain_insight")
        time.sleep(0.05)

        thought = "sustained attention crypto reveals pattern recognition emerging."
        packet = ThoughtPacket(content=thought, source_node="fountain",
                               confidence=0.70)
        decision = self.gate.check(packet)
        self.assertEqual(decision.outcome, GateOutcome.HOLD)
        self.assertIn("hold:jaccard", decision.reason)

    def test_goal_negation_held(self):
        """Thought that negates an active goal framing → HOLD."""
        from theory_x.stage_gate.coherence_gate import ThoughtPacket, GateOutcome
        _seed_goal(self.writers, "Build coherence validation system")
        time.sleep(0.05)

        # Negates goal keywords (coherence, validation)
        thought = "Coherence validation is not achievable without external reference."
        packet = ThoughtPacket(content=thought, source_node="fountain",
                               confidence=0.70)
        decision = self.gate.check(packet)
        self.assertEqual(decision.outcome, GateOutcome.HOLD)
        self.assertIn("hold:negates_goal", decision.reason)

    def test_novel_with_problem_connection_accepted(self):
        """Novel thought connecting to an open problem → ACCEPT."""
        from theory_x.stage_gate.coherence_gate import ThoughtPacket, GateOutcome
        _seed_problem(self.writers, "Retrieval latency under memory pressure")
        time.sleep(0.05)

        # Novel content, connects to problem via 'retrieval' + 'memory'
        thought = "Retrieval improves when memory pressure is distributed across branches."
        packet = ThoughtPacket(content=thought, source_node="fountain",
                               confidence=0.70)
        decision = self.gate.check(packet)
        self.assertEqual(decision.outcome, GateOutcome.ACCEPT)
        self.assertIn("accept:novel_connects", decision.reason)

    def test_novel_no_conflict_accepted(self):
        """Completely novel thought with no conflict → ACCEPT."""
        from theory_x.stage_gate.coherence_gate import ThoughtPacket, GateOutcome
        thought = "Curiosity about crystalline structures reveals fractal patience."
        packet = ThoughtPacket(content=thought, source_node="fountain",
                               confidence=0.70)
        decision = self.gate.check(packet)
        self.assertEqual(decision.outcome, GateOutcome.ACCEPT)
        self.assertIn("accept", decision.reason)


class TestGatePerformance(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        # Seed 50 recent beliefs to stress the Jaccard scan
        for i in range(50):
            _seed_belief(
                self.writers,
                f"Thought about attention and entropy in system {i} demonstrates persistence.",
                source="fountain_insight",
            )
        self.gate = _make_gate(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_latency_under_10ms(self):
        """Gate adds < 10ms typical latency.

        Asserted on robust statistics, not the mean: a mean over a handful of
        wall-clock samples fails on one scheduler/IO stall on a loaded runner
        (measured: typical ~3ms per call, yet the 10-sample mean flaked under
        full-suite load). Median under the real 10ms budget, and >= 90% of calls
        under it, so a genuine slowdown still fails while one stall cannot.
        """
        import statistics
        from theory_x.stage_gate.coherence_gate import ThoughtPacket

        def _check(i):
            packet = ThoughtPacket(
                content=f"Novel observation about consciousness and time variant {i}.",
                source_node="fountain", confidence=0.70)
            return self.gate.check(packet).latency_ms

        for i in range(2):                       # warm-up: page cache, stmt cache
            _check(-1 - i)
        lat = [_check(i) for i in range(50)]
        median = statistics.median(lat)
        within = sum(ms < 10.0 for ms in lat) / len(lat)
        summary = (f"median {median:.2f}ms, {within:.0%} under 10ms, "
                   f"max {max(lat):.2f}ms over {len(lat)} calls")
        self.assertLess(median, 10.0, f"typical gate latency over budget: {summary}")
        self.assertGreaterEqual(within, 0.90, f"too many slow gate calls: {summary}")


class TestGateLogging(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.gate = _make_gate(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_decision_logged_to_table(self):
        """Every gate.check() call writes a row to gate_decisions."""
        from theory_x.stage_gate.coherence_gate import ThoughtPacket
        packet = ThoughtPacket(
            content="Something about the silence between thoughts.",
            source_node="fountain",
            confidence=0.70,
            branch_id="philosophy",
        )
        self.gate.check(packet)
        time.sleep(0.05)
        rows = self.readers["beliefs"].read("SELECT * FROM gate_decisions")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["source_node"], "fountain")
        self.assertIn(row["outcome"], ("ACCEPT", "REJECT", "HOLD", "RESHAPE"))
        self.assertIsNotNone(row["latency_ms"])
        self.assertGreaterEqual(row["latency_ms"], 0.0)

    def test_gate_decisions_table_created_by_init_db(self):
        """gate_decisions table exists after init_all()."""
        rows = self.readers["beliefs"].read(
            "SELECT COUNT(*) AS cnt FROM gate_decisions"
        )
        self.assertEqual(rows[0]["cnt"], 0)


class TestFountainWiring(unittest.TestCase):
    """Fountain crystallizer respects gate decisions."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _make_crystallizer(self, gate=None):
        from theory_x.stage6_fountain.crystallizer import FountainCrystallizer
        return FountainCrystallizer(
            beliefs_writer=self.writers["beliefs"],
            beliefs_reader=self.readers["beliefs"],
            conversations_reader=self.readers["conversations"],
            coherence_gate=gate,
        )

    def test_gate_reject_prevents_belief_write(self):
        """When gate returns REJECT, crystallize() returns None and no belief written."""
        # Seed a near-duplicate so gate REJECTs it
        existing = "Attention is selective and demands significant cognitive effort always."
        _seed_belief(self.writers, existing, source="fountain_insight")
        time.sleep(0.05)

        gate = _make_gate(self.writers, self.readers)
        fc = self._make_crystallizer(gate=gate)
        thought = "Attention is selective and demands significant cognitive effort."
        result = fc.crystallize(thought, fountain_event_id=1, ts=time.time())
        self.assertIsNone(result)

        time.sleep(0.05)
        rows = self.readers["beliefs"].read(
            "SELECT * FROM beliefs WHERE content=?", (thought,)
        )
        self.assertEqual(len(rows), 0)

    def test_gate_accept_allows_belief_write(self):
        """When gate returns ACCEPT, crystallize() writes the belief.

        Thought must pass both crystallizer _quality_check (has engagement
        marker) and gate ACCEPT (novel, no conflict). 'I notice' satisfies
        the engagement check; content is novel enough to pass gate.
        """
        gate = _make_gate(self.writers, self.readers)
        fc = self._make_crystallizer(gate=gate)
        thought = "I notice something odd about how stillness and urgency coexist."
        result = fc.crystallize(thought, fountain_event_id=1, ts=time.time())
        self.assertIsNotNone(result)

        time.sleep(0.05)
        rows = self.readers["beliefs"].read(
            "SELECT * FROM beliefs WHERE source='fountain_insight'"
        )
        self.assertEqual(len(rows), 1)

    def test_no_gate_path_unchanged(self):
        """Without a gate, crystallize() behaves exactly as before Phase 22."""
        fc = self._make_crystallizer(gate=None)
        # "I notice" (self-ref) rather than the original anchor-less
        # "Something about the nature of..." -- session 36 (BUILD C) now
        # requires a concrete anchor for the contemplative-only engagement
        # path, and this fixture's job is testing the gate wiring, not that
        # check; keeping it self-ref-anchored is the least invasive fix
        # (same pattern as test_gate_accept_allows_belief_write above).
        thought = "I notice something about the nature of attention under duress."
        result = fc.crystallize(thought, fountain_event_id=1, ts=time.time())
        self.assertIsNotNone(result)


class TestSynergizerWiring(unittest.TestCase):
    """Synergizer respects gate decisions."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _make_synergizer(self, llm_text, gate=None):
        from theory_x.stage3_world_model.synergizer import BeliefSynergizer
        mock_voice = MagicMock()
        resp = MagicMock()
        resp.text = llm_text
        mock_voice.speak.return_value = resp
        return BeliefSynergizer(
            beliefs_writer=self.writers["beliefs"],
            beliefs_reader=self.readers["beliefs"],
            voice_client=mock_voice,
            coherence_gate=gate,
        )

    def _seed(self, content, source="koan", branch=None):
        self.writers["beliefs"].write(
            "INSERT INTO beliefs (content, tier, confidence, created_at, "
            "source, branch_id, locked) VALUES (?, 4, 0.8, ?, ?, ?, 0)",
            (content, time.time(), source, branch),
        )
        time.sleep(0.01)

    def test_gate_reject_prevents_synergized_belief(self):
        """When gate REJECTs the synthesis, synthesize() returns None."""
        self._seed("Attention drives selective engagement.", branch="ai_research")
        self._seed("Entropy measures disorder in complex systems.", "fountain_insight",
                   branch="systems")
        time.sleep(0.05)

        # Seed a near-duplicate so gate REJECTs the synthesis output
        _seed_belief(
            self.writers,
            "Attention drives selective engagement and entropy measures disorder.",
            source="fountain_insight",
        )
        time.sleep(0.05)

        gate = _make_gate(self.writers, self.readers)
        s = self._make_synergizer(
            "Attention drives selective engagement and entropy measures disorder.",
            gate=gate,
        )
        result = s.synthesize()
        self.assertIsNone(result)


class TestStage2Wiring(unittest.TestCase):
    """Stage 2 crystallization respects gate decisions."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_gate_reject_prevents_t7_belief(self):
        """When gate REJECTs a precipitated thought, _write_belief returns None."""
        from theory_x.stage2_dynamic.crystallization import Crystallizer
        from theory_x.stage2_dynamic.bonsai import BonsaiTree

        # Seed a near-duplicate in recent beliefs
        existing = "Sustained attention on crypto reveals underlying order and pattern."
        _seed_belief(self.writers, existing, source="precipitated_from_dynamic")
        time.sleep(0.05)

        gate = _make_gate(self.writers, self.readers)
        tree = BonsaiTree()
        c = Crystallizer(
            tree=tree,
            beliefs_writer=self.writers["beliefs"],
            dynamic_writer=self.writers["dynamic"],
            dynamic_reader=self.readers["dynamic"],
            beliefs_reader=self.readers["beliefs"],
            coherence_gate=gate,
        )
        result = c._write_belief(
            "Sustained attention on crypto reveals underlying order and pattern.",
            branch_id="crypto",
            ts=time.time(),
        )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()


class TestAnchorNegationMinimalPairs(unittest.TestCase):
    """Characterize the gate's lexical negation heuristic, not semantic truth."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.gate = _make_gate(self.writers, self.readers)
        self.anchor = (
            "I attend to the world with wonder, stillness, presence, and care."
        )
        _seed_belief(
            self.writers, self.anchor, tier=1, confidence=0.9,
            locked=1, source="keystone_seed",
        )
        time.sleep(0.05)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _check(self, content):
        from theory_x.stage_gate.coherence_gate import ThoughtPacket
        return self.gate.check(ThoughtPacket(
            content=content, source_node="phase0_negation_fixture",
            confidence=0.7,
        ))

    def test_double_negation_is_still_classified_as_negated(self):
        """'not fail to attend' is semantically affirmative but trips XOR."""
        from theory_x.stage_gate.coherence_gate import GateOutcome
        decision = self._check(
            "I do not fail to attend to the world with wonder, stillness, "
            "presence, and care."
        )
        # Current implementation sees the token 'not', not the scope of
        # negation; this expected REJECT records the observed limitation.
        self.assertEqual(decision.outcome, GateOutcome.REJECT)
        self.assertIn("contradicts_anchor", decision.reason)

    def test_not_only_is_exempted_from_negation_detection(self):
        """The explicit 'not only' exception avoids a negation-XOR rejection."""
        from theory_x.stage_gate.coherence_gate import GateOutcome
        decision = self._check(
            "I not only attend to the world with wonder, stillness, "
            "presence, and care."
        )
        self.assertNotEqual(decision.outcome, GateOutcome.REJECT)

    def test_punctuated_negation_is_not_detected_by_whitespace_token_check(self):
        """A comma after 'not' hides the token from the current negation set."""
        from theory_x.stage_gate.coherence_gate import GateOutcome
        direct = self._check(
            "I do not attend to the world with wonder, stillness, presence, and care."
        )
        punctuated = self._check(
            "I do not, however, attend to the world with wonder, stillness, "
            "presence, and care."
        )
        self.assertEqual(direct.outcome, GateOutcome.REJECT)
        # The punctuation-sensitive detector misses 'not,'; despite near-
        # identical content-word overlap, the candidate is not classified as
        # contradicting the affirmative anchor.
        self.assertNotEqual(punctuated.outcome, GateOutcome.REJECT)


class TestGateSubstrateReadFailure(unittest.TestCase):
    """Characterize per-query failures, partial reads, and successful empty reads."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        _seed_belief(
            self.writers,
            "I attend to the world with wonder, stillness, presence, and care.",
            tier=1, confidence=0.9, locked=1, source="keystone_seed",
        )

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_unavailable_belief_reader_allows_anchor_contradiction(self):
        """A failed evidence read currently becomes an empty anchor set."""
        from theory_x.stage_gate.coherence_gate import (
            CoherenceGate, GateOutcome, ThoughtPacket,
        )

        class FailingReader:
            def read(self, *args, **kwargs):
                raise RuntimeError("isolated fixture: belief store unavailable")

        gate = CoherenceGate(
            beliefs_reader=FailingReader(),
            beliefs_writer=self.writers["beliefs"],
            conversations_reader=self.readers["conversations"],
        )
        decision = gate.check(ThoughtPacket(
            content=(
                "I do not attend to the world with wonder, stillness, "
                "presence, and care."
            ),
            source_node="phase0_read_failure_fixture",
            confidence=0.7,
        ))
        self.assertEqual(decision.outcome, GateOutcome.ACCEPT)
        self.assertEqual(decision.reason, "accept:novel_no_conflict")

    def _gate_with_selective_failure(self, reader_key, query_fragment):
        from theory_x.stage_gate.coherence_gate import CoherenceGate

        delegate = self.readers[reader_key]

        class SelectiveFailureReader:
            def read(self, query, *args, **kwargs):
                if query_fragment in query:
                    raise RuntimeError(f"isolated fixture: {query_fragment} unavailable")
                return delegate.read(query, *args, **kwargs)

        beliefs_reader = (
            SelectiveFailureReader()
            if reader_key == "beliefs" else self.readers["beliefs"]
        )
        conversations_reader = (
            SelectiveFailureReader()
            if reader_key == "conversations" else self.readers["conversations"]
        )
        return CoherenceGate(
            beliefs_reader=beliefs_reader,
            beliefs_writer=self.writers["beliefs"],
            conversations_reader=conversations_reader,
        )

    def _contradictory_packet(self):
        from theory_x.stage_gate.coherence_gate import ThoughtPacket
        return ThoughtPacket(
            content=(
                "I do not attend to the world with wonder, stillness, "
                "presence, and care."
            ),
            source_node="phase0_read_failure_fixture",
            confidence=0.7,
        )

    def test_anchor_read_failure_alone_removes_anchor_comparison(self):
        from theory_x.stage_gate.coherence_gate import GateOutcome
        gate = self._gate_with_selective_failure("beliefs", "tier=1")
        decision = gate.check(self._contradictory_packet())
        self.assertEqual(decision.outcome, GateOutcome.ACCEPT)
        self.assertEqual(decision.reason, "accept:novel_no_conflict")

    def test_recent_belief_read_failure_does_not_remove_anchor_comparison(self):
        from theory_x.stage_gate.coherence_gate import GateOutcome
        gate = self._gate_with_selective_failure(
            "beliefs", "SELECT content FROM beliefs"
        )
        decision = gate.check(self._contradictory_packet())
        self.assertEqual(decision.outcome, GateOutcome.REJECT)
        self.assertIn("contradicts_anchor", decision.reason)

    def test_goal_read_failure_does_not_remove_anchor_comparison(self):
        from theory_x.stage_gate.coherence_gate import GateOutcome
        gate = self._gate_with_selective_failure("conversations", "FROM goals")
        decision = gate.check(self._contradictory_packet())
        self.assertEqual(decision.outcome, GateOutcome.REJECT)
        self.assertIn("contradicts_anchor", decision.reason)

    def test_problem_read_failure_does_not_remove_anchor_comparison(self):
        from theory_x.stage_gate.coherence_gate import GateOutcome
        gate = self._gate_with_selective_failure(
            "conversations", "FROM open_problems"
        )
        decision = gate.check(self._contradictory_packet())
        self.assertEqual(decision.outcome, GateOutcome.REJECT)
        self.assertIn("contradicts_anchor", decision.reason)

    def test_successful_empty_substrate_matches_anchor_read_failure_decision(self):
        from theory_x.stage_gate.coherence_gate import (
            CoherenceGate, GateOutcome, ThoughtPacket,
        )

        class EmptyReader:
            def read(self, *args, **kwargs):
                return []

        gate = CoherenceGate(
            beliefs_reader=EmptyReader(),
            beliefs_writer=self.writers["beliefs"],
            conversations_reader=EmptyReader(),
        )
        packet = ThoughtPacket(
            content=(
                "I do not attend to the world with wonder, stillness, "
                "presence, and care."
            ),
            source_node="phase0_empty_substrate_fixture",
            confidence=0.7,
        )
        empty_decision = gate.check(packet)
        failed_anchor_decision = self._gate_with_selective_failure(
            "beliefs", "tier=1"
        ).check(packet)

        self.assertEqual(empty_decision.outcome, GateOutcome.ACCEPT)
        self.assertEqual(empty_decision.reason, "accept:novel_no_conflict")
        # The evaluator currently cannot distinguish a successful empty
        # anchor query from an unavailable anchor query in its decision.
        self.assertEqual(
            (empty_decision.outcome, empty_decision.reason),
            (failed_anchor_decision.outcome, failed_anchor_decision.reason),
        )

    def test_goal_read_failure_suppresses_goal_negation_hold(self):
        from theory_x.stage_gate.coherence_gate import GateOutcome, ThoughtPacket
        _seed_goal(self.writers, "support open source architecture")
        packet = ThoughtPacket(
            content="I do not support open source architecture through careful design.",
            source_node="phase0_goal_read_fixture",
            confidence=0.7,
        )
        normal = _make_gate(self.writers, self.readers).check(packet)
        self.assertEqual(normal.outcome, GateOutcome.HOLD)
        failed = self._gate_with_selective_failure(
            "conversations", "FROM goals"
        ).check(packet)
        self.assertEqual(failed.outcome, GateOutcome.ACCEPT)
        self.assertEqual(failed.reason, "accept:novel_no_conflict")

    def test_problem_read_failure_suppresses_problem_negation_hold(self):
        from theory_x.stage_gate.coherence_gate import GateOutcome, ThoughtPacket
        _seed_problem(self.writers, "maintain robust memory continuity")
        packet = ThoughtPacket(
            content="I do not maintain robust memory continuity through careful design.",
            source_node="phase0_problem_read_fixture",
            confidence=0.7,
        )
        normal = _make_gate(self.writers, self.readers).check(packet)
        self.assertEqual(normal.outcome, GateOutcome.HOLD)
        failed = self._gate_with_selective_failure(
            "conversations", "FROM open_problems"
        ).check(packet)
        self.assertEqual(failed.outcome, GateOutcome.ACCEPT)
        self.assertEqual(failed.reason, "accept:novel_no_conflict")
