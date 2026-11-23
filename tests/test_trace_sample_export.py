"""Validate the opt-in isolated Phase-0 trace sample assembled by paired fixtures."""
import json
import os
from pathlib import Path

import pytest


def test_export_contains_complete_fountain_and_chat_traces_when_enabled():
    destination = os.environ.get("NEX_CAUSAL_TRACE_SAMPLE_PATH")
    if not destination:
        pytest.skip("CI artifact export is opt-in")
    path = Path(destination)
    assert path.is_file()
    sample = json.loads(path.read_text(encoding="utf-8"))
    assert sample["classification"] == "isolated_fixture_not_live_runtime"
    assert sample["source_revision"]
    assert set(sample["traces"]) == {"fountain_cycle", "chat_turn"}
    for trace in sample["traces"].values():
        rows = trace["records"]
        assert trace["off_on_equivalence"] is True
        assert trace["record_count"] == len(rows) > 0
        assert rows[0]["event_type"] == "trace_start"
        assert rows[-1]["event_type"] == "trace_end"
        assert len({row["trace_id"] for row in rows}) == 1
        seen = set()
        for row in rows:
            assert all(parent in seen for parent in row["parent_ids"])
            seen.add(row["record_id"])
    serialized = path.read_text(encoding="utf-8")
    assert "Hello, NEX. Give me one observation." not in serialized
    assert "A deterministic reply." not in serialized
    assert "private prompt" not in serialized
