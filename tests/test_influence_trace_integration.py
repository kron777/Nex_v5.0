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
