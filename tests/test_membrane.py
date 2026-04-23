"""Phase 5 smoke tests — Membrane (Inside/Outside Boundary).

Covers:
- Classifier: internal streams → INSIDE, external feeds → OUTSIDE
- Classifier: inside belief sources → INSIDE, other sources → OUTSIDE
- Classifier: self-inquiry queries → INSIDE, world queries → OUTSIDE
- SelfModel snapshot: returns dict with all expected keys, graceful fallback
- format_self_state: returns non-empty string with inner state language
- Router INSIDE path: register_hint='philosophical', belief_text includes self-state
- Router OUTSIDE path: register_hint=None, belief_text from normal retrieval
- GUI /api/membrane/snapshot returns 200
- GUI /api/membrane/classify?stream=internal.proprioception returns INSIDE
- GUI /api/membrane/classify?stream=ai_research.arxiv returns OUTSIDE
- No direct sqlite3 outside substrate/ (grep check)
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_membrane_")
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
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    os.environ.pop("NEX5_DATA_DIR", None)
    os.environ.pop("NEX5_ADMIN_HASH_FILE", None)


# ---- Classifier --------------------------------------------------------------

class TestMembraneClassifier(unittest.TestCase):
    def setUp(self):
        from theory_x.stage4_membrane.classifier import MembraneClassifier, MembraneSide
        self.cls = MembraneClassifier()
        self.INSIDE = MembraneSide.INSIDE
        self.OUTSIDE = MembraneSide.OUTSIDE

    def test_internal_streams_are_inside(self):
        for stream in ("internal.proprioception", "internal.temporal",
                       "internal.interoception", "internal.meta_awareness"):
            self.assertEqual(self.cls.classify_stream(stream), self.INSIDE,
                             f"{stream} should be INSIDE")

    def test_external_streams_are_outside(self):
        for stream in ("ai_research.arxiv", "crypto.coingecko", "news.reuters",
                       "emerging_tech.hn", "computing.arxiv"):
            self.assertEqual(self.cls.classify_stream(stream), self.OUTSIDE,
                             f"{stream} should be OUTSIDE")

    def test_inside_belief_sources(self):
        for source in ("precipitated_from_dynamic", "nex_seed", "manual",
                       "identity", "injector", "keystone"):
            b = {"source": source}
            self.assertEqual(self.cls.classify_belief(b), self.INSIDE,
                             f"source={source} should be INSIDE")

    def test_outside_belief_sources(self):
        for source in ("auto_growth", "distilled", "web_scrape", "unknown", None, ""):
            b = {"source": source}
            self.assertEqual(self.cls.classify_belief(b), self.OUTSIDE,
                             f"source={source!r} should be OUTSIDE")

    def test_self_inquiry_queries_are_inside(self):
        queries = [
            "how are you feeling?",
            "what do you believe?",
            "tell me about yourself",
            "who are you?",
            "what are you thinking right now",
            "do you feel anything?",
            "what is your inner state?",
        ]
        for q in queries:
            self.assertEqual(self.cls.classify_query(q), self.INSIDE,
                             f"query {q!r} should be INSIDE")

    def test_world_queries_are_outside(self):
        queries = [
            "what's BTC doing?",
            "latest AI papers this week",
            "summarize the news",
            "what is the price of ethereum",
            "show me recent research on transformers",
        ]
        for q in queries:
            self.assertEqual(self.cls.classify_query(q), self.OUTSIDE,
                             f"query {q!r} should be OUTSIDE")


# ---- SelfModel ---------------------------------------------------------------

class TestSelfModel(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _make_self_model(self):
        from theory_x.stage4_membrane.self_model import SelfModel
        return SelfModel(
            sense_reader=self.readers["sense"],
            beliefs_reader=self.readers["beliefs"],
        )

    def test_snapshot_returns_expected_keys(self):
        sm = self._make_self_model()
        snap = sm.snapshot()
        for key in ("timestamp", "membrane_side", "proprioception", "temporal",
                    "interoception", "meta_awareness", "attention", "inside_beliefs"):
            self.assertIn(key, snap, f"missing key: {key}")

    def test_snapshot_membrane_side_is_inside(self):
        sm = self._make_self_model()
        snap = sm.snapshot()
        self.assertEqual(snap["membrane_side"], "INSIDE")

    def test_snapshot_graceful_on_empty_db(self):
        sm = self._make_self_model()
        # No sense events — should still return a valid dict without raising
        snap = sm.snapshot()
        self.assertIsInstance(snap, dict)
        self.assertIsNone(snap["proprioception"]["cpu_percent"])

    def test_snapshot_reads_sense_events(self):
        # Write a proprioception event
        self.writers["sense"].write(
            "INSERT INTO sense_events (stream, payload, provenance, timestamp) "
            "VALUES (?, ?, ?, ?)",
            ("internal.proprioception",
             json.dumps({"cpu_percent": 25.5, "memory_percent": 60.0, "load_avg": [0.5, 0.4, 0.3]}),
             "substrate://psutil", int(time.time())),
        )
        time.sleep(0.1)
        sm = self._make_self_model()
        snap = sm.snapshot()
        self.assertAlmostEqual(snap["proprioception"]["cpu_percent"], 25.5)
        self.assertAlmostEqual(snap["proprioception"]["mem_percent"], 60.0)

    def test_format_self_state_non_empty(self):
        from theory_x.stage4_membrane.self_model import format_self_state
        sm = self._make_self_model()
        snap = sm.snapshot()
        text = format_self_state(snap)
        self.assertIn("inner state", text.lower())
        self.assertGreater(len(text), 20)

    def test_format_self_state_includes_alpha(self):
        from theory_x.stage4_membrane.self_model import format_self_state
        from alpha import ALPHA
        sm = self._make_self_model()
        snap = sm.snapshot()
        text = format_self_state(snap)
        self.assertIn(ALPHA.lines[0][:20], text)


# ---- Router ------------------------------------------------------------------

class TestQueryRouter(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _make_components(self):
        from theory_x.stage3_world_model.retrieval import BeliefRetriever
        from theory_x.stage4_membrane.self_model import SelfModel
        from theory_x.stage4_membrane.router import QueryRouter
        retriever = BeliefRetriever(self.readers["beliefs"])
        self_model = SelfModel(self.readers["sense"], self.readers["beliefs"])
        router = QueryRouter()
        return retriever, self_model, router

    def test_inside_route_returns_philosophical_hint(self):
        retriever, self_model, router = self._make_components()
        result = router.route("how are you feeling?", retriever, self_model)
        self.assertEqual(result["side"], "INSIDE")
        self.assertEqual(result["register_hint"], "philosophical")

    def test_inside_route_belief_text_contains_state(self):
        retriever, self_model, router = self._make_components()
        result = router.route("what do you think?", retriever, self_model)
        self.assertIsNotNone(result["belief_text"])
        self.assertIn("inner state", result["belief_text"].lower())

    def test_outside_route_returns_no_register_hint(self):
        retriever, self_model, router = self._make_components()
        result = router.route("what's happening in AI research?", retriever, self_model)
        self.assertEqual(result["side"], "OUTSIDE")
        self.assertIsNone(result["register_hint"])

    def test_outside_route_belief_text_none_when_no_beliefs(self):
        retriever, self_model, router = self._make_components()
        result = router.route("bitcoin price today", retriever, self_model)
        self.assertEqual(result["side"], "OUTSIDE")
        # With no beliefs in DB, belief_text is None
        self.assertIsNone(result["belief_text"])


# ---- Side filter in retrieval ------------------------------------------------

class TestRetrievalSideFilter(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _seed(self, content, source, tier=5, confidence=0.52):
        return self.writers["beliefs"].write(
            "INSERT INTO beliefs (content, tier, confidence, created_at, source, locked) "
            "VALUES (?, ?, ?, ?, ?, 0)",
            (content, tier, confidence, int(time.time()), source),
        )

    def test_inside_filter_returns_only_inside_beliefs(self):
        from theory_x.stage3_world_model.retrieval import BeliefRetriever
        self._seed("Neural AI research inside belief", source="precipitated_from_dynamic")
        self._seed("Neural AI research outside belief", source="web_scrape")
        time.sleep(0.1)
        r = BeliefRetriever(self.readers["beliefs"])
        results = r.retrieve("neural AI research", side_filter="INSIDE", limit=10)
        sources = {b["source"] for b in results}
        self.assertIn("precipitated_from_dynamic", sources)
        self.assertNotIn("web_scrape", sources)

    def test_outside_filter_returns_only_outside_beliefs(self):
        from theory_x.stage3_world_model.retrieval import BeliefRetriever
        self._seed("Market crypto price belief inside", source="precipitated_from_dynamic")
        self._seed("Market crypto price belief outside", source="web_scrape")
        time.sleep(0.1)
        r = BeliefRetriever(self.readers["beliefs"])
        results = r.retrieve("market crypto price", side_filter="OUTSIDE", limit=10)
        sources = {b["source"] for b in results}
        self.assertNotIn("precipitated_from_dynamic", sources)


# ---- GUI endpoints -----------------------------------------------------------

class TestMembraneGUIEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.writers, cls.readers, cls.tmp = _make_env()
        from admin.auth import set_password
        set_password("membrane-test-pw")
        from voice.llm import VoiceClient
        from gui.server import AppState, create_app
        from theory_x.stage4_membrane import build_membrane

        membrane = build_membrane(cls.writers, cls.readers)
        cls.membrane = membrane
        cls.state = AppState(
            writers=cls.writers,
            readers=cls.readers,
            voice=VoiceClient(
                request_fn=lambda u, p: {"choices": [{"message": {"content": "ok"}}]}
            ),
            membrane=membrane,
        )
        cls.app = create_app(cls.state)
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.state.close()
        _cleanup(cls.writers, cls.tmp)

    def test_membrane_snapshot_200(self):
        r = self.client.get("/api/membrane/snapshot")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["membrane_side"], "INSIDE")
        self.assertIn("proprioception", data)
        self.assertIn("attention", data)

    def test_membrane_classify_internal_is_inside(self):
        r = self.client.get("/api/membrane/classify?stream=internal.proprioception")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["side"], "INSIDE")

    def test_membrane_classify_external_is_outside(self):
        r = self.client.get("/api/membrane/classify?stream=ai_research.arxiv")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["side"], "OUTSIDE")

    def test_membrane_classify_crypto_is_outside(self):
        r = self.client.get("/api/membrane/classify?stream=crypto.coingecko")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["side"], "OUTSIDE")

    def test_membrane_snapshot_503_when_not_wired(self):
        from voice.llm import VoiceClient
        from gui.server import AppState, create_app
        state2 = AppState(
            writers=self.writers,
            readers=self.readers,
            voice=VoiceClient(
                request_fn=lambda u, p: {"choices": [{"message": {"content": "ok"}}]}
            ),
        )
        app2 = create_app(state2)
        c = app2.test_client()
        r = c.get("/api/membrane/snapshot")
        self.assertEqual(r.status_code, 503)


# ---- Architecture compliance -------------------------------------------------

class TestMembraneCompliance(unittest.TestCase):
    def test_no_direct_sqlite3_outside_substrate(self):
        result = subprocess.run(
            [
                "grep", "-r", "sqlite3.connect",
                "/home/rr/Desktop/nex5",
                "--include=*.py",
                "--exclude-dir=.venv",
                "--exclude-dir=substrate",
                "--exclude-dir=tests",
                "--exclude-dir=strikes",
                "--exclude-dir=__pycache__",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.stdout.strip(), "",
            f"Direct sqlite3.connect found outside substrate/:\n{result.stdout}",
        )

    def test_theory_x_stage_4_in_all_modules(self):
        import importlib
        for mod in [
            "theory_x.stage4_membrane.classifier",
            "theory_x.stage4_membrane.self_model",
            "theory_x.stage4_membrane.router",
        ]:
            m = importlib.import_module(mod)
            self.assertEqual(getattr(m, "THEORY_X_STAGE", None), 4,
                             f"{mod} missing THEORY_X_STAGE = 4")


if __name__ == "__main__":
    unittest.main()
