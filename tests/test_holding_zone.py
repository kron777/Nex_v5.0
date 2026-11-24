"""Holding Zone tests — Phase 23.

Covers:
- hold() persists a held thought with status='holding'
- find_corroborations() returns Jaccard >= 0.40 matches
- increment_corroboration() increments count correctly
- corroboration at N=3 promotes held thought to real belief
- find_contradictions() returns overlap>=2 + negation-parity mismatch
- mark_resolved('rejected') fires on contradiction
- fade_stale() marks 24h+ thoughts as 'faded'
- gate HOLD outcome writes to held_thoughts (end-to-end)
- gate ACCEPT triggers resolver (end-to-end)
- resolver error does not break gate ACCEPT decision
- terminal-status thoughts are not revived by subsequent calls
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
    tmp = tempfile.mkdtemp(prefix="nex5_hz_")
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


def _make_zone(writers, readers):
    from theory_x.stage_gate.holding_zone import HoldingZone
    return HoldingZone(writers["beliefs"], readers["beliefs"])


def _make_resolver(zone, writers):
    from theory_x.stage_gate.resolver import HoldingZoneResolver
    return HoldingZoneResolver(zone, beliefs_writer=writers["beliefs"])


def _make_gate(writers, readers, holding_zone=None, resolver=None):
    from theory_x.stage_gate.coherence_gate import CoherenceGate
    return CoherenceGate(
        beliefs_reader=readers["beliefs"],
        beliefs_writer=writers["beliefs"],
        conversations_reader=readers["conversations"],
        holding_zone=holding_zone,
        resolver=resolver,
    )


def _packet(content, source="fountain", confidence=0.70, branch_id=None):
    from theory_x.stage_gate.coherence_gate import ThoughtPacket
    return ThoughtPacket(
        content=content,
        source_node=source,
        confidence=confidence,
        branch_id=branch_id,
    )


def _seed_belief(writers, content, source="fountain_insight", tier=6):
    writers["beliefs"].write(
        "INSERT INTO beliefs "
        "(content, tier, confidence, created_at, source, branch_id, locked) "
        "VALUES (?, ?, 0.7, ?, ?, 'ai_research', 0)",
        (content, tier, time.time(), source),
    )
    time.sleep(0.01)


# ── HoldingZone unit tests ─────────────────────────────────────────────────────

class TestHoldPersists(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.zone = _make_zone(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_hold_persists_thought(self):
        """hold() writes a row with status='holding'."""
        p = _packet("I notice something odd about how stillness and urgency coexist.")
        held_id = self.zone.hold(p, "hold:jaccard_0.55")
        self.assertIsNotNone(held_id)
        time.sleep(0.02)
        rows = self.readers["beliefs"].read(
            "SELECT * FROM held_thoughts WHERE id=?", (held_id,)
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "holding")
        self.assertEqual(rows[0]["source_node"], "fountain")
        self.assertEqual(rows[0]["hold_reason"], "hold:jaccard_0.55")
        self.assertEqual(rows[0]["corroboration_count"], 0)

    def test_corroboration_increments_count(self):
        """increment_corroboration() raises count by 1 each call."""
        p = _packet("sustained attention crypto involves pattern recognition carefully always.")
        held_id = self.zone.hold(p, "hold:jaccard_0.50")
        self.assertIsNotNone(held_id)
        time.sleep(0.02)

        c1 = self.zone.increment_corroboration(held_id)
        self.assertEqual(c1, 1)
        c2 = self.zone.increment_corroboration(held_id)
        self.assertEqual(c2, 2)


class TestCorroborationThreshold(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.zone = _make_zone(self.writers, self.readers)
        self.resolver = _make_resolver(self.zone, self.writers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_corroboration_threshold_promotes_held(self):
        """N=3 corroborations promote held thought to real belief in beliefs table."""
        held_content = "sustained attention crypto involves pattern recognition carefully always."
        p = _packet(held_content)
        held_id = self.zone.hold(p, "hold:jaccard_0.50")
        self.assertIsNotNone(held_id)
        time.sleep(0.02)

        # Corroborating content: Jaccard >= 0.40 against held_content
        corr_content = "sustained attention crypto reveals pattern recognition emerging."

        # First two: count goes to 1, 2 — not yet promoted
        for _ in range(2):
            self.resolver.on_gate_accept(_packet(corr_content))
            time.sleep(0.02)

        rows = self.readers["beliefs"].read(
            "SELECT status FROM held_thoughts WHERE id=?", (held_id,)
        )
        self.assertEqual(rows[0]["status"], "holding")

        # Third: count reaches 3 → promoted
        self.resolver.on_gate_accept(_packet(corr_content))
        time.sleep(0.05)

        rows = self.readers["beliefs"].read(
            "SELECT status FROM held_thoughts WHERE id=?", (held_id,)
        )
        self.assertEqual(rows[0]["status"], "accepted")

        # Real belief written
        beliefs = self.readers["beliefs"].read(
            "SELECT tier, source FROM beliefs WHERE content=?", (held_content,)
        )
        self.assertEqual(len(beliefs), 1)
        self.assertEqual(beliefs[0]["source"], "fountain")
        self.assertEqual(beliefs[0]["tier"], 6)

        # Audit row written
        resolutions = self.readers["beliefs"].read(
            "SELECT action FROM held_resolutions WHERE held_id=?", (held_id,)
        )
        self.assertEqual(len(resolutions), 1)
        self.assertEqual(resolutions[0]["action"], "accepted")


    def test_failed_promotion_write_still_marks_held_thought_accepted(self):
        """Characterize the non-atomic promotion/resolution failure path."""
        from theory_x.stage_gate.holding_zone import HoldingZone

        held_content = (
            "sustained attention crypto involves pattern recognition carefully always."
        )
        held_id = self.zone.hold(
            _packet(held_content), "fixture:promotion_write_failure"
        )
        self.assertIsNotNone(held_id)

        delegate = self.writers["beliefs"]

        class PromotionFailingWriter:
            def write(self, query, params=()):
                if query.lstrip().lower().startswith("insert into beliefs"):
                    raise RuntimeError("isolated fixture: promotion write unavailable")
                return delegate.write(query, params)

        failing_zone = HoldingZone(
            PromotionFailingWriter(), self.readers["beliefs"]
        )
        resolver = _make_resolver(failing_zone, self.writers)
        corroborating_packet = _packet(
            "sustained attention crypto reveals pattern recognition emerging."
        )

        for _ in range(3):
            resolver.on_gate_accept(corroborating_packet)
            time.sleep(0.02)

        held = self.readers["beliefs"].read_one(
            "SELECT status, corroboration_count FROM held_thoughts WHERE id=?",
            (held_id,),
        )
        self.assertEqual(held["corroboration_count"], 3)
        self.assertEqual(held["status"], "accepted")

        promoted = self.readers["beliefs"].read(
            "SELECT id FROM beliefs WHERE content=?", (held_content,)
        )
        self.assertEqual(promoted, [])

        resolution = self.readers["beliefs"].read_one(
            "SELECT action, reason FROM held_resolutions WHERE held_id=?",
            (held_id,),
        )
        self.assertEqual(resolution["action"], "accepted")
        self.assertEqual(
            resolution["reason"], "corroboration_threshold_3"
        )


class TestResolutionPersistenceFailure(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.zone = _make_zone(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_resolution_audit_insert_failure_leaves_terminal_status_without_audit(self):
        """Characterize the split status-update / resolution-audit write path."""
        from theory_x.stage_gate.holding_zone import HoldingZone

        held_id = self.zone.hold(
            _packet("I retain a clear distinction between evidence and inference."),
            "fixture:resolution_audit_failure",
        )
        self.assertIsNotNone(held_id)
        delegate = self.writers["beliefs"]

        class AuditFailingWriter:
            def write(self, query, params=()):
                if query.lstrip().lower().startswith("insert into held_resolutions"):
                    raise RuntimeError("isolated fixture: resolution audit unavailable")
                return delegate.write(query, params)

        failing_zone = HoldingZone(
            AuditFailingWriter(), self.readers["beliefs"]
        )
        failing_zone.mark_resolved(
            held_id, "accepted", "fixture:audit_insert_failure"
        )

        held = self.readers["beliefs"].read_one(
            "SELECT status FROM held_thoughts WHERE id=?", (held_id,)
        )
        self.assertEqual(held["status"], "accepted")
        audit_rows = self.readers["beliefs"].read(
            "SELECT action FROM held_resolutions WHERE held_id=?", (held_id,)
        )
        self.assertEqual(audit_rows, [])


class TestContradiction(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.zone = _make_zone(self.writers, self.readers)
        self.resolver = _make_resolver(self.zone, self.writers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_contradiction_rejects_held(self):
        """Held thought contradicted by an incoming ACCEPT becomes 'rejected'."""
        # Held: affirmative statement about attending with wonder
        held_content = "I attend to the world with wonder and care always."
        p = _packet(held_content)
        held_id = self.zone.hold(p, "hold:negates_goal_1")
        self.assertIsNotNone(held_id)
        time.sleep(0.02)

        # Contradicting: negates the held content (overlap>=2, different negation)
        contra_content = "I do not attend to the world with wonder or care."
        self.resolver.on_gate_accept(_packet(contra_content))
        time.sleep(0.05)

        rows = self.readers["beliefs"].read(
            "SELECT status FROM held_thoughts WHERE id=?", (held_id,)
        )
        self.assertEqual(rows[0]["status"], "rejected")

        resolutions = self.readers["beliefs"].read(
            "SELECT action FROM held_resolutions WHERE held_id=?", (held_id,)
        )
        self.assertEqual(len(resolutions), 1)
        self.assertEqual(resolutions[0]["action"], "rejected")


    def test_contradictory_accept_at_threshold_promotes_before_rejection_scan(self):
        """A packet matching both heuristics is processed as corroboration first."""
        held_content = "I attend to the world with wonder and care always."
        held_id = self.zone.hold(
            _packet(held_content), "fixture:corroboration_contradiction_overlap"
        )
        self.assertIsNotNone(held_id)
        time.sleep(0.02)
        self.assertEqual(self.zone.increment_corroboration(held_id), 1)
        self.assertEqual(self.zone.increment_corroboration(held_id), 2)

        contradictory_packet = _packet(
            "I do not attend to the world with wonder or care."
        )
        # The same incoming packet satisfies both lexical predicates.
        self.assertEqual(
            [row["id"] for row in self.zone.find_corroborations(contradictory_packet)],
            [held_id],
        )
        self.assertEqual(
            [row["id"] for row in self.zone.find_contradictions(contradictory_packet)],
            [held_id],
        )

        from theory_x.stage_gate.coherence_gate import CoherenceGate, GateOutcome

        class EmptyBeliefsReader:
            """Successful empty substrate fixture; resolver retains the real held-zone reader."""
            def read(self, *args, **kwargs):
                return []

            def read_one(self, *args, **kwargs):
                return None

        gate = CoherenceGate(
            beliefs_reader=EmptyBeliefsReader(),
            beliefs_writer=self.writers["beliefs"],
            conversations_reader=self.readers["conversations"],
            holding_zone=self.zone,
            resolver=self.resolver,
        )
        decision = gate.check(contradictory_packet)
        self.assertEqual(decision.outcome, GateOutcome.ACCEPT)

        held = self.readers["beliefs"].read_one(
            "SELECT status, corroboration_count FROM held_thoughts WHERE id=?",
            (held_id,),
        )
        self.assertEqual(held["corroboration_count"], 3)
        self.assertEqual(held["status"], "accepted")
        promoted = self.readers["beliefs"].read(
            "SELECT id FROM beliefs WHERE content=?", (held_content,)
        )
        self.assertEqual(len(promoted), 1)
        resolution = self.readers["beliefs"].read_one(
            "SELECT action, reason FROM held_resolutions WHERE held_id=?",
            (held_id,),
        )
        self.assertEqual(resolution["action"], "accepted")
        self.assertEqual(resolution["reason"], "corroboration_threshold_3")


class TestTimeFade(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.zone = _make_zone(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_time_decay_fades_held(self):
        """Held thoughts older than max_age_seconds are faded."""
        # Insert directly with an ancient timestamp
        ancient_ts = time.time() - 90000  # 25h ago
        self.writers["beliefs"].write(
            "INSERT INTO held_thoughts "
            "(content, source_node, confidence, hold_reason, "
            "created_at, last_seen_at, corroboration_count, status) "
            "VALUES (?, 'fountain', 0.7, 'hold:jaccard_0.55', ?, ?, 0, 'holding')",
            ("Ancient thought about stillness.", ancient_ts, ancient_ts),
        )
        time.sleep(0.02)

        faded = self.zone.fade_stale(time.time(), max_age_seconds=86400)
        self.assertEqual(faded, 1)
        time.sleep(0.02)

        rows = self.readers["beliefs"].read(
            "SELECT status FROM held_thoughts WHERE content=?",
            ("Ancient thought about stillness.",),
        )
        self.assertEqual(rows[0]["status"], "faded")

    def test_terminal_status_not_revived(self):
        """Accepted/rejected/faded thoughts are not modified by corroboration or fade."""
        p = _packet("sustained attention crypto involves pattern recognition carefully always.")
        held_id = self.zone.hold(p, "hold:jaccard_0.55")
        self.assertIsNotNone(held_id)
        time.sleep(0.02)

        # Manually mark accepted
        self.zone.mark_resolved(held_id, "accepted", "test_manual")
        time.sleep(0.02)

        # Corroboration increment should not apply to non-holding row
        count = self.zone.increment_corroboration(held_id)
        # Row is 'accepted', UPDATE WHERE status='holding' matches nothing
        row = self.readers["beliefs"].read_one(
            "SELECT corroboration_count, status FROM held_thoughts WHERE id=?",
            (held_id,),
        )
        self.assertEqual(row["status"], "accepted")
        self.assertEqual(row["corroboration_count"], 0)  # not incremented

        # Fade should not affect terminal row
        faded = self.zone.fade_stale(time.time() + 999999, max_age_seconds=0)
        row = self.readers["beliefs"].read_one(
            "SELECT status FROM held_thoughts WHERE id=?", (held_id,)
        )
        self.assertEqual(row["status"], "accepted")


# ── End-to-end wiring tests ────────────────────────────────────────────────────

class TestGateWiring(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.zone = _make_zone(self.writers, self.readers)
        self.resolver = _make_resolver(self.zone, self.writers)
        self.gate = _make_gate(
            self.writers, self.readers,
            holding_zone=self.zone,
            resolver=self.resolver,
        )

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_gate_hold_outcome_writes_held_thought(self):
        """Gate HOLD outcome persists to held_thoughts table."""
        # Seed a belief to trigger HOLD (Jaccard in [0.40, 0.70))
        _seed_belief(
            self.writers,
            "sustained attention crypto involves pattern recognition always.",
        )
        time.sleep(0.05)

        thought = "sustained attention crypto reveals pattern recognition emerging."
        p = _packet(thought)
        from theory_x.stage_gate.coherence_gate import GateOutcome
        decision = self.gate.check(p)
        self.assertEqual(decision.outcome, GateOutcome.HOLD)
        time.sleep(0.05)

        rows = self.readers["beliefs"].read(
            "SELECT * FROM held_thoughts WHERE content=?", (thought,)
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "holding")
        self.assertIn("hold:jaccard", rows[0]["hold_reason"])

    def test_gate_accept_triggers_resolver(self):
        """Gate ACCEPT calls resolver.on_gate_accept() — corroboration count incremented."""
        # Seed a held thought whose content is similar to an upcoming ACCEPT
        held_content = "sustained attention crypto involves pattern recognition carefully always."
        self.zone.hold(_packet(held_content), "hold:jaccard_0.50")
        time.sleep(0.02)

        # Novel ACCEPT that corroborates the held thought
        accept_content = "sustained attention crypto reveals pattern recognition emerging."
        from theory_x.stage_gate.coherence_gate import GateOutcome
        decision = self.gate.check(_packet(accept_content))
        self.assertEqual(decision.outcome, GateOutcome.ACCEPT)
        time.sleep(0.05)

        rows = self.readers["beliefs"].read(
            "SELECT corroboration_count FROM held_thoughts WHERE content=?",
            (held_content,),
        )
        self.assertEqual(rows[0]["corroboration_count"], 1)

    def test_anchor_read_failure_accept_still_triggers_resolver(self):
        """An ACCEPT caused by missing anchor evidence reaches the normal resolver sink."""
        from theory_x.stage_gate.coherence_gate import (
            CoherenceGate, GateOutcome,
        )

        anchor = "I attend to the world with wonder, stillness, presence, and care."
        self.writers["beliefs"].write(
            "INSERT INTO beliefs "
            "(content, tier, confidence, created_at, source, branch_id, locked) "
            "VALUES (?, 1, 0.9, ?, 'keystone_seed', 'phase0_fixture', 1)",
            (anchor, time.time()),
        )
        time.sleep(0.03)

        packet = _packet(
            "I do not attend to the world with wonder, stillness, presence, and care."
        )
        held_id = self.zone.hold(packet, "fixture:pre-existing-held-thought")
        self.writers["beliefs"].write(
            "UPDATE held_thoughts SET corroboration_count=2 WHERE id=?",
            (held_id,),
        )
        time.sleep(0.02)

        delegate = self.readers["beliefs"]

        class AnchorFailingReader:
            def read(self, query, *args, **kwargs):
                if "tier=1" in query:
                    raise RuntimeError("isolated fixture: anchor query unavailable")
                return delegate.read(query, *args, **kwargs)

        gate = CoherenceGate(
            beliefs_reader=AnchorFailingReader(),
            beliefs_writer=self.writers["beliefs"],
            conversations_reader=self.readers["conversations"],
            holding_zone=self.zone,
            resolver=self.resolver,
        )
        decision = gate.check(packet)
        self.assertEqual(decision.outcome, GateOutcome.ACCEPT)
        time.sleep(0.03)

        row = self.readers["beliefs"].read_one(
            "SELECT corroboration_count, status FROM held_thoughts WHERE content=?",
            (packet.content,),
        )
        self.assertEqual(row["corroboration_count"], 3)
        self.assertEqual(row["status"], "accepted")
        promoted = self.readers["beliefs"].read(
            "SELECT content, source FROM beliefs WHERE content=?",
            (packet.content,),
        )
        self.assertEqual(len(promoted), 1)
        self.assertEqual(promoted[0]["source"], "fountain")

    def test_evaluation_error_fallback_accept_still_triggers_resolver(self):
        """Characterize that the outer evaluation-error ACCEPT reaches resolver."""
        mock_resolver = MagicMock()
        gate = _make_gate(
            self.writers, self.readers,
            holding_zone=self.zone,
            resolver=mock_resolver,
        )
        gate._evaluate = MagicMock(side_effect=RuntimeError("isolated evaluation failure"))

        from theory_x.stage_gate.coherence_gate import GateOutcome
        decision = gate.check(_packet(
            "A novel thought about careful evidence and patient reasoning."
        ))

        self.assertEqual(decision.outcome, GateOutcome.ACCEPT)
        self.assertEqual(decision.reason, "gate_error_fallback")
        mock_resolver.on_gate_accept.assert_called_once()

    def test_anchor_read_failure_accept_can_reject_held_thought(self):
        """An ACCEPT after an unavailable anchor read reaches contradiction resolution."""
        from theory_x.stage_gate.coherence_gate import CoherenceGate, GateOutcome

        affirmative = "I attend to the world with wonder and care always."
        self.writers["beliefs"].write(
            "INSERT INTO beliefs "
            "(content, tier, confidence, created_at, source, branch_id, locked) "
            "VALUES (?, 1, 0.9, ?, 'keystone_seed', 'phase0_fixture', 1)",
            (affirmative, time.time()),
        )
        held_id = self.zone.hold(
            _packet(affirmative), "fixture:held_affirmative_thought"
        )
        self.assertIsNotNone(held_id)
        time.sleep(0.02)

        delegate = self.readers["beliefs"]

        class AnchorFailingReader:
            def read(self, query, *args, **kwargs):
                if "tier=1" in query:
                    raise RuntimeError("isolated fixture: anchor query unavailable")
                return delegate.read(query, *args, **kwargs)

        packet = _packet("I do not attend to the world with wonder or care.")
        gate = CoherenceGate(
            beliefs_reader=AnchorFailingReader(),
            beliefs_writer=self.writers["beliefs"],
            conversations_reader=self.readers["conversations"],
            holding_zone=self.zone,
            resolver=self.resolver,
        )
        decision = gate.check(packet)
        self.assertEqual(decision.outcome, GateOutcome.ACCEPT)
        time.sleep(0.03)

        held = self.readers["beliefs"].read_one(
            "SELECT corroboration_count, status FROM held_thoughts WHERE id=?",
            (held_id,),
        )
        self.assertEqual(held["corroboration_count"], 1)
        self.assertEqual(held["status"], "rejected")
        resolution = self.readers["beliefs"].read_one(
            "SELECT action, reason FROM held_resolutions WHERE held_id=?",
            (held_id,),
        )
        self.assertEqual(resolution["action"], "rejected")
        self.assertEqual(resolution["reason"], "contradicted_by_accept")

    def test_resolver_error_does_not_break_gate(self):
        """Gate ACCEPT is returned correctly even when resolver raises."""
        mock_resolver = MagicMock()
        mock_resolver.on_gate_accept.side_effect = RuntimeError("resolver exploded")

        gate = _make_gate(
            self.writers, self.readers,
            holding_zone=self.zone,
            resolver=mock_resolver,
        )
        thought = "Curiosity about crystalline structures reveals fractal patience."
        p = _packet(thought)
        from theory_x.stage_gate.coherence_gate import GateOutcome
        decision = gate.check(p)

        self.assertEqual(decision.outcome, GateOutcome.ACCEPT)
        mock_resolver.on_gate_accept.assert_called_once()

    def test_resolver_loop_calls_fade_stale(self):
        """resolver.tick() calls fade_stale(); stale thoughts are faded."""
        ancient_ts = time.time() - 90000
        self.writers["beliefs"].write(
            "INSERT INTO held_thoughts "
            "(content, source_node, confidence, hold_reason, "
            "created_at, last_seen_at, corroboration_count, status) "
            "VALUES (?, 'fountain', 0.7, 'hold:jaccard_0.55', ?, ?, 0, 'holding')",
            ("Old thought for fade test.", ancient_ts, ancient_ts),
        )
        time.sleep(0.02)

        self.resolver.tick()
        time.sleep(0.02)

        rows = self.readers["beliefs"].read(
            "SELECT status FROM held_thoughts WHERE content=?",
            ("Old thought for fade test.",),
        )
        self.assertEqual(rows[0]["status"], "faded")


if __name__ == "__main__":
    unittest.main()
