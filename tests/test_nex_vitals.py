"""Offline tests for tools/nex_vitals.py — the READ-ONLY vitals instrument.

These run with NO data/*.db and NO ~/.nex (the cloud checkout). A tiny temp
sqlite `fountain_events` fixture stands in for the live dynamic.db, pointed at
by the DB-reading functions' injectable `db_path` argument.

Covers the pre-registered offline verification (spec §5):
  V1  frozen detectors are pure + deterministic + versioned.
  V2  per-mode decomposition splits correctly; aggregate == mode recombination.
  V3  within-window touched/untouched partition is exact given a marker list.
  V4  read-only: the fixture DB is opened mode=ro (a write raises); with no
      --log flag no file is created.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest

from tests import _bootstrap  # noqa: F401  (puts repo root on sys.path)

from tools import nex_vitals as V


# ── fixture ──────────────────────────────────────────────────────────────────

_BASE = 1_700_000_000.0

# (id, ts, thought, word_count, mode, focal_item)
# Modes span DRIFT / ARGUE / EXPLAIN / null; held-out and opener hits are known.
_ROWS = [
    # DRIFT (focal_item NULL by design) — held-out hit, no opener
    (1, _BASE + 0,  "makes me wonder about the quiet hum today", 8, "DRIFT", None),
    (2, _BASE + 10, "the rain is loud on the roof tonight",      8, "DRIFT", None),
    # ARGUE — row 3 trips BOTH held-out and the anchored opener
    (3, _BASE + 20, "This item talks about the merger deal",     7, "ARGUE", "merger deal"),
    (4, _BASE + 30, "Bitcoin dropped four percent after the vote", 7, "ARGUE", "bitcoin vote"),
    # EXPLAIN — row 5 opener-only, row 6 held-out-only
    (5, _BASE + 40, "The feed reports a new chip release",        7, "EXPLAIN", "chip release"),
    (6, _BASE + 50, "This feels surreal and resonates with my ground stance", 9, "EXPLAIN", "x"),
    # null mode
    (7, _BASE + 60, "quiet market noise again",                   4, None, None),
]

# Known truth over the fixture:
#   held-out hits : rows 1, 3, 6        -> aggregate 3/7
#   opener  hits  : rows 3, 5           -> aggregate 2/7
_HELD_BY_MODE = {"DRIFT": (1, 2), "ARGUE": (1, 2), "EXPLAIN": (1, 2), "null": (0, 1)}
_OPEN_BY_MODE = {"DRIFT": (0, 2), "ARGUE": (1, 2), "EXPLAIN": (1, 2), "null": (0, 1)}


def _make_fixture_db() -> str:
    fd, path = tempfile.mkstemp(prefix="nex5_vitals_fix_", suffix=".db")
    os.close(fd)
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE fountain_events ("
        "id INTEGER PRIMARY KEY, ts REAL, thought TEXT, readiness, hot_branch, "
        "word_count INTEGER, droplet, stillness_reason, tag, mode TEXT, focal_item)")
    con.executemany(
        "INSERT INTO fountain_events (id, ts, thought, word_count, mode, focal_item) "
        "VALUES (?,?,?,?,?,?)", _ROWS)
    con.commit()
    con.close()
    return path


class _Fixture(unittest.TestCase):
    def setUp(self):
        self.db = _make_fixture_db()

    def tearDown(self):
        try:
            os.remove(self.db)
        except OSError:
            pass


# ── V1: frozen detectors pure + deterministic + versioned ───────────────────

class TestV1FrozenDetectors(unittest.TestCase):

    def test_instrument_version_present(self):
        self.assertTrue(isinstance(V.INSTRUMENT_VERSION, str) and V.INSTRUMENT_VERSION)

    def test_held_out_detector(self):
        self.assertTrue(V.held_out_hit("makes me wonder about X"))
        self.assertTrue(V.held_out_hit("This FEELS SURREAL right now"))   # case-insensitive
        self.assertTrue(V.held_out_hit("it resonates with my ground stance"))
        self.assertFalse(V.held_out_hit("the rain is loud on the roof"))
        self.assertFalse(V.held_out_hit(""))
        self.assertFalse(V.held_out_hit(None))

    def test_held_out_set_is_intervention_disjoint(self):
        # C1: the frozen held-out set shares NO phrase with the live FRAME ban
        # list. "this item talks about" (held-out) != "this item is about" (ban).
        from theory_x.stage6_fountain import generator as G
        ban = {p.lower() for p in G._FRAME_STOCK_PHRASES}
        self.assertEqual(set(V._FROZEN_HELD_OUT) & ban, set())

    def test_opener_is_anchored(self):
        self.assertTrue(V.opener_hit("This item talks about the merger"))
        self.assertTrue(V.opener_hit('   "The feed reports a thing"'))     # leading punct
        self.assertFalse(V.opener_hit("Well, this item talks about the merger"))
        self.assertFalse(V.opener_hit("the rain is loud"))
        self.assertFalse(V.opener_hit(None))

    def test_frozen_tokenizer_deterministic(self):
        # Pinned output — must not move if live crystallizer drifts (C2).
        self.assertEqual(
            V._frozen_fidelity_tokens("Bitcoin dropped four percent"),
            ["bitcoin", "dropped", "four", "percent"])
        self.assertEqual(
            V._frozen_fidelity_tokens("The feed reports a new chip release"),
            ["feed", "chip", "release"])   # 'reports','new','the','a' are furniture
        self.assertEqual(V._frozen_fidelity_tokens(""), [])
        self.assertEqual(V._frozen_fidelity_tokens(None), [])

    def test_frozen_tokenizer_matches_live(self):
        # The copy must equal the live _fidelity_tokens where importable.
        try:
            from theory_x.stage6_fountain.crystallizer import _fidelity_tokens as live
        except Exception:
            self.skipTest("live crystallizer not importable in this env")
        for s in ("The feed reports a new chip release",
                  "NEX5’s quiet hum echoes today",
                  "this item is about the merger", ""):
            self.assertEqual(V._frozen_fidelity_tokens(s), live(s), s)

    def test_frozen_dominant_topic_terms_primitive(self):
        # Needs >= 10 docs; a token in >= 40% of docs is returned.
        thoughts = ["alpha beta"] * 6 + ["gamma delta"] * 5
        self.assertIn("alpha", V._frozen_dominant_topic_terms(thoughts))
        self.assertEqual(V._frozen_dominant_topic_terms(["alpha"] * 3), [])  # sub-min


# ── V2: per-mode decomposition + exact recombination ────────────────────────

class TestV2PerMode(_Fixture):

    def _fires(self):
        fires = V.load_fires(db_path=self.db, window=100)
        self.assertEqual(len(fires), len(_ROWS))
        return fires

    def test_per_mode_split_counts(self):
        pm = V.per_mode_metrics(self._fires())
        for mode, (hits, n) in _HELD_BY_MODE.items():
            self.assertEqual(pm[mode]["n"], n, mode)
            self.assertEqual(pm[mode]["held_out_hits"], hits, mode)
        for mode, (hits, n) in _OPEN_BY_MODE.items():
            self.assertEqual(pm[mode]["opener_hits"], hits, mode)

    def test_aggregate_equals_mode_recombination(self):
        fires = self._fires()
        pm = V.per_mode_metrics(fires)
        agg = V.compute_fire_metrics(fires)
        # exact integer recombination (the point of exposing raw counts, C6/V2)
        self.assertEqual(agg["n"], sum(m["n"] for m in pm.values()))
        self.assertEqual(agg["held_out_hits"],
                         sum(m["held_out_hits"] for m in pm.values()))
        self.assertEqual(agg["opener_hits"],
                         sum(m["opener_hits"] for m in pm.values()))
        self.assertEqual(agg["held_out_hits"], 3)
        self.assertEqual(agg["opener_hits"], 2)
        self.assertAlmostEqual(agg["held_out_rate"], 3 / 7)
        self.assertAlmostEqual(agg["opener_rate"], 2 / 7)
        # words/fire mean recombines as a weighted mean of the per-mode means
        recomb = sum(m["words"]["mean"] * m["n"]
                     for m in pm.values() if m["words"]["mean"] is not None)
        self.assertAlmostEqual(agg["words"]["mean"] * agg["n"], recomb)

    def test_canonical_modes_always_present(self):
        pm = V.per_mode_metrics(self._fires())
        for mode in ("DRIFT", "ARGUE", "EXPLAIN", "null"):
            self.assertIn(mode, pm)


# ── V3: within-window partition is exact ────────────────────────────────────

class TestV3WithinWindow(_Fixture):

    def test_partition_exact(self):
        fires = V.load_fires(db_path=self.db, window=100)
        markers = [_BASE + 20, _BASE + 40]            # rows 3 and 5
        touched, untouched = V.partition_touched(fires, markers, tol=0.5)
        self.assertEqual({r["id"] for r in touched}, {3, 5})
        self.assertEqual({r["id"] for r in untouched}, {1, 2, 4, 6, 7})

    def test_split_metrics_partition(self):
        fires = V.load_fires(db_path=self.db, window=100)
        ww = V.within_window_split(fires, [_BASE + 20, _BASE + 40], tol=0.5)
        self.assertEqual(ww["n_touched"], 2)
        self.assertEqual(ww["n_untouched"], 5)
        # touched = rows 3 (held-out+opener) and 5 (opener only)
        self.assertEqual(ww["touched"]["held_out_hits"], 1)
        self.assertEqual(ww["touched"]["opener_hits"], 2)
        # untouched = rows 1,2,4,6,7 -> held-out on 1 and 6
        self.assertEqual(ww["untouched"]["held_out_hits"], 2)
        self.assertEqual(ww["untouched"]["opener_hits"], 0)

    def test_empty_markers_all_untouched(self):
        fires = V.load_fires(db_path=self.db, window=100)
        touched, untouched = V.partition_touched(fires, [], tol=0.5)
        self.assertEqual(touched, [])
        self.assertEqual(len(untouched), len(_ROWS))


# ── V4: read-only ───────────────────────────────────────────────────────────

class TestV4ReadOnly(_Fixture):

    def test_connection_is_read_only(self):
        con = V._ro(self.db)
        try:
            with self.assertRaises(sqlite3.OperationalError):
                con.execute("INSERT INTO fountain_events (id, ts) VALUES (999, 1.0)")
        finally:
            con.close()
        # the fixture is unchanged
        con2 = sqlite3.connect(self.db)
        n = con2.execute("SELECT COUNT(*) FROM fountain_events").fetchone()[0]
        con2.close()
        self.assertEqual(n, len(_ROWS))

    def test_no_log_writes_no_file(self):
        # build_result + maybe_log(None) must create nothing.
        tmp = tempfile.mkdtemp(prefix="nex5_vitals_nolog_")
        would_be = os.path.join(tmp, "logs", "vitals_log.jsonl")
        res = V.build_result(dynamic_db=self.db, window=100,
                             history_log=os.path.join(tmp, "history.jsonl"))
        self.assertIsNone(V.maybe_log(res, None))
        self.assertFalse(os.path.exists(would_be))
        self.assertEqual(os.listdir(tmp), [])          # nothing written anywhere

    def test_log_flag_appends_one_row_with_version(self):
        tmp = tempfile.mkdtemp(prefix="nex5_vitals_log_")
        log_path = os.path.join(tmp, "logs", "vitals_log.jsonl")
        res = V.build_result(dynamic_db=self.db, window=100,
                             history_log=log_path)
        self.assertEqual(V.maybe_log(res, log_path), log_path)
        import json
        with open(log_path) as fh:
            lines = fh.read().splitlines()
        self.assertEqual(len(lines), 1)                # exactly one row
        row = json.loads(lines[0])
        # the pre-registered row shape (spec §4)
        for key in ("ts", "when_utc", "instrument_version", "window",
                    "arm_ledger", "topic_mix", "per_mode", "aggregate",
                    "within_window", "trajectory_ref"):
            self.assertIn(key, row)
        self.assertEqual(row["instrument_version"], V.INSTRUMENT_VERSION)
        self.assertIsNone(row["within_window"])        # no trip info given


class TestReportRenders(_Fixture):
    """The stdout report renders end-to-end on the fixture (and degrades
    gracefully with no beliefs/conversations db, no ~/.nex)."""

    def test_render(self):
        res = V.build_result(dynamic_db=self.db, window=100,
                             history_log=os.path.join(tempfile.mkdtemp(), "h.jsonl"))
        text = V.render_report(res)
        self.assertIn("NEX VITALS", text)
        self.assertIn("PER-MODE", text)
        self.assertIn("TOPIC-MIX", text)
        self.assertIn("ARM-LEDGER", text)


class TestSurpriseWindowing(unittest.TestCase):
    """surprise_reading windows by triggered_at (the real column, not ts) and
    honours `since` — so rate/mean are window-scoped, not all-time (the fix that
    turned the garbage 'rate 320.79' of snapshot #1 into a comparable number)."""

    def _db(self):
        fd, path = tempfile.mkstemp(prefix="nex5_vitals_surp_", suffix=".db")
        os.close(fd)
        con = sqlite3.connect(path)
        con.execute(
            "CREATE TABLE surprise_events (triggered_at REAL, surprise_score REAL)")
        con.executemany(
            "INSERT INTO surprise_events (triggered_at, surprise_score) VALUES (?,?)",
            [(100.0, 0.1), (200.0, 0.3), (300.0, 0.5), (400.0, 0.7)])
        con.commit()
        con.close()
        return path

    def test_windowed_by_triggered_at(self):
        path = self._db()
        try:
            r = V.surprise_reading(db_path=path, since=250.0, n_fires=2)
            self.assertTrue(r["available"])
            self.assertEqual(r["n"], 2)                 # only the 300 & 400 events
            self.assertAlmostEqual(r["mean"], 0.6)      # (0.5 + 0.7)/2
            self.assertAlmostEqual(r["rate"], 1.0)      # 2 events / 2 window fires
            r_all = V.surprise_reading(db_path=path, since=None, n_fires=4)
            self.assertEqual(r_all["n"], 4)             # no floor -> all four
        finally:
            os.remove(path)


class TestRetrospectiveDaily(unittest.TestCase):
    """load_fires time-bounds (since, until] + daily_series bucketing over the
    existing history — the retrospective read that answers climate-vs-weather now."""

    def _db(self):
        import datetime as dt
        fd, path = tempfile.mkstemp(prefix="nex5_vitals_daily_", suffix=".db")
        os.close(fd)
        con = sqlite3.connect(path)
        con.execute(
            "CREATE TABLE fountain_events (id INTEGER PRIMARY KEY, ts REAL, "
            "thought TEXT, word_count INTEGER, mode TEXT, focal_item)")

        def e(day, hour):
            return dt.datetime(2026, 10, day, hour, tzinfo=dt.timezone.utc).timestamp()

        rows = [  # 10-01: 2 fires | 10-02: 1 | 10-03: 3
            (1, e(1, 1), "makes me wonder about alpha", 5, "ARGUE", "x"),
            (2, e(1, 2), "the rain is loud",            4, "DRIFT", None),
            (3, e(2, 5), "This item talks about beta",  5, "ARGUE", "y"),
            (4, e(3, 1), "feels surreal here",          3, "EXPLAIN", "z"),
            (5, e(3, 2), "plain concrete thing",        3, "DRIFT", None),
            (6, e(3, 3), "resonates with my view",      4, "ARGUE", "w"),
        ]
        con.executemany(
            "INSERT INTO fountain_events (id,ts,thought,word_count,mode,focal_item) "
            "VALUES (?,?,?,?,?,?)", rows)
        con.commit()
        con.close()
        return path, e

    def test_until_bounds(self):
        path, e = self._db()
        try:
            fires = V.load_fires(db_path=path, since=e(1, 0), until=e(2, 0))
            self.assertEqual({r["id"] for r in fires}, {1, 2})  # only day-1
        finally:
            os.remove(path)

    def test_daily_bucketing(self):
        path, e = self._db()
        try:
            series = V.daily_series(dynamic_db=path, days=3, now_ts=e(3, 12))
            by = {r["date"]: r for r in series}
            self.assertEqual(by["2026-10-01"]["n"], 2)
            self.assertEqual(by["2026-10-02"]["n"], 1)
            self.assertEqual(by["2026-10-03"]["n"], 3)
            # 10-03 ARGUE = 1 fire ("resonates with my") -> held-out 100%
            self.assertEqual(by["2026-10-03"]["argue_n"], 1)
            self.assertAlmostEqual(by["2026-10-03"]["argue_held"], 1.0)
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
