"""Tests for provenance — self-grounded vs mirrored (NEX5_PROVENANCE).

Provenance, not emotional authentication: the module may say a reply is mostly
Jon's own turn handed back, or that nothing is established. It may never claim a
reply is a genuine feeling, authentic, or self-grounded — grounding did not
discriminate in measurement, so there is no such verdict to reach.

Directions tested: mirror reads high on a reply that hands the turn back and low
on one that does not; the verdict vocabulary is closed; the cue fires only above
its (stricter) threshold and carries provenance language only; the snapshot is
written pre-turn when armed and is inert when the flag is off; everything is
fail-safe.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

from theory_x.stage_provenance import provenance as P

_USER = "Nex, yes — exactly. The action of returning, catching those early drifts toward narratives and snapping back to direct observation."
_MIRRORED = "Yes, exactly. The action of returning — catching those early drifts toward narratives and snapping back to direct observation."
_OWN = "I notice the belief graph has been quiet on that. What I hold is nearer to a slow accretion than a snap."


class TestMirrorRead(unittest.TestCase):

    def test_mirrored_reply_reads_high(self):
        r = P.mirror_read(_MIRRORED, _USER)
        self.assertGreaterEqual(r["mirror"], P.MIRROR_DOMINANT)
        self.assertGreater(r["copy_rate"], 0.5)

    def test_own_reply_reads_low(self):
        r = P.mirror_read(_OWN, _USER)
        self.assertLess(r["mirror"], P.MIRROR_DOMINANT)

    def test_failsafe_on_empty_and_none(self):
        for reply, turn in ((None, _USER), (_MIRRORED, None), ("", ""), ("  ", _USER)):
            self.assertEqual(P.mirror_read(reply, turn)["mirror"], 0.0)


class TestVerdictHardLine(unittest.TestCase):
    """The hard line, enforced as a test: provenance only, never authentication."""

    def test_verdict_vocabulary_is_closed(self):
        for m in (0.0, 0.2, 0.449, 0.45, 0.8, 1.0, None, "x"):
            self.assertIn(P.verdict_for(m if not isinstance(m, str) else 0.0),
                          (P.MIRROR, P.UNSET))

    def test_no_self_grounded_or_authenticity_language_is_emitted(self):
        """Checks what the module can EMIT, not what its docstring discusses."""
        banned = ("genuine", "authentic", "real feeling", "really feel",
                  "truly feel", "self-grounded", "announce your feelings")
        self.assertEqual(P.MIRROR, "mirror-dominant")
        self.assertEqual(P.UNSET, "not established")
        emitted = [P.MIRROR, P.UNSET, P.honesty_cue(1.0)]
        for m in (0.0, 0.3, 0.45, 0.6, 1.0):
            out = P.read_provenance(_MIRRORED, _USER, snap={}, log=False)
            emitted += [out["verdict"], out["cue"]]
            emitted.append(P.honesty_cue(m))
        for s in emitted:
            for word in banned:
                self.assertNotIn(word, (s or "").lower())

    def test_cue_only_above_its_threshold(self):
        self.assertEqual(P.honesty_cue(P.CUE_THRESHOLD - 0.01), "")
        self.assertEqual(P.honesty_cue(0.0), "")
        self.assertTrue(P.honesty_cue(P.CUE_THRESHOLD))
        # stricter than the verdict line, so a flagged reply is not always cued
        self.assertGreater(P.CUE_THRESHOLD, P.MIRROR_DOMINANT)

    def test_cue_is_failsafe(self):
        self.assertEqual(P.honesty_cue(None), "")


class TestReadProvenance(unittest.TestCase):

    def test_read_returns_verdict_and_cue(self):
        out = P.read_provenance(_MIRRORED, _USER, snap={}, log=False)
        self.assertEqual(out["verdict"], P.MIRROR)
        self.assertIn("mirror", out)
        self.assertIn("grounding_hint", out)

    def test_read_is_failsafe(self):
        out = P.read_provenance(None, None, snap=None, log=False)
        self.assertEqual(out["verdict"], P.UNSET)
        self.assertEqual(out["cue"], "")


class _FakeReader:
    def __init__(self, rows):
        self.rows = rows

    def read(self, sql, params=()):
        for key, rows in self.rows.items():
            if key in sql:
                return rows
        return []


class _FakeWriter:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)

    def write(self, sql, params=()):
        self.conn.execute(sql, params)
        self.conn.commit()


class TestSnapshot(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nex5_prov_")
        self.db = str(Path(self.tmp) / "conversations.db")
        self.writer = _FakeWriter(self.db)
        self.readers = {
            "beliefs": _FakeReader({"FROM beliefs": [{"id": 11, "content": "a standing belief about meaning forming slowly"}]}),
            "dynamic": _FakeReader({"current_focus": [{"problem_id": 7}],
                                    "fountain_events": [{"thought": "a pre-turn thought"}]}),
            "conversations": _FakeReader({"open_problems": [{"title": "the focus"}],
                                          "affect_state": [{"valence": 0.4, "arousal": 0.2,
                                                            "stability": 0.9,
                                                            "mood_label": "positive"}]}),
        }
        self._prev = os.environ.pop("NEX5_PROVENANCE", None)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.pop("NEX5_PROVENANCE", None)
        if self._prev is not None:
            os.environ["NEX5_PROVENANCE"] = self._prev
        P._table_ready = False

    def test_flag_off_writes_nothing(self):
        snap = P.provenance_snapshot(self.readers, self.writer, "S", "hello")
        self.assertEqual(snap, {})
        rows = self.writer.conn.execute(
            "SELECT name FROM sqlite_master WHERE name='provenance_snapshots'").fetchall()
        self.assertEqual(rows, [])

    def test_armed_writes_pre_turn_state(self):
        os.environ["NEX5_PROVENANCE"] = "1"
        snap = P.provenance_snapshot(self.readers, self.writer, "S", "hello", now=123.0)
        self.assertEqual(snap["focus_problem_id"], 7)
        self.assertEqual(snap["belief_ids"], [11])
        self.assertEqual(snap["mood_label"], "positive")
        row = self.writer.conn.execute(
            "SELECT session_id, ts, focus_problem_id, belief_ids, mood_label, user_turn "
            "FROM provenance_snapshots").fetchone()
        self.assertEqual(row[0], "S")
        self.assertEqual(row[2], 7)
        self.assertEqual(row[4], "positive")
        self.assertEqual(row[5], "hello")

    def test_snapshot_failsafe_on_broken_readers(self):
        os.environ["NEX5_PROVENANCE"] = "1"
        snap = P.provenance_snapshot(None, None, "S", "hello")
        self.assertEqual(snap.get("belief_ids"), [])


if __name__ == "__main__":
    unittest.main()
