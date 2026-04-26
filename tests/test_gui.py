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
        self.assertEqual(data["register"], "Conversational")
        self.assertTrue(data["voice_ok"])

        # Explicit register selection.
        r = self.client.post(
            "/api/chat", json={"prompt": "deep dive", "register": "Technical"}
        )
        self.assertEqual(r.get_json()["register"], "Technical")

        # Verify persistence: each chat writes user + nex rows.
        n = self.readers["conversations"].count("messages")
        self.assertGreaterEqual(n, 4)


if __name__ == "__main__":
    unittest.main()
