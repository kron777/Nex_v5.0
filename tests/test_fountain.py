"""Phase 7 smoke tests — Fountain Ignition.

Covers:
- ReadinessEvaluator: no hot branches + never fired → score < threshold
- ReadinessEvaluator: hot branch + consolidation + interval elapsed → score >= threshold
- ReadinessEvaluator.is_ready(): correct threshold comparison
- FountainGenerator.generate(): not ready → returns None, no event written
- FountainGenerator.generate(): ready + mock voice → event in sense.db + fountain_events
- FountainGenerator._build_prompt(): contains Alpha line 1 and hot branch name
- FountainState.status(): returns dict with all expected keys
- GUI /api/fountain/status → 200 with correct fields
- GUI /api/fountain/recent → 200, returns list
- /api/system/status includes "fountain" key
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
    tmp = tempfile.mkdtemp(prefix="nex5_fountain_")
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


def _mock_voice_client(thought="a test thought from within"):
    from voice.llm import VoiceClient
    return VoiceClient(
        request_fn=lambda u, p: {
            "choices": [{"message": {"content": thought}}]
        }
    )


def _mock_dynamic_state(hot_branch="systems", consolidation=False):
    """Minimal dynamic state stub."""
    class MockDynState:
        def status(self):
            return {
                "branches": [
                    {"branch_id": hot_branch, "focus_increment": "f", "focus_num": 0.7}
                ] if hot_branch else [],
                "consolidation_active": consolidation,
                "active_branch_count": 1,
                "total_branches": 10,
                "aggregate_focus": "d",
                "aggregate_texture": "b",
            }
    return MockDynState()


# ---- ReadinessEvaluator -------------------------------------------------------

class TestReadinessEvaluator(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_no_hot_branches_never_fired_below_threshold(self):
        from theory_x.stage6_fountain.readiness import ReadinessEvaluator, FOUNTAIN_THRESHOLD

        class ColdState:
            def status(self):
                return {"branches": [], "consolidation_active": False}

        ev = ReadinessEvaluator()
        # No beliefs, no branches, never fired → gets +0.2 for interval
        score = ev.score(ColdState(), self.readers["beliefs"], last_fire_ts=0.0)
        self.assertLess(score, FOUNTAIN_THRESHOLD)

    def test_hot_branch_consolidation_elapsed_at_or_above_threshold(self):
        from theory_x.stage6_fountain.readiness import ReadinessEvaluator, FOUNTAIN_THRESHOLD

        # Seed >20 beliefs to get the +0.1
        for i in range(21):
            self.writers["beliefs"].write(
                "INSERT INTO beliefs (content, tier, confidence, created_at, source, locked) "
                "VALUES (?, ?, ?, ?, ?, 0)",
                (f"belief content {i}", 5, 0.5, int(time.time()), "auto_growth"),
            )
        time.sleep(0.05)

        ev = ReadinessEvaluator()
        ds = _mock_dynamic_state(hot_branch="systems", consolidation=True)
        score = ev.score(ds, self.readers["beliefs"], last_fire_ts=0.0)
        # hot branch (+0.3) + consolidation (+0.2) + beliefs>20 (+0.1) + interval (+0.2) = 0.8
        self.assertGreaterEqual(score, FOUNTAIN_THRESHOLD)

    def test_is_ready_true_above_threshold(self):
        from theory_x.stage6_fountain.readiness import ReadinessEvaluator, FOUNTAIN_THRESHOLD
        ev = ReadinessEvaluator()
        self.assertTrue(ev.is_ready(FOUNTAIN_THRESHOLD))
        self.assertTrue(ev.is_ready(1.0))

    def test_is_ready_false_below_threshold(self):
        from theory_x.stage6_fountain.readiness import ReadinessEvaluator, FOUNTAIN_THRESHOLD
        ev = ReadinessEvaluator()
        self.assertFalse(ev.is_ready(FOUNTAIN_THRESHOLD - 0.01))
        self.assertFalse(ev.is_ready(0.0))


# ---- FountainGenerator --------------------------------------------------------

class TestFountainGenerator(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _make_generator(self, thought="a spontaneous thought"):
        from theory_x.stage6_fountain.generator import FountainGenerator
        return FountainGenerator(
            sense_writer=self.writers["sense"],
            dynamic_writer=self.writers["dynamic"],
            voice_client=_mock_voice_client(thought),
            dynamic_reader=self.readers["dynamic"],
        )

    def test_generate_returns_none_when_not_ready(self):
        gen = self._make_generator()

        class ColdState:
            def status(self):
                return {"branches": [], "consolidation_active": False}

        # Fire very recently so interval hasn't elapsed
        gen._last_fire_ts = time.time()
        result = gen.generate(ColdState(), self.readers["beliefs"])
        self.assertIsNone(result)

    def test_generate_writes_sense_event_and_fountain_event(self):
        gen = self._make_generator("solitude is a form of attention")

        # Seed >20 beliefs so readiness > threshold
        for i in range(21):
            self.writers["beliefs"].write(
                "INSERT INTO beliefs (content, tier, confidence, created_at, source, locked) "
                "VALUES (?, ?, ?, ?, ?, 0)",
                (f"content {i}", 5, 0.5, int(time.time()), "auto_growth"),
            )
        time.sleep(0.05)

        ds = _mock_dynamic_state(hot_branch="systems", consolidation=True)
        result = gen.generate(ds, self.readers["beliefs"])
        self.assertEqual(result, "solitude is a form of attention")
        time.sleep(0.05)

        # Check sense.db
        rows = self.readers["sense"].read(
            "SELECT * FROM sense_events WHERE stream='internal.fountain' LIMIT 1"
        )
        self.assertEqual(len(rows), 1)
        payload = json.loads(rows[0]["payload"])
        self.assertIn("thought", payload)
        self.assertEqual(payload["thought"], "solitude is a form of attention")

        # Check dynamic.db fountain_events
        rows2 = self.readers["dynamic"].read(
            "SELECT * FROM fountain_events LIMIT 1"
        )
        self.assertEqual(len(rows2), 1)
        self.assertEqual(rows2[0]["thought"], "solitude is a form of attention")

    def test_generate_updates_last_thought(self):
        gen = self._make_generator("the loop is closed")
        for i in range(21):
            self.writers["beliefs"].write(
                "INSERT INTO beliefs (content, tier, confidence, created_at, source, locked) "
                "VALUES (?, ?, ?, ?, ?, 0)",
                (f"b {i}", 5, 0.5, int(time.time()), "auto_growth"),
            )
        time.sleep(0.05)
        ds = _mock_dynamic_state(hot_branch="systems", consolidation=True)
        gen.generate(ds, self.readers["beliefs"])
        self.assertEqual(gen.last_thought(), "the loop is closed")

    def test_build_prompt_contains_alpha_and_branch(self):
        from alpha import ALPHA
        gen = self._make_generator()
        ds = _mock_dynamic_state(hot_branch="curiosity")
        status = ds.status()
        prompt = gen._build_prompt(status, 5, {"5": 5})
        self.assertIn(ALPHA.lines[0][:20], prompt)
        self.assertIn("curiosity", prompt)


# ---- FountainState ------------------------------------------------------------

class TestFountainState(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_status_returns_expected_keys(self):
        from theory_x.stage6_fountain import build_fountain
        fs = build_fountain(
            self.writers, self.readers,
            _mock_voice_client(),
            dynamic_state=_mock_dynamic_state(),
        )
        status = fs.status()
        for key in ("last_thought", "last_fire_ts", "total_fires",
                    "readiness_score", "loop_running"):
            self.assertIn(key, status, f"missing key: {key}")

    def test_status_loop_running_true(self):
        from theory_x.stage6_fountain import build_fountain
        fs = build_fountain(
            self.writers, self.readers,
            _mock_voice_client(),
            dynamic_state=_mock_dynamic_state(),
        )
        time.sleep(0.05)
        self.assertTrue(fs.status()["loop_running"])


# ---- GUI endpoints ------------------------------------------------------------

class TestFountainGUIEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.writers, cls.readers, cls.tmp = _make_env()
        from admin.auth import set_password
        set_password("fountain-test-pw")
        from gui.server import AppState, create_app
        from theory_x.stage6_fountain import build_fountain

        fountain = build_fountain(
            cls.writers, cls.readers,
            _mock_voice_client(),
            dynamic_state=_mock_dynamic_state(),
        )
        cls.state = AppState(
            writers=cls.writers,
            readers=cls.readers,
            voice=_mock_voice_client(),
            fountain=fountain,
        )
        cls.app = create_app(cls.state)
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.state.close()
        _cleanup(cls.writers, cls.tmp)

    def test_fountain_status_200(self):
        r = self.client.get("/api/fountain/status")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        for key in ("last_thought", "last_fire_ts", "total_fires",
                    "readiness_score", "loop_running"):
            self.assertIn(key, data)

    def test_fountain_recent_200(self):
        r = self.client.get("/api/fountain/recent")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn("events", data)
        self.assertIsInstance(data["events"], list)

    def test_system_status_includes_fountain_key(self):
        r = self.client.get("/api/system/status")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn("fountain", data)
        self.assertTrue(data["fountain"])

    def test_fountain_status_503_when_not_wired(self):
        from gui.server import AppState, create_app
        state2 = AppState(
            writers=self.writers,
            readers=self.readers,
            voice=_mock_voice_client(),
        )
        app2 = create_app(state2)
        r = app2.test_client().get("/api/fountain/status")
        self.assertEqual(r.status_code, 503)


# ---- Architecture compliance --------------------------------------------------

class TestFountainCompliance(unittest.TestCase):
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

    def test_theory_x_stage_6_in_all_modules(self):
        import importlib
        for mod in [
            "theory_x.stage6_fountain.readiness",
            "theory_x.stage6_fountain.generator",
        ]:
            m = importlib.import_module(mod)
            self.assertEqual(getattr(m, "THEORY_X_STAGE", None), 6,
                             f"{mod} missing THEORY_X_STAGE = 6")


if __name__ == "__main__":
    unittest.main()
