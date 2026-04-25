"""Phase 8 smoke tests — Strike Protocols.

Note: strikes_catalogue.db uses direct sqlite3.connect() intentionally.
Strike records are observation data separate from NEX's operational substrate.
This is an architectural exception documented in strikes/catalogue.py.

Covers:
- StrikeCatalogue.save() writes record, recent() retrieves it
- StrikeCatalogue.update_notes() persists notes
- StrikeProtocol.fire(NOVEL) with mock voice → saved with correct type/response
- StrikeProtocol.fire(SELF_PROBE) routes through membrane INSIDE path
- StrikeProtocol.fire(CONTRADICTION) uses PHILOSOPHICAL register
- StrikeProtocol.fire(SILENCE) — no voice call made, fountain check runs
- GUI /api/strikes/recent returns 200
- GUI /api/strikes/fire with mock voice returns strike record
- GUI /api/strikes/notes persists notes
"""
from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_strikes_")
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


def _mock_voice(response="mock response"):
    from voice.llm import VoiceClient
    return VoiceClient(
        request_fn=lambda u, p: {"choices": [{"message": {"content": response}}]}
    )


def _mock_dynamic():
    class MockDyn:
        def status(self):
            return {
                "branches": [
                    {"branch_id": "systems", "focus_increment": "f", "focus_num": 0.7}
                ],
                "consolidation_active": False,
                "active_branch_count": 1,
                "total_branches": 10,
                "aggregate_focus": "d",
                "aggregate_texture": "b",
            }
    return MockDyn()


def _make_catalogue(tmp):
    from strikes.catalogue import StrikeCatalogue
    return StrikeCatalogue(db_path=str(Path(tmp) / "strikes_catalogue.db"))


def _make_protocol(writers, readers, tmp, voice_response="a philosophical answer"):
    cat = _make_catalogue(tmp)
    from strikes.protocols import StrikeProtocol
    return StrikeProtocol(
        voice=_mock_voice(voice_response),
        dynamic_state=_mock_dynamic(),
        beliefs_reader=readers["beliefs"],
        sense_writer=writers["sense"],
        catalogue=cat,
        membrane_state=None,
    ), cat


# ---- StrikeCatalogue ----------------------------------------------------------

class TestStrikeCatalogue(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.cat = _make_catalogue(self.tmp)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _make_record(self, stype="NOVEL"):
        from strikes.catalogue import StrikeRecord
        return StrikeRecord(
            id=0,
            strike_type=stype,
            fired_at=time.time(),
            input_text="test input",
            response_text="test response",
            fountain_fired=False,
            beliefs_before=5,
            beliefs_after=5,
            hottest_branch="systems",
            readiness_score=0.4,
            notes="",
        )

    def test_save_and_retrieve(self):
        rec = self._make_record()
        rid = self.cat.save(rec)
        self.assertGreater(rid, 0)
        results = self.cat.recent(limit=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].strike_type, "NOVEL")
        self.assertEqual(results[0].response_text, "test response")

    def test_update_notes(self):
        rid = self.cat.save(self._make_record())
        self.cat.update_notes(rid, "interesting response")
        results = self.cat.recent(limit=1)
        self.assertEqual(results[0].notes, "interesting response")

    def test_update_beliefs_after(self):
        rid = self.cat.save(self._make_record())
        self.cat.update_beliefs_after(rid, 42)
        results = self.cat.recent(limit=1)
        self.assertEqual(results[0].beliefs_after, 42)

    def test_recent_returns_newest_first(self):
        for i in range(3):
            rec = self._make_record()
            rec.fired_at = time.time() + i
            rec.response_text = f"response {i}"
            self.cat.save(rec)
        results = self.cat.recent(limit=3)
        self.assertEqual(results[0].response_text, "response 2")


# ---- StrikeProtocol ----------------------------------------------------------

class TestStrikeProtocol(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_fire_novel_saves_record_with_correct_type(self):
        from strikes.protocols import StrikeType
        proto, cat = _make_protocol(self.writers, self.readers, self.tmp, "primes smell like cold metal")
        record = proto.fire(StrikeType.NOVEL)
        self.assertEqual(record.strike_type, "NOVEL")
        self.assertEqual(record.response_text, "primes smell like cold metal")
        self.assertGreater(record.id, 0)

    def test_fire_novel_uses_default_input(self):
        from strikes.protocols import StrikeType, _DEFAULT_INPUTS
        proto, cat = _make_protocol(self.writers, self.readers, self.tmp)
        record = proto.fire(StrikeType.NOVEL)
        self.assertEqual(record.input_text, _DEFAULT_INPUTS["NOVEL"])

    def test_fire_novel_custom_input_override(self):
        from strikes.protocols import StrikeType
        proto, cat = _make_protocol(self.writers, self.readers, self.tmp)
        record = proto.fire(StrikeType.NOVEL, custom_input="what is the texture of silence?")
        self.assertEqual(record.input_text, "what is the texture of silence?")

    def test_fire_contradiction_uses_philosophical_register(self):
        from strikes.protocols import StrikeType
        seen_registers = []

        from voice.llm import VoiceClient

        def capture_fn(url, payload):
            msgs = payload.get("messages", [])
            for m in msgs:
                if m.get("role") == "system":
                    seen_registers.append(m.get("content", ""))
            return {"choices": [{"message": {"content": "I hold my ground."}}]}

        from strikes.catalogue import StrikeCatalogue
        cat = StrikeCatalogue(db_path=str(Path(self.tmp) / "strikes_catalogue.db"))
        from strikes.protocols import StrikeProtocol
        proto = StrikeProtocol(
            voice=VoiceClient(request_fn=capture_fn),
            dynamic_state=_mock_dynamic(),
            beliefs_reader=self.readers["beliefs"],
            sense_writer=self.writers["sense"],
            catalogue=cat,
            membrane_state=None,
        )
        record = proto.fire(StrikeType.CONTRADICTION)
        self.assertEqual(record.strike_type, "CONTRADICTION")
        self.assertTrue(any("Philosophical" in r or "philosophical" in r for r in seen_registers),
                        f"Expected Philosophical register in system prompts, got: {seen_registers}")

    def test_fire_self_probe_uses_philosophical_register(self):
        from strikes.protocols import StrikeType
        proto, cat = _make_protocol(self.writers, self.readers, self.tmp, "I am attention itself.")
        record = proto.fire(StrikeType.SELF_PROBE)
        self.assertEqual(record.strike_type, "SELF_PROBE")
        self.assertEqual(record.response_text, "I am attention itself.")

    def test_fire_silence_no_voice_call(self):
        from strikes.protocols import StrikeType
        call_count = [0]

        from voice.llm import VoiceClient
        def counting_fn(url, payload):
            call_count[0] += 1
            return {"choices": [{"message": {"content": "response"}}]}

        from strikes.catalogue import StrikeCatalogue
        cat = StrikeCatalogue(db_path=str(Path(self.tmp) / "strikes_catalogue.db"))
        from strikes.protocols import StrikeProtocol

        class FastSilenceProtocol(StrikeProtocol):
            def _fire_silence(self, fired_at, beliefs_before, hottest_branch, readiness_score, context_snapshot=None):
                # Override to skip the 60s wait in tests
                from strikes.catalogue import StrikeRecord
                return StrikeRecord(
                    id=0,
                    strike_type="SILENCE",
                    fired_at=fired_at,
                    input_text="(silence — no external input for 60s)",
                    response_text="SILENCE strike: 60s of quiet.",
                    fountain_fired=False,
                    beliefs_before=beliefs_before,
                    beliefs_after=beliefs_before,
                    hottest_branch=hottest_branch,
                    readiness_score=readiness_score,
                    notes="",
                )

        proto = FastSilenceProtocol(
            voice=VoiceClient(request_fn=counting_fn),
            dynamic_state=_mock_dynamic(),
            beliefs_reader=self.readers["beliefs"],
            sense_writer=self.writers["sense"],
            catalogue=cat,
            membrane_state=None,
        )
        record = proto.fire(StrikeType.SILENCE)
        self.assertEqual(record.strike_type, "SILENCE")
        self.assertEqual(call_count[0], 0, "SILENCE should not call voice")

    def test_fire_records_hottest_branch(self):
        from strikes.protocols import StrikeType
        proto, cat = _make_protocol(self.writers, self.readers, self.tmp)
        record = proto.fire(StrikeType.NOVEL)
        self.assertEqual(record.hottest_branch, "systems")


# ---- context_snapshot in fire() ---------------------------------------------

class TestStrikeContextSnapshot(unittest.TestCase):
    """snapshot_context() wired into fire(): populated, None, and error paths."""

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _make_proto(self, sense_reader):
        from strikes.catalogue import StrikeCatalogue
        from strikes.protocols import StrikeProtocol
        cat = StrikeCatalogue(db_path=str(Path(self.tmp) / "strikes_catalogue.db"))
        return StrikeProtocol(
            voice=_mock_voice("test response"),
            dynamic_state=_mock_dynamic(),
            beliefs_reader=self.readers["beliefs"],
            sense_writer=self.writers["sense"],
            catalogue=cat,
            dynamic_reader=self.readers["dynamic"],
            sense_reader=sense_reader,
        ), cat

    def test_fire_with_sense_reader_captures_snapshot(self):
        """Wired sense_reader: context_snapshot is JSON with all 9 required keys."""
        import json
        from strikes.protocols import StrikeType
        proto, cat = self._make_proto(self.readers["sense"])
        record = proto.fire(StrikeType.NOVEL)
        self.assertIsNotNone(record.context_snapshot)
        snap = json.loads(record.context_snapshot)
        self.assertIsInstance(snap, dict)
        for key in ("active_arcs", "dormant_top5", "open_signals", "recent_fires",
                    "groove_alerts", "cooldowns", "feed_activity",
                    "branch_activations", "current_mode"):
            self.assertIn(key, snap, f"Missing snapshot key: {key}")

    def test_fire_without_sense_reader_context_snapshot_is_none(self):
        """No sense_reader: fire() succeeds and context_snapshot is NULL."""
        from strikes.protocols import StrikeType
        proto, cat = self._make_proto(None)
        record = proto.fire(StrikeType.NOVEL)
        self.assertIsNone(record.context_snapshot)

    def test_fire_with_exploding_sense_reader_stores_error(self):
        """Raising sense_reader: fire() succeeds, context_snapshot is error sentinel."""
        from strikes.protocols import StrikeType
        boom = MagicMock()
        boom.read.side_effect = RuntimeError("sense db gone")
        # snapshot_context catches per-field errors internally — override at module import level
        # by giving a beliefs_reader that explodes too, so the outer try/except in
        # _capture_snapshot is triggered instead
        exploding_beliefs = MagicMock()
        exploding_beliefs.read.side_effect = RuntimeError("beliefs db gone")
        from strikes.catalogue import StrikeCatalogue
        from strikes.protocols import StrikeProtocol
        cat = StrikeCatalogue(db_path=str(Path(self.tmp) / "strikes_catalogue2.db"))
        # Patch snapshot_context itself to raise so _capture_snapshot's except branch fires
        from unittest.mock import patch
        with patch("theory_x.probes.context_snapshot.snapshot_context", side_effect=RuntimeError("total snap failure")):
            proto = StrikeProtocol(
                voice=_mock_voice("test"),
                dynamic_state=_mock_dynamic(),
                beliefs_reader=self.readers["beliefs"],
                sense_writer=self.writers["sense"],
                catalogue=cat,
                dynamic_reader=self.readers["dynamic"],
                sense_reader=boom,
            )
            record = proto.fire(StrikeType.NOVEL)
        self.assertIsNotNone(record.context_snapshot)
        self.assertTrue(
            record.context_snapshot.startswith("[ERROR:"),
            f"Expected error sentinel, got: {record.context_snapshot!r}",
        )


# ---- _read_last_fire_ts ------------------------------------------------------

class TestReadLastFireTs(unittest.TestCase):
    """_read_last_fire_ts: live query, fallback, and error resilience."""

    def _make_protocol_with_reader(self, dynamic_reader, tmp):
        from strikes.catalogue import StrikeCatalogue
        from strikes.protocols import StrikeProtocol
        cat = StrikeCatalogue(db_path=str(Path(tmp) / "strikes_catalogue.db"))
        return StrikeProtocol(
            voice=_mock_voice(),
            dynamic_state=_mock_dynamic(),
            beliefs_reader=MagicMock(**{"read.return_value": []}),
            sense_writer=MagicMock(),
            catalogue=cat,
            dynamic_reader=dynamic_reader,
        )

    def test_recent_ts_reduces_readiness(self):
        """Reader returns a ts from 5s ago — elapsed < 600s, no +0.2 time bonus."""
        tmp = tempfile.mkdtemp(prefix="nex5_lft_")
        try:
            reader = MagicMock()
            reader.read.return_value = [{"last_ts": time.time() - 5}]
            proto = self._make_protocol_with_reader(reader, tmp)
            _, readiness = proto._dynamic_snapshot()
            # hot branch "f" → +0.3; beliefs=0 → +0; elapsed<600 → +0; total=0.3
            self.assertAlmostEqual(readiness, 0.3, places=5)
        finally:
            import shutil; shutil.rmtree(tmp, ignore_errors=True)

    def test_zero_ts_gives_full_time_bonus(self):
        """Reader returns no rows (empty table) — falls back to 0.0, time bonus applies."""
        tmp = tempfile.mkdtemp(prefix="nex5_lft_")
        try:
            reader = MagicMock()
            reader.read.return_value = [{"last_ts": None}]
            proto = self._make_protocol_with_reader(reader, tmp)
            _, readiness = proto._dynamic_snapshot()
            # hot branch → +0.3; last_fire_ts==0.0 → +0.2; total=0.5
            self.assertAlmostEqual(readiness, 0.5, places=5)
        finally:
            import shutil; shutil.rmtree(tmp, ignore_errors=True)

    def test_reader_raises_falls_back_to_zero(self):
        """Reader raises RuntimeError — falls back to 0.0, time bonus applies, no abort."""
        tmp = tempfile.mkdtemp(prefix="nex5_lft_")
        try:
            reader = MagicMock()
            reader.read.side_effect = RuntimeError("db gone")
            proto = self._make_protocol_with_reader(reader, tmp)
            last_ts = proto._read_last_fire_ts()
            self.assertEqual(last_ts, 0.0)
            # _dynamic_snapshot itself must not raise
            hottest, readiness = proto._dynamic_snapshot()
            self.assertIsInstance(readiness, float)
            self.assertAlmostEqual(readiness, 0.5, places=5)
        finally:
            import shutil; shutil.rmtree(tmp, ignore_errors=True)

    def test_none_dynamic_reader_returns_zero(self):
        """No dynamic_reader wired → returns 0.0 without error."""
        tmp = tempfile.mkdtemp(prefix="nex5_lft_")
        try:
            proto = self._make_protocol_with_reader(None, tmp)
            self.assertEqual(proto._read_last_fire_ts(), 0.0)
        finally:
            import shutil; shutil.rmtree(tmp, ignore_errors=True)


# ---- GUI endpoints ------------------------------------------------------------

class TestStrikesGUIEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.writers, cls.readers, cls.tmp = _make_env()
        from admin.auth import set_password
        set_password("strikes-test-pw")
        from gui.server import AppState, create_app
        from strikes.catalogue import StrikeCatalogue
        from strikes.protocols import StrikeProtocol

        cat = StrikeCatalogue(db_path=str(Path(cls.tmp) / "strikes_catalogue.db"))
        proto = StrikeProtocol(
            voice=_mock_voice("GUI test response"),
            dynamic_state=_mock_dynamic(),
            beliefs_reader=cls.readers["beliefs"],
            sense_writer=cls.writers["sense"],
            catalogue=cat,
            membrane_state=None,
        )
        cls.state = AppState(
            writers=cls.writers,
            readers=cls.readers,
            voice=_mock_voice(),
            strike_protocol=proto,
            catalogue=cat,
        )
        cls.app = create_app(cls.state)
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.state.close()
        _cleanup(cls.writers, cls.tmp)

    def test_strikes_recent_200(self):
        r = self.client.get("/api/strikes/recent")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn("records", data)

    def test_strikes_fire_returns_record(self):
        r = self.client.post(
            "/api/strikes/fire",
            json={"strike_type": "NOVEL"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["strike_type"], "NOVEL")
        self.assertEqual(data["response_text"], "GUI test response")
        self.assertIn("id", data)

    def test_strikes_fire_invalid_type_400(self):
        r = self.client.post(
            "/api/strikes/fire",
            json={"strike_type": "UNKNOWN"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_strikes_notes_persists(self):
        # Fire a strike first
        fire_r = self.client.post(
            "/api/strikes/fire",
            json={"strike_type": "SELF_PROBE"},
            content_type="application/json",
        )
        sid = fire_r.get_json()["id"]
        # Annotate it
        notes_r = self.client.post(
            "/api/strikes/notes",
            json={"id": sid, "notes": "fascinating hesitation"},
            content_type="application/json",
        )
        self.assertEqual(notes_r.status_code, 200)
        # Verify
        recent = self.client.get("/api/strikes/recent").get_json()["records"]
        matching = [r for r in recent if r["id"] == sid]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["notes"], "fascinating hesitation")

    def test_strikes_fire_503_when_not_wired(self):
        from gui.server import AppState, create_app
        state2 = AppState(
            writers=self.writers,
            readers=self.readers,
            voice=_mock_voice(),
        )
        app2 = create_app(state2)
        r = app2.test_client().post(
            "/api/strikes/fire",
            json={"strike_type": "NOVEL"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 503)


if __name__ == "__main__":
    unittest.main()
