"""Left-censoring, deletion, and the CHECK-widening rebuild (Beam's six rulings).

  * a window opened before the undo log went live is LEFT-CENSORED: an undo seen
    in the covered span -> 'undone'; none seen -> 'indeterminate'; never
    'confirmed', no valence, no learning, out of falsifiability's rate;
  * coverage is stamped on every owned window, open ones included;
  * deleting a belief (any path, raw SQL included) logs 'belief_deleted' out of
    the undo denominator; its owned window is VOIDED (zero valence, event ref);
  * the gap report is split: a violation with no logged undo on an ALIVE belief
    is the finding; deletions are lifecycle, reported apart;
  * an aged store's CHECK constraints are widened in place, rows, guards and
    foreign keys intact.
"""
import json
import os
import sqlite3
import tempfile
import time
import unittest
from unittest import mock

from tests import _bootstrap  # noqa: F401

from substrate import connect, Row, Writer
from theory_x.stage_world import expectations as X

DAY = 86400.0


class _Store(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(os.environ, {
            "NEX5_DATA_DIR": self._tmp.name, "NEX5_SCHEMA_TRIPWIRE": "1"})
        self._env.start()
        for f in ("NEX5_EXPECT_LEARN", "NEX5_EXPECT_MOOD"):
            os.environ.pop(f, None)
        from substrate.init_db import init_all
        init_all()
        from substrate.paths import db_paths
        p = db_paths()
        self.bel, self.conv = str(p["beliefs"]), str(p["conversations"])
        cx = connect(self.bel)
        self.installed = cx.execute("SELECT installed_at FROM undo_log_meta").fetchone()[0]
        cx.close()
        from theory_x.stage_world import owned_belief
        owned_belief.ensure_schema()

    def tearDown(self):
        self._env.stop()
        self._tmp.cleanup()

    def _owned(self, made, content=None):
        from theory_x.stage_world.frozen_at_made import (
            FROZEN_INSERT_COLS, FROZEN_PLACEHOLDERS, basis_entry, frozen_values)
        cx = connect(self.bel)
        bid = cx.execute("INSERT INTO beliefs (content, tier, confidence, created_at, source) "
                         "VALUES (?, 6, 0.7, ?, 'wonder_loop')",
                         (content or f"mine {made}", int(made))).lastrowid
        cx.commit(); cx.close()
        with mock.patch("theory_x.stage_world.frozen_at_made.snapshot_stakes",
                        return_value=(0.0, 0, 0.0)):
            frozen = frozen_values(0.7, "stated_p", 0.0, "exact_label",
                                   basis=[basis_entry(bid, "authored", 0.7)], cost_band=4)
        cx = connect(self.conv)
        cx.execute("INSERT INTO owned_belief_expectations (made_at, belief_id, claimed_state, "
                   "resolve_at, state, " + FROZEN_INSERT_COLS + ") VALUES (?,?,?,?, 'open', "
                   + FROZEN_PLACEHOLDERS + ")",
                   (made, bid, json.dumps({"belief_id": bid, "holds": True, "tier": 6,
                                           "paused": 0, "erosion_stage": "external"}),
                    made + DAY, *frozen))
        cx.commit(); cx.close()
        return bid

    def _header(self, bid):
        cx = connect(self.conv)
        cx.row_factory = Row
        try:
            r = cx.execute("SELECT e.*, v.valence, v.reason FROM expectations e "
                           "JOIN owned_belief_expectations o ON o.id = e.producer_row_id "
                           "LEFT JOIN event_valence v ON v.expectation_id = e.id "
                           "WHERE e.producer = 'owned_belief_expectations' AND o.belief_id = ?",
                           (bid,)).fetchone()
            return dict(r) if r else None
        finally:
            cx.close()

    def _log(self, bid, kind, at):
        from theory_x.stage3_world_model.undo_log import log_undo
        w = Writer(self.bel, name="beliefs")
        try:
            log_undo(w, kind, [bid], at=at)
        finally:
            w.close()


class TestLeftCensoring(_Store):

    def test_coverage_stamped_on_open_windows(self):
        early = self._owned(self.installed - 3600)
        late = self._owned(self.installed + 10)
        X.reconcile(now=self.installed + 20)            # nothing due; stamping only
        e, l = self._header(early), self._header(late)
        self.assertEqual((e["state"], e["coverage"], e["coverage_start"]),
                         ("open", "partial", self.installed))
        self.assertEqual((l["coverage"], l["coverage_start"]), ("full", self.installed + 10))

    def test_partial_window_never_confirms(self):
        quiet = self._owned(self.installed - 3600)                    # holds, no undo seen
        seen = self._owned(self.installed - 3500)
        self._log(seen, "contradiction_raised", self.installed + 100)  # undo in covered span
        broke = self._owned(self.installed - 3400)
        cx = connect(self.bel)
        cx.execute("UPDATE beliefs SET paused = 1 WHERE id = ?", (broke,))
        cx.commit(); cx.close()
        X.reconcile(now=self.installed + 2 * DAY)
        got = {b: self._header(b) for b in (quiet, seen, broke)}
        self.assertEqual([got[b]["state"] for b in (quiet, seen, broke)],
                         ["indeterminate", "undone", "undone"])
        for h in got.values():
            self.assertEqual((h["valence"], h["reason"]), (0.0, "partial_coverage"))
        f = X.falsifiability()
        self.assertEqual((f["resolved"], f["exercised"], f["rate"]), (0, 0, None))
        self.assertEqual(f["censored"], {"indeterminate": 1, "undone": 2})
        rows = {c[0]: c for c in X.canaries(now=self.installed + 2 * DAY)}
        self.assertTrue(rows["partial_window_terminals"][3])          # a finding

    def test_full_window_still_confirms(self):
        b = self._owned(self.installed + 10)
        X.reconcile(now=self.installed + 2 * DAY)
        self.assertEqual(self._header(b)["state"], "confirmed")


class TestDeletion(_Store):

    def test_any_delete_is_logged_out_of_the_denominator(self):
        b = self._owned(self.installed + 10)
        cx = connect(self.bel)
        cx.execute("DELETE FROM beliefs WHERE id = ?", (b,))          # raw SQL path
        cx.commit()
        row = cx.execute("SELECT kind, cause_ref FROM undo_events WHERE belief_id = ?",
                         (b,)).fetchone()
        cx.close()
        self.assertEqual(row, ("belief_deleted", "delete:wonder_loop"))
        X.reconcile(now=self.installed + 2 * DAY)
        h = self._header(b)
        self.assertEqual((h["state"], h["valence"], h["reason"]), ("voided", 0.0, "voided"))
        ev = json.loads(h["evidence"])
        self.assertEqual((ev["why"], ev["event_seq"] is not None), ("belief_deleted", True))
        f = X.falsifiability()
        self.assertEqual((f["exercised"], f["violated_unlogged"], f["censored"]),
                         (0, 0, {"voided": 1}))

    def test_gap_report_split_alive_violation_is_the_finding(self):
        alive = self._owned(self.installed + 10)
        cx = connect(self.bel)
        cx.execute("UPDATE beliefs SET tier = 7 WHERE id = ?", (alive,))   # changed, no log row
        cx.commit(); cx.close()
        X.reconcile(now=self.installed + 2 * DAY)
        f = X.falsifiability()
        self.assertEqual(f["violated_unlogged"], 1)
        self.assertIn("alive-belief violations with no logged undo (FINDING)", f["status"])

    def test_belief_deleted_is_not_an_undo_kind(self):
        self.assertNotIn("belief_deleted", X.UNDO_KINDS)
        self.assertNotIn("eroded", X.UNDO_KINDS)


class TestCheckWidening(unittest.TestCase):
    """An aged store (old CHECK lists, rows, guards, FKs) is widened in place."""

    def test_rebuild_preserves_rows_guards_and_keys(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {"NEX5_DATA_DIR": tmp}):
            from substrate.init_db import init_all, _CHECK_WIDENINGS
            from substrate.paths import db_paths
            init_all()
            p = db_paths()
            # Age both tables: put the OLD CHECK lists back, with rows and a child FK row.
            for (dbname, table), (old, new) in _CHECK_WIDENINGS.items():
                cx = connect(str(p[dbname]), isolation_level=None)
                sql = cx.execute("SELECT sql FROM sqlite_master WHERE name=?", (table,)).fetchone()[0]
                extras = [r[0] for r in cx.execute(
                    "SELECT sql FROM sqlite_master WHERE tbl_name=? AND type IN ('index','trigger') "
                    "AND sql IS NOT NULL", (table,))]
                cx.execute("PRAGMA foreign_keys=OFF")
                cx.execute(f"DROP TABLE {table}")
                cx.execute(sql.replace(new, old))
                for s in extras:
                    cx.execute(s)
                cx.close()
            cx = connect(str(p["beliefs"]))
            cx.execute("INSERT INTO undo_events (belief_id, kind, at) VALUES (5, 'paused', 1)")
            cx.commit(); cx.close()
            cx = connect(str(p["conversations"]))
            cx.execute("INSERT INTO expectations (subject, producer, producer_row_id, made_at, "
                       "claimed_state, ownership, basis_kind, horizon_at, horizon_kind) "
                       "VALUES ('self', 'owned_belief_expectations', 1, 0, '{}', 1, 'owned', 0, "
                       "'timer')")
            cx.execute("INSERT INTO event_valence (expectation_id, ts, valence, admitted, reason, "
                       "state) VALUES (1, 0, 0.0, 0, 'x', 'open')")
            cx.commit()
            with self.assertRaises(sqlite3.IntegrityError):
                cx.execute("UPDATE expectations SET state='voided', resolved_by='reconciler'")
            cx.close()

            init_all()                                         # widen

            cx = connect(str(p["beliefs"]))
            cx.execute("INSERT INTO undo_events (belief_id, kind, at) VALUES (6, 'belief_deleted', 2)")
            cx.commit()
            self.assertEqual(cx.execute("SELECT COUNT(*) FROM undo_events").fetchone()[0], 2)
            with self.assertRaises(sqlite3.IntegrityError):    # append-only guard survived
                cx.execute("DELETE FROM undo_events")
            cx.close()
            cx = connect(str(p["conversations"]))
            cx.execute("UPDATE expectations SET state='voided', resolved_by='reconciler'")
            cx.commit()
            with self.assertRaises(sqlite3.IntegrityError):    # single-writer guard survived
                cx.execute("UPDATE expectations SET state='violated', resolved_by='x'")
            self.assertEqual(cx.execute("PRAGMA foreign_key_check").fetchall(), [])
            self.assertEqual(cx.execute("SELECT COUNT(*) FROM event_valence").fetchone()[0], 1)
            cx.close()
            init_all()                                         # idempotent


if __name__ == "__main__":
    unittest.main()
