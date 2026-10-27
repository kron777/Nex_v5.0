"""The undo log: append-only, written AT each belief-undo transition site.

Pinned here:
  * undo_events refuses UPDATE and DELETE (guard triggers, logged);
  * a re-raised opposes edge on an existing pair emits NEW rows even though the
    edge upsert changes nothing in belief_edges (the old blind spot);
  * a raise-then-clear (harmonizer pause, then its retirement unpause) in one
    window yields both rows -- and the retirement's tier-8 move is logged as a
    demotion though it never stamps last_demoted_at;
  * every wired site writes its kind; a log failure never breaks the transition;
  * falsifiability reads the log per belief: a row landing in a window flips it
    from UNEXERCISED to measured; the divergence canary is UNMEASURABLE until a
    window is fully covered.
"""
import json
import os
import sqlite3
import tempfile
import time
import unittest
from unittest import mock

from tests import _bootstrap  # noqa: F401

from substrate import connect, Reader, Writer


class _Store(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(os.environ, {
            "NEX5_DATA_DIR": self._tmp.name, "NEX5_SCHEMA_TRIPWIRE": "1"})
        self._env.start()
        from substrate.init_db import init_all
        init_all()
        from substrate.paths import db_paths
        p = db_paths()
        self.bel, self.dyn, self.conv = str(p["beliefs"]), str(p["dynamic"]), str(p["conversations"])
        self.w = Writer(self.bel, name="beliefs")
        self.addCleanup(self.w.close)

    def tearDown(self):
        self._env.stop()
        self._tmp.cleanup()

    def _belief(self, content, tier=6, source="wonder_loop", **cols):
        cx = connect(self.bel)
        try:
            extra = "".join(f", {k}" for k in cols)
            bid = cx.execute(
                f"INSERT INTO beliefs (content, tier, confidence, created_at, source{extra}) "
                f"VALUES (?, ?, 0.7, ?, ?{', ?' * len(cols)})",
                (content, tier, int(time.time()), source, *cols.values())).lastrowid
            cx.commit()
            return bid
        finally:
            cx.close()

    def _events(self, bid=None):
        cx = connect(self.bel)
        try:
            q = "SELECT belief_id, kind, cause_ref FROM undo_events"
            return cx.execute(q + (" WHERE belief_id=?" if bid else "") + " ORDER BY seq",
                              (bid,) if bid else ()).fetchall()
        finally:
            cx.close()


class TestAppendOnly(_Store):

    def test_update_and_delete_refused_and_logged(self):
        from theory_x.stage3_world_model.undo_log import log_undo
        log_undo(self.w, "paused", [1])
        cx = connect(self.bel)
        try:
            with self.assertLogs("substrate.guard", "ERROR"):
                with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
                    cx.execute("UPDATE undo_events SET kind='unpaused'")
            with self.assertLogs("substrate.guard", "ERROR"):
                with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
                    cx.execute("DELETE FROM undo_events")
        finally:
            cx.close()
        self.assertEqual(len(self._events()), 1)

    def test_kind_is_checked(self):
        cx = connect(self.bel)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                cx.execute("INSERT INTO undo_events (belief_id, kind, at) VALUES (1, 'nudged', 0)")
        finally:
            cx.close()

    def test_log_failure_never_breaks_the_transition(self):
        from theory_x.stage3_world_model.promotion import BeliefPromoter

        class _Flaky:
            def __init__(self, real):
                self.real = real

            def write(self, *a, **k):
                return self.real.write(*a, **k)

            def write_many(self, *a, **k):
                raise RuntimeError("disk on fire")
        a, b = self._belief("one claim"), self._belief("its opposite")
        BeliefPromoter(_Flaky(self.w), Reader(self.bel)).write_edge(a, b, "opposes", 0.6)
        cx = connect(self.bel)
        n = cx.execute("SELECT COUNT(*) FROM belief_edges WHERE edge_type='opposes'").fetchone()[0]
        cx.close()
        self.assertEqual(n, 1)                 # the edge landed; the log failure was swallowed


class TestTransitionSites(_Store):

    def test_re_raised_contradiction_is_a_new_event(self):
        from theory_x.stage3_world_model.promotion import BeliefPromoter
        a, b = self._belief("the market is rational"), self._belief("the market is not rational")
        p = BeliefPromoter(self.w, Reader(self.bel))
        p.write_edge(a, b, "opposes", 0.6)
        cx = connect(self.bel)
        created_first = cx.execute("SELECT created_at FROM belief_edges").fetchone()[0]
        cx.close()
        time.sleep(0.01)
        p.write_edge(a, b, "opposes", 0.6)                    # upsert: edge unchanged
        cx = connect(self.bel)
        edges = cx.execute("SELECT COUNT(*), MAX(created_at) FROM belief_edges").fetchone()
        cx.close()
        self.assertEqual(edges, (1, created_first))           # the table can't show it...
        raised = [e for e in self._events() if e[1] == "contradiction_raised"]
        self.assertEqual(sorted(r[0] for r in raised), [a, a, b, b])   # ...the log does
        p.write_edge(a, b, "supports", 0.6)
        self.assertEqual(len(self._events()), 4)              # only opposes is an undo

    def test_raise_then_clear_in_one_window_is_two_rows_each(self):
        from theory_x.stage3_world_model.harmonizer import Harmonizer
        from theory_x.stage3_world_model.promotion import BeliefPromoter
        a, b = self._belief("cats are warm"), self._belief("cats are cold")
        dw = Writer(self.dyn, name="dynamic")
        self.addCleanup(dw.close)
        h = Harmonizer(self.w, Reader(self.bel), dw, BeliefPromoter(self.w, Reader(self.bel)))
        self.assertEqual(h.resolve(a, b), "both_deleted")
        kinds_a = [k for _, k, _ in self._events(a)]
        self.assertEqual(kinds_a, ["paused", "unpaused", "demoted"])
        cx = connect(self.bel)
        demoted_col = cx.execute("SELECT last_demoted_at FROM beliefs WHERE id=?", (a,)).fetchone()[0]
        cx.close()
        self.assertIsNone(demoted_col)          # the tier-8 retirement the column never saw

    def test_demotions_erosion_and_the_generator(self):
        from theory_x.stage3_world_model.edge_generator import EdgeGenerator
        from theory_x.stage3_world_model.erosion import ProvenanceErosion
        from theory_x.stage3_world_model.promotion import BeliefPromoter
        p = BeliefPromoter(self.w, Reader(self.bel))
        target = self._belief("a contested claim")
        p.decisive_contradiction(target)
        stale = self._belief("old and unvisited", tier=5, last_referenced_at=1)
        p.decay_pass()
        eroding = self._belief("used a lot", reinforce_count=10)
        ProvenanceErosion(self.w, Reader(self.bel))._erosion_check(eroding)
        x, y = self._belief("generated left"), self._belief("generated right")
        EdgeGenerator(self.w, Reader(self.bel)).persist_edges(x, [(y, "opposes", 0.4),
                                                                  (y, "cross_domain", 0.4)])
        got = {(b, k) for b, k, _ in self._events()}
        self.assertIn((target, "demoted"), got)
        self.assertIn((stale, "demoted"), got)
        self.assertIn((eroding, "eroded"), got)
        self.assertIn((x, "contradiction_raised"), got)
        self.assertIn((y, "contradiction_raised"), got)
        self.assertEqual(sum(1 for b, k in got if b in (x, y)), 2)    # cross_domain: none

    def test_contradiction_cleared_has_no_site(self):
        # Nothing in the tree retires an opposes edge: the kind is declared but
        # unreachable. If a site is ever added it must log; this pins the fact.
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[1]
        hits = []
        for f in (root / "theory_x").rglob("*.py"):
            t = f.read_text()
            if "DELETE FROM belief_edges" in t or "UPDATE belief_edges SET edge_type" in t:
                hits.append(str(f))
        self.assertEqual(hits, [])


class TestFalsifiabilityReadsTheLog(_Store):
    T0 = 1_800_000_000.0

    def _owned(self, made):
        from theory_x.stage_world import owned_belief
        from theory_x.stage_world.frozen_at_made import (
            FROZEN_INSERT_COLS, FROZEN_PLACEHOLDERS, basis_entry, frozen_values)
        owned_belief.ensure_schema()
        bid = self._belief(f"mine at {made}")
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
                    made + 86400, *frozen))
        cx.commit(); cx.close()
        return bid

    def test_a_logged_event_flips_unexercised_to_measured(self):
        from theory_x.stage3_world_model.undo_log import log_undo
        from theory_x.stage_world import expectations as X
        quiet = self._owned(self.T0)
        tested = self._owned(self.T0 + 1)
        X.reconcile(now=self.T0 + 86400 - 10)               # nothing due yet
        log_undo(self.w, "contradiction_raised", [tested], at=self.T0 + 600)  # re-raise only
        X.reconcile(now=self.T0 + 2 * 86400)
        f = X.falsifiability()
        self.assertEqual((f["resolved"], f["exercised"], f["rate"]), (2, 1, 0.0))
        cx = connect(self.conv)
        ev = dict(cx.execute("SELECT producer_row_id, undo_events FROM expectations "
                             "WHERE producer='owned_belief_expectations'").fetchall())
        cx.close()
        rows = [json.loads(v) for v in ev.values()]
        hit = next(r for r in rows if r["log_rows"])
        self.assertEqual((hit["kinds"], hit["legacy_heuristic"]),
                         ({"contradiction_raised": 1}, False))   # the old check was blind
        self.assertEqual(quiet and len([r for r in rows if not r["log_rows"]]), 1)

    def test_erosion_is_logged_but_is_not_an_undo(self):
        from theory_x.stage3_world_model.undo_log import log_undo
        from theory_x.stage_world import expectations as X
        bid = self._owned(self.T0)
        log_undo(self.w, "eroded", [bid], at=self.T0 + 100)
        cx = connect(self.bel)
        cx.execute("UPDATE beliefs SET erosion_stage='nex_absorbed' WHERE id=?", (bid,))
        cx.commit(); cx.close()
        X.reconcile(now=self.T0 + 2 * 86400)
        cx = connect(self.conv)
        state, elig, ev = cx.execute("SELECT state, undo_eligible, undo_events FROM expectations "
                                     "WHERE producer='owned_belief_expectations'").fetchone()
        cx.close()
        self.assertEqual((state, elig), ("confirmed", 0))    # assimilation still holds
        self.assertEqual(json.loads(ev)["kinds"], {"eroded": 1})   # but it is recorded

    def test_divergence_unmeasurable_until_a_window_is_covered(self):
        from theory_x.stage3_world_model.undo_log import log_undo
        from theory_x.stage_world import expectations as X
        before_log = time.time() - 3 * 86400                  # opened before the log: partial
        self._owned(before_log)
        X.reconcile(now=before_log + 2 * 86400)
        u = X.belief_undo_divergence()
        self.assertTrue(u["status"].startswith("UNMEASURABLE"))
        self.assertEqual(u["partial"], 1)
        now = time.time()
        bid = self._owned(now)                                # fully covered
        log_undo(self.w, "paused", [bid], at=now + 5)
        log_undo(self.w, "unpaused", [bid], at=now + 6)
        X.reconcile(now=now + 2 * 86400)
        u = X.belief_undo_divergence()
        self.assertEqual((u["covered"], u["with_undo"], u["blind_spot_hits"]), (1, 1, 1))


if __name__ == "__main__":
    unittest.main()
