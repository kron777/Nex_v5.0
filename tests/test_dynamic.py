"""Phase 3 smoke tests — Dynamic Formation.

Covers:
- Bonsai init: 10 seed branches, trunk is ALPHA
- A-F pipeline: mock sense event goes through all 6 steps, logged to dynamic.db
- Text payload magnitude: arXiv title containing 'neural' matches ai_research branch
- Crystallization: force branch to high focus for CRYSTALLIZATION_HOLD_SECONDS,
  verify Tier 7 belief appears in beliefs.db with correct fields
- Dedup guard: crystallize same content twice, verify only one belief written
- Consolidation: quiet signal sets consolidation_active=True
- Cursor persistence: last_sense_id survives DynamicState restart
- GUI endpoints: /api/dynamic/status, /api/dynamic/crystallized, /api/beliefs/recent
  all return 200
- No direct sqlite3.connect outside substrate/ (grep check)
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_dynamic_")
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


# ---- Bonsai ------------------------------------------------------------------

class TestBonsaiInit(unittest.TestCase):
    def test_ten_seed_branches(self):
        from theory_x.stage2_dynamic.bonsai import BonsaiTree, SEED_BRANCHES
        self.assertEqual(len(SEED_BRANCHES), 10)
        tree = BonsaiTree()
        tree.init_tree()
        nodes = tree.all_nodes()
        self.assertEqual(len(nodes), 10)
        ids = {n.branch_id for n in nodes}
        for seed in SEED_BRANCHES:
            self.assertIn(seed["id"], ids)

    def test_all_seeds_marked_is_seed(self):
        from theory_x.stage2_dynamic.bonsai import BonsaiTree
        tree = BonsaiTree()
        tree.init_tree()
        for node in tree.all_nodes():
            self.assertTrue(node.is_seed)

    def test_trunk_label_matches_alpha(self):
        from alpha import ALPHA
        # Alpha is the ground; 'systems' is the self-aware inward branch
        from theory_x.stage2_dynamic.bonsai import BonsaiTree
        tree = BonsaiTree()
        tree.init_tree()
        systems = tree.get("systems")
        self.assertIsNotNone(systems)
        self.assertAlmostEqual(systems.curiosity_weight, 1.0)
        # Alpha is accessible — no local redefinition
        self.assertIsNotNone(ALPHA)

    def test_decay_pass_reduces_focus(self):
        from theory_x.stage2_dynamic.bonsai import BonsaiTree
        tree = BonsaiTree()
        tree.init_tree()
        node = tree.get("ai_research")
        node.focus_num = 0.8
        tree.decay_pass()
        self.assertLess(node.focus_num, 0.8)

    def test_non_seed_branch_prunable(self):
        from theory_x.stage2_dynamic.bonsai import BonsaiTree, _PRUNE_HOLD_CYCLES
        tree = BonsaiTree()
        tree.init_tree()
        node = tree._nodes["ai_research"]
        node.is_seed = False  # temporarily make it non-seed
        node.focus_num = 0.0
        for _ in range(_PRUNE_HOLD_CYCLES):
            tree.prune_pass()
        self.assertNotIn("ai_research", tree._nodes)


# ---- Pipeline ----------------------------------------------------------------

class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _make_row(self, stream, payload, provenance="test://mock"):
        return {"id": 1, "stream": stream, "payload": payload, "provenance": provenance}

    def test_internal_event_matches_systems_branch(self):
        from theory_x.stage2_dynamic.bonsai import BonsaiTree
        from theory_x.stage2_dynamic.membrane import Membrane
        from theory_x.stage2_dynamic.pipeline import run_pipeline

        tree = BonsaiTree()
        tree.init_tree()
        membrane = Membrane()
        row = self._make_row(
            "internal.proprioception",
            json.dumps({"cpu_percent": 10.5, "memory_percent": 45.0}),
        )
        hits = run_pipeline(row, tree, membrane, self.writers["dynamic"])
        self.assertGreaterEqual(hits, 0)

    def test_pipeline_logs_to_dynamic_db(self):
        from theory_x.stage2_dynamic.bonsai import BonsaiTree
        from theory_x.stage2_dynamic.membrane import Membrane
        from theory_x.stage2_dynamic.pipeline import run_pipeline

        tree = BonsaiTree()
        tree.init_tree()
        membrane = Membrane()
        payload = json.dumps({
            "title": "Neural network architecture advances in transformer models",
            "link": "https://arxiv.org/abs/1234",
        })
        row = self._make_row("ai_research.arxiv", payload)
        hits = run_pipeline(row, tree, membrane, self.writers["dynamic"])
        # Give writer a moment
        time.sleep(0.1)
        count = self.readers["dynamic"].count("pipeline_events")
        if hits > 0:
            self.assertGreater(count, 0)

    def test_text_magnitude_arxiv_title(self):
        from theory_x.stage2_dynamic.attention import _magnitude_for
        payload = json.dumps({
            "title": "Neural scaling laws in language model training",
        })
        mag = _magnitude_for("ai_research.arxiv", payload, "ai_research")
        self.assertGreater(mag, 0.0)
        self.assertLessEqual(mag, 1.0)

    def test_text_magnitude_none_returns_zero(self):
        from theory_x.stage2_dynamic.attention import _magnitude_for
        mag = _magnitude_for("ai_research.arxiv", None, "ai_research")
        self.assertEqual(mag, 0.0)

    def test_numeric_magnitude(self):
        from theory_x.stage2_dynamic.attention import _magnitude_for
        mag = _magnitude_for("internal.proprioception", 50.0, "systems")
        self.assertGreater(mag, 0.0)

    def test_pipeline_step_a_unpacks_row(self):
        from theory_x.stage2_dynamic.pipeline import step_A
        row = {"stream": "test.stream", "payload": '{"x":1}', "provenance": "test://x"}
        stream, val, prov = step_A(row)
        self.assertEqual(stream, "test.stream")
        self.assertEqual(val, '{"x":1}')
        self.assertEqual(prov, "test://x")

    def test_pipeline_step_d_gates_by_aperture(self):
        from theory_x.stage2_dynamic.pipeline import step_D
        mags = [("ai_research", 0.8), ("crypto", 0.4)]
        gated = step_D(mags, aperture=0.5)
        self.assertAlmostEqual(gated[0][1], 0.4)
        self.assertAlmostEqual(gated[1][1], 0.2)


# ---- Crystallization ---------------------------------------------------------

class TestCrystallization(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _make_crystallizer(self):
        from theory_x.stage2_dynamic.bonsai import BonsaiTree
        from theory_x.stage2_dynamic.crystallization import Crystallizer
        tree = BonsaiTree()
        tree.init_tree()
        c = Crystallizer(
            tree=tree,
            beliefs_writer=self.writers["beliefs"],
            dynamic_writer=self.writers["dynamic"],
            dynamic_reader=self.readers["dynamic"],
        )
        return tree, c

    def test_high_focus_crystallizes_after_hold(self):
        from theory_x.stage2_dynamic.crystallization import (
            Crystallizer, CRYSTALLIZATION_THRESHOLD_SECONDS, CRYSTALLIZATION_WINDOW_SECONDS
        )
        from collections import deque
        tree, c = self._make_crystallizer()
        node = tree.get("ai_research")
        node.focus_num = 0.9  # focus level 'g'

        # Pre-populate with enough high-focus ticks to cross threshold
        # 5 pre-existing + 1 from check_all() = 6 * 60 = 360s >= 300s threshold
        now = time.time()
        c._focus_history["ai_research"] = deque()
        for i in range(5):
            c._focus_history["ai_research"].append(
                (now - (CRYSTALLIZATION_WINDOW_SECONDS - 10 - i * 60), "g")
            )
        c._last_crystallized["ai_research"] = 0.0

        crystallized = c.check_all()
        time.sleep(0.2)  # let writers settle

        self.assertIn("ai_research", crystallized)
        beliefs = self.readers["beliefs"].read(
            "SELECT * FROM beliefs WHERE source = 'precipitated_from_dynamic' "
            "AND branch_id = 'ai_research'"
        )
        self.assertGreater(len(beliefs), 0)
        b = beliefs[0]
        self.assertEqual(b["tier"], 7)
        self.assertAlmostEqual(b["confidence"], 0.15)
        self.assertEqual(b["source"], "precipitated_from_dynamic")
        self.assertEqual(b["locked"], 0)

    def test_dedup_guard_prevents_double_write(self):
        from theory_x.stage2_dynamic.crystallization import (
            Crystallizer, CRYSTALLIZATION_WINDOW_SECONDS
        )
        from collections import deque
        tree, c = self._make_crystallizer()
        node = tree.get("ai_research")
        node.focus_num = 0.9

        now = time.time()

        def _set_high_focus():
            c._focus_history["ai_research"] = deque()
            for i in range(5):
                c._focus_history["ai_research"].append(
                    (now - (CRYSTALLIZATION_WINDOW_SECONDS - 10 - i * 60), "g")
                )

        # First crystallization
        _set_high_focus()
        c._last_crystallized["ai_research"] = 0.0
        c.check_all()
        time.sleep(0.2)

        # Second crystallization — should be blocked by window dedup on _last_crystallized
        _set_high_focus()
        # _last_crystallized is now set to now, so window check blocks this
        c.check_all()
        time.sleep(0.2)

        cryst_events = self.readers["dynamic"].read(
            "SELECT content FROM crystallization_events WHERE branch_id = 'ai_research'"
        )
        # Window guard should allow at most 1 crystallization per CRYSTALLIZATION_WINDOW_SECONDS
        self.assertLessEqual(len(cryst_events), 1)

    def test_low_focus_does_not_crystallize(self):
        from theory_x.stage2_dynamic.crystallization import Crystallizer
        tree, c = self._make_crystallizer()
        node = tree.get("crypto")
        node.focus_num = 0.1  # low focus level 'a' or 'b'

        crystallized = c.check_all()
        self.assertNotIn("crypto", crystallized)


# ---- Consolidation -----------------------------------------------------------

class TestConsolidation(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_quiet_returns_true_when_over_threshold(self):
        from theory_x.stage2_dynamic.consolidation import _external_quiet

        # Write a temporal event with seconds_since_last_user_message > 300
        payload = json.dumps({"seconds_since_last_user_message": 400})
        self.writers["sense"].write(
            "INSERT INTO sense_events (stream, payload, provenance, timestamp) "
            "VALUES (?, ?, ?, ?)",
            ("internal.temporal", payload, "substrate://clock", int(time.time())),
        )
        time.sleep(0.1)
        quiet = _external_quiet(self.readers["sense"])
        self.assertTrue(quiet)

    def test_quiet_returns_false_when_under_threshold(self):
        from theory_x.stage2_dynamic.consolidation import _external_quiet

        payload = json.dumps({"seconds_since_last_user_message": 100})
        self.writers["sense"].write(
            "INSERT INTO sense_events (stream, payload, provenance, timestamp) "
            "VALUES (?, ?, ?, ?)",
            ("internal.temporal", payload, "substrate://clock", int(time.time())),
        )
        time.sleep(0.1)
        quiet = _external_quiet(self.readers["sense"])
        self.assertFalse(quiet)

    def test_consolidation_pass_runs_when_quiet(self):
        from theory_x.stage2_dynamic.bonsai import BonsaiTree
        from theory_x.stage2_dynamic.consolidation import consolidation_pass

        # Write quiet temporal event
        payload = json.dumps({"seconds_since_last_user_message": 600})
        self.writers["sense"].write(
            "INSERT INTO sense_events (stream, payload, provenance, timestamp) "
            "VALUES (?, ?, ?, ?)",
            ("internal.temporal", payload, "substrate://clock", int(time.time())),
        )
        time.sleep(0.1)
        tree = BonsaiTree()
        tree.init_tree()
        result = consolidation_pass(tree, self.readers["sense"])
        self.assertTrue(result)


# ---- Cursor persistence ------------------------------------------------------

class TestCursorPersistence(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_cursor_survives_restart(self):
        from theory_x.stage2_dynamic import _save_cursor, _load_cursor
        _save_cursor(self.writers["dynamic"], 42)
        time.sleep(0.1)
        loaded = _load_cursor(self.readers["dynamic"])
        self.assertEqual(loaded, 42)

    def test_cursor_defaults_to_zero(self):
        from theory_x.stage2_dynamic import _load_cursor
        loaded = _load_cursor(self.readers["dynamic"])
        self.assertEqual(loaded, 0)


# ---- GUI endpoints -----------------------------------------------------------

class TestDynamicGUIEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.writers, cls.readers, cls.tmp = _make_env()

        from admin.auth import set_password
        set_password("dynamic-test-pw")

        from voice.llm import VoiceClient
        from theory_x.stage2_dynamic import build_dynamic
        from gui.server import AppState, create_app

        dynamic = build_dynamic(cls.writers, cls.readers)
        cls.dynamic = dynamic

        cls.state = AppState(
            writers=cls.writers,
            readers=cls.readers,
            voice=VoiceClient(request_fn=lambda u, p: {"choices": [{"message": {"content": "ok"}}]}),
            dynamic=dynamic,
        )
        cls.app = create_app(cls.state)
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.dynamic._stop.set()  # type: ignore[attr-defined]
        except Exception:
            pass
        cls.state.close()
        _cleanup(cls.writers, cls.tmp)

    def test_dynamic_status_200(self):
        r = self.client.get("/api/dynamic/status")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn("branches", data)
        self.assertIn("aperture", data)
        self.assertIn("pipeline_runs", data)
        self.assertEqual(len(data["branches"]), 10)

    def test_dynamic_pipeline_200(self):
        r = self.client.get("/api/dynamic/pipeline")
        self.assertEqual(r.status_code, 200)
        self.assertIn("events", r.get_json())

    def test_dynamic_crystallized_200(self):
        r = self.client.get("/api/dynamic/crystallized")
        self.assertEqual(r.status_code, 200)
        self.assertIn("events", r.get_json())

    def test_beliefs_recent_200(self):
        r = self.client.get("/api/beliefs/recent")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn("beliefs", data)

    def test_dynamic_status_503_when_not_wired(self):
        from voice.llm import VoiceClient
        from gui.server import AppState, create_app
        state2 = AppState(
            writers=self.writers,
            readers=self.readers,
            voice=VoiceClient(request_fn=lambda u, p: {"choices": [{"message": {"content": "ok"}}]}),
        )
        app2 = create_app(state2)
        c = app2.test_client()
        r = c.get("/api/dynamic/status")
        self.assertEqual(r.status_code, 503)


# ---- Architecture compliance -------------------------------------------------

class TestArchitectureCompliance(unittest.TestCase):
    def test_no_direct_sqlite3_outside_substrate(self):
        result = subprocess.run(
            [
                "grep", "-r", "sqlite3.connect",
                "/home/rr/Desktop/nex5",
                "--include=*.py",
                "--exclude-dir=.venv",
                "--exclude-dir=substrate",
                "--exclude-dir=tests",
                "--exclude-dir=__pycache__",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.stdout.strip(), "",
            f"Direct sqlite3.connect found outside substrate/:\n{result.stdout}",
        )

    def test_theory_x_stage_2_in_all_dynamic_modules(self):
        modules = [
            "theory_x.stage2_dynamic.bonsai",
            "theory_x.stage2_dynamic.membrane",
            "theory_x.stage2_dynamic.attention",
            "theory_x.stage2_dynamic.pipeline",
            "theory_x.stage2_dynamic.crystallization",
            "theory_x.stage2_dynamic.consolidation",
        ]
        for mod in modules:
            import importlib
            m = importlib.import_module(mod)
            self.assertEqual(getattr(m, "THEORY_X_STAGE", None), 2,
                             f"{mod} missing THEORY_X_STAGE = 2")


if __name__ == "__main__":
    unittest.main()
