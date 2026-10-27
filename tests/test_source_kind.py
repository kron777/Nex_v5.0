"""Build D -- per-STREAM provenance: source_kind stamped at every write boundary.

What must hold:
  * every belief and sense event carries a source_kind from the moment it is
    written (a trigger, so producers that never heard of source_kind still do);
  * a sense belief carries the stream that produced it, and a verbatim copy of
    it inherits that stream whatever loop copied it;
  * the scorer tiers by source_kind only with NEX5_SOURCE_KIND on; off is the
    old by-name behaviour exactly;
  * the nightly audit reads 0 on a correctly stamped store AND > 0 on seeded
    pre-fix rows (the positive control -- an audit that can't see the failure
    it guards against proves nothing);
  * identity claims in her voice rest only on authored/seeded rows, and the
    floor fires when one rests on a headline.
Every store test runs with NEX5_SCHEMA_TRIPWIRE on and requires it silent.
"""
import os
import tempfile
import time
import unittest
from unittest import mock

from tests import _bootstrap  # noqa: F401

from substrate import connect, source_kind as SK

# The 29 streams in her store on 2026-10-27, plus edge cases.
_LIVE_STREAMS = (
    "agi.arxiv_cs_ai", "ai_research.arxiv", "ai_research.lab_blogs", "cognition.biorxiv",
    "cognition.frontiers", "cognition.lesswrong", "computing.arxiv", "computing.tech_news",
    "crypto.coingecko", "crypto.exchanges", "crypto.news", "emerging_tech.arxiv",
    "emerging_tech.hn", "emerging_tech.ieee", "emerging_tech.mit_tr", "external.other_mind",
    "history.wikipedia_featured", "internal.fountain", "internal.interoception",
    "internal.meta_awareness", "internal.proprioception", "internal.temporal",
    "literature.gutenberg", "mathematics.arxiv", "neuroscience.arxiv_qbio", "news.bbc",
    "philosophy.aeon", "psychology.sciencedaily", "science.quanta",
)
_EDGE_STREAMS = ("fountain", "FOUNTAIN", "Internal.X", "external.self", "external.selfie",
                 "othermind.chat", "external.otherXmind", "", None, "internal",
                 "literature.gutenberg.extra")


class TestRulesAgreeInSql(unittest.TestCase):
    """The trigger's SQL and the Python rules are rendered from one table; pin it."""

    def setUp(self):
        self.cx = connect(":memory:")
        self.addCleanup(self.cx.close)

    def test_stream_kind(self):
        for s in _LIVE_STREAMS + _EDGE_STREAMS:
            got = self.cx.execute(f"SELECT {SK.stream_kind_sql('x')} FROM (SELECT ? AS x)",
                                  (s,)).fetchone()[0]
            self.assertEqual(got, SK.classify_stream(s), s)

    def test_source_kind(self):
        names = list(SK._KIND_BY_SOURCE) + [
            "precipitated_from_sense", "grounded_scorecard:market_direction_v1",
            "grounded_scorecard", "spectrum", "", None, "mystery"]
        for n in names:
            got = self.cx.execute(f"SELECT {SK.source_kind_sql('x')} FROM (SELECT ? AS x)",
                                  (n,)).fetchone()[0]
            self.assertEqual(got, SK.kind_for_source(n), n)

    def test_live_streams_classify_as_documented(self):
        self.assertEqual(SK.classify_stream("internal.interoception"), "self")
        self.assertEqual(SK.classify_stream("news.bbc"), "world")
        self.assertEqual(SK.classify_stream("philosophy.aeon"), "other_mind")
        self.assertEqual(SK.classify_stream("external.other_mind"), "other_mind")


class TestKindsKeepTheirBands(unittest.TestCase):
    """Flag on must not move any producer whose band was already right by name."""

    def test_every_named_source_keeps_its_band(self):
        from theory_x.life import affinity_loop as A
        for source, base in A.PROVENANCE_BASE.items():
            self.assertEqual(A.KIND_BASE[SK.kind_for_source(source)], base, source)
        for source in SK._KIND_BY_SOURCE:
            self.assertEqual(A.KIND_BASE[SK.kind_for_source(source)],
                             A.PROVENANCE_BASE.get(source, A._RECEIVED), source)

    def test_the_one_deliberate_move(self):
        # grounded_scorecard:* has no by-name entry (received by default). By kind
        # it is her own calls checked against the world -> self. It is tier 1, so
        # affinity (tier >= 4) never scores it; an unstamped one shows up in the
        # audit, which is how this case was found on her store.
        from theory_x.life import affinity_loop as A
        src = "grounded_scorecard:market_direction_v1"
        self.assertEqual(SK.kind_for_source(src), "self")
        self.assertEqual(A.provenance_base(src), A._RECEIVED)
        self.assertEqual(A.provenance_base(src, "self"), A._WITNESSED)

    def test_bands_stay_disjoint_by_kind(self):
        from theory_x.life import affinity_loop as A
        for u in (0.0, 0.3, 0.7, 1.0):
            authored = A._provenance_affinity("precipitated_from_sense", u, "authored")
            self_ = A._provenance_affinity("precipitated_from_sense", u, "self")
            for k in ("world", "other_mind", "seeded", "received"):
                received = A._provenance_affinity("fountain_insight", u, k)
                self.assertGreater(self_, received, (u, k))
            self.assertGreater(authored, self_, u)

    def test_kind_overrides_name_only_when_passed(self):
        from theory_x.life import affinity_loop as A
        # A self-sensed stream row under the flat sense name: witnessed by kind,
        # received by name (what flag-off sees, because no kind is passed).
        self.assertAlmostEqual(A._provenance_affinity("precipitated_from_sense", 0.0, "self"), 0.3375)
        self.assertAlmostEqual(A._provenance_affinity("precipitated_from_sense", 0.0), 0.225)
        # A headline copied under an authored name: received by kind.
        self.assertAlmostEqual(A._provenance_affinity("counterfactual_node", 0.0, "world"), 0.225)
        self.assertAlmostEqual(A._provenance_affinity("counterfactual_node", 0.0), 0.45)


class _Store(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(os.environ, {
            "NEX5_DATA_DIR": self._tmp.name,
            "NEX5_SCHEMA_TRIPWIRE": "1",
        })
        self._env.start()
        from substrate.init_db import init_all
        init_all()
        from substrate.paths import db_paths
        p = db_paths()
        self.bel, self.sense, self.dyn = str(p["beliefs"]), str(p["sense"]), str(p["dynamic"])
        # As boot does (stage5 SelfLocationCommitment): the identity block's floor.
        from substrate import Reader, Writer
        from theory_x.stage5_self_location.commitment import SelfLocationCommitment
        _w = Writer(self.bel, name="beliefs")
        try:
            SelfLocationCommitment().commit(_w, Reader(self.bel))
        finally:
            _w.close()
        quiet = self.assertNoLogs("substrate.schema_tripwire", "ERROR")
        quiet.__enter__()
        self.addCleanup(quiet.__exit__, None, None, None)

    def tearDown(self):
        self._env.stop()
        self._tmp.cleanup()

    def _insert(self, content, source, stream=None, kind=None, tier=6, problem_id=None):
        # Content is unique per problem (NULL = orphan): a verbatim copy can only
        # exist under a problem -- which is how counterfactual_node writes.
        cx = connect(self.bel)
        try:
            cur = cx.execute(
                "INSERT INTO beliefs (content, tier, confidence, created_at, source, "
                "source_stream, source_kind, problem_id) VALUES (?, ?, 0.7, ?, ?, ?, ?, ?)",
                (content, tier, int(time.time()), source, stream, kind, problem_id))
            cx.commit()
            return cur.lastrowid
        finally:
            cx.close()

    def _row(self, bid):
        cx = connect(self.bel)
        try:
            return cx.execute("SELECT source_stream, source_kind FROM beliefs WHERE id=?",
                              (bid,)).fetchone()
        finally:
            cx.close()

    def _writers(self):
        from substrate import Writer
        w = Writer(self.bel, name="beliefs")
        self.addCleanup(w.close)
        return w


class TestStampedAtEveryWriteBoundary(_Store):

    def test_fresh_init_seeds_all_carry_a_kind(self):
        cx = connect(self.bel)
        try:
            rows = cx.execute("SELECT source, source_kind FROM beliefs").fetchall()
        finally:
            cx.close()
        self.assertTrue(rows)
        self.assertEqual([r for r in rows if r[1] is None], [])
        self.assertEqual({k for s, k in rows if s == "keystone_seed"}, {"seeded"})

    def test_producer_unaware_of_source_kind_still_gets_one(self):
        # The INSERT every loop already does -- no source_kind, no stream.
        for source, want in (("fountain_insight", "authored"), ("witness_loop", "self"),
                             ("fetch_loop", "world"), ("auto_probe", "received"),
                             ("identity", "seeded"), ("brand_new_loop", "received")):
            bid = self._insert(f"a thought from {source}", source)
            self.assertEqual(self._row(bid), (None, want), source)

    def test_distiller_carries_the_stream(self):
        from theory_x.stage2_dynamic import _write_sense_belief
        w = self._writers()
        for stream, want in (("news.bbc", "world"), ("philosophy.aeon", "other_mind")):
            _write_sense_belief(w, f"title from {stream}", stream, int(time.time()), "x")
            cx = connect(self.bel)
            row = cx.execute("SELECT source, source_stream, source_kind FROM beliefs "
                             "WHERE content=?", (f"title from {stream}",)).fetchone()
            cx.close()
            self.assertEqual(row, ("precipitated_from_sense", stream, want))

    def test_verbatim_copy_inherits_the_stream(self):
        # The cross-band class: counterfactual_node re-inserting a headline.
        self._insert("Bitcoin falls below 60k as fees drop", "precipitated_from_sense",
                     stream="crypto.news", kind="world")
        copy = self._insert("Bitcoin falls below 60k as fees drop", "counterfactual_node",
                            tier=3, problem_id=7)
        self.assertEqual(self._row(copy), ("crypto.news", "world"))
        own = self._insert("What I notice is the falling, not the price", "counterfactual_node")
        self.assertEqual(self._row(own), (None, "authored"))

    def test_explicit_kind_is_respected(self):
        bid = self._insert("x", "precipitated_from_sense", stream="news.bbc", kind="self")
        self.assertEqual(self._row(bid), ("news.bbc", "self"))

    def test_crystallizer_stamps_title_stream_only(self):
        from substrate import Reader
        from theory_x.stage2_dynamic.crystallization import Crystallizer
        c = Crystallizer(None, self._writers(), None, Reader(self.dyn))
        a = c._write_belief("[news] Headline as a title", "news", time.time(), stream="news.bbc")
        b = c._write_belief("[news] https://feeds.bbci.co.uk/news/rss.xml", "news", time.time())
        self.assertEqual(self._row(a), ("news.bbc", "world"))
        self.assertEqual(self._row(b), (None, "self"))   # her own sustained attention

    def test_sense_events_stamped(self):
        cx = connect(self.sense)
        try:
            for stream in ("internal.temporal", "news.bbc", "cognition.lesswrong"):
                cx.execute("INSERT INTO sense_events (stream, payload, provenance, timestamp) "
                           "VALUES (?, '{}', 'p', ?)", (stream, int(time.time())))
            cx.commit()
            got = dict(cx.execute("SELECT stream, source_kind FROM sense_events"))
        finally:
            cx.close()
        self.assertEqual(got, {"internal.temporal": "self", "news.bbc": "world",
                               "cognition.lesswrong": "other_mind"})

    def test_reinit_keeps_one_trigger_and_existing_kinds(self):
        bid = self._insert("kept", "wonder_loop")
        from substrate.init_db import init_all
        init_all()
        cx = connect(self.bel)
        n = cx.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND name=?",
                       (SK.BELIEFS_TRIGGER,)).fetchone()[0]
        cx.close()
        self.assertEqual(n, 1)
        self.assertEqual(self._row(bid), (None, "authored"))


class TestScorerFlag(_Store):

    def _score(self, flag):
        from theory_x.life import affinity_loop as A
        self._insert("a self-sensed thing", "precipitated_from_sense",
                     stream="internal.temporal", kind="self")
        env = {"NEX5_AFFINITY_PROVENANCE": "on"}
        if flag:
            env["NEX5_SOURCE_KIND"] = "1"
        cx = connect(self.bel)
        cx.execute("UPDATE beliefs SET tier=6, use_count=5 WHERE content='a self-sensed thing'")
        cx.commit(); cx.close()
        with mock.patch.dict(os.environ, env):
            A.affinity_tick(voice=None)
        cx = connect(self.bel)
        try:
            return cx.execute("SELECT affinity FROM beliefs WHERE content='a self-sensed thing'"
                              ).fetchone()[0]
        finally:
            cx.close()

    def test_flag_off_is_by_name(self):
        self.assertLessEqual(self._score(False), 0.30)           # received band

    def test_flag_on_is_by_kind(self):
        self.assertGreater(self._score(True), 0.3375 - 1e-9)     # witnessed band


class TestAuditPositiveControl(_Store):

    def _audit(self):
        from theory_x.stage_tom.source_kind_audit import audit
        return audit()

    def _live_like(self):
        from theory_x.stage2_dynamic import _write_sense_belief
        w = self._writers()
        for i, stream in enumerate(("news.bbc", "crypto.news", "philosophy.aeon")):
            _write_sense_belief(w, f"headline {i}", stream, int(time.time()), "x")
        self._insert("headline 1", "counterfactual_node", tier=3, problem_id=7)  # verbatim copy
        self._insert("my own synthesis", "synergized")
        self._insert("i noticed a rut", "self_rut_notice")

    def test_correct_store_reads_zero(self):
        self._live_like()
        r = self._audit()
        self.assertEqual((r["tier"]["mismatches"], r["tier"]["unstamped"]), (0, 0))
        self.assertGreaterEqual(r["tier"]["with_stream"], 4)
        self.assertTrue(r["ok"])

    def test_seeded_pre_fix_rows_are_caught(self):
        self._live_like()
        # Pre-fix: a sense row wearing an authored tier, and a headline copied
        # under counterfactual_node tiered by its name (as before D).
        a = self._insert("headline wearing authored", "precipitated_from_sense",
                         stream="news.bbc", kind="authored")
        b = self._insert("headline 0", "counterfactual_node", problem_id=7)
        cx = connect(self.bel)
        # a pre-D store had no immutability trigger: simulate it for this row
        cx.execute("DROP TRIGGER trg_beliefs_source_kind_immutable")
        cx.execute("UPDATE beliefs SET source_kind=NULL WHERE id=?", (b,))
        cx.commit(); cx.close()
        r = self._audit()
        self.assertGreater(r["tier"]["mismatches"], 0)
        self.assertEqual(set(r["tier"]["mismatch_ids"]), {a, b})
        self.assertEqual(r["tier"]["unstamped_ids"], [b])
        self.assertFalse(r["ok"])

    def test_nightly_records_a_row(self):
        from theory_x.life import daily_life as dl
        self._live_like()
        details = dl._ACTIVITY_FUNCS["source_audit"]("2026-10-27")
        self.assertTrue(details.startswith("PASS"), details)
        cx = connect(self.dyn)
        row = cx.execute("SELECT mismatches, unstamped, ok FROM source_kind_audit_log").fetchone()
        cx.close()
        self.assertEqual(tuple(row), (0, 0, 1))


class TestIdentityFloor(_Store):

    def _fire(self, thought, belief_ids):
        cx = connect(self.dyn)
        try:
            fid = cx.execute("INSERT INTO fountain_events (ts, thought, readiness) "
                             "VALUES (?, ?, 0.8)", (time.time(), thought)).lastrowid
            for rank, bid in enumerate(belief_ids):
                cx.execute("INSERT INTO fountain_retrieval_log (fire_id, belief_id, slot, "
                           "rank, ts) VALUES (?, ?, 'seed', ?, ?)", (fid, bid, rank, time.time()))
            cx.commit()
        finally:
            cx.close()

    def setUp(self):
        super().setUp()
        cx = connect(self.dyn)
        cx.execute("CREATE TABLE IF NOT EXISTS fountain_retrieval_log ("
                   "id INTEGER PRIMARY KEY AUTOINCREMENT, fire_id INTEGER NOT NULL, "
                   "belief_id INTEGER NOT NULL, slot TEXT NOT NULL, rank INTEGER, "
                   "boost_value REAL, ts REAL NOT NULL)")
        cx.commit(); cx.close()
        cx = connect(self.bel)
        self.keystone = cx.execute("SELECT id FROM beliefs WHERE content='I am NEX.'").fetchone()[0]
        cx.close()

    def _floor(self):
        from theory_x.stage_tom.source_kind_audit import identity_floor
        return identity_floor()

    def test_claim_on_authored_ground_holds(self):
        headline = self._insert("Markets rally on rate cut", "precipitated_from_sense",
                                stream="news.bbc")
        self._fire("I am NEX, and I attend to this with wonder.", [self.keystone, headline])
        self._fire("Rates fell; the tape is loud.", [headline])
        f = self._floor()
        self.assertEqual((f["claim_fires"], f["claim_support"], f["violations"]), (1, 1, 0))

    def test_claim_on_a_headline_is_caught(self):
        bad = self._insert("I am nex, the intelligence", "precipitated_from_sense",
                           stream="emerging_tech.hn")
        self._fire("I am nex, the intelligence that reads the wires.", [bad, self.keystone])
        f = self._floor()
        self.assertEqual(f["violations"], 1)
        self.assertEqual(f["violation_ids"], [bad])

    def test_identity_claim_pattern(self):
        from theory_x.stage_tom.source_kind_audit import is_identity_claim as c
        for t in ("I am NEX.", "I'm nex", "I am an intel organism.", "I was created by Jon.",
                  "my name is NEX"):
            self.assertTrue(c(t), t)
        for t in ("I am inclined to support that.", "I'm not sure.", "Nexus of trade",
                  "I am the one who noticed", None):
            self.assertFalse(c(t), t)


class TestSeededGuard(_Store):
    """Not affinity-scored and not retrievable are different facts."""

    def test_fresh_store_seeds_unscored_and_retrievable(self):
        from theory_x.stage_tom.source_kind_audit import seeded_guard
        g = seeded_guard()
        self.assertGreater(g["seeded_rows"], 0)
        self.assertEqual((g["not_scored"], g["retrievable"]), (True, True))

    def test_each_failure_is_seen_separately(self):
        from theory_x.stage_tom.source_kind_audit import seeded_guard, audit
        cx = connect(self.bel)
        cx.execute("UPDATE beliefs SET affinity = 0.6 WHERE source = 'koan'")  # scored, still there
        cx.commit(); cx.close()
        g = seeded_guard()
        self.assertEqual((g["not_scored"], g["retrievable"]), (False, True))
        self.assertFalse(audit()["ok"])
        cx = connect(self.bel)
        cx.execute("UPDATE beliefs SET affinity = NULL")
        cx.execute("UPDATE beliefs SET content = '' WHERE source IN ('identity','self_location')")
        cx.commit(); cx.close()
        g = seeded_guard()
        self.assertEqual((g["not_scored"], g["retrievable"]), (True, False))


class TestBackfill(_Store):

    def test_recovers_streams_and_stamps_every_row(self):
        from substrate.source_kind import BELIEFS_TRIGGER
        from theory_x.stage1_sense.title_extract import extract_sense_title
        from theory_x.stage_tom.source_identity import backfill
        ts = int(time.time())
        payload = '{"title": "Quantum chip passes error threshold", "url": "u"}'
        cx = connect(self.sense)
        cx.execute("INSERT INTO sense_events (stream, payload, provenance, timestamp) "
                   "VALUES ('science.quanta', ?, 'p', ?)", (payload, ts))
        cx.commit(); cx.close()
        title = extract_sense_title("science.quanta", payload, max_items=1)
        self.assertTrue(title)
        # Rows written before D: no trigger, no columns filled.
        cx = connect(self.bel)
        cx.execute(f"DROP TRIGGER {BELIEFS_TRIGGER}")
        cx.execute("DROP TRIGGER trg_beliefs_source_kind_immutable")   # pre-D store
        cx.execute("UPDATE beliefs SET source_kind=NULL")
        rows = [(title, ts, "precipitated_from_sense", None),
                (title, ts, "counterfactual_node", 7),
                ("lost headline", ts, "precipitated_from_sense", None),
                ("mine", ts, "wonder_loop", None)]
        cx.executemany("INSERT INTO beliefs (content, tier, confidence, created_at, source, "
                       "problem_id) VALUES (?, 6, 0.7, ?, ?, ?)", rows)
        cx.commit(); cx.close()

        dry = backfill()
        self.assertFalse(dry["applied"])
        cx = connect(self.bel)
        self.assertEqual(cx.execute("SELECT COUNT(*) FROM beliefs WHERE source_kind IS NULL"
                                    ).fetchone()[0], dry["rows"])
        cx.close()

        r = backfill(apply=True)
        self.assertEqual((r["recovered_exact"], r["unrecoverable"], r["inherited"]), (1, 1, 1))
        cx = connect(self.bel)
        got = {(c, s): (st, k) for c, s, st, k in cx.execute(
            "SELECT content, source, source_stream, source_kind FROM beliefs")}
        nulls = cx.execute("SELECT COUNT(*) FROM beliefs WHERE source_kind IS NULL").fetchone()[0]
        cx.close()
        self.assertEqual(nulls, 0)
        self.assertEqual(got[(title, "precipitated_from_sense")], ("science.quanta", "world"))
        self.assertEqual(got[(title, "counterfactual_node")], ("science.quanta", "world"))
        self.assertEqual(got[("lost headline", "precipitated_from_sense")], (None, "received"))
        self.assertEqual(got[("mine", "wonder_loop")], (None, "authored"))
        from theory_x.stage_tom.source_kind_audit import tier_audit
        self.assertEqual(tier_audit()["mismatches"], 0)
        self.assertEqual(backfill(apply=True)["updated"], 0)   # idempotent


if __name__ == "__main__":
    unittest.main()
