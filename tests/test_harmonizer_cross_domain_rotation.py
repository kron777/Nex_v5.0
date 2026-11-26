"""Regression tests for rotating cross-domain candidate coverage."""
from __future__ import annotations

from tests import _bootstrap  # noqa: F401

from theory_x.stage3_world_model.harmonizer import Harmonizer


class _Reader:
    def __init__(self, rows):
        self.rows = rows

    def read(self, sql, params=()):
        if "FROM beliefs" in sql:
            cursor, limit = params
            if "id > ?" in sql:
                selected = [r for r in self.rows if r["id"] > cursor]
            else:
                selected = [r for r in self.rows if r["id"] <= cursor]
            return selected[:limit]
        if "FROM belief_edges" in sql:
            return []
        raise AssertionError(f"Unexpected query: {sql}")


def _harmonizer(rows):
    h = object.__new__(Harmonizer)
    h._beliefs_reader = _Reader(rows)
    h._cross_domain_cursor = 0
    return h


def test_cross_domain_windows_rotate_past_first_two_hundred_ids():
    rows = [
        {"id": i, "content": f"shared quantum coherence concept {i}",
         "branch_id": f"branch-{i % 7}"}
        for i in range(1, 202)
    ]
    h = _harmonizer(rows)

    first, cursor = h._load_cross_domain_candidates(limit=200)
    assert [r["id"] for r in first] == list(range(1, 201))
    assert cursor == 200
    assert h._cross_domain_cursor == 0  # candidate loading alone must not commit

    h._cross_domain_cursor = cursor
    second, cursor = h._load_cross_domain_candidates(limit=200)
    second_ids = {r["id"] for r in second}
    assert len(second) == 200
    assert 201 in second_ids
    assert 200 not in second_ids
    assert cursor == 199

    h._cross_domain_cursor = cursor
    third, cursor = h._load_cross_domain_candidates(limit=200)
    third_ids = {r["id"] for r in third}
    assert 200 in third_ids
    assert 201 in third_ids
    assert set(range(1, 202)).issubset(
        {r["id"] for r in first} | second_ids | third_ids
    )
    assert cursor == 198


def test_cross_domain_empty_store_keeps_cursor():
    h = _harmonizer([])
    rows, cursor = h._load_cross_domain_candidates(limit=200)
    assert rows == []
    assert cursor == 0
