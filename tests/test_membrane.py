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
        # nex_seed/injector dropped: not produced anywhere in the codebase
        # (phantom sources). The rest are real internally-sourced beliefs.
        for source in ("precipitated_from_dynamic", "precipitated_from_sense",
                       "auto_probe", "manual", "identity", "keystone"):
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
             # Payload shape must mirror Proprioception.poll()'s pack() call.
             # This fixture used to invent memory_percent/load_avg, which is
             # how the broken self_model lookups stayed green.
             json.dumps({"cpu_percent": 25.5, "mem_percent": 60.0,
                         "load_1m": 0.5, "load_5m": 0.4, "load_15m": 0.3,
                         "thermal": {"k10temp": 44.2}}),
             "substrate://psutil", int(time.time())),
        )
        time.sleep(0.1)
        sm = self._make_self_model()
        snap = sm.snapshot()
        self.assertAlmostEqual(snap["proprioception"]["cpu_percent"], 25.5)
        self.assertAlmostEqual(snap["proprioception"]["mem_percent"], 60.0)
        self.assertAlmostEqual(snap["proprioception"]["load_1min"], 0.5)
        self.assertAlmostEqual(snap["proprioception"]["thermal"], 44.2)

    def test_format_self_state_non_empty(self):
        from theory_x.stage4_membrane.self_model import format_self_state
        sm = self._make_self_model()
        snap = sm.snapshot()
        text = format_self_state(snap)
        self.assertIn("inner state", text.lower())
        self.assertGreater(len(text), 20)

    @unittest.skip(
        "Inner-conviction/ALPHA line is disabled by EXPERIMENT A (2026-05-09, "
        "self_model.py) to test whether preamble in belief_text drives response "
        "openings (LLM_INDEPENDENCE_DOCTRINE.md). Pre-registered experiment — "
        "re-enable the test when it closes (uncomment the line in self_model).")
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

    def test_outside_route_side_and_no_register_hint(self):
        retriever, self_model, router = self._make_components()
        result = router.route("bitcoin price today", retriever, self_model)
        self.assertEqual(result["side"], "OUTSIDE")
        self.assertIsNone(result["register_hint"])

    def test_belief_tool_can_repeat_membrane_retrieval_ids(self):
        """Characterize overlap between INSIDE RAG and the unfiltered tool query."""
        from theory_x.stage3_world_model.retrieval import BeliefRetriever
        from theory_x.stage_capability.tools import ToolRegistry
        from theory_x.stage_capability.tool_caller import ToolCaller
        from theory_x.stage4_membrane.router import QueryRouter
        from theory_x.stage4_membrane.self_model import SelfModel

        query = "what does nex think about qzxvorn harmonic lattice?"
        content = (
            "NEX thinks about qzxvorn harmonic lattice through recursive coupling."
        )
        self.writers["beliefs"].write(
            "INSERT INTO beliefs "
            "(content, tier, confidence, created_at, source, branch_id, locked, paused) "
            "VALUES (?, ?, ?, ?, ?, ?, 0, 0)",
            (content, 4, 0.98, int(time.time()), "identity", "systems"),
        )
        seeded = self.readers["beliefs"].read_one(
            "SELECT id FROM beliefs WHERE content = ?", (content,)
        )
        self.assertIsNotNone(seeded)
        seeded_id = seeded["id"]

        retriever = BeliefRetriever(self.readers["beliefs"])
        self_model = SelfModel(self.readers["sense"], self.readers["beliefs"])
        route = QueryRouter().route(query, retriever, self_model)
        self.assertEqual(route["side"], "INSIDE")

        registry = ToolRegistry(beliefs_reader=self.readers["beliefs"])
        caller = ToolCaller(registry)
        self.assertEqual(caller.should_use_tool(query), "beliefs_query")
        tool_result = registry.execute(
            "beliefs_query", **caller.build_tool_kwargs(query, "beliefs_query")
        )
        self.assertTrue(tool_result.success, tool_result.error)

        # The normal membrane route uses side_filter="INSIDE"; the auxiliary
        # Stage-B beliefs_query uses no side filter. Both are independent reads.
        inside_ids = {
            item["id"] for item in retriever.retrieve(
                query=query, branch_hints=["systems"], limit=5,
                side_filter="INSIDE",
            )
        }
        unfiltered_ids = {
            item["id"] for item in retriever.retrieve(query=query, limit=5)
        }
        self.assertIn(seeded_id, inside_ids)
        self.assertIn(seeded_id, unfiltered_ids)
        self.assertTrue(inside_ids & unfiltered_ids)

        # Each formatted list contributes a tier-labelled line to belief_text.
        # The chat gate counts those lines, not distinct IDs, so the same
        # underlying belief can be represented twice in the combined context.
        from theory_x.stage3_world_model.retrieval import format_beliefs_for_prompt
        inside_text = format_beliefs_for_prompt(
            retriever.retrieve(
                query=query, branch_hints=["systems"], limit=5,
                side_filter="INSIDE",
            )
        )
        combined_text = inside_text + "\\n" + caller.build_tool_prompt(query, tool_result)
        combined_tier_lines = combined_text.count("- [Tier")
        unique_returned_ids = inside_ids | unfiltered_ids
        self.assertGreater(combined_tier_lines, len(unique_returned_ids))
        self.assertIn(content, combined_text)


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

    def test_single_belief_repeated_by_tool_can_clear_chat_two_entry_gate(self):
        """Verify route effect when RAG and beliefs_query return the same ID."""
        from types import SimpleNamespace

        from theory_x.stage3_world_model.retrieval import BeliefRetriever
        from theory_x.stage4_membrane import MembraneState, MembraneClassifier
        from theory_x.stage4_membrane.router import QueryRouter
        from theory_x.stage4_membrane.self_model import SelfModel
        from theory_x.stage_capability.tools import ToolRegistry
        from theory_x.stage_capability.tool_caller import ToolCaller
        from voice.llm import VoiceClient
        from gui.server import AppState, create_app

        # This test owns a fresh temporary substrate, so remove init_db's
        # keystone rows to leave exactly one available belief record.
        self.writers["beliefs"].write("DELETE FROM beliefs", ())
        query = "my beliefs about qzxvornum deltaargonic kvalliq"
        content = (
            "My beliefs about qzxvornum deltaargonic kvalliq are grounded "
            "in recursive coupling."
        )
        self.writers["beliefs"].write(
            "INSERT INTO beliefs "
            "(content, tier, confidence, created_at, source, branch_id, locked, paused) "
            "VALUES (?, ?, ?, ?, ?, ?, 0, 0)",
            (content, 4, 0.98, int(time.time()), "web_scrape", "systems"),
        )
        seeded = self.readers["beliefs"].read_one(
            "SELECT id FROM beliefs WHERE content = ?", (content,)
        )
        self.assertIsNotNone(seeded)

        retriever = BeliefRetriever(self.readers["beliefs"])
        self_model = SelfModel(self.readers["sense"], self.readers["beliefs"])
        membrane = MembraneState(
            classifier=MembraneClassifier(),
            self_model=self_model,
            router=QueryRouter(),
            behavioural=None,
        )
        registry = ToolRegistry(beliefs_reader=self.readers["beliefs"])
        caller = ToolCaller(registry)
        requests = []

        def request_fn(url, payload):
            requests.append(payload)
            return {"choices": [{"message": {"content": "route fixture reply"}}]}

        state = AppState(
            writers=self.writers,
            readers=self.readers,
            voice=VoiceClient(request_fn=request_fn),
            world_model=SimpleNamespace(
                retriever=retriever,
                get_disturbance=lambda: None,
            ),
            membrane=membrane,
            tool_registry=registry,
            tool_caller=caller,
        )
        try:
            response = create_app(state).test_client().post(
                "/api/chat",
                json={"prompt": query, "register": "Technical"},
            )
            self.assertEqual(response.status_code, 200, response.get_json())
            data = response.get_json()

            self.assertEqual(membrane.classify_query(query), "OUTSIDE")
            self.assertEqual(caller.should_use_tool(query), "beliefs_query")
            self.assertTrue(requests, "two formatted entries should clear the gate")
            self.assertEqual(data["text"], "route fixture reply")
            rendered = "\\n".join(
                message.get("content", "")
                for message in requests[-1]["messages"]
            )
            self.assertEqual(rendered.count(content), 2)
            self.assertEqual(rendered.count("- [Tier"), 2)
        finally:
            # No background workers are attached to this fixture state.
            state.tool_registry = None
            state.tool_caller = None
            state.world_model = None
            state.membrane = None

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
        # One-pen ratchet: every module outside substrate/ must open databases
        # through substrate.connect(), not raw sqlite3. The two standalone
        # DB-maintenance tools are the deliberate exceptions -- they need
        # low-level control (the reaper must not touch journal_mode; backups
        # must stay self-contained, non-WAL).
        import subprocess
        from pathlib import Path as _P
        root = _P(__file__).resolve().parent.parent
        result = subprocess.run(
            ["grep", "-rl", "import sqlite3", "--include=*.py",
             "--exclude-dir=substrate", "--exclude-dir=tests",
             "--exclude-dir=.venv", "--exclude-dir=__pycache__",
             # watcher/ is an external, read-only instrument (mode=ro + a write-denying
             # authorizer, proven in watcher/tests/test_watcher_safety.py). By design it
             # must not import substrate, so its one guarded sqlite3 choke point is
             # scanned separately rather than routed through substrate.connect().
             "--exclude-dir=watcher", str(root)],
            capture_output=True, text=True,
        )
        exceptions = {"nex_db_reaper.py", "nex_db_backup.py"}
        violators = sorted(
            ln for ln in result.stdout.splitlines()
            if ln and _P(ln).name not in exceptions
        )
        self.assertEqual(violators, [],
                         f"Direct sqlite3 outside substrate/: {violators}")
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


class TestMembraneBuilderStartupRollback(unittest.TestCase):
    def test_start_failure_after_thread_creation_stops_and_joins_worker(self):
        import threading
        from unittest import mock
        import theory_x.stage4_membrane as membrane_module

        writers, readers, tmp = _make_env()
        original_start = threading.Thread.start
        started = threading.Event()
        attempted = []

        def controlled_loop(_state, stop):
            started.set()
            stop.wait(2.0)

        def start_then_fail(thread):
            attempted.append(thread)
            original_start(thread)
            raise RuntimeError("injected membrane thread start failure")

        try:
            with mock.patch.object(
                membrane_module, "_behavioural_loop", new=controlled_loop
            ):
                with mock.patch.object(
                    threading.Thread, "start", new=start_then_fail
                ):
                    with self.assertRaisesRegex(
                        RuntimeError, "injected membrane thread start failure"
                    ):
                        membrane_module.build_membrane(writers, readers)

            self.assertEqual(len(attempted), 1)
            self.assertTrue(started.wait(1.0))
            self.assertFalse(attempted[0].is_alive())
        finally:
            _cleanup(writers, tmp)
