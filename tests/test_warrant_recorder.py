"""Tests for the warrant recorder (NEX5_WARRANT_RECORD) — append-only logging of
survival checks and per-belief use days, plus the retrieval-log keep-on-restart
gate in the fountain generator."""
from __future__ import annotations

import os
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

from substrate import Reader
from theory_x.stage_warrant import recorder as rec

_DAY = 86400
_T0 = 1_790_000_000.0


class _W:
    """Minimal writer without write_many (like TaggingBeliefWriter)."""
    def __init__(self, path):
        self.c = sqlite3.connect(path)

    def write(self, sql, params=()):
        self.c.execute(sql, params)
        self.c.commit()


def _beliefs(path):
    c = sqlite3.connect(path)
    c.executescript(
        "CREATE TABLE beliefs (id INTEGER PRIMARY KEY, content TEXT, tier INTEGER, "
        " locked INTEGER DEFAULT 0, paused INTEGER DEFAULT 0);"
        "CREATE TABLE synergizer_log (id INTEGER PRIMARY KEY, ts REAL, belief_id_a INTEGER, "
        " belief_id_b INTEGER);"
        "CREATE TABLE belief_lineage (child_id INTEGER, parent_id INTEGER, relationship TEXT, created_at REAL, "
        " PRIMARY KEY (child_id, parent_id, relationship));"
        "CREATE TABLE arc_members (arc_id INTEGER, belief_id INTEGER, position INTEGER, role TEXT, "
        " joined_at REAL, PRIMARY KEY (arc_id, belief_id));")
    rows = [(i, f"plain belief number {i} about ordinary things", t, 0, 0)
            for i, t in [(1, 3), (2, 3), (3, 3), (4, 6), (5, 6), (6, 7), (7, 7), (8, 7)]]
    rows += [(9, "a locked keystone", 1, 1, 0), (10, "paused one", 7, 0, 1)]
    c.executemany("INSERT INTO beliefs VALUES (?,?,?,?,?)", rows)
    c.executemany("INSERT INTO synergizer_log VALUES (?,?,?,?)",
                  [(1, _T0, 4, 6), (2, _T0 + 3600, 4, 7)])          # 4 used twice same day
    c.execute("INSERT INTO belief_lineage VALUES (50, 4, 'test', ?)", (_T0 + 2 * _DAY,))
    c.execute("INSERT INTO arc_members VALUES (1, 6, 0, 'test', ?)", (_T0 + 5 * _DAY,))
    c.commit(); c.close()


def _dynamic(path):
    c = sqlite3.connect(path)
    c.executescript(
        "CREATE TABLE fountain_retrieval_log (id INTEGER PRIMARY KEY, fire_id INTEGER, "
        " belief_id INTEGER, slot TEXT, ts REAL);"
        "CREATE TABLE fountain_events (id INTEGER PRIMARY KEY, ts REAL, anchor_belief_id INTEGER);")
    c.executemany("INSERT INTO fountain_retrieval_log VALUES (?,?,?,?,?)",
                  [(1, 1, 5, "seed", _T0), (2, 1, 5, "seed", _T0 + 10 * _DAY)])
    c.execute("INSERT INTO fountain_events VALUES (1, ?, 5)", (_T0 + 10 * _DAY + 60,))
    c.commit(); c.close()


class TestRecorder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bdb = str(Path(self.tmp.name) / "beliefs.db")
        self.ddb = str(Path(self.tmp.name) / "dynamic.db")
        _beliefs(self.bdb); _dynamic(self.ddb)
        self.r = rec.WarrantRecorder(_W(self.bdb), Reader(self.bdb), Reader(self.ddb))
        self._per_band = rec._PER_BAND
        self._use_batch = rec._USE_BATCH

    def tearDown(self):
        rec._PER_BAND = self._per_band
        rec._USE_BATCH = self._use_batch
        self.tmp.cleanup()

    def _q(self, sql):
        c = sqlite3.connect(self.bdb)
        try:
            return c.execute(sql).fetchall()
        finally:
            c.close()

    def test_survival_covers_t7_and_skips_locked_paused(self):
        n = self.r.survival_cycle(now=_T0)
        self.assertEqual(n, 8)                       # 3 x T3, 2 x T6, 3 x T7
        tiers = {t for (t,) in self._q("SELECT DISTINCT tier FROM belief_survival")}
        self.assertEqual(tiers, {3, 6, 7})
        ids = {i for (i,) in self._q("SELECT belief_id FROM belief_survival")}
        self.assertNotIn(9, ids); self.assertNotIn(10, ids)
        self.assertEqual(self._q("SELECT MIN(passed) FROM belief_survival")[0][0], 1)

    def test_survival_rotates_and_wraps(self):
        rec._PER_BAND = 2
        self.r.survival_cycle(now=_T0)
        self.r.survival_cycle(now=_T0 + 1)
        self.r.survival_cycle(now=_T0 + 2)
        t7 = [i for (i,) in self._q("SELECT belief_id FROM belief_survival WHERE tier=7 ORDER BY id")]
        self.assertEqual(t7[:4], [6, 7, 8, 6])       # 2 per cycle, wraps back to the start
        self.assertEqual(set(t7), {6, 7, 8})

    def test_use_days_counts_distinct_days_and_is_idempotent(self):
        self.r.use_cycle(now=_T0 + 11 * _DAY)
        got = dict(self._q("SELECT belief_id, days FROM belief_use_days"))
        self.assertEqual(got[4], 2)                  # synergizer x2 same day + lineage day+2
        self.assertEqual(got[5], 2)                  # retrieval day0 + day10 (+anchor day10 dedup)
        self.assertEqual(got[6], 2)                  # synergizer day0 + arc day5
        self.assertEqual(got[7], 1)
        self.assertEqual(self.r.use_cycle(now=_T0 + 12 * _DAY), 0)    # cursors hold
        self.assertEqual(dict(self._q("SELECT belief_id, days FROM belief_use_days")), got)

    def test_lineage_and_arc_cursors_use_stable_composite_primary_keys(self):
        rec._USE_BATCH = 2
        same_ts = _T0 + 30 * _DAY
        c = sqlite3.connect(self.bdb)
        # Leave a rowid gap before the tied rows. VACUUM will renumber their
        # hidden rowids, but must not disturb the declared composite-key cursor.
        c.execute(
            "INSERT INTO belief_lineage (child_id, parent_id, relationship, created_at) "
            "VALUES (99, 99, 'temporary', ?)", (same_ts,)
        )
        c.execute(
            "INSERT INTO arc_members (arc_id, belief_id, position, role, joined_at) "
            "VALUES (1, 101, 99, 'temporary', ?)", (same_ts,)
        )
        c.executemany(
            "INSERT INTO belief_lineage (child_id, parent_id, relationship, created_at) "
            "VALUES (?, ?, 'test', ?)",
            [(100 + i, 101, same_ts) for i in range(5)],
        )
        c.executemany(
            "INSERT INTO arc_members (arc_id, belief_id, position, role, joined_at) "
            "VALUES (1, ?, ?, 'test', ?)",
            [(102 + i, i, same_ts) for i in range(5)],
        )
        c.execute("DELETE FROM belief_lineage WHERE relationship='temporary'")
        c.execute("DELETE FROM arc_members WHERE role='temporary'")
        # Assign deliberately sparse, large hidden rowids so VACUUM must
        # compact them. These are not declared keys and must never be cursors.
        c.execute(
            "UPDATE belief_lineage SET rowid=1000000 + child_id "
            "WHERE child_id BETWEEN 100 AND 104"
        )
        c.execute(
            "UPDATE arc_members SET rowid=2000000 + belief_id "
            "WHERE belief_id BETWEEN 102 AND 106"
        )
        c.commit()
        c.close()

        # First page consumes the original fixture row and the first tied row.
        self.r.use_cycle(now=same_ts)
        with sqlite3.connect(self.bdb) as db:
            rowid_before = db.execute(
                "SELECT rowid FROM belief_lineage WHERE child_id=100"
            ).fetchone()[0]
            arc_rowid_before = db.execute(
                "SELECT rowid FROM arc_members WHERE belief_id=102"
            ).fetchone()[0]
        # VACUUM is permitted, but not required, to renumber hidden rowids.
        # Run it between pages, then force a remap to exercise the exact
        # instability the cursor must not depend on.
        self.r._w.c.execute("VACUUM")
        self.r._w.c.execute(
            "UPDATE belief_lineage SET rowid=200 + child_id "
            "WHERE child_id BETWEEN 100 AND 104"
        )
        self.r._w.c.execute(
            "UPDATE arc_members SET rowid=300 + belief_id "
            "WHERE belief_id BETWEEN 102 AND 106"
        )
        self.r._w.c.commit()
        with sqlite3.connect(self.bdb) as db:
            rowid_after = db.execute(
                "SELECT rowid FROM belief_lineage WHERE child_id=100"
            ).fetchone()[0]
            arc_rowid_after = db.execute(
                "SELECT rowid FROM arc_members WHERE belief_id=102"
            ).fetchone()[0]
        self.assertNotEqual(rowid_before, rowid_after)
        self.assertNotEqual(arc_rowid_before, arc_rowid_after)

        for offset in range(1, 5):
            self.r.use_cycle(now=same_ts + offset)

        lineage_day = int(same_ts // _DAY)
        arc_day = int(same_ts // _DAY)
        lineage = self._q(
            "SELECT days FROM belief_use_days WHERE belief_id=101"
        )
        self.assertEqual(lineage[0][0], 1)
        self.assertEqual(
            self._q("SELECT COUNT(*) FROM belief_use_day WHERE belief_id=101")[0][0],
            1,
        )
        self.assertEqual(
            {row[0] for row in self._q(
                "SELECT belief_id FROM belief_use_day WHERE belief_id BETWEEN 102 AND 106"
            )},
            {102, 103, 104, 105, 106},
        )
        self.assertEqual(self.r._tuple_cursor("use_lineage_pk", (0, 0, "")),
                         (104, 101, "test"))
        self.assertEqual(self.r._tuple_cursor("use_arc_pk", (0, 0)),
                         (1, 106))
    def test_legacy_timestamp_cursor_schema_migrates_without_reset(self):
        old_value = _T0 + 2 * _DAY
        self.r._w.write(
            "CREATE TABLE warrant_record_cursor (name TEXT PRIMARY KEY, value REAL NOT NULL)"
        )
        self.r._w.write(
            "INSERT INTO warrant_record_cursor (name, value) VALUES (?, ?)",
            ("use_lineage_ts", old_value),
        )
        self.r._ensure()
        columns = {r["name"] for r in self.r._br.read(
            "PRAGMA table_info(warrant_record_cursor)"
        )}
        self.assertIn("tie_id", columns)
        cursor = self.r._cursor_pair("use_lineage_ts")
        self.assertEqual(cursor, (old_value, 0))

    def test_use_days_increment_on_new_day_only(self):
        self.r.use_cycle(now=_T0)
        c = sqlite3.connect(self.ddb)
        c.execute("INSERT INTO fountain_retrieval_log VALUES (3, 2, 5, 'seed', ?)", (_T0 + 10 * _DAY + 5,))
        c.execute("INSERT INTO fountain_retrieval_log VALUES (4, 3, 5, 'seed', ?)", (_T0 + 20 * _DAY,))
        c.commit(); c.close()
        self.r.use_cycle(now=_T0 + 21 * _DAY)
        self.assertEqual(self._q("SELECT days FROM belief_use_days WHERE belief_id=5")[0][0], 3)

    def test_identity_block_retrievals_are_not_use(self):
        # The guaranteed identity block shows its beliefs every fire by
        # construction; that is not reliance, so it must not earn use days.
        c = sqlite3.connect(self.ddb)
        c.executemany("INSERT INTO fountain_retrieval_log VALUES (?,?,?,?,?)",
                      [(3, 2, 9, "identity_block", _T0 + 1 * _DAY),
                       (4, 3, 9, "identity_block", _T0 + 2 * _DAY),
                       (5, 4, 9, "identity_block", _T0 + 3 * _DAY)])
        c.commit(); c.close()
        self.r.use_cycle(now=_T0 + 4 * _DAY)
        self.assertEqual(self._q("SELECT days FROM belief_use_days WHERE belief_id=9"), [])
        # the cursor moved past them: a later ordinary retrieval still counts once
        c = sqlite3.connect(self.ddb)
        c.execute("INSERT INTO fountain_retrieval_log VALUES (6, 5, 9, 'seed', ?)",
                  (_T0 + 5 * _DAY,))
        c.commit(); c.close()
        self.r.use_cycle(now=_T0 + 6 * _DAY)
        self.assertEqual(self._q("SELECT days FROM belief_use_days WHERE belief_id=9")[0][0], 1)

    def test_write_batch_prefers_write_many(self):
        calls = []

        class WM:
            def write_many(self, stmts):
                calls.append(len(stmts))
        rec.write_batch(WM(), [("x", ()), ("y", ())])
        self.assertEqual(calls, [2])

    def test_start_loop_inert_when_off(self):
        prev = os.environ.pop("NEX5_WARRANT_RECORD", None)
        try:
            before = {t.name for t in threading.enumerate()}
            self.r.start_loop()
            self.assertNotIn("warrant_recorder",
                             {t.name for t in threading.enumerate()} - before)
        finally:
            if prev is not None:
                os.environ["NEX5_WARRANT_RECORD"] = prev


class TestShadowCheck(unittest.TestCase):
    def test_conflicting_pair_fails_others_pass(self):
        rows = [{"id": 1, "content": "stability is what holds the self together over time"},
                {"id": 2, "content": "stability is not what holds the self, change and flux do"},
                {"id": 3, "content": "the market closed higher on tuesday afternoon"}]
        from theory_x.stage3_world_model.harmonizer import _conflict_score
        from theory_x.stage3_world_model.retrieval import _tokenize
        s = _conflict_score(_tokenize(rows[0]["content"]), rows[0]["content"],
                            _tokenize(rows[1]["content"]), rows[1]["content"])
        v = rec.shadow_conflict_check(rows)
        self.assertTrue(v[3])
        self.assertEqual(v[1], s < rec._CONFLICT_THRESHOLD)
        self.assertEqual(v[1], v[2])


class TestGeneratorRetrievalLogGate(unittest.TestCase):
    def test_drop_is_conditional_only_under_flag(self):
        src = (Path(__file__).resolve().parents[1] / "theory_x" / "stage6_fountain"
               / "generator.py").read_text()
        i = src.index('_drop_rlog = True')
        seg = src[i: i + 1200]
        self.assertIn('os.environ.get("NEX5_WARRANT_RECORD") == "1"', seg)
        self.assertIn("PRAGMA foreign_key_list(fountain_retrieval_log)", seg)
        self.assertIn('r["table"] == "beliefs"', seg)
        self.assertLess(seg.index("if _drop_rlog:"),
                        seg.index('"DROP TABLE IF EXISTS fountain_retrieval_log"'))


if __name__ == "__main__":
    unittest.main()
