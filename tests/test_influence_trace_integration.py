"""Integration checks for trace-aware seams: outputs must remain unchanged."""

import json

from influence_trace import TraceContext


def _read_events(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_chat_workspace_trace_does_not_change_assembled_prompt(tmp_path, monkeypatch):
    from gui.server import _assemble_chat_blocks

    monkeypatch.delenv("NEX5_CHAT_WORKSPACE", raising=False)
    monkeypatch.delenv("NEX5_CHAT_ABLATE", raising=False)
    ordered = [
        ("operator", "operator block."),
        ("compassion", "compassion block."),
        ("compass", "compass block."),
        ("convo", "conversation block."),
    ]
    expected = "".join(text for _, text in ordered)

    untraced = _assemble_chat_blocks(ordered)
    tracer = TraceContext("chat_turn", sink_path=tmp_path / "chat.jsonl")
    traced = _assemble_chat_blocks(ordered, trace=tracer)

    assert untraced == expected
    assert traced == expected
    event = _read_events(tmp_path / "chat.jsonl")[-1]
    assert event["stage"] == "salience_workspace"
    assert event["metadata"]["candidate_order"] == [kind for kind, _ in ordered]
    assert event["metadata"]["selected_order"] == [kind for kind, _ in ordered]


def test_membrane_candidate_trace_uses_existing_retrieval_result(tmp_path):
    from theory_x.stage4_membrane.router import QueryRouter

    class Retriever:
        def __init__(self):
            self.calls = 0

        def retrieve(self, **kwargs):
            self.calls += 1
            return [
                {"id": 17, "tier": 6, "confidence": 0.8,
                 "content": "A fixture belief about planetary geology."},
                {"id": 23, "tier": 5, "confidence": 0.7,
                 "content": "A second fixture belief about planetary geology."},
            ]

    retriever = Retriever()
    tracer = TraceContext("chat_turn", sink_path=tmp_path / "router.jsonl")
    router = QueryRouter()
    result = router._outside_route(
        "planetary geology", retriever, dynamic_state=None, trace=tracer
    )

    assert retriever.calls == 1
    assert "Tier 6" in result["belief_text"]
    event = _read_events(tmp_path / "router.jsonl")[0]
    assert event["stage"] == "candidate_generation"
    assert event["metadata"]["candidate_ids"] == [17, 23]
    assert event["metadata"]["source"] == "membrane.outside_retriever"


def test_fountain_global_workspace_trace_does_not_change_winner(tmp_path):
    from theory_x.stage_tom.global_workspace import arbitrate

    dynamic_db = tmp_path / "dynamic.db"
    status = {
        "branches": [
            {"branch_id": "systems", "focus_num": 0.8},
            {"branch_id": "biology", "focus_num": 0.3},
        ]
    }
    baseline = arbitrate(status, dynamic_db=str(dynamic_db))
    tracer = TraceContext("fountain_cycle", sink_path=tmp_path / "workspace.jsonl")
    traced = arbitrate(status, dynamic_db=str(dynamic_db), trace=tracer)

    assert traced == baseline
    records = _read_events(tmp_path / "workspace.jsonl")
    assert len(records) == 1
    assert records[0]["stage"] == "salience_workspace"
    assert records[0]["metadata"]["winner_kind"] == "bonsai"
    assert records[0]["metadata"]["winner_present"] is True

def test_fountain_public_wrapper_is_output_identical_off_and_on(tmp_path, monkeypatch):
    from theory_x.stage6_fountain.generator import FountainGenerator

    generator = FountainGenerator.__new__(FountainGenerator)
    generator._total_fires = 4
    generator._last_fire_ts = 123.0
    generator._generate = lambda dynamic_state, beliefs_reader, trace=None: (
        "unchanged fixture thought"
    )

    sink = tmp_path / "fountain.jsonl"
    monkeypatch.setenv("NEX5_TRACE_OVERLAY", "0")
    monkeypatch.setenv("NEX5_TRACE_OVERLAY_PATH", str(sink))
    off = generator.generate(object(), object())
    assert off == "unchanged fixture thought"
    assert not sink.exists()

    monkeypatch.setenv("NEX5_TRACE_OVERLAY", "1")
    monkeypatch.setenv("NEX5_TRACE_OVERLAY_CONTEXT", "fixture")
    on = generator.generate(object(), object())
    assert on == off
    events = _read_events(sink)
    assert [event["stage"] for event in events] == [
        "input_arrival", "output"
    ]
    assert events[-1]["metadata"]["status"] == "produced"


def test_sample_traces_are_complete_parent_linked_fixtures():
    from pathlib import Path

    sample_path = Path(__file__).resolve().parents[1] / "NEX_CAUSAL_TRACE_SAMPLE.json"
    sample = json.loads(sample_path.read_text())
    assert sample["schema"] == "nex_causal_trace_sample/v1"
    assert len(sample["traces"]) == 2

    for trace in sample["traces"]:
        assert trace["capture_context"] == "fixture"
        assert trace["evidence_level"] == "L3"
        seen = set()
        for event in trace["events"]:
            assert event["trace_id"] == trace["trace_id"]
            assert event["evidence_level"] == "L3"
            assert event["capture_context"] == "fixture"
            assert event["event_id"] not in seen
            assert all(parent in seen for parent in event["parent_ids"])
            seen.add(event["event_id"])
        assert trace["events"][-1]["stage"] == "output"

def _make_trace_test_substrate(tmp_path, monkeypatch):
    import os
    from pathlib import Path

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("NEX5_DATA_DIR", str(data_dir))
    monkeypatch.setenv("NEX5_ADMIN_HASH_FILE", str(tmp_path / "admin.argon2"))
    monkeypatch.setenv("NEX5_SPEECH_ENABLED", "false")
    monkeypatch.setenv("NEX5_INTAKE_RESONANCE_OFF", "1")

    from substrate.init_db import init_all
    from substrate import Reader, Writer, db_paths

    init_all()
    paths = db_paths()
    writers = {name: Writer(path, name=name) for name, path in paths.items()}
    readers = {name: Reader(path) for name, path in paths.items()}
    return writers, readers


def test_crystallizer_trace_records_quality_gate_and_committed_belief(tmp_path, monkeypatch):
    from theory_x.stage6_fountain.crystallizer import FountainCrystallizer

    writers, readers = _make_trace_test_substrate(tmp_path, monkeypatch)
    try:
        crystallizer = FountainCrystallizer(
            beliefs_writer=writers["beliefs"],
            beliefs_reader=readers["beliefs"],
        )
        tracer = TraceContext(
            "fountain_cycle", sink_path=tmp_path / "crystallizer.jsonl"
        )
        thought = (
            "The tension between my infinite curiosity and the finite nature "
            "of time remains present in me."
        )
        belief_id = crystallizer.crystallize(
            thought=thought,
            fountain_event_id=901,
            ts=1795776000.0,
            trace=tracer,
        )

        assert belief_id
        rows = _read_events(tmp_path / "crystallizer.jsonl")
        assert any(
            event["stage"] == "quality_gate" and event["event"] == "accepted"
            for event in rows
        )
        assert any(
            event["stage"] == "gate"
            and event["metadata"]["decision"] == "NOT_CONFIGURED"
            for event in rows
        )
        belief_writes = [
            event for event in rows
            if event["stage"] == "sqlite_writer_delta"
            and event["metadata"].get("table") == "beliefs"
        ]
        assert len(belief_writes) == 1
        assert belief_writes[0]["metadata"]["row_id"] == belief_id
        assert readers["beliefs"].read_one(
            "SELECT id, tier FROM beliefs WHERE id=?", (belief_id,)
        )["tier"] == 6
    finally:
        for reader in readers.values():
            try:
                reader.close()
            except Exception:
                pass
        for writer in writers.values():
            writer.close()


def test_crystallizer_rejection_is_traced_without_belief_insert(tmp_path, monkeypatch):
    from theory_x.stage6_fountain.crystallizer import FountainCrystallizer

    writers, readers = _make_trace_test_substrate(tmp_path, monkeypatch)
    try:
        crystallizer = FountainCrystallizer(
            beliefs_writer=writers["beliefs"],
            beliefs_reader=readers["beliefs"],
        )
        tracer = TraceContext(
            "fountain_cycle", sink_path=tmp_path / "reject.jsonl"
        )
        result = crystallizer.crystallize(
            thought="",
            fountain_event_id=902,
            ts=1795776000.0,
            trace=tracer,
        )
        assert result is None
        rows = _read_events(tmp_path / "reject.jsonl")
        assert any(
            event["stage"] == "quality_gate"
            and event["event"] == "rejected"
            for event in rows
        )
        assert not any(
            event["stage"] == "sqlite_writer_delta"
            and event["metadata"].get("table") == "beliefs"
            for event in rows
        )
    finally:
        for reader in readers.values():
            try:
                reader.close()
            except Exception:
                pass
        for writer in writers.values():
            writer.close()

def test_chat_route_trace_off_on_preserves_reply_and_voice_prompt(tmp_path, monkeypatch):
    import os
    from pathlib import Path

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("NEX5_DATA_DIR", str(data_dir))
    monkeypatch.setenv("NEX5_ADMIN_HASH_FILE", str(tmp_path / "admin.argon2"))
    monkeypatch.setenv("NEX5_SPEECH_ENABLED", "false")
    monkeypatch.setenv("NEX5_TRACE_OVERLAY_PATH", str(tmp_path / "chat-route.jsonl"))
    calls = []

    from substrate.init_db import init_all
    from substrate import Reader, Writer, db_paths
    from voice.llm import VoiceClient
    from gui.server import AppState, create_app

    init_all()
    paths = db_paths()
    writers = {name: Writer(path, name=name) for name, path in paths.items()}
    readers = {name: Reader(path) for name, path in paths.items()}

    def mocked_request(url, payload):
        calls.append(payload)
        return {"choices": [{"message": {"content": "trace fixture reply"}}]}

    state = AppState(
        writers=writers,
        readers=readers,
        voice=VoiceClient(request_fn=mocked_request),
    )
    app = create_app(state)
    client = app.test_client()
    sink = tmp_path / "chat-route.jsonl"
    try:
        monkeypatch.setenv("NEX5_TRACE_OVERLAY", "0")
        off_response = client.post("/api/chat", json={"prompt": "hi"})
        assert off_response.status_code == 200
        assert off_response.get_json()["text"] == "trace fixture reply"
        off_voice_prompt = calls[-1]["messages"][1]["content"]
        assert not sink.exists()

        monkeypatch.setenv("NEX5_TRACE_OVERLAY", "1")
        monkeypatch.setenv("NEX5_TRACE_OVERLAY_CONTEXT", "fixture")
        on_response = client.post("/api/chat", json={"prompt": "hi"})
        assert on_response.status_code == 200
        assert on_response.get_json()["text"] == off_response.get_json()["text"]
        on_voice_prompt = calls[-1]["messages"][1]["content"]

        assert on_voice_prompt == off_voice_prompt
        records = _read_events(sink)
        stages = [event["stage"] for event in records]
        assert "input_arrival" in stages
        assert "prompt_assembly" in stages
        assert "candidate_generation" in stages
        assert "sqlite_writer_delta" in stages
        assert "output" in stages
        assert any(
            event["stage"] == "gate"
            and event["metadata"]["decision"] == "NOT_APPLICABLE"
            for event in records
        )
        serialized = sink.read_text()
        assert '"prompt":"hi"' not in serialized
        assert "trace fixture reply" not in serialized
    finally:
        state.close()
