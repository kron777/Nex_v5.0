"""Tests for fair, retry-safe Tier-6 climb coverage in PipelineHooks."""
from __future__ import annotations

from tests import _bootstrap  # noqa: F401

from theory_x.stage3_world_model.pipeline_hooks import PipelineHooks


class _Reader:
    def __init__(self, rows, newest=None):
        self.rows = rows
        self.newest = newest or []

    def read(self, sql, params=()):
        if "WHERE tier <= 7" in sql:
            return self.newest[:params[-1]] if params else self.newest
        if "WHERE tier = 6" in sql:
            cursor, limit = params
            if "id > ?" in sql:
                selected = [r for r in self.rows if r["id"] > cursor]
            else:
                selected = [r for r in self.rows if r["id"] <= cursor]
            return selected[:limit]
        raise AssertionError(f"Unexpected query: {sql}")


class _Promoter:
    def __init__(self, fail_ids=()):
        self.fail_ids = set(fail_ids)
        self.calls = []

    def corroborate(self, belief_id):
        self.calls.append(belief_id)
        if belief_id in self.fail_ids:
            raise RuntimeError("injected corroboration failure")


def test_t6_climb_windows_rotate_through_all_ids():
    rows = [{"id": i, "content": "quantum coherence", "tier": 6}
            for i in range(1, 502)]
    hooks = PipelineHooks(_Promoter(), _Reader(rows))

    first, cursor = hooks._load_t6_climb_candidates(limit=500)
    assert [r["id"] for r in first] == list(range(1, 501))
    assert cursor == 500
    assert hooks._t6_climb_cursor == 0

    hooks._t6_climb_cursor = cursor
    second, cursor = hooks._load_t6_climb_candidates(limit=500)
    ids = {r["id"] for r in second}
    assert len(second) == 500
    assert 501 in ids
    assert 500 not in ids
    assert cursor == 499


def test_t6_climb_does_not_advance_after_corroboration_failure(monkeypatch):
    import os

    monkeypatch.setenv("NEX5_TIER_CLIMB", "1")
    rows = [
        {"id": 1, "content": "quantum coherence is important", "tier": 6},
        {"id": 2, "content": "quantum coherence has consequences", "tier": 6},
    ]
    promoter = _Promoter(fail_ids={1})
    hooks = PipelineHooks(promoter, _Reader(rows, newest=[rows[0]]))

    hooks.on_pipeline_event({
        "magnitude": 0.9,
        "sensation_source": "quantum coherence",
        "branch_id": "",
    })

    assert promoter.calls == [1, 2]
    assert hooks._t6_climb_cursor == 0
