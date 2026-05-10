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
