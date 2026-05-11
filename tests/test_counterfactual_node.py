"""CounterfactualNode unit tests — Phase 25b.

Tests 1–14 per COUNTERFACTUAL_NODE_SPEC.md §9.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_cn_")
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


def _make_cn(writers, readers, gate=None, time_fetch=None, refinement_engine=None):
    from theory_x.stage_counterfactual import CounterfactualNode
    if gate is None:
        gate = MagicMock()
        from theory_x.stage_gate.coherence_gate import GateDecision, GateOutcome
        gate.check.return_value = GateDecision(
            outcome=GateOutcome.REJECT, reason="default_mock"
        )
    if time_fetch is None:
        time_fetch = MagicMock()
        time_fetch.fetch_from_beliefs.return_value = []
    if refinement_engine is None:
        refinement_engine = MagicMock()
        refinement_engine.run.return_value = []
    return CounterfactualNode(
        beliefs_reader=readers["beliefs"],
        beliefs_writer=writers["beliefs"],
        conversations_reader=readers["conversations"],
        conversations_writer=writers["conversations"],
        coherence_gate=gate,
        time_fetch=time_fetch,
        refinement_engine=refinement_engine,
    )


def _seed_problem(writers, title="test problem", description="test description",
                  state="open", tags="[]"):
    now = time.time()
    writers["conversations"].write(
        "INSERT INTO open_problems "
        "(title, description, state, created_at, last_touched_at, tags) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (title, description, state, now, now, tags),
    )
    rows = writers["conversations"]._conn  # not available via Writer; use reader
    return None  # caller reads id separately


def _seed_problem_r(writers, readers, title="test problem",
                    description="test description", state="open", tags="[]"):
    now = time.time()
    writers["conversations"].write(
        "INSERT INTO open_problems "
        "(title, description, state, created_at, last_touched_at, tags) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (title, description, state, now, now, tags),
    )
    time.sleep(0.05)  # let writer flush
    rows = readers["conversations"].read(
        "SELECT id FROM open_problems WHERE title = ? AND state = ? ORDER BY id DESC LIMIT 1",
        (title, state),
    )
    return rows[0]["id"] if rows else None


def _accepted_gate():
    gate = MagicMock()
    from theory_x.stage_gate.coherence_gate import GateDecision, GateOutcome
    gate.check.return_value = GateDecision(outcome=GateOutcome.ACCEPT, reason="mock_accept")
    return gate


def _buildable_candidate(content="The relationship between recursion and computation "
                          "reveals deep structural patterns in formal systems."):
    return {
        "candidate": {
            "content": content,
            "source": "belief",
            "branch_id": "test_branch",
            "confidence": 0.8,
            "origin_id": 1,
        },
        "score": 5,
        "max_score": 6,
        "checks": {},
        "buildable": True,
    }


def _make_fetch_and_engine(content="The relationship between recursion and computation "
                            "reveals deep structural patterns in formal systems."):
    tf = MagicMock()
    tf.fetch_from_beliefs.return_value = [{
        "content": content,
        "source": "belief",
        "branch_id": "test_branch",
        "confidence": 0.8,
        "origin_id": 1,
    }]
    re_eng = MagicMock()
    re_eng.run.return_value = [_buildable_candidate(content)]
    return tf, re_eng


# ─────────────────────────────────────────────────────────────────────────────

class TestStateShape(unittest.TestCase):
    """Test 1, 3 — state dict shape."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_state_returns_expected_keys_before_tick(self):
        """Test 3 — state() has all expected keys after zero ticks."""
        cn = _make_cn(self.writers, self.readers)
        s = cn.state()
        for key in ("name", "tick_count", "problems_processed", "candidates_accepted"):
            self.assertIn(key, s)
        self.assertEqual(s["name"], "counterfactual_node")
        self.assertEqual(s["tick_count"], 0)
        self.assertEqual(s["problems_processed"], 0)
        self.assertEqual(s["candidates_accepted"], 0)

    def test_tick_returns_state_dict(self):
        """Test 1 — tick() return value has expected keys."""
        cn = _make_cn(self.writers, self.readers)
        result = cn.tick()
        for key in ("name", "tick_count", "problems_processed", "candidates_accepted"):
            self.assertIn(key, result)
        self.assertEqual(result["tick_count"], 1)


class TestNoProblems(unittest.TestCase):
    """Test 2 (equivalent) — no retrieval when no open problems exist."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_tick_with_no_open_problems_is_noop(self):
        """No candidates fetched when open_problems is empty."""
        tf = MagicMock()
        tf.fetch_from_beliefs.return_value = []
        cn = _make_cn(self.writers, self.readers, time_fetch=tf)
        cn.tick()
        tf.fetch_from_beliefs.assert_not_called()
        self.assertEqual(cn.state()["problems_processed"], 0)


class TestOpenStateFilter(unittest.TestCase):
    """Test 4 — only state='open' problems are processed."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_closed_problem_not_processed(self):
        """Closed problems are not retrieved for processing."""
        _seed_problem_r(self.writers, self.readers,
                        title="closed problem", state="closed")
        tf = MagicMock()
        tf.fetch_from_beliefs.return_value = []
        cn = _make_cn(self.writers, self.readers, time_fetch=tf)
        cn.tick()
        # No open problems → fetch should not be called
        tf.fetch_from_beliefs.assert_not_called()

    def test_open_problem_is_processed(self):
        """Open problems trigger fetch_from_beliefs."""
        _seed_problem_r(self.writers, self.readers, title="open problem", state="open")
        tf = MagicMock()
        tf.fetch_from_beliefs.return_value = []
        cn = _make_cn(self.writers, self.readers, time_fetch=tf)
        cn.tick()
        tf.fetch_from_beliefs.assert_called_once()


class TestThoughtPacketShape(unittest.TestCase):
    """Tests 5, 6 — ThoughtPacket carries correct problem_id and source_node."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_thought_packet_problem_id_in_metadata(self):
        """Test 5 — metadata["problem_id"] equals the open problem's id."""
        problem_id = _seed_problem_r(self.writers, self.readers,
                                      title="recursion problem")
        self.assertIsNotNone(problem_id)

        tf, re_eng = _make_fetch_and_engine()
        gate = MagicMock()
        from theory_x.stage_gate.coherence_gate import GateDecision, GateOutcome
        gate.check.return_value = GateDecision(
            outcome=GateOutcome.REJECT, reason="mock"
        )
        cn = _make_cn(self.writers, self.readers, gate=gate,
                      time_fetch=tf, refinement_engine=re_eng)
        cn.tick()

        self.assertTrue(gate.check.called)
        packet = gate.check.call_args[0][0]
        self.assertEqual(packet.metadata["problem_id"], problem_id)

    def test_thought_packet_source_node_includes_problem_id(self):
        """Test 6 — source_node = 'counterfactual.{problem_id}'."""
        problem_id = _seed_problem_r(self.writers, self.readers,
                                      title="source node test")
        self.assertIsNotNone(problem_id)

        tf, re_eng = _make_fetch_and_engine()
        gate = MagicMock()
        from theory_x.stage_gate.coherence_gate import GateDecision, GateOutcome
        gate.check.return_value = GateDecision(
            outcome=GateOutcome.REJECT, reason="mock"
        )
        cn = _make_cn(self.writers, self.readers, gate=gate,
                      time_fetch=tf, refinement_engine=re_eng)
        cn.tick()

        packet = gate.check.call_args[0][0]
        self.assertEqual(packet.source_node, f"counterfactual.{problem_id}")


class TestGateErrorHandling(unittest.TestCase):
    """Test 7 — gate errors per packet are caught; tick continues."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_gate_exception_does_not_abort_tick(self):
        """gate.check() raising an exception is caught; tick returns normally."""
        _seed_problem_r(self.writers, self.readers, title="gate error test")

        tf, re_eng = _make_fetch_and_engine()
        gate = MagicMock()
        gate.check.side_effect = RuntimeError("gate exploded")
        cn = _make_cn(self.writers, self.readers, gate=gate,
                      time_fetch=tf, refinement_engine=re_eng)
        # Should not raise
        result = cn.tick()
        self.assertEqual(result["tick_count"], 1)


class TestPromotionThreshold(unittest.TestCase):
    """Tests 8, 9 — promotion fires at threshold, not below."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _insert_accepted_beliefs(self, problem_id, count):
        """Directly insert beliefs linked to problem_id to simulate prior accepts."""
        for i in range(count):
            self.writers["beliefs"].write(
                "INSERT OR IGNORE INTO beliefs "
                "(content, tier, confidence, source, problem_id, created_at) "
                "VALUES (?, 3, 0.65, 'counterfactual_node', ?, ?)",
                (f"prior accepted belief {i} for problem {problem_id} with unique content",
                 problem_id, time.time()),
            )
        time.sleep(0.05)

    def test_move_fires_when_threshold_reached(self):
        """Test 8 — problem moves to review_queue when accept count >= 3."""
        problem_id = _seed_problem_r(self.writers, self.readers,
                                      title="promote me problem",
                                      tags='["test-tag"]')
        self.assertIsNotNone(problem_id)

        # Pre-insert 2 accepted beliefs (need one more to trigger)
        self._insert_accepted_beliefs(problem_id, 2)

        # One more ACCEPT this tick → total = 3 → promotion
        content = ("The structural analysis of recursive systems reveals "
                   "an underlying computational invariant across all domains.")
        tf, re_eng = _make_fetch_and_engine(content=content)
        gate = _accepted_gate()
        cn = _make_cn(self.writers, self.readers, gate=gate,
                      time_fetch=tf, refinement_engine=re_eng)
        cn.tick()
        time.sleep(0.1)

        # Problem should now be in review_queue, not open_problems
        rq = self.readers["conversations"].read(
            "SELECT id FROM review_queue WHERE id = ?", (problem_id,)
        )
        self.assertEqual(len(rq), 1, "Problem should be in review_queue")

        op = self.readers["conversations"].read(
            "SELECT id FROM open_problems WHERE id = ?", (problem_id,)
        )
        self.assertEqual(len(op), 0, "Problem should be gone from open_problems")

    def test_move_does_not_fire_below_threshold(self):
        """Test 9 — problem stays in open_problems when accept count < 3."""
        problem_id = _seed_problem_r(self.writers, self.readers,
                                      title="stay open problem")
        self.assertIsNotNone(problem_id)

        # Only 1 accepted belief pre-seeded; one more this tick → total = 2
        self._insert_accepted_beliefs(problem_id, 1)

        content = ("Exploring the boundaries of computation through recursive "
                   "structures and their emergent properties in complex systems.")
        tf, re_eng = _make_fetch_and_engine(content=content)
        gate = _accepted_gate()
        cn = _make_cn(self.writers, self.readers, gate=gate,
                      time_fetch=tf, refinement_engine=re_eng)
        cn.tick()
        time.sleep(0.1)

        # Problem should still be in open_problems
        op = self.readers["conversations"].read(
            "SELECT id FROM open_problems WHERE id = ?", (problem_id,)
        )
        self.assertEqual(len(op), 1, "Problem should still be in open_problems")
        rq = self.readers["conversations"].read(
            "SELECT id FROM review_queue WHERE id = ?", (problem_id,)
        )
        self.assertEqual(len(rq), 0, "Problem should not be in review_queue yet")


class TestPromotionIdempotency(unittest.TestCase):
    """Test 10 — move does not re-fire if already in review_queue."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_second_promotion_attempt_is_noop(self):
        """Problem already in review_queue → no duplicate INSERT, no crash."""
        problem_id = _seed_problem_r(self.writers, self.readers,
                                      title="already promoted problem")
        self.assertIsNotNone(problem_id)

        # Pre-populate review_queue with the same id
        now = time.time()
        self.writers["conversations"].write(
            "INSERT INTO review_queue (id, title, description, created_at, flagged_at, tags) "
            "VALUES (?, 'already promoted problem', '', ?, ?, '[]')",
            (problem_id, now, now),
        )
        time.sleep(0.05)

        # Seed 3 accepted beliefs so _accept_count_for returns >= threshold
        for i in range(3):
            self.writers["beliefs"].write(
                "INSERT OR IGNORE INTO beliefs "
                "(content, tier, confidence, source, problem_id, created_at) "
                "VALUES (?, 3, 0.65, 'counterfactual_node', ?, ?)",
                (f"idempotency belief {i} with unique content for problem {problem_id}",
                 problem_id, time.time()),
            )
        time.sleep(0.05)

        content = ("Idempotency test belief with sufficient length for scoring "
                   "through the refinement engine and coherence gate pipeline.")
        tf, re_eng = _make_fetch_and_engine(content=content)
        gate = _accepted_gate()
        cn = _make_cn(self.writers, self.readers, gate=gate,
                      time_fetch=tf, refinement_engine=re_eng)
        # Should not raise; review_queue should still have exactly one row
        cn.tick()
        time.sleep(0.1)

        rq = self.readers["conversations"].read(
            "SELECT id FROM review_queue WHERE id = ?", (problem_id,)
        )
        self.assertEqual(len(rq), 1, "Should still be exactly one review_queue row")


class TestTagsInherited(unittest.TestCase):
    """Test 11 — tags are inherited on move to review_queue."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_tags_copied_to_review_queue(self):
        """review_queue.tags equals open_problems.tags at move time."""
        expected_tags = '["recursion","computation","formal-systems"]'
        problem_id = _seed_problem_r(self.writers, self.readers,
                                      title="tagged problem",
                                      tags=expected_tags)
        self.assertIsNotNone(problem_id)

        # Pre-insert 2 beliefs; one ACCEPT this tick → total 3
        for i in range(2):
            self.writers["beliefs"].write(
                "INSERT OR IGNORE INTO beliefs "
                "(content, tier, confidence, source, problem_id, created_at) "
                "VALUES (?, 3, 0.65, 'counterfactual_node', ?, ?)",
                (f"tag inheritance prior belief {i} unique for problem {problem_id}",
                 problem_id, time.time()),
            )
        time.sleep(0.05)

        content = ("Formal systems demonstrate that recursion and computation share "
                   "deep structural invariants observable across logical frameworks.")
        tf, re_eng = _make_fetch_and_engine(content=content)
        gate = _accepted_gate()
        cn = _make_cn(self.writers, self.readers, gate=gate,
                      time_fetch=tf, refinement_engine=re_eng)
        cn.tick()
        time.sleep(0.1)

        rq = self.readers["conversations"].read(
            "SELECT tags FROM review_queue WHERE id = ?", (problem_id,)
        )
        self.assertEqual(len(rq), 1, "Should be in review_queue")
        self.assertEqual(rq[0]["tags"], expected_tags)


class TestSchemaMigrations(unittest.TestCase):
    """Tests 12, 13 — schema migrations are idempotent."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_review_queue_table_exists(self):
        """Test 12 — review_queue table created by init_db."""
        rows = self.readers["conversations"].read(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='review_queue'"
        )
        self.assertEqual(len(rows), 1, "review_queue table should exist")

    def test_beliefs_problem_id_column_exists(self):
        """Test 13 — beliefs.problem_id column created by init_db."""
        import sqlite3
        from substrate import db_paths
        paths = db_paths()
        with sqlite3.connect(paths["beliefs"]) as conn:
            cols = [row[1] for row in conn.execute("PRAGMA table_info(beliefs)").fetchall()]
        self.assertIn("problem_id", cols, "beliefs.problem_id column should exist")

    def test_review_queue_migration_is_idempotent(self):
        """Test 12b — running migrations again does not raise."""
        from substrate import db_paths
        from substrate.init_db import _apply_migrations
        from substrate import Writer
        paths = db_paths()
        w = Writer(paths["conversations"], name="conversations")
        try:
            _apply_migrations({"conversations": w})
        finally:
            w.close()


class TestSentienceNodeProtocol(unittest.TestCase):
    """Test 14 — SentienceNode protocol satisfied."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_isinstance_sentience_node(self):
        """Test 14 — CounterfactualNode implements SentienceNode protocol."""
        from theory_x import SentienceNode
        cn = _make_cn(self.writers, self.readers)
        self.assertIsInstance(cn, SentienceNode)


if __name__ == "__main__":
    unittest.main()
