"""Tests for TN-4 ThrowNetEngine — orchestrator cycle."""
from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, call, patch

from theory_x.stage_throw_net.throw_net_engine import ThrowNetEngine
from theory_x.stage_gate.coherence_gate import GateDecision, GateOutcome


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_engine(
    pending=None,
    candidates=None,
    scored=None,
    gate_outcome=GateOutcome.ACCEPT,
):
    """Build a ThrowNetEngine with all dependencies mocked."""
    bw = MagicMock()
    br = MagicMock()
    td = MagicMock()
    tf = MagicMock()
    re = MagicMock()
    gate = MagicMock()

    td.pending_triggers.return_value = pending or []
    tf.run.return_value = candidates if candidates is not None else _default_candidates()
    re.run.return_value = scored if scored is not None else _default_scored()
    gate.check.return_value = GateDecision(outcome=gate_outcome, reason="test")

    eng = ThrowNetEngine(
        beliefs_writer=bw,
        beliefs_reader=br,
        trigger_detector=td,
        time_fetch=tf,
        refinement_engine=re,
        coherence_gate=gate,
    )
    return eng, bw, br, td, tf, re, gate


def _trigger_row(topic="hum", trigger_type="gate_reject", trigger_id=1):
    return {
        "id": trigger_id,
        "trigger_type": trigger_type,
        "topic": topic,
        "threshold_state": '{"count": 4}',
        "ts": 1234567890.0,
    }


def _default_candidates(n=5):
    return [
        {"content": f"content {i}", "source": "belief", "origin_id": i,
         "confidence": 0.7}
        for i in range(n)
    ]


def _default_scored(n=5, score=6):
    return [
        {
            "candidate": {"content": f"content {i}", "source": "belief",
                          "origin_id": i, "confidence": 0.7},
            "score": score,
            "max_score": 6,
            "checks": {},
            "buildable": score >= 3,
        }
        for i in range(n)
    ]


# ── run_session ───────────────────────────────────────────────────────────────

class TestRunSessionSqliteRow(unittest.TestCase):

    def test_run_session_accepts_sqlite_row_like_object(self):
        """sqlite3.Row has no .get() — must be normalized to dict first."""
        import sqlite3
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute(
            "CREATE TABLE t (id INTEGER, trigger_type TEXT, topic TEXT, "
            "threshold_state TEXT, ts REAL)"
        )
        conn.execute("INSERT INTO t VALUES (7, 'gate_reject', 'hum', '{}', 0.0)")
        row = conn.execute("SELECT * FROM t").fetchone()

        eng, *_ = _make_engine()
        result = eng.run_session(row)
        self.assertIn("session_id", result)
        self.assertEqual(result["topic"], "hum")
        conn.close()


class TestRunSessionSessionRow(unittest.TestCase):

    def test_run_session_creates_session_row(self):
        eng, bw, *_ = _make_engine()
        eng.run_session(_trigger_row())
        # First write call is the INSERT
        insert_sql = bw.write.call_args_list[0][0][0]
        self.assertIn("INSERT INTO throw_net_sessions", insert_sql)

    def test_run_session_completes_session_row_with_counts(self):
        eng, bw, *_ = _make_engine()
        eng.run_session(_trigger_row())
        # Second write call is the UPDATE
        update_sql = bw.write.call_args_list[1][0][0]
        self.assertIn("UPDATE throw_net_sessions", update_sql)

    def test_run_session_returns_session_dict_with_expected_keys(self):
        eng, *_ = _make_engine()
        result = eng.run_session(_trigger_row())
        for key in ("session_id", "status", "topic", "throw_count",
                    "refined_count", "accepted_count", "outcomes"):
            self.assertIn(key, result)


class TestRunSessionTimeFetch(unittest.TestCase):

    def test_run_session_calls_time_fetch_with_topic(self):
        eng, _, _, _, tf, *_ = _make_engine()
        eng.run_session(_trigger_row(topic="consciousness"))
        tf.run.assert_called_once_with("consciousness")

    def test_run_session_handles_zero_candidates_status_empty(self):
        eng, *_ = _make_engine(candidates=[])
        result = eng.run_session(_trigger_row())
        self.assertEqual(result["status"], "empty")
        self.assertEqual(result["throw_count"], 0)

    def test_run_session_throw_count_equals_candidates_returned(self):
        eng, *_ = _make_engine(candidates=_default_candidates(15))
        result = eng.run_session(_trigger_row())
        self.assertEqual(result["throw_count"], 15)


class TestRunSessionCap(unittest.TestCase):

    def test_run_session_caps_at_top_10(self):
        # 25 candidates → refinement returns 25 → engine slices to 10
        scored_25 = _default_scored(n=25)
        eng, _, _, _, _, re, gate = _make_engine(
            candidates=_default_candidates(25),
            scored=scored_25,
        )
        eng.run_session(_trigger_row())
        self.assertEqual(gate.check.call_count, 10)

    def test_run_session_refined_count_is_capped_value(self):
        scored_25 = _default_scored(n=25)
        eng, *_ = _make_engine(
            candidates=_default_candidates(25),
            scored=scored_25,
        )
        result = eng.run_session(_trigger_row())
        self.assertEqual(result["refined_count"], 10)


class TestRunSessionReshapeHint(unittest.TestCase):

    def test_run_session_sets_reshape_hint_when_score_lt_5(self):
        scored_low = _default_scored(n=1, score=4)
        eng, _, _, _, _, _, gate = _make_engine(
            candidates=_default_candidates(1),
            scored=scored_low,
        )
        eng.run_session(_trigger_row())
        packet = gate.check.call_args[0][0]
        self.assertTrue(packet.metadata.get("reshape_hint"))

    def test_run_session_no_reshape_hint_when_score_gte_5(self):
        scored_high = _default_scored(n=1, score=5)
        eng, _, _, _, _, _, gate = _make_engine(
            candidates=_default_candidates(1),
            scored=scored_high,
        )
        eng.run_session(_trigger_row())
        packet = gate.check.call_args[0][0]
        self.assertNotIn("reshape_hint", packet.metadata)


class TestRunSessionGate(unittest.TestCase):

    def test_run_session_calls_gate_check_for_each_candidate(self):
        eng, _, _, _, _, _, gate = _make_engine(
            candidates=_default_candidates(5),
            scored=_default_scored(n=5),
        )
        eng.run_session(_trigger_row())
        self.assertEqual(gate.check.call_count, 5)

    def test_run_session_uses_throw_net_dot_trigger_type_source_node(self):
        eng, _, _, _, _, _, gate = _make_engine(
            candidates=_default_candidates(1),
            scored=_default_scored(n=1),
        )
        eng.run_session(_trigger_row(trigger_type="gap_deflection"))
        packet = gate.check.call_args[0][0]
        self.assertEqual(packet.source_node, "throw_net.gap_deflection")

    def test_run_session_handles_gate_error_per_candidate(self):
        eng, _, _, _, _, _, gate = _make_engine(
            candidates=_default_candidates(3),
            scored=_default_scored(n=3),
        )
        gate.check.side_effect = Exception("gate exploded")
        result = eng.run_session(_trigger_row())
        # Should not raise; error counted in outcomes
        self.assertEqual(result["outcomes"]["error"], 3)
        self.assertEqual(result["outcomes"]["accept"], 0)

    def test_run_session_accepted_count_reflects_gate_accepts(self):
        scored = _default_scored(n=4)
        eng, _, _, _, _, _, gate = _make_engine(
            candidates=_default_candidates(4),
            scored=scored,
            gate_outcome=GateOutcome.ACCEPT,
        )
        result = eng.run_session(_trigger_row())
        self.assertEqual(result["accepted_count"], 4)


class TestRunSessionMarkFired(unittest.TestCase):

    def test_run_session_marks_trigger_fired(self):
        eng, _, _, td, *_ = _make_engine()
        sess_result = eng.run_session(_trigger_row(trigger_id=42))
        td.mark_fired.assert_called_once_with(42, sess_result["session_id"])

    def test_run_session_skips_mark_fired_when_trigger_id_none(self):
        eng, _, _, td, *_ = _make_engine()
        row = _trigger_row(trigger_id=None)
        eng.run_session(row)
        td.mark_fired.assert_not_called()


# ── run_pending ───────────────────────────────────────────────────────────────

class TestRunPending(unittest.TestCase):

    def test_run_pending_processes_all_pending_triggers(self):
        triggers = [_trigger_row(topic="hum"), _trigger_row(topic="silence")]
        eng, _, _, td, tf, *_ = _make_engine(pending=triggers)
        eng.run_pending()
        self.assertEqual(tf.run.call_count, 2)

    def test_run_pending_returns_session_dicts(self):
        triggers = [_trigger_row(topic="hum"), _trigger_row(topic="silence")]
        eng, *_ = _make_engine(pending=triggers)
        results = eng.run_pending()
        self.assertEqual(len(results), 2)
        for r in results:
            self.assertIn("session_id", r)

    def test_run_pending_handles_pending_triggers_error(self):
        eng, _, _, td, *_ = _make_engine()
        td.pending_triggers.side_effect = Exception("db gone")
        results = eng.run_pending()
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
