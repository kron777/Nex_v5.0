"""Tests for the Phase 0 default-OFF causal trace writer."""

import json

import influence_trace as trace
from influence_trace import TraceContext as InfluenceTracer


def _sink(tmp_path):
    return tmp_path / "trace.jsonl"


def test_overlay_is_default_off(monkeypatch, tmp_path):
    monkeypatch.delenv("NEX5_TRACE_OVERLAY", raising=False)
    monkeypatch.delenv("NEX5_TRACE_OVERLAY_PATH", raising=False)
    assert trace.overlay_enabled() is False
    assert trace.new_trace("chat_turn") is None
    assert not (tmp_path / "trace.jsonl").exists()


def test_zero_value_is_off_and_truthy_value_is_on(monkeypatch):
    monkeypatch.setenv("NEX5_TRACE_OVERLAY", "0")
    assert trace.new_trace("fountain_cycle") is None
    monkeypatch.setenv("NEX5_TRACE_OVERLAY", "1")
    assert trace.new_trace("fountain_cycle") is not None


def test_events_have_trace_ids_parent_ids_and_monotonic_sequence(tmp_path):
    tracer = trace.TraceContext("fountain_cycle", sink_path=tmp_path / "trace.jsonl",
                                context="fixture", trace_id="fixture-trace")
    first = tracer.input("prompt must not be stored", source="fixture.input")
    second = tracer.candidates([41, 42], source="fixture.retrieval")
    third = tracer.selection(source="fixture.workspace",
                             candidate_order=[41, 42], selected_order=[42, 41],
                             strategy="fixture_order")

    assert first and second and third
    events = [json.loads(line) for line in (tmp_path / "trace.jsonl").read_text().splitlines()]
    assert [event["sequence"] for event in events] == [1, 2, 3]
    assert all(event["trace_id"] == "fixture-trace" for event in events)
    assert events[0]["parent_ids"] == []
    assert events[1]["parent_ids"] == [first]
    assert events[2]["parent_ids"] == [second]
    assert all(event["evidence_level"] == "L3" for event in events)
    assert all(event["capture_context"] == "fixture" for event in events)


def test_text_is_hashed_and_never_persisted(tmp_path):
    secret_prompt = "distinctive prompt text not to persist"
    secret_reply = "distinctive assistant output not to persist"
    tracer = trace.TraceContext("chat_turn", sink_path=tmp_path / "trace.jsonl")
    tracer.input(secret_prompt, source="chat.user")
    tracer.record("prompt_assembly", "blocks_ready", metadata={
        "prompt": secret_prompt,
        "block_names": ["operator", "compassion"],
        "text": secret_reply,
    })
    tracer.output(secret_reply, output_kind="chat_reply")

    content = (tmp_path / "trace.jsonl").read_text()
    assert secret_prompt not in content
    assert secret_reply not in content
    records = [json.loads(line) for line in content.splitlines()]
    assert records[0]["metadata"]["sha256"].startswith("sha256:")
    assert records[1]["metadata"]["prompt"]["length"] == len(secret_prompt)
    assert records[1]["metadata"]["text"]["length"] == len(secret_reply)
    assert records[2]["metadata"]["length"] == len(secret_reply)


def test_nested_text_collections_are_hashed(tmp_path):
    hidden_candidates = ["candidate secret alpha", "candidate secret beta"]
    tracer = InfluenceTracer("test", sink_path=_sink(tmp_path), enabled=True)
    tracer.record("candidate_generation", "candidates", metadata={
        "candidate_texts": hidden_candidates,
    })
    content = _sink(tmp_path).read_text()
    assert all(value not in content for value in hidden_candidates)
    record = json.loads(content)
    assert record["metadata"]["candidate_texts"]["value_type"] == "list"
    assert record["metadata"]["candidate_texts"]["length"] > 0


def test_unrecognised_metadata_strings_are_hashed_by_default(tmp_path):
    private_note = "unexpected free-form diagnostic with private content"
    tracer = InfluenceTracer("test", sink_path=_sink(tmp_path), enabled=True)
    tracer.record("diagnostic", "observed", metadata={
        "unexpected_future_field": private_note,
        "source": "stage6_fountain",
    })
    content = _sink(tmp_path).read_text()
    assert private_note not in content
    record = json.loads(content)
    assert record["metadata"]["source"] == "stage6_fountain"
    assert record["metadata"]["unexpected_future_field"]["value_type"] == "str"
    assert record["metadata"]["unexpected_future_field"]["length"] == len(
        private_note.encode("utf-8")
    )


def test_trace_metadata_does_not_mutate_candidate_order_or_confidence(tmp_path):
    candidates = [
        {"id": 11, "confidence": 0.82},
        {"id": 12, "confidence": 0.65},
        {"id": 13, "confidence": 0.91},
    ]
    original_order = [item["id"] for item in candidates]
    original_confidence = [item["confidence"] for item in candidates]
    selected_order = [11, 13]
    original_selected = list(selected_order)

    tracer = trace.TraceContext("chat_turn", sink_path=tmp_path / "trace.jsonl")
    tracer.candidates(original_order, source="fixture.retrieval")
    tracer.selection(source="fixture.workspace",
                     candidate_order=original_order,
                     selected_order=selected_order,
                     strategy="fixture")
    tracer.record("quality", "observed", metadata={
        "confidence_values": original_confidence,
    })

    assert [item["id"] for item in candidates] == original_order
    assert [item["confidence"] for item in candidates] == original_confidence
    assert selected_order == original_selected


def test_writer_delta_records_single_database_commit_scope(tmp_path):
    tracer = trace.TraceContext("fountain_cycle", sink_path=tmp_path / "trace.jsonl")
    tracer.writer_delta(database="beliefs", table="beliefs", operation="INSERT", row_id=77)
    record = json.loads((tmp_path / "trace.jsonl").read_text())
    assert record["stage"] == "sqlite_writer_delta"
    assert record["metadata"]["row_id"] == 77
    assert record["metadata"]["transaction_scope"] == "single_statement_single_database"


def test_write_many_delta_records_atomic_single_database_scope(tmp_path):
    tracer = InfluenceTracer("test", sink_path=_sink(tmp_path), enabled=True)
    tracer.writer_delta(
        database="dynamic", table="fountain_retrieval_log",
        operation="WRITE_MANY", row_id=[1, 2], metadata={"row_count": 2},
    )
    record = json.loads(_sink(tmp_path).read_text())
    assert record["metadata"]["transaction_scope"] == "single_database_atomic_write_many"


def test_non_jsonl_sink_is_rejected_without_writing(tmp_path):
    sink = tmp_path / "beliefs.db"
    tracer = trace.TraceContext("fountain_cycle", sink_path=sink)
    assert tracer.record("sqlite_writer_delta", "write", metadata={}) is None
    assert not sink.exists()


def test_sink_failure_is_non_fatal(tmp_path):
    blocker = tmp_path / "not_a_directory"
    blocker.write_text("file")
    tracer = trace.TraceContext("chat_turn", sink_path=blocker / "trace.jsonl")
    assert tracer.record("output", "result", metadata={}) is None


def test_runtime_evidence_requires_explicit_runtime_context(tmp_path):
    fixture = trace.TraceContext("fixture", sink_path=tmp_path / "fixture.jsonl")
    runtime = trace.TraceContext("runtime", sink_path=tmp_path / "runtime.jsonl",
                                 context="runtime")
    fixture.record("output", "result", metadata={})
    runtime.record("output", "result", metadata={})
    fixture_record = json.loads((tmp_path / "fixture.jsonl").read_text())
    runtime_record = json.loads((tmp_path / "runtime.jsonl").read_text())
    assert fixture_record["evidence_level"] == "L3"
    assert fixture_record["evidence_class"] == "implemented"
    assert runtime_record["evidence_level"] == "L4"
    assert runtime_record["evidence_class"] == "measured"


def test_disabled_context_is_a_complete_noop(tmp_path):
    tracer = trace.TraceContext("chat_turn", sink_path=tmp_path / "trace.jsonl", enabled=False)
    assert tracer.input("prompt", source="chat.user") is None
    assert tracer.output("reply", output_kind="chat_reply") is None
    assert tracer.events == ()
    assert not (tmp_path / "trace.jsonl").exists()

def test_sink_rejects_symlink_to_substrate_database(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    database = data_dir / "beliefs.db"
    database.write_bytes(b"do-not-touch")
    sink = tmp_path / "trace.jsonl"
    sink.symlink_to(database)
    monkeypatch.setenv("NEX5_DATA_DIR", str(data_dir))

    tracer = InfluenceTracer("test", sink_path=sink, enabled=True)
    assert tracer.record("writer", "observed", metadata={}) is None
    assert database.read_bytes() == b"do-not-touch"


def test_sink_rejects_hardlink_to_substrate_database(tmp_path, monkeypatch):
    import os

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    database = data_dir / "beliefs.db"
    database.write_bytes(b"do-not-touch")
    sink = tmp_path / "trace.jsonl"
    os.link(database, sink)
    monkeypatch.setenv("NEX5_DATA_DIR", str(data_dir))

    tracer = InfluenceTracer("test", sink_path=sink, enabled=True)
    assert tracer.record("writer", "observed", metadata={}) is None
    assert database.read_bytes() == b"do-not-touch"


def test_chat_workspace_trace_is_observational_and_order_preserving(tmp_path, monkeypatch):
    from gui.server import _assemble_chat_blocks

    for name in ("NEX5_CHAT_WORKSPACE", "NEX5_CHAT_WORKSPACE_BUDGET",
                 "NEX5_SELF_PRESENT", "NEX5_CHAT_ABLATE"):
        monkeypatch.delenv(name, raising=False)

    original = [
        ("operator", "operator block"),
        ("compassion", "compassion block"),
        ("convo", "conversation block"),
        ("spectrum", "spectrum block"),
    ]
    untouched_snapshot = list(original)
    expected = _assemble_chat_blocks(list(original))

    tracer = InfluenceTracer("chat_turn", sink_path=_sink(tmp_path), enabled=True)
    observed = _assemble_chat_blocks(list(original), trace=tracer)

    assert observed == expected
    assert original == untouched_snapshot
    events = tracer.events
    selection = [event for event in events
                 if event["stage"] == "salience_workspace"]
    assert len(selection) == 1
    metadata = selection[0]["metadata"]
    assert metadata["candidate_order"] == ["operator", "compassion", "convo", "spectrum"]
    assert metadata["selected_order"] == metadata["candidate_order"]


def test_chat_workspace_budget_trace_does_not_change_selected_text(tmp_path, monkeypatch):
    from gui.server import _assemble_chat_blocks

    monkeypatch.setenv("NEX5_CHAT_WORKSPACE", "1")
    monkeypatch.setenv("NEX5_CHAT_WORKSPACE_BUDGET", "38")
    monkeypatch.delenv("NEX5_CHAT_ABLATE", raising=False)
    monkeypatch.delenv("NEX5_SELF_PRESENT", raising=False)
    original = [
        ("operator", "short operator block"),
        ("compassion", "short compassion block"),
        ("spectrum", "a much longer spectrum block that will not fit"),
        ("tag", "short tag block"),
    ]

    expected = _assemble_chat_blocks(list(original))
    tracer = InfluenceTracer("chat_turn", sink_path=_sink(tmp_path), enabled=True)
    observed = _assemble_chat_blocks(list(original), trace=tracer)

    assert observed == expected
    assert original[0][0] == "operator"
    selection = [event for event in tracer.events
                 if event["stage"] == "salience_workspace"][-1]
    assert selection["metadata"]["strategy"] == "NEX5_CHAT_WORKSPACE"
    assert selection["metadata"]["selected_order"]


def test_fountain_generate_trace_wrapper_preserves_result(tmp_path, monkeypatch):
    from types import MethodType
    from theory_x.stage6_fountain.generator import FountainGenerator

    generator = object.__new__(FountainGenerator)
    generator._total_fires = 4
    generator._last_fire_ts = 123.0
    calls = []

    def fake_generate(self, dynamic_state, beliefs_reader, trace=None):
        calls.append(trace)
        if trace is not None:
            trace.record("candidate_generation", "fixture_candidate",
                         metadata={"candidate_ids": [7, 8]})
        return "same fountain thought"

    generator._generate = MethodType(fake_generate, generator)
    monkeypatch.setenv("NEX5_TRACE_OVERLAY", "0")
    monkeypatch.setenv("NEX5_TRACE_OVERLAY_PATH", str(_sink(tmp_path / "off")))
    off_result = generator.generate(None, None)
    assert off_result == "same fountain thought"
    assert calls[-1] is None
    assert not (tmp_path / "off" / "trace.jsonl").exists()

    monkeypatch.setenv("NEX5_TRACE_OVERLAY", "1")
    monkeypatch.setenv("NEX5_TRACE_OVERLAY_PATH", str(_sink(tmp_path / "on")))
    on_result = generator.generate(None, None)
    assert on_result == off_result
    assert calls[-1] is not None
    records = [json.loads(line) for line in _sink(tmp_path / "on").read_text().splitlines()]
    assert [record["stage"] for record in records] == [
        "input_arrival", "candidate_generation", "output"
    ]
    assert records[1]["parent_ids"] == [records[0]["event_id"]]
    assert records[2]["parent_ids"] == [records[1]["event_id"]]


def test_membrane_route_trace_preserves_retrieval_and_return_value(tmp_path):
    from theory_x.stage4_membrane.classifier import MembraneSide
    from theory_x.stage4_membrane.router import QueryRouter

    class OutsideClassifier:
        def classify_query(self, query):
            return MembraneSide.OUTSIDE

    class DynamicState:
        def status(self):
            return {"branches": [{"branch_id": "systems", "focus_num": 0.4}]}

    class Retriever:
        def __init__(self):
            self.calls = []

        def retrieve(self, **kwargs):
            self.calls.append(dict(kwargs))
            return [{
                "id": 901,
                "tier": 6,
                "confidence": 0.82,
                "content": "A grounded candidate belief",
            }]

    router = QueryRouter(classifier=OutsideClassifier())
    retriever_off = Retriever()
    retriever_on = Retriever()
    dynamic = DynamicState()

    off = router.route("a query", retriever_off, object(), dynamic_state=dynamic)
    tracer = InfluenceTracer("chat_turn", sink_path=_sink(tmp_path), enabled=True)
    on = router.route("a query", retriever_on, object(), dynamic_state=dynamic,
                      trace=tracer)

    assert on == off
    assert retriever_on.calls == retriever_off.calls
    candidate_events = [event for event in tracer.events
                        if event["stage"] == "candidate_generation"]
    assert len(candidate_events) == 1
    assert candidate_events[0]["metadata"]["candidate_ids"] == [901]
