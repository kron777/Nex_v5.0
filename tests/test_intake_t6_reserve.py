"""NEX5_INTAKE_T6_RESERVE: the T6 standing-voice draw must not let AUTHORED
affinity saturation fully evict identity_loop / witnessed beliefs.

Background: the provenance affinity go-live lifted authored beliefs to 0.45-0.60,
filling the fixed top-N tier-6 standing-voice pool with authored content and
dropping identity_loop from 13.5% to 0% of it (a band collapse). The reserve flag
guarantees N of the slots to the highest-affinity NON-authored tier-6 beliefs.

Pure fixture test: in-memory beliefs DB, no embeddings (prewarm only reads ids).
"""
import os
import sqlite3
import unittest
from unittest import mock

from tests import _bootstrap  # noqa: F401

from theory_x.stage2_dynamic import intake_resonance as IR


class _FakeReader:
    """Minimal beliefs_reader: .read(sql, params) -> list[sqlite3.Row]."""

    def __init__(self, cx):
        self._cx = cx
        self._cx.row_factory = sqlite3.Row

    def read(self, sql, params=()):
        return self._cx.execute(sql, params).fetchall()


def _make_beliefs(n_authored=10, n_identity=4):
    cx = sqlite3.connect(":memory:")
    cx.execute(
        "CREATE TABLE beliefs (id INTEGER PRIMARY KEY, content TEXT, tier INTEGER, "
        "source TEXT, affinity REAL, reinforce_count INTEGER)"
    )
    rid = 1
    # authored tier-6 beliefs, HIGH affinity (0.55-0.60) -> saturate the pool
    for i in range(n_authored):
        cx.execute("INSERT INTO beliefs VALUES (?,?,?,?,?,?)",
                   (rid, f"authored thought {i}", 6, "fountain_insight", 0.60 - i * 0.001, 0))
        rid += 1
    # identity_loop tier-6 beliefs, LOWER affinity (witnessed band ~0.39)
    for i in range(n_identity):
        cx.execute("INSERT INTO beliefs VALUES (?,?,?,?,?,?)",
                   (rid, f"who I am {i}", 6, "identity_loop", 0.39 - i * 0.001, 0))
        rid += 1
    cx.commit()
    return cx


class TestT6Reserve(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("NEX5_INTAKE_T6_RESERVE", None)
        os.environ.pop("NEX5_INTAKE_TIGHT_CORE", None)

    def _standing_sources(self, cx):
        reader = _FakeReader(cx)
        ir = IR.IntakeResonance(reader, beliefs_writer=None, prewarm=True)
        src = {}
        for bid in ir._standing_ids:
            r = cx.execute("SELECT source FROM beliefs WHERE id=?", (bid,)).fetchone()
            src[r["source"]] = src.get(r["source"], 0) + 1
        return src, len(ir._standing_ids)

    def test_self_downtime_excluded_from_standing_voice(self):
        # self_downtime is tier-6 + witnessed, so without the exclusion it would win
        # a reserved slot (and accrue one row per restart, diluting identity share).
        # Give it a HIGH affinity so it would otherwise top the non-authored reserve;
        # assert it is absent from the standing-points even with the reserve on.
        cx = _make_beliefs(10, 2)
        cx.execute(
            "INSERT INTO beliefs VALUES (99, 'I was offline for 2h (clean). boot #7', "
            "6, 'self_downtime', 0.44, 0)"  # higher than any identity belief
        )
        cx.commit()
        with mock.patch.object(IR, "_STRIKING_T6_LIMIT", 5):
            os.environ["NEX5_INTAKE_T6_RESERVE"] = "3"
            src, _ = self._standing_sources(cx)
        self.assertEqual(src.get("self_downtime", 0), 0,
                         "self_downtime must never enter the standing voice")
        self.assertGreater(src.get("identity_loop", 0), 0,
                           "the reserved slots go to real non-authored voice instead")

    def test_default_off_authored_saturates(self):
        # LIMIT 5, 10 authored + 4 identity: top-5 is all authored, identity evicted.
        with mock.patch.object(IR, "_STRIKING_T6_LIMIT", 5):
            os.environ.pop("NEX5_INTAKE_T6_RESERVE", None)
            src, total = self._standing_sources(_make_beliefs(10, 4))
        self.assertEqual(total, 5)
        self.assertEqual(src.get("identity_loop", 0), 0, "identity should be evicted when off")
        self.assertEqual(src.get("fountain_insight", 0), 5)

    def test_reserve_guarantees_nonauthored_slots(self):
        with mock.patch.object(IR, "_STRIKING_T6_LIMIT", 5):
            os.environ["NEX5_INTAKE_T6_RESERVE"] = "2"
            src, total = self._standing_sources(_make_beliefs(10, 4))
        self.assertEqual(total, 5, "pool size unchanged")
        self.assertEqual(src.get("identity_loop", 0), 2, "2 slots reserved for identity")
        self.assertEqual(src.get("fountain_insight", 0), 3, "authored fills the rest")

    def test_reserve_bounded_by_available_nonauthored(self):
        # only 1 identity belief but reserve 3 -> include the 1, fill rest authored,
        # pool still full.
        with mock.patch.object(IR, "_STRIKING_T6_LIMIT", 5):
            os.environ["NEX5_INTAKE_T6_RESERVE"] = "3"
            src, total = self._standing_sources(_make_beliefs(10, 1))
        self.assertEqual(total, 5)
        self.assertEqual(src.get("identity_loop", 0), 1)
        self.assertEqual(src.get("fountain_insight", 0), 4)


if __name__ == "__main__":
    unittest.main()
