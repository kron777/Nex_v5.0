"""GUI endpoint smoke tests — Alpha, stats, queues, errors, admin, chat."""
import os
import tempfile
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401


def _mock_req(url, payload):
    return {"choices": [{"message": {"content": "mocked"}}]}


class TestGuiEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        tmp = cls._tmp.name
        os.environ["NEX5_DATA_DIR"] = tmp
        os.environ["NEX5_ADMIN_HASH_FILE"] = str(Path(tmp) / "admin.argon2")

        from substrate.init_db import init_all
        init_all()

        from admin.auth import set_password
        set_password("unit-test-pw")

        from substrate import Reader, Writer, db_paths
        from voice.llm import VoiceClient
        from gui.server import AppState, create_app

        paths = db_paths()
        cls.writers = {n: Writer(p, name=n) for n, p in paths.items()}
        cls.readers = {n: Reader(p) for n, p in paths.items()}
        cls.state = AppState(
            writers=cls.writers,
            readers=cls.readers,
            voice=VoiceClient(request_fn=_mock_req),
        )
        cls.app = create_app(cls.state)

        # A route that raises, wired before the first request, so the global
        # error handler's 500 path is exercisable.
        def _boom():
            raise RuntimeError("boom")
        cls.app.add_url_rule("/__boom__", "__boom__", _boom)

        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.state.close()
        cls._tmp.cleanup()
        os.environ.pop("NEX5_DATA_DIR", None)
        os.environ.pop("NEX5_ADMIN_HASH_FILE", None)

    def test_alpha(self):
        r = self.client.get("/api/alpha")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.get_json()["lines"]), 5)

    def test_db_stats(self):
        r = self.client.get("/api/db/stats")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertGreaterEqual(data["beliefs"]["tables"]["beliefs"], 7)
        self.assertIn("sense_events", data["sense"]["tables"])

    def test_writer_queues(self):
        r = self.client.get("/api/writers/queues")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            set(r.get_json().keys()),
            {"beliefs", "sense", "dynamic", "intel", "conversations", "probes"},
        )

    def test_health_ok(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("beliefs", data["dbs"])
        self.assertTrue(all(v == "ok" for v in data["dbs"].values()), data["dbs"])

    def test_admin_flow(self):
        r = self.client.get("/api/admin/status")
        self.assertTrue(r.get_json()["configured"])
        self.assertFalse(r.get_json()["authenticated"])

        # Wrong password.
        r = self.client.post("/api/admin/login", json={"password": "no"})
        self.assertEqual(r.status_code, 401)

        # Right password.
        r = self.client.post("/api/admin/login", json={"password": "unit-test-pw"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["authenticated"])

        # Logout.
        r = self.client.post("/api/admin/logout")
        self.assertEqual(r.status_code, 200)

    def test_chat_persists(self):
        # Empty prompt rejected.
        r = self.client.post("/api/chat", json={"prompt": "  "})
        self.assertEqual(r.status_code, 400)

        r = self.client.post("/api/chat", json={"prompt": "hi"})
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["text"], "mocked")
        # Default chat register is Philosophical since EDIT A (2026-05-29,
        # gui/server.py — "probe-quality richness"); was Conversational.
        self.assertEqual(data["register"], "Philosophical")
        self.assertTrue(data["voice_ok"])

        # Explicit register selection.
        r = self.client.post(
            "/api/chat", json={"prompt": "deep dive", "register": "Technical"}
        )
        self.assertEqual(r.get_json()["register"], "Technical")

        # Verify persistence: each chat writes user + nex rows.
        n = self.readers["conversations"].count("messages")
        self.assertGreaterEqual(n, 4)


    def test_chat_calculation_uses_safe_tool_wire(self):
        from theory_x.stage_capability.tools import ToolRegistry
        from theory_x.stage_capability.tool_caller import ToolCaller

        registry = ToolRegistry(beliefs_reader=self.readers["beliefs"])
        self.state.tool_registry = registry
        self.state.tool_caller = ToolCaller(registry)
        captured = []
        original_request = self.state.voice._request_fn
        self.state.voice._request_fn = (
            lambda url, payload: (captured.append(payload) or _mock_req(url, payload))
        )
        try:
            response = self.client.post(
                "/api/chat",
                json={"prompt": "calculate 15 * 37", "is_probe": True},
            )
            self.assertEqual(response.status_code, 200, response.get_json())
            data = response.get_json()
            self.assertEqual(data["tool_used"], "python_exec")
            self.assertTrue(captured)
            self.assertIn("Result: 555", captured[-1]["messages"][1]["content"])
        finally:
            self.state.voice._request_fn = original_request
            self.state.tool_registry = None
            self.state.tool_caller = None

    def test_g83_reflection_reaches_voice_prompt_only_after_chat_gap_gate(self):
        """Trace the reflective strings through the real chat route to transport."""
        import time
        from unittest.mock import patch
        from theory_x.stage9_metacognition.metacognition import Metacognition
        from theory_x.stage_self_narrative.self_narrative import SelfNarrative

        old_mc = getattr(self.state, "metacognition", None)
        old_narrative = getattr(self.state, "self_narrative", None)
        original_request = self.state.voice._request_fn
        captured = []
        self.state.voice._request_fn = (
            lambda url, payload: (captured.append(payload) or _mock_req(url, payload))
        )
        narrative = SelfNarrative(
            self.writers["conversations"], self.readers["conversations"]
        )
        mc = Metacognition(
            self.writers["conversations"],
            self.readers["conversations"],
            self.readers["beliefs"],
            narrative=narrative,
        )
        mc._detect_goal_drift = lambda now: None
        mc._detect_drift = lambda: []
        mc._detect_digest = lambda now: []
        mc._detect_self_pattern = lambda now: []
        self.state.metacognition = mc
        self.state.self_narrative = narrative
        source_id = None
        try:
            source_id = self.writers["beliefs"].write(
                "INSERT INTO groove_alerts "
                "(detected_at, alert_type, severity, pattern, window_size) "
                "VALUES (?, 'ngram_repetition', 0.7, 'same source pattern', 5)",
                (time.time() - 5,),
            )

            # Technical is not in _ALLOW_THIN_REGISTERS. Force the documented
            # threshold branch deterministically so this first request returns
            # before VoiceClient.speak(), even though reflection was formatted.
            with patch("gui.server.CHAT_GAP_MIN_BELIEFS", 999):
                blocked = self.client.post(
                    "/api/chat",
                    json={"prompt": "same source pattern", "register": "Technical"},
                )
            self.assertEqual(blocked.status_code, 200, blocked.get_json())
            self.assertEqual(
                blocked.get_json()["text"],
                "That doesn't reach my graph right now.",
            )
            self.assertEqual(captured, [], "gap return must precede voice transport")

            # Philosophical is explicitly allowed through the thin-belief gate.
            allowed = self.client.post(
                "/api/chat",
                json={"prompt": "same source pattern", "register": "Philosophical"},
            )
            self.assertEqual(allowed.status_code, 200, allowed.get_json())
            self.assertEqual(len(captured), 1)
            user_message = captured[0]["messages"][1]["content"]
            self.assertIn(
                "Self-observation: I notice repeated patterns in my recent thinking.",
                user_message,
            )
            self.assertIn(
                "I noticed I am repeatedly returning to same source pattern",
                user_message,
            )
        finally:
            self.state.voice._request_fn = original_request
            self.state.metacognition = old_mc
            self.state.self_narrative = old_narrative
            if source_id is not None:
                self.writers["beliefs"].write(
                    "DELETE FROM groove_alerts WHERE id = ?", (source_id,)
                )

    def test_unknown_path_returns_json_404(self):
        r = self.client.get("/api/definitely-not-a-route")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.get_json()["error"], "not found")

    def test_wrong_method_returns_json_405(self):
        # /api/admin/login is POST-only; a GET must be a JSON 405, not HTML.
        r = self.client.get("/api/admin/login")
        self.assertEqual(r.status_code, 405)
        self.assertIn("error", r.get_json())

    def test_unhandled_exception_returns_json_500(self):
        # The global handler must turn an unhandled error into a JSON 500,
        # never a bare HTML traceback (/__boom__ is wired in setUpClass).
        r = self.client.get("/__boom__")
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.get_json()["error"], "internal error")

    def test_auth_gate_covers_every_mutating_route(self):
        # C1 regression lock: EVERY mutating route except the small public
        # allowlist must 403 for an unauthenticated caller. Introspects the
        # url_map so a future route added without the gate fails this test.
        import re as _re
        public = {"api_admin_login", "api_admin_logout", "api_chat", "static",
                  "__boom__"}
        mutating = {"POST", "PUT", "PATCH", "DELETE"}
        anon = self.app.test_client()  # fresh client, no admin session
        checked = 0
        for rule in self.app.url_map.iter_rules():
            methods = (rule.methods or set()) & mutating
            if not methods or rule.endpoint in public:
                continue
            path = _re.sub(r"<[^>]+>", "1", rule.rule)  # fill path params
            method = "POST" if "POST" in methods else sorted(methods)[0]
            r = anon.open(path, method=method, json={})
            self.assertEqual(
                r.status_code, 403,
                f"{method} {path} ({rule.endpoint}) not gated -> {r.status_code}",
            )
            checked += 1
        self.assertGreater(checked, 20, "expected a real mutating surface")


if __name__ == "__main__":
    unittest.main()
