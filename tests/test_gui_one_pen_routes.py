"""GUI admin writes and coincidence snapshots must use AppState Writers."""
from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from tests import _bootstrap  # noqa: F401


def _mock_req(url, payload):
    return {"choices": [{"message": {"content": "mocked"}}]}


class TestGuiOnePenRoutes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="nex5_gui_one_pen_")
        os.environ["NEX5_DATA_DIR"] = self.tmp.name
        os.environ["NEX5_ADMIN_HASH_FILE"] = str(Path(self.tmp.name) / "admin.argon2")
        from substrate.init_db import init_all
        init_all()
        from admin.auth import set_password
        set_password("unit-test-pw")
        from substrate import Reader, Writer, db_paths
        from voice.llm import VoiceClient
        from gui.server import AppState, create_app
        paths = db_paths()
        self.writers = {name: Writer(path, name=name) for name, path in paths.items()}
        self.readers = {name: Reader(path) for name, path in paths.items()}
        self.state = AppState(
            writers=self.writers,
            readers=self.readers,
            voice=VoiceClient(request_fn=_mock_req),
        )
        self.app = create_app(self.state)
        self.client = self.app.test_client()
        self._login()

    def tearDown(self):
        self.state.close()
        os.environ.pop("NEX5_DATA_DIR", None)
        os.environ.pop("NEX5_ADMIN_HASH_FILE", None)
        self.tmp.cleanup()

    def _login(self):
        response = self.client.post("/api/admin/login", json={"password": "unit-test-pw"})
        self.assertEqual(response.status_code, 200)

    def _seed_fire(self, thought="Astronomy can be surprising."):
        return self.writers["dynamic"].write(
            "INSERT INTO fountain_events (ts, thought, readiness, hot_branch, word_count) "
            "VALUES (?, ?, ?, ?, ?)",
            (time.time(), thought, 0.8, "systems", len(thought.split())),
        )

    def test_word_tag_mutations_do_not_open_raw_connections(self):
        from gui import server as gui_server

        with patch.object(
            gui_server, "connect",
            side_effect=AssertionError("word-tag route opened a raw DB connection"),
        ):
            response = self.client.post(
                "/api/decoder/word_tag",
                json={"word": "astronomy", "tag": "key", "note": "grounded"},
            )
        self.assertEqual(response.status_code, 200)
        row = self.readers["dynamic"].read_one(
            "SELECT tag, note FROM word_tags WHERE word=?", ("astronomy",)
        )
        self.assertEqual(row["tag"], "key")
        self.assertEqual(row["note"], "grounded")

    def test_coincidence_tag_uses_writer_for_tag_and_hypothesis_updates(self):
        from gui import server as gui_server
        from theory_x.coincidence import context_capture

        fid = self._seed_fire()
        self.writers["dynamic"].write(
            "INSERT INTO word_contexts (word, fountain_event_id) VALUES (?, ?)",
            ("astronomy", fid),
        )
        hid = self.writers["dynamic"].write(
            "INSERT INTO hypotheses (created_at, claim, keywords) VALUES (?, ?, ?)",
            (time.time(), "Astronomy is relevant", "astronomy"),
        )
        captured = {}

        def capture_stub(fire_id, tag, dynamic_writer=None):
            captured.update(fire_id=fire_id, tag=tag, writer=dynamic_writer)
            return {}

        with patch.object(
            gui_server, "connect",
            side_effect=AssertionError("coincidence route opened a raw DB connection"),
        ), patch.object(context_capture, "capture_and_persist", side_effect=capture_stub):
            response = self.client.post(
                "/api/coincidence/tag",
                json={"fountain_event_id": fid, "tag": "coin"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIs(captured["writer"], self.writers["dynamic"])
        fire = self.readers["dynamic"].read_one(
            "SELECT tag FROM fountain_events WHERE id=?", (fid,)
        )
        word = self.readers["dynamic"].read_one(
            "SELECT fountain_tag FROM word_contexts WHERE fountain_event_id=?", (fid,)
        )
        hypothesis = self.readers["dynamic"].read_one(
            "SELECT supporting FROM hypotheses WHERE id=?", (hid,)
        )
        self.assertEqual(fire["tag"], "coin")
        self.assertEqual(word["fountain_tag"], "coin")
        self.assertEqual(hypothesis["supporting"], 1)

    def test_ghost_flag_routes_use_shared_dynamic_writer(self):
        from gui import server as gui_server

        fid = self._seed_fire("A ghostly coincidence in the world.")
        with patch.object(
            gui_server, "connect",
            side_effect=AssertionError("ghost route opened a raw DB connection"),
        ):
            flagged = self.client.post(
                "/api/ghost/flag",
                json={"fountain_event_id": fid, "reason": "felt significant"},
            )
            self.assertEqual(flagged.status_code, 200)
            row = self.readers["dynamic"].read_one(
                "SELECT reason FROM ghost_flags WHERE fountain_event_id=?", (fid,)
            )
            self.assertEqual(row["reason"], "felt significant")
            unflagged = self.client.post(
                "/api/ghost/unflag", json={"fountain_event_id": fid}
            )
        self.assertEqual(unflagged.status_code, 200)
        self.assertIsNone(self.readers["dynamic"].read_one(
            "SELECT id FROM ghost_flags WHERE fountain_event_id=?", (fid,)
        ))

    def test_hypothesis_create_and_update_use_shared_writer(self):
        from gui import server as gui_server

        with patch.object(
            gui_server, "connect",
            side_effect=AssertionError("hypothesis route opened a raw DB connection"),
        ):
            created = self.client.post(
                "/api/hypothesis",
                json={"claim": "The sky is blue", "keywords": "sky", "time_window": None},
            )
            self.assertEqual(created.status_code, 200)
            hid = created.get_json()["id"]
            updated = self.client.patch(
                f"/api/hypothesis/{hid}",
                json={"status": "confirmed", "notes": "checked"},
            )
        self.assertEqual(updated.status_code, 200)
        row = self.readers["dynamic"].read_one(
            "SELECT status, notes FROM hypotheses WHERE id=?", (hid,)
        )
        self.assertEqual(row["status"], "confirmed")
        self.assertEqual(row["notes"], "checked")

    def test_context_snapshot_persist_uses_injected_dynamic_writer(self):
        from theory_x.coincidence import context_capture

        snapshot = {
            "fountain_event_id": 999,
            "tagged_at": time.time(),
            "tag": "coin",
            "aperture": 0.4,
            "hot_branch": "systems",
            "branch_activations": "[]",
            "recent_fountain": "[]",
            "recent_surprises": "[]",
            "recent_daemons": "[]",
            "belief_delta_1h": 0,
            "groove_alerts": None,
            "last_identity": None,
            "last_pattern": None,
            "last_witness": None,
            "full_snapshot": "{}",
        }
        with patch.object(
            context_capture, "Writer",
            side_effect=AssertionError("context capture opened a second dynamic Writer"),
        ):
            self.assertTrue(context_capture.persist(
                snapshot, dynamic_writer=self.writers["dynamic"]
            ))
        row = self.readers["dynamic"].read_one(
            "SELECT tag, hot_branch FROM coincidence_context WHERE fountain_event_id=999"
        )
        self.assertEqual(row["tag"], "coin")
        self.assertEqual(row["hot_branch"], "systems")


if __name__ == "__main__":
    unittest.main()
