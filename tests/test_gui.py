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
