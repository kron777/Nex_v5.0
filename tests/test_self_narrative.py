"""SelfNarrative tests — Phase 26-build.

Covers:
- write_narrative inserts row with correct trigger, content, source_id, created_at
- format_for_prompt returns most recent N rows matching topic
- format_for_prompt returns "" when no rows match topic
- format_for_prompt returns "" when narrative_log is empty
- tick(context) is a no-op (no rows written, no exception)
- decay(now) is a no-op (no rows deleted, no exception)
- state() returns correct narrative_count after N writes
- state() returns last_write_ts=None when table is empty

Phase 26 trigger wiring (audit-completion):
- Gate ACCEPT on problem-relevant topic fires narrative write
- Gate ACCEPT below confidence threshold does not write
- ProblemMemory.open() fires problem_opened narrative
- ProblemMemory.close() fires problem_closed narrative with title
- NovelAssociation._scan() fires narrative only at _NARRATIVE_THRESHOLD
- NovelAssociation._scan() below narrative threshold does not write
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_sn_")
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


def _make_sn(writers, readers):
    from theory_x.stage_self_narrative.self_narrative import SelfNarrative
    return SelfNarrative(writers["conversations"], readers["conversations"])


class TestWriteNarrative(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.sn = _make_sn(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_write_narrative_inserts_row(self):
        """write_narrative inserts a row with correct fields."""
        before = time.time()
        self.sn.write_narrative(
            "I completed the goal: understand entropy",
            "goal_complete",
            42,
        )
        time.sleep(0.05)

        rows = self.readers["conversations"].read(
            "SELECT content, trigger, source_id, created_at FROM narrative_log"
        )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["content"], "I completed the goal: understand entropy")
        self.assertEqual(row["trigger"], "goal_complete")
        self.assertEqual(row["source_id"], 42)
        self.assertGreaterEqual(row["created_at"], before)
        self.assertLessEqual(row["created_at"], time.time())

    def test_write_narrative_source_id_nullable(self):
        """source_id may be None."""
        self.sn.write_narrative(
            "I noticed I am repeatedly returning to recursion",
            "groove",
            None,
        )
        time.sleep(0.05)

        rows = self.readers["conversations"].read(
            "SELECT source_id FROM narrative_log"
        )
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["source_id"])

    def test_write_narrative_multiple_rows(self):
        """Multiple calls produce multiple independent rows."""
        self.sn.write_narrative("I completed the goal: map the terrain", "goal_complete", 1)
        self.sn.write_narrative("I noticed I am repeatedly returning to identity", "groove", 7)
        time.sleep(0.05)

        rows = self.readers["conversations"].read(
            "SELECT trigger FROM narrative_log ORDER BY created_at ASC"
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["trigger"], "goal_complete")
        self.assertEqual(rows[1]["trigger"], "groove")


class TestFormatForPrompt(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.sn = _make_sn(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_format_for_prompt_empty_table_returns_empty_string(self):
        """Returns '' when narrative_log has no rows."""
        result = self.sn.format_for_prompt(None)
        self.assertEqual(result, "")

    def test_format_for_prompt_no_topic_match_returns_empty_string(self):
        """Returns '' when no entries match the topic."""
        self.sn.write_narrative("I completed the goal: explore recursion", "goal_complete", 1)
        time.sleep(0.05)

        ctx = MagicMock()
        ctx.current_topic = "entropy"
        result = self.sn.format_for_prompt(ctx)
        self.assertEqual(result, "")

    def test_format_for_prompt_returns_matching_rows(self):
        """Returns bullet lines for rows matching context.current_topic."""
        self.sn.write_narrative(
            "I completed the goal: understand consciousness", "goal_complete", 10
        )
        self.sn.write_narrative(
            "I noticed I am repeatedly returning to consciousness patterns",
            "groove", 5,
        )
        time.sleep(0.05)

        ctx = MagicMock()
        ctx.current_topic = "consciousness"
        result = self.sn.format_for_prompt(ctx)

        self.assertIn("consciousness", result)
        lines = result.strip().split("\n")
        self.assertEqual(len(lines), 2)
        for line in lines:
            self.assertTrue(line.startswith("- "))

    def test_format_for_prompt_returns_at_most_5_rows(self):
        """Caps output at N=5 rows even when more exist."""
        for i in range(8):
            self.sn.write_narrative(
                f"I completed the goal: task {i} consciousness",
                "goal_complete", i,
            )
        time.sleep(0.1)

        ctx = MagicMock()
        ctx.current_topic = "consciousness"
        result = self.sn.format_for_prompt(ctx)
        lines = [l for l in result.strip().split("\n") if l]
        self.assertLessEqual(len(lines), 5)
        self.assertEqual(len(lines), 5)

    def test_format_for_prompt_no_context_returns_recent_rows(self):
        """When context is None, returns most recent rows regardless of topic."""
        self.sn.write_narrative("I completed the goal: alpha", "goal_complete", 1)
        self.sn.write_narrative("I completed the goal: beta", "goal_complete", 2)
        time.sleep(0.05)

        result = self.sn.format_for_prompt(None)
        self.assertIn("- ", result)
        lines = [l for l in result.strip().split("\n") if l]
        self.assertEqual(len(lines), 2)

    def test_format_for_prompt_age_string_present(self):
        """Each bullet includes a parenthesised age string."""
        self.sn.write_narrative("I completed the goal: explore time", "goal_complete", 3)
        time.sleep(0.05)

        result = self.sn.format_for_prompt(None)
        self.assertRegex(result, r'\(\d+[mh] ago\)')


class TestSentienceNodeProtocol(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.sn = _make_sn(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_tick_is_noop(self):
        """tick() writes no rows and does not raise."""
        self.sn.tick(context=None)
        time.sleep(0.05)

        rows = self.readers["conversations"].read("SELECT * FROM narrative_log")
        self.assertEqual(len(rows), 0)

    def test_decay_is_noop(self):
        """decay() deletes no rows and does not raise."""
        self.sn.write_narrative("I completed the goal: survive", "goal_complete", 1)
        time.sleep(0.05)

        before = self.readers["conversations"].read("SELECT COUNT(*) AS n FROM narrative_log")
        self.sn.decay(time.time())
        time.sleep(0.05)
        after = self.readers["conversations"].read("SELECT COUNT(*) AS n FROM narrative_log")

        self.assertEqual(before[0]["n"], after[0]["n"])

    def test_state_returns_count_after_writes(self):
        """state() returns correct narrative_count after N writes."""
        for i in range(3):
            self.sn.write_narrative(f"I completed the goal: item {i}", "goal_complete", i)
        time.sleep(0.05)

        s = self.sn.state()
        self.assertEqual(s["narrative_count"], 3)
        self.assertIsNotNone(s["last_write_ts"])

    def test_state_last_write_ts_none_when_empty(self):
        """state() returns last_write_ts=None when narrative_log is empty."""
        s = self.sn.state()
        self.assertEqual(s["narrative_count"], 0)
        self.assertIsNone(s["last_write_ts"])


# ── Trigger 1: Gate ACCEPT on problem-relevant topic ─────────────────────────

class TestGateAcceptProblemTrigger(unittest.TestCase):
    """Gate ACCEPT on a problem-relevant thought fires a narrative write."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.sn = _make_sn(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_accept_above_confidence_writes_gate_accept_problem(self):
        from theory_x.stage7_sustained.problem_memory import ProblemMemory
        from theory_x.stage_gate.coherence_gate import CoherenceGate, ThoughtPacket
        ProblemMemory(self.writers["conversations"], self.readers["conversations"]).open(
            "recursive learning patterns", "How learning compounds over time"
        )
        gate = CoherenceGate(
            beliefs_reader=self.readers["beliefs"],
            beliefs_writer=self.writers["beliefs"],
            conversations_reader=self.readers["conversations"],
            self_narrative=self.sn,
        )
        packet = ThoughtPacket(
            content="New observation about recursive learning patterns",
            source_node="test",
            confidence=0.75,
        )
        gate.check(packet)
        time.sleep(0.05)

        rows = self.readers["conversations"].read(
            "SELECT trigger, source_id FROM narrative_log "
            "WHERE trigger='gate_accept_problem'"
        )
        self.assertEqual(len(rows), 1)
        self.assertIsNotNone(rows[0]["source_id"])

    def test_accept_below_confidence_threshold_does_not_write(self):
        from theory_x.stage7_sustained.problem_memory import ProblemMemory
        from theory_x.stage_gate.coherence_gate import CoherenceGate, ThoughtPacket
        ProblemMemory(self.writers["conversations"], self.readers["conversations"]).open(
            "recursive learning patterns", "How learning compounds over time"
        )
        gate = CoherenceGate(
            beliefs_reader=self.readers["beliefs"],
            beliefs_writer=self.writers["beliefs"],
            conversations_reader=self.readers["conversations"],
            self_narrative=self.sn,
        )
        packet = ThoughtPacket(
            content="New observation about recursive learning patterns",
            source_node="test",
            confidence=0.50,  # below _NARRATIVE_CONFIDENCE_THRESHOLD = 0.60
        )
        gate.check(packet)
        time.sleep(0.05)

        rows = self.readers["conversations"].read(
            "SELECT trigger FROM narrative_log WHERE trigger='gate_accept_problem'"
        )
        self.assertEqual(len(rows), 0)


# ── Trigger 2: Problem state transitions ─────────────────────────────────────

class TestProblemTransitionTrigger(unittest.TestCase):
    """ProblemMemory.open() and .close() fire SelfNarrative writes."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.sn = _make_sn(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_problem_open_writes_problem_opened_narrative(self):
        from theory_x.stage7_sustained.problem_memory import ProblemMemory
        pm = ProblemMemory(
            self.writers["conversations"],
            self.readers["conversations"],
            self_narrative=self.sn,
        )
        pm.open("understanding emergence", "How complexity arises from simplicity")
        time.sleep(0.05)

        rows = self.readers["conversations"].read(
            "SELECT content, trigger FROM narrative_log WHERE trigger='problem_opened'"
        )
        self.assertEqual(len(rows), 1)
        self.assertIn("understanding emergence", rows[0]["content"])

    def test_problem_close_writes_problem_closed_narrative_with_title(self):
        from theory_x.stage7_sustained.problem_memory import ProblemMemory
        pm = ProblemMemory(
            self.writers["conversations"],
            self.readers["conversations"],
            self_narrative=self.sn,
        )
        pid = pm.open("understanding emergence", "How complexity arises from simplicity")
        pm.close(pid)
        time.sleep(0.05)

        rows = self.readers["conversations"].read(
            "SELECT content, trigger FROM narrative_log WHERE trigger='problem_closed'"
        )
        self.assertEqual(len(rows), 1)
        self.assertIn("understanding emergence", rows[0]["content"])


# ── Trigger 3: Novel association threshold crossing ───────────────────────────

class TestNovelAssociationCrossingTrigger(unittest.TestCase):
    """NovelAssociation._scan() fires SelfNarrative only at _NARRATIVE_THRESHOLD."""

    def _make_na_with_mock_sn(self):
        sn = MagicMock()
        writer = MagicMock()
        writer.write.return_value = 1
        reader = MagicMock()
        from theory_x.stage10_imagination.novel_association import NovelAssociation
        na = NovelAssociation(writer, reader, self_narrative=sn)
        return na, sn

    def _run_scan_with_sim(self, sim):
        from theory_x.stage10_imagination.novel_association import _SIMILARITY_THRESHOLD
        na, sn = self._make_na_with_mock_sn()
        a = {"id": 1, "content": "concept alpha", "branch_id": "systems"}
        b = {"id": 2, "content": "concept beta",  "branch_id": "cognition"}
        mock_embeddings = MagicMock()
        mock_embeddings.embed_belief = MagicMock(return_value=[0.1] * 10)
        mock_embeddings.cosine = MagicMock(return_value=sim)
        with patch.object(na, "_pull_candidates", return_value=[a, b]):
            with patch.dict(sys.modules, {"theory_x.diversity.embeddings": mock_embeddings}):
                # Force re-import inside _scan by clearing cached module if present
                sys.modules.pop("theory_x.diversity.embeddings", None)
                sys.modules["theory_x.diversity.embeddings"] = mock_embeddings
                na._scan(time.time())
        return sn

    def test_at_narrative_threshold_fires_write(self):
        from theory_x.stage10_imagination.novel_association import _NARRATIVE_THRESHOLD
        sn = self._run_scan_with_sim(_NARRATIVE_THRESHOLD)
        sn.write_narrative.assert_called_once()
        trigger = sn.write_narrative.call_args[0][1]
        self.assertEqual(trigger, "novel_association_crossing")

    def test_below_narrative_threshold_does_not_fire(self):
        from theory_x.stage10_imagination.novel_association import _NARRATIVE_THRESHOLD
        sn = self._run_scan_with_sim(_NARRATIVE_THRESHOLD - 0.05)
        sn.write_narrative.assert_not_called()


if __name__ == "__main__":
    unittest.main()
