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

    # Exercise the budgeted selector as well: tracing must not change the
    # selected faculty set or the assembled prompt under competition.
    monkeypatch.setenv("NEX5_CHAT_WORKSPACE", "1")
    monkeypatch.setenv("NEX5_CHAT_WORKSPACE_BUDGET", "40")
    baseline_selected = _assemble_chat_blocks(ordered)
    traced_selected = _assemble_chat_blocks(
        ordered, trace=TraceContext(
            "chat_turn", sink_path=tmp_path / "chat-workspace.jsonl"
        )
    )
    assert traced_selected == baseline_selected
    workspace_event = _read_events(tmp_path / "chat-workspace.jsonl")[-1]
    assert workspace_event["metadata"]["workspace_enabled"] is True
    assert workspace_event["metadata"]["selected_order"] == ["compassion", "compass"]


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

    fountain = next(t for t in sample["traces"] if t["producer"] == "fountain_cycle")
    f = {event["event_id"]: event for event in fountain["events"]}
    assert f["f-005"]["parent_ids"] == ["f-001"]
    assert set(f["f-006"]["parent_ids"]) == {"f-003", "f-005"}
    assert set(f["f-011"]["parent_ids"]) == {"f-009", "f-010"}
    assert set(f["f-016"]["parent_ids"]) == {"f-014", "f-015"}
    assert set(f["f-018"]["parent_ids"]) == {"f-009", "f-011"}

    chat = next(t for t in sample["traces"] if t["producer"] == "chat_turn")
    c = {event["event_id"]: event for event in chat["events"]}
    assert c["c-004"]["parent_ids"] == ["c-001"]
    assert set(c["c-007"]["parent_ids"]) == {"c-001", "c-004", "c-006"}
    assert c["c-008"]["parent_ids"] == ["c-007"]
    assert c["c-009"]["parent_ids"] == ["c-001", "c-004", "c-006", "c-008"]
    assert c["c-014"]["metadata"]["length"] == c["c-010"]["metadata"]["reply"]["length"]


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

def test_voice_engine_trace_preserves_selected_reply_and_records_trigger(tmp_path, monkeypatch):
    from theory_x.stage_throw_net.voice_engine import VoiceEngine

    writers, readers = _make_trace_test_substrate(tmp_path, monkeypatch)
    try:
        engine = VoiceEngine(
            beliefs_reader=readers["beliefs"],
            problem_memory=None,
            beliefs_writer=writers["beliefs"],
            min_score=0.5,
        )
        candidates = [{
            "origin_id": 77,
            "source": "fountain_insight",
            "content": "A private stored answer that must not appear in the trace.",
        }]
        engine._retrieve_candidates = lambda query: candidates
        engine._embed = lambda query: None
        engine._score_candidate = lambda candidate, query_emb: 0.91

        baseline = engine.query_reply(
            "a private question", session_id="fixture-session", turn_n=1
        )
        tracer = TraceContext(
            "chat_turn", sink_path=tmp_path / "voice-engine.jsonl"
        )
        observed = engine.query_reply(
            "a private question", session_id="fixture-session", turn_n=1,
            trace=tracer,
        )

        assert observed == baseline
        assert observed["belief_id"] == 77
        records = _read_events(tmp_path / "voice-engine.jsonl")
        candidate_event = next(
            event for event in records
            if event["stage"] == "candidate_generation"
        )
        assert candidate_event["metadata"]["candidate_ids"] == [77]
        selection_event = next(
            event for event in records
            if event["stage"] == "salience_workspace"
        )
        assert selection_event["metadata"]["selected_order"] == [77]
        trigger_event = next(
            event for event in records
            if event["stage"] == "sqlite_writer_delta"
        )
        assert trigger_event["metadata"]["table"] == "throw_net_triggers"
        assert trigger_event["metadata"]["status"] == "committed"
        trigger_row = readers["beliefs"].read_one(
            "SELECT id, fired FROM throw_net_triggers WHERE id=?",
            (trigger_event["metadata"]["row_id"],),
        )
        assert trigger_row is not None
        assert trigger_row["fired"] == 1
        serialized = (tmp_path / "voice-engine.jsonl").read_text()
        assert "a private question" not in serialized
        assert "A private stored answer" not in serialized
    finally:
        for reader in readers.values():
            try:
                reader.close()
            except Exception:
                pass
        for writer in writers.values():
            writer.close()

def test_chat_route_voice_engine_shortcut_is_traced_without_llm_call(tmp_path, monkeypatch):
    from pathlib import Path

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("NEX5_DATA_DIR", str(data_dir))
    monkeypatch.setenv("NEX5_ADMIN_HASH_FILE", str(tmp_path / "admin.argon2"))
    monkeypatch.setenv("NEX5_SPEECH_ENABLED", "false")
    monkeypatch.setenv("NEX5_TRACE_OVERLAY", "1")
    monkeypatch.setenv("NEX5_TRACE_OVERLAY_CONTEXT", "fixture")
    sink = tmp_path / "chat-voice-engine.jsonl"
    monkeypatch.setenv("NEX5_TRACE_OVERLAY_PATH", str(sink))
    llm_calls = []

    from substrate.init_db import init_all
    from substrate import Reader, Writer, db_paths
    from voice.llm import VoiceClient
    from theory_x.stage_throw_net.voice_engine import VoiceEngine
    from gui.server import AppState, create_app

    init_all()
    paths = db_paths()
    writers = {name: Writer(path, name=name) for name, path in paths.items()}
    readers = {name: Reader(path) for name, path in paths.items()}

    engine = VoiceEngine(
        beliefs_reader=readers["beliefs"],
        problem_memory=None,
        beliefs_writer=writers["beliefs"],
        min_score=0.5,
    )
    candidates = [{
        "origin_id": 88,
        "source": "fountain_insight",
        "content": "stored private answer from the substrate",
    }]
    engine._retrieve_candidates = lambda query: candidates
    engine._embed = lambda query: None
    engine._score_candidate = lambda candidate, query_emb: 0.95

    def forbidden_llm_call(url, payload):
        llm_calls.append(payload)
        return {"choices": [{"message": {"content": "LLM must not run"}}]}

    state = AppState(
        writers=writers,
        readers=readers,
        voice=VoiceClient(request_fn=forbidden_llm_call),
        voice_engine=engine,
    )
    client = create_app(state).test_client()
    try:
        response = client.post("/api/chat", json={"prompt": "hi"})
        assert response.status_code == 200
        assert response.get_json()["text"] == "stored private answer from the substrate"
        assert llm_calls == []

        records = _read_events(sink)
        assert any(
            event["stage"] == "candidate_generation"
            and event["event"] == "candidates_selected"
            and event["metadata"]["source"] == "voice_engine._retrieve_candidates"
            and event["metadata"]["candidate_ids"] == [88]
            for event in records
        )
        assert any(
            event["stage"] == "salience_workspace"
            and event["metadata"]["source"] == "voice_engine.query_reply"
            and event["metadata"]["selected_order"] == [88]
            for event in records
        )
        assert any(
            event["stage"] == "candidate_generation"
            and event["event"] == "voice_engine_stored_candidate"
            and event["metadata"]["returned_verbatim"] is True
            for event in records
        )
        assert any(
            event["stage"] == "sqlite_writer_delta"
            and event["metadata"]["table"] == "throw_net_triggers"
            and event["metadata"]["fired"] is True
            for event in records
        )
        serialized = sink.read_text()
        assert "stored private answer from the substrate" not in serialized
    finally:
        state.close()

def test_crystallizer_trace_does_not_change_belief_confidence(tmp_path, monkeypatch):
    from theory_x.stage6_fountain.crystallizer import FountainCrystallizer

    writers, readers = _make_trace_test_substrate(tmp_path, monkeypatch)
    monkeypatch.setenv("NEX5_SURPRISE_WEIGHT", "0")
    try:
        crystallizer = FountainCrystallizer(
            beliefs_writer=writers["beliefs"],
            beliefs_reader=readers["beliefs"],
        )
        baseline_id = crystallizer.crystallize(
            thought="The tension between my infinite curiosity and the finite nature of time.",
            fountain_event_id=910,
            ts=1795776200.0,
        )
        tracer = TraceContext(
            "fountain_cycle", sink_path=tmp_path / "confidence.jsonl"
        )
        traced_id = crystallizer.crystallize(
            thought="I notice how Saturn's rings trace a quiet regularity around the planet.",
            fountain_event_id=911,
            ts=1795776201.0,
            trace=tracer,
        )

        assert baseline_id and traced_id
        baseline = readers["beliefs"].read_one(
            "SELECT confidence FROM beliefs WHERE id=?", (baseline_id,)
        )
        traced = readers["beliefs"].read_one(
            "SELECT confidence FROM beliefs WHERE id=?", (traced_id,)
        )
        assert baseline["confidence"] == traced["confidence"] == 0.7
        events = _read_events(tmp_path / "confidence.jsonl")
        assert any(
            event["stage"] == "sqlite_writer_delta"
            and event["metadata"].get("table") == "beliefs"
            and event["metadata"].get("row_id") == traced_id
            for event in events
        )
    finally:
        for reader in readers.values():
            try:
                reader.close()
            except Exception:
                pass
        for writer in writers.values():
            writer.close()

def test_fountain_prompt_builder_trace_is_byte_identical(tmp_path, monkeypatch):
    import datetime
    import random

    from theory_x.stage6_fountain.generator import FountainGenerator
    from voice.llm import VoiceClient
    import nex_config

    writers, readers = _make_trace_test_substrate(tmp_path, monkeypatch)
    try:
        fixed_now = datetime.datetime(2026, 11, 27, 12, 34)
        monkeypatch.setattr(nex_config, "local_now", lambda: fixed_now)
        for name in (
            "NEX5_GLOBAL_WORKSPACE", "NEX5_TOPIC_GATE_SHADOW",
            "NEX5_PHRASING_ROTATE", "NEX5_FRAME_DEDUP",
            "NEX5_SENSE_OVERWHELM_N", "NEX5_SELF_LAYER_N",
            "NEX5_CONTINUITY_N", "NEX5_SOCIAL_N",
        ):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv("NEX5_GLOBAL_WORKSPACE", "0")

        generator = FountainGenerator(
            sense_writer=writers["sense"],
            dynamic_writer=writers["dynamic"],
            voice_client=VoiceClient(
                request_fn=lambda url, payload: {
                    "choices": [{"message": {"content": "unused fixture"}}]
                }
            ),
            dynamic_reader=readers["dynamic"],
        )
        dynamic_status = {
            "branches": [
                {"branch_id": "systems", "focus_num": 0.7,
                 "focus_increment": "f"},
            ],
            "consolidation_active": False,
            "active_branch_count": 1,
            "total_branches": 1,
            "aggregate_focus": "d",
            "aggregate_texture": "b",
        }

        random.seed(314159)
        baseline_prompt, baseline_manifest = generator._build_prompt(
            dynamic_status, 0, {}
        )
        tracer = TraceContext(
            "fountain_cycle", sink_path=tmp_path / "fountain-prompt.jsonl"
        )
        random.seed(314159)
        traced_prompt, traced_manifest = generator._build_prompt(
            dynamic_status, 0, {}, trace=tracer
        )

        assert traced_prompt == baseline_prompt
        assert traced_manifest == baseline_manifest
        events = _read_events(tmp_path / "fountain-prompt.jsonl")
        assert any(event["stage"] == "candidate_generation" for event in events)
        assert any(
            event["stage"] == "prompt_context_selection"
            and event["event"] == "belief_manifest_recorded"
            for event in events
        )
        serialized = (tmp_path / "fountain-prompt.jsonl").read_text()
        assert traced_prompt not in serialized
    finally:
        for reader in readers.values():
            try:
                reader.close()
            except Exception:
                pass
        for writer in writers.values():
            writer.close()


def test_complete_fountain_cycle_traces_generation_gate_and_belief_write(
    tmp_path, monkeypatch
):
    """Exercise the real Fountain producer through its configured crystallizer."""
    import time

    from theory_x.stage6_fountain.generator import FountainGenerator
    from theory_x.stage6_fountain.crystallizer import FountainCrystallizer
    from voice.llm import VoiceClient

    writers, readers = _make_trace_test_substrate(tmp_path, monkeypatch)
    sink = tmp_path / "complete-fountain.jsonl"
    thought = (
        "The tension between my infinite curiosity and the finite nature of time."
    )
    try:
        for name, value in {
            "NEX5_TRACE_OVERLAY": "1",
            "NEX5_TRACE_OVERLAY_CONTEXT": "fixture",
            "NEX5_TRACE_OVERLAY_PATH": str(sink),
            "NEX5_GLOBAL_WORKSPACE": "1",
            "NEX5_MOMENTUM": "0",
            "NEX5_RECONCILE": "0",
            "NEX5_SUBSTRATE_EMIT": "0",
            "NEX5_SPEECH_ENABLED": "false",
            "NEX5_SURPRISE_WEIGHT": "0",
            "NEX5_INTAKE_RESONANCE_OFF": "1",
            "NEX5_FRAME_GATE": "0",
            "NEX5_FIRE_LANG_GUARD": "0",
        }.items():
            monkeypatch.setenv(name, value)

        for index in range(21):
            writers["beliefs"].write(
                "INSERT INTO beliefs "
                "(content, tier, confidence, created_at, source, locked, tags) "
                "VALUES (?, 5, 0.7, ?, 'auto_growth', 0, '[]')",
                (f"fixture belief number {index} about a stable topic", int(time.time())),
            )

        crystallizer = FountainCrystallizer(
            beliefs_writer=writers["beliefs"],
            beliefs_reader=readers["beliefs"],
            dynamic_writer=writers["dynamic"],
        )
        generator = FountainGenerator(
            sense_writer=writers["sense"],
            dynamic_writer=writers["dynamic"],
            voice_client=VoiceClient(request_fn=lambda _url, _payload: {
                "choices": [{"message": {"content": thought}}]
            }),
            dynamic_reader=readers["dynamic"],
            beliefs_writer=writers["beliefs"],
            beliefs_reader=readers["beliefs"],
            crystallizer=crystallizer,
            sense_reader=readers["sense"],
        )

        class ReadyDynamicState:
            def status(self):
                return {
                    "branches": [{
                        "branch_id": "systems",
                        "focus_num": 0.7,
                        "focus_increment": "f",
                    }],
                    "consolidation_active": True,
                    "active_branch_count": 1,
                    "total_branches": 1,
                    "aggregate_focus": "d",
                    "aggregate_texture": "b",
                }

        result = generator.generate(ReadyDynamicState(), readers["beliefs"])
        assert result == thought

        belief = readers["beliefs"].read_one(
            "SELECT id, tier, confidence FROM beliefs "
            "WHERE source='fountain_insight' AND content=? ORDER BY id DESC LIMIT 1",
            (thought,),
        )
        assert belief is not None
        assert belief["tier"] == 6
        assert belief["confidence"] == 0.7

        sense_event = readers["sense"].read_one(
            "SELECT id FROM sense_events WHERE stream='internal.fountain' "
            "ORDER BY id DESC LIMIT 1"
        )
        fountain_event = readers["dynamic"].read_one(
            "SELECT id FROM fountain_events WHERE thought=? ORDER BY id DESC LIMIT 1",
            (thought,),
        )
        crystallization = readers["beliefs"].read_one(
            "SELECT id FROM fountain_crystallizations WHERE belief_id=?",
            (belief["id"],),
        )
        assert sense_event is not None
        assert fountain_event is not None
        assert crystallization is not None

        records = _read_events(sink)
        stages = [event["stage"] for event in records]
        assert stages[0] == "input_arrival"
        assert "readiness" in stages
        assert "candidate_generation" in stages
        assert "salience_workspace" in stages
        assert "sqlite_writer_delta" in stages
        assert "quality_gate" in stages
        assert "gate" in stages
        assert stages[-1] == "output"
        assert all(event["trace_id"] == records[0]["trace_id"] for event in records)
        seen = set()
        for event in records:
            assert all(parent in seen for parent in event["parent_ids"])
            seen.add(event["event_id"])
        belief_delta = next(
            event for event in records
            if event["stage"] == "sqlite_writer_delta"
            and event["metadata"].get("table") == "beliefs"
            and event["metadata"].get("row_id") == belief["id"]
        )
        assert belief_delta["metadata"]["status"] == "committed"
        # The trace contains the output digest, not the raw thought.
        assert thought not in sink.read_text()
    finally:
        for reader in readers.values():
            try:
                reader.close()
            except Exception:
                pass
        for writer in writers.values():
            writer.close()


def _run_paired_fountain_once(
    run_root, *, trace_on, monkeypatch, original_reader_open, original_gw_arbitrate
):
    import copy
    import datetime
    import os
    import random
    import time

    run_root.mkdir(parents=True, exist_ok=True)
    data_dir = run_root / "data"
    data_dir.mkdir()
    sink = run_root / "fountain-trace.jsonl"

    with monkeypatch.context() as mp:
        for key in list(os.environ):
            if key.startswith("NEX5_"):
                mp.delenv(key, raising=False)
        mp.setenv("NEX5_DATA_DIR", str(data_dir))
        mp.setenv("NEX5_ADMIN_HASH_FILE", str(data_dir / "admin.argon2"))
        mp.setenv("NEX5_GLOBAL_WORKSPACE", "1")
        mp.setenv("NEX5_MOMENTUM", "0")
        mp.setenv("NEX5_RECONCILE", "0")
        mp.setenv("NEX5_SUBSTRATE_EMIT", "0")
        mp.setenv("NEX5_SPEECH_ENABLED", "false")
        mp.setenv("NEX5_SURPRISE_WEIGHT", "0")
        mp.setenv("NEX5_INTAKE_RESONANCE_OFF", "1")
        mp.setenv("NEX5_FRAME_GATE", "0")
        mp.setenv("NEX5_FIRE_LANG_GUARD", "0")
        mp.setenv("NEX5_TRACE_OVERLAY", "1" if trace_on else "0")
        mp.setenv("NEX5_TRACE_OVERLAY_CONTEXT", "fixture")
        mp.setenv("NEX5_TRACE_OVERLAY_PATH", str(sink))

        from substrate.init_db import init_all
        from substrate import Reader, Writer, db_paths
        from voice.llm import VoiceClient
        import nex_config
        import theory_x.stage_tom.global_workspace as global_workspace
        from theory_x.stage6_fountain.generator import FountainGenerator
        from theory_x.stage6_fountain.crystallizer import FountainCrystallizer

        # Control SQLite RANDOM() on every reader connection so paired runs
        # retrieve the same records. This modifies only the test fixture.
        def deterministic_reader_open(reader):
            connection = original_reader_open(reader)
            sqlite_rng = random.Random(8675309)
            connection.create_function(
                "random", 0, lambda: sqlite_rng.getrandbits(63)
            )
            return connection

        mp.setattr(Reader, "_open", deterministic_reader_open)
        fixed_local_now = datetime.datetime(2026, 11, 27, 12, 0, 0)
        mp.setattr(nex_config, "local_now", lambda: fixed_local_now)

        workspace_winners = []
        def capture_workspace(*args, **kwargs):
            winner = original_gw_arbitrate(*args, **kwargs)
            workspace_winners.append(winner)
            return winner
        mp.setattr(global_workspace, "arbitrate", capture_workspace)

        init_all()
        paths = db_paths()
        writers = {name: Writer(path, name=name) for name, path in paths.items()}
        readers = {name: Reader(path) for name, path in paths.items()}
        model_requests = []
        retrieval_manifests = []

        def deterministic_model(url, payload):
            model_requests.append(copy.deepcopy(payload))
            return {"choices": [{"message": {
                "content": (
                    "A small observation can change how a familiar pattern "
                    "is understood."
                )
            }}]}

        for index in range(21):
            writers["beliefs"].write(
                "INSERT INTO beliefs "
                "(content, tier, confidence, created_at, source, locked, tags) "
                "VALUES (?, 5, 0.7, ?, 'auto_growth', 0, '[]')",
                (f"fixture belief number {index} about a stable topic", 1795776000),
            )

        class DynamicState:
            def status(self):
                return {
                    "branches": [{
                        "branch_id": "phase0-test",
                        "focus_increment": "f",
                        "focus_num": 0.8,
                    }],
                    "consolidation_active": True,
                }

        crystallizer = FountainCrystallizer(
            beliefs_writer=writers["beliefs"],
            beliefs_reader=readers["beliefs"],
            conversations_reader=readers.get("conversations"),
            dynamic_reader=readers["dynamic"],
            dynamic_writer=writers["dynamic"],
        )
        generator = FountainGenerator(
            sense_writer=writers["sense"],
            dynamic_writer=writers["dynamic"],
            voice_client=VoiceClient(request_fn=deterministic_model),
            dynamic_reader=readers["dynamic"],
            beliefs_writer=writers["beliefs"],
            beliefs_reader=readers["beliefs"],
            crystallizer=crystallizer,
            sense_reader=readers["sense"],
            conversations_reader=readers.get("conversations"),
        )
        original_build_prompt = generator._build_prompt

        def capture_prompt_and_manifest(*args, **kwargs):
            prompt, manifest = original_build_prompt(*args, **kwargs)
            retrieval_manifests.append(list(manifest))
            return prompt, manifest

        generator._build_prompt = capture_prompt_and_manifest
        random.seed(8675309)
        try:
            thought = generator.generate(DynamicState(), readers["beliefs"])

            beliefs = [
                tuple(row[key] for key in
                      ("content", "tier", "confidence", "source", "branch_id"))
                for row in readers["beliefs"].read(
                    "SELECT content, tier, confidence, source, branch_id "
                    "FROM beliefs ORDER BY id"
                )
            ]
            fires = [
                tuple(row[key] for key in
                      ("thought", "readiness", "hot_branch", "word_count"))
                for row in readers["dynamic"].read(
                    "SELECT thought, readiness, hot_branch, word_count "
                    "FROM fountain_events ORDER BY id"
                )
            ]
            table_counts = {}
            for db_name, reader in readers.items():
                tables = reader.read(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                )
                table_counts[db_name] = {
                    row["name"]: reader.count(row["name"])
                    for row in tables
                }

            trace_rows = (
                _read_events(sink) if trace_on else []
            )
            if not trace_on:
                assert not sink.exists()

            return {
                "thought": thought,
                "model_requests": model_requests,
                "retrieval_manifests": retrieval_manifests,
                "workspace_winners": workspace_winners,
                "beliefs": beliefs,
                "fires": fires,
                "table_counts": table_counts,
                "trace_rows": trace_rows,
                "trace_path": sink,
            }
        finally:
            for reader in readers.values():
                try:
                    reader.close()
                except Exception:
                    pass
            for writer in writers.values():
                writer.close()


def test_full_fountain_generator_trace_overlay_on_off_equivalence(tmp_path, monkeypatch):
    from substrate import Reader
    import theory_x.stage_tom.global_workspace as global_workspace

    original_reader_open = Reader._open
    original_gw_arbitrate = global_workspace.arbitrate

    off = _run_paired_fountain_once(
        tmp_path / "off", trace_on=False, monkeypatch=monkeypatch,
        original_reader_open=original_reader_open,
        original_gw_arbitrate=original_gw_arbitrate,
    )
    on = _run_paired_fountain_once(
        tmp_path / "on", trace_on=True, monkeypatch=monkeypatch,
        original_reader_open=original_reader_open,
        original_gw_arbitrate=original_gw_arbitrate,
    )

    assert on["thought"] == off["thought"]
    assert on["model_requests"] == off["model_requests"]
    assert on["retrieval_manifests"] == off["retrieval_manifests"]
    assert on["workspace_winners"] == off["workspace_winners"]
    assert on["beliefs"] == off["beliefs"]
    assert on["fires"] == off["fires"]
    assert on["table_counts"] == off["table_counts"]

    rows = on["trace_rows"]
    assert rows
    assert rows[0]["stage"] == "input_arrival"
    assert rows[-1]["stage"] == "output"
    assert {row["stage"] for row in rows} >= {
        "input_arrival", "readiness", "candidate_generation",
        "salience_workspace", "prompt_context_selection",
        "prompt_assembly", "output_filter", "sqlite_writer_delta",
        "quality_gate", "gate", "output",
    }
    assert any(
        row["stage"] == "sqlite_writer_delta"
        and row["metadata"].get("table") == "beliefs"
        and row["metadata"].get("status") == "committed"
        for row in rows
    )
    seen = set()
    for row in rows:
        assert all(parent in seen for parent in row["parent_ids"])
        seen.add(row["event_id"])
        assert row["evidence_level"] == "L3"
    serialized = on["trace_path"].read_text(encoding="utf-8")
    assert "A small observation can change how a familiar pattern is understood." not in serialized
