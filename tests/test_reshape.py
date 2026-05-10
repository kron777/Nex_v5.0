"""Reshape Path tests — Phase 24.

Covers:
- Existing five generative paths never produce RESHAPE (option δ: no reshape_hint)
- reshape_hint=True with depth < 2 → RESHAPE outcome + reshape_pending row
- reshape_hint=True with depth >= 2 → ACCEPT (cognitive-effort cap)
- ReshapeTransformer.transform() returns new ThoughtPacket with depth+1
- ReshapeTransformer.transform() returns None on voice failure
- resolver.tick() picks up reshape_pending, transforms, re-submits, marks complete
- resolver marks reshape_failed when transformer returns None
- resolver processes at most 10 pending items per tick
- held_resolutions audit row written with action='reshaped'
- transformer/resolver errors do not affect gate decision outcome
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_rs_")
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


def _make_resolver(zone, writers, transformer=None, gate=None):
    from theory_x.stage_gate.resolver import HoldingZoneResolver
    return HoldingZoneResolver(
        zone,
        beliefs_writer=writers["beliefs"],
        transformer=transformer,
        gate=gate,
    )


def _make_gate(writers, readers, holding_zone=None, resolver=None):
    from theory_x.stage_gate.coherence_gate import CoherenceGate
    return CoherenceGate(
        beliefs_reader=readers["beliefs"],
        beliefs_writer=writers["beliefs"],
        conversations_reader=readers["conversations"],
        holding_zone=holding_zone,
        resolver=resolver,
    )


def _packet(content, source="fountain", confidence=0.70,
            reshape_hint=False, reshape_depth=0, branch_id=None):
    from theory_x.stage_gate.coherence_gate import ThoughtPacket
    metadata = {}
    if reshape_hint:
        metadata["reshape_hint"] = True
        metadata["reshape_depth"] = reshape_depth
    return ThoughtPacket(
        content=content,
        source_node=source,
        confidence=confidence,
        branch_id=branch_id,
        metadata=metadata,
    )


def _mock_voice(text="Reframed thought captures the same essence clearly."):
    """Return a mock VoiceClient whose speak() returns text."""
    resp = MagicMock()
    resp.text = text
    voice = MagicMock()
    voice.speak.return_value = resp
    return voice


# ── No-RESHAPE-without-hint ───────────────────────────────────────────────────

class TestNoReshapeWithoutHint(unittest.TestCase):

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

    def test_no_reshape_without_hint(self):
        """Novel packet with no reshape_hint never produces RESHAPE."""
        from theory_x.stage_gate.coherence_gate import GateOutcome
        for source in ("fountain", "synergizer", "stage2_crystallization",
                       "bsm", "emergent_drives"):
            p = _packet(
                f"Curious observation about crystalline patterns emerging {source}.",
                source=source,
            )
            decision = self.gate.check(p)
            self.assertNotEqual(
                decision.outcome, GateOutcome.RESHAPE,
                f"source={source} unexpectedly produced RESHAPE",
            )

    def test_no_reshape_when_hint_missing_from_metadata(self):
        """Packet with empty metadata dict never triggers RESHAPE."""
        from theory_x.stage_gate.coherence_gate import GateOutcome, ThoughtPacket
        p = ThoughtPacket(
            content="Absence of reshape signal means this falls through.",
            source_node="fountain",
            confidence=0.8,
            metadata={},
        )
        decision = self.gate.check(p)
        self.assertNotEqual(decision.outcome, GateOutcome.RESHAPE)


# ── RESHAPE trigger ───────────────────────────────────────────────────────────

class TestReshapeTrigger(unittest.TestCase):

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

    def test_reshape_hint_triggers_reshape_outcome(self):
        """reshape_hint=True + depth=0 → GateOutcome.RESHAPE."""
        from theory_x.stage_gate.coherence_gate import GateOutcome
        p = _packet(
            "Test thought intentionally reshape-hinted.",
            reshape_hint=True,
            reshape_depth=0,
        )
        decision = self.gate.check(p)
        self.assertEqual(decision.outcome, GateOutcome.RESHAPE)
        self.assertEqual(decision.reason, "reshape:hinted_depth_0")

    def test_reshape_pending_row_written_on_reshape(self):
        """Gate RESHAPE outcome writes reshape_pending row to held_thoughts."""
        from theory_x.stage_gate.coherence_gate import GateOutcome
        content = "Test thought intentionally reshape-hinted."
        p = _packet(content, reshape_hint=True, reshape_depth=0)
        decision = self.gate.check(p)
        self.assertEqual(decision.outcome, GateOutcome.RESHAPE)
        time.sleep(0.05)

        rows = self.readers["beliefs"].read(
            "SELECT status, reshape_depth FROM held_thoughts WHERE content=?",
            (content,),
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "reshape_pending")
        self.assertEqual(rows[0]["reshape_depth"], 0)

    def test_reshape_depth_cap_at_2_falls_through_to_accept(self):
        """reshape_hint=True + depth=2 falls through to ACCEPT (cap reached)."""
        from theory_x.stage_gate.coherence_gate import GateOutcome
        p = _packet(
            "Twice-reshaped thought should now be accepted.",
            reshape_hint=True,
            reshape_depth=2,
        )
        decision = self.gate.check(p)
        self.assertEqual(decision.outcome, GateOutcome.ACCEPT)

    def test_reshape_depth_1_still_triggers_reshape(self):
        """reshape_hint=True + depth=1 still produces RESHAPE (1 < cap=2)."""
        from theory_x.stage_gate.coherence_gate import GateOutcome
        p = _packet(
            "Once-reshaped thought can be reshaped again.",
            reshape_hint=True,
            reshape_depth=1,
        )
        decision = self.gate.check(p)
        self.assertEqual(decision.outcome, GateOutcome.RESHAPE)
        self.assertEqual(decision.reason, "reshape:hinted_depth_1")


# ── ReshapeTransformer unit tests ─────────────────────────────────────────────

class TestReshapeTransformer(unittest.TestCase):

    def test_transform_produces_new_packet(self):
        """transform() returns ThoughtPacket with depth+1 and confidence decay."""
        from theory_x.stage_gate.transformer import ReshapeTransformer
        from theory_x.stage_gate.coherence_gate import ThoughtPacket

        voice = _mock_voice("Reframed thought captures the same essence clearly.")
        transformer = ReshapeTransformer(voice)

        packet = ThoughtPacket(
            content="Original thought about something important here.",
            source_node="fountain",
            confidence=0.80,
            metadata={"reshape_hint": True, "reshape_depth": 0},
        )
        result = transformer.transform(packet, original_thought_id=42, current_depth=0)

        self.assertIsNotNone(result)
        self.assertEqual(result.source_node, "reshape_transformer")
        self.assertAlmostEqual(result.confidence, 0.80 * 0.9, places=3)
        self.assertEqual(result.metadata["reshape_depth"], 1)
        self.assertEqual(result.metadata["original_from"], "fountain")
        self.assertEqual(result.metadata["original_thought_id"], 42)

    def test_transform_failure_returns_none(self):
        """transform() returns None when voice_client raises."""
        from theory_x.stage_gate.transformer import ReshapeTransformer
        from theory_x.stage_gate.coherence_gate import ThoughtPacket

        voice = MagicMock()
        voice.speak.side_effect = RuntimeError("voice down")
        transformer = ReshapeTransformer(voice)

        packet = ThoughtPacket(
            content="This will fail to transform.",
            source_node="fountain",
            confidence=0.75,
            metadata={"reshape_hint": True, "reshape_depth": 0},
        )
        result = transformer.transform(packet, original_thought_id=99, current_depth=0)
        self.assertIsNone(result)


# ── Resolver reshape processing ───────────────────────────────────────────────

class TestResolverReshape(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.zone = _make_zone(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _seed_reshape_pending(self, content, depth=0):
        from theory_x.stage_gate.coherence_gate import ThoughtPacket
        p = ThoughtPacket(
            content=content,
            source_node="fountain",
            confidence=0.70,
            metadata={"reshape_hint": True, "reshape_depth": depth},
        )
        return self.zone.put_reshape_pending(p, depth)

    def test_resolver_processes_reshape_pending(self):
        """tick() picks up reshape_pending rows, transforms, re-submits."""
        held_id = self._seed_reshape_pending(
            "Original thought about curiosity and pattern recognition always."
        )
        self.assertIsNotNone(held_id)
        time.sleep(0.02)

        voice = _mock_voice(
            "Curiosity about pattern recognition connects to active inquiry."
        )
        from theory_x.stage_gate.transformer import ReshapeTransformer
        transformer = ReshapeTransformer(voice)
        gate = _make_gate(self.writers, self.readers, holding_zone=self.zone)
        resolver = _make_resolver(
            self.zone, self.writers, transformer=transformer, gate=gate
        )
        resolver.set_gate(gate)

        resolver.tick()
        time.sleep(0.05)

        rows = self.readers["beliefs"].read(
            "SELECT status FROM held_thoughts WHERE id=?", (held_id,)
        )
        self.assertEqual(rows[0]["status"], "reshaped")

        resolutions = self.readers["beliefs"].read(
            "SELECT action FROM held_resolutions WHERE held_id=?", (held_id,)
        )
        self.assertEqual(len(resolutions), 1)
        self.assertEqual(resolutions[0]["action"], "reshaped")

    def test_resolver_failed_transform_marks_reshape_failed(self):
        """When transformer returns None, row is marked reshape_failed."""
        held_id = self._seed_reshape_pending(
            "Thought that will fail to transform due to voice error."
        )
        self.assertIsNotNone(held_id)
        time.sleep(0.02)

        voice = MagicMock()
        voice.speak.side_effect = RuntimeError("voice exploded")
        from theory_x.stage_gate.transformer import ReshapeTransformer
        transformer = ReshapeTransformer(voice)
        gate = _make_gate(self.writers, self.readers, holding_zone=self.zone)
        resolver = _make_resolver(
            self.zone, self.writers, transformer=transformer, gate=gate
        )
        resolver.tick()
        time.sleep(0.05)

        rows = self.readers["beliefs"].read(
            "SELECT status FROM held_thoughts WHERE id=?", (held_id,)
        )
        self.assertEqual(rows[0]["status"], "reshape_failed")

        resolutions = self.readers["beliefs"].read(
            "SELECT action, reason FROM held_resolutions WHERE held_id=?", (held_id,)
        )
        self.assertEqual(resolutions[0]["action"], "reshape_failed")
        self.assertEqual(resolutions[0]["reason"], "transformer_returned_none")

    def test_resolver_reshape_loop_bounded_at_10(self):
        """tick() processes at most 10 reshape_pending items."""
        # Seed at depth=1 so reshaped output (depth=2) falls through to ACCEPT
        # and does not re-queue, keeping the remaining-count arithmetic clean.
        for i in range(15):
            self._seed_reshape_pending(
                f"Thought number {i} about something interesting and novel.",
                depth=1,
            )
        time.sleep(0.05)

        voice = _mock_voice("Reframed thought preserving core meaning intact.")
        from theory_x.stage_gate.transformer import ReshapeTransformer
        transformer = ReshapeTransformer(voice)
        gate = _make_gate(self.writers, self.readers, holding_zone=self.zone)
        resolver = _make_resolver(
            self.zone, self.writers, transformer=transformer, gate=gate
        )
        resolver.tick()
        time.sleep(0.10)

        # voice.speak should have been called exactly 10 times (limit=10)
        self.assertEqual(voice.speak.call_count, 10)

        # 10 processed; 5 still pending
        remaining = self.readers["beliefs"].read(
            "SELECT COUNT(*) as n FROM held_thoughts WHERE status='reshape_pending'"
        )
        self.assertEqual(remaining[0]["n"], 5)

    def test_gate_unaffected_by_reshape_path_error(self):
        """Errors in put_reshape_pending do not affect gate decision outcome."""
        mock_zone = MagicMock()
        mock_zone.hold.return_value = None
        mock_zone.find_corroborations.return_value = []
        mock_zone.find_contradictions.return_value = []
        mock_zone.put_reshape_pending.side_effect = RuntimeError("zone exploded")

        gate = _make_gate(
            self.writers, self.readers, holding_zone=mock_zone
        )
        from theory_x.stage_gate.coherence_gate import GateOutcome
        p = _packet(
            "Reshape-hinted thought where zone explodes.",
            reshape_hint=True,
            reshape_depth=0,
        )
        decision = gate.check(p)
        self.assertEqual(decision.outcome, GateOutcome.RESHAPE)
        mock_zone.put_reshape_pending.assert_called_once()


if __name__ == "__main__":
    unittest.main()
