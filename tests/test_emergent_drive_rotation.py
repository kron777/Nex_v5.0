"""Tests for rotating EmergentDrive pressure-scan coverage."""
from __future__ import annotations

from tests import _bootstrap  # noqa: F401

from theory_x.stage2_dynamic.emergent_drives import EmergentDriveDetector


class _Reader:
    def __init__(self, rows):
        self.rows = rows

    def read(self, sql, params=()):
        cursor, limit = params
        if "id > ?" in sql:
            selected = [r for r in self.rows if r["id"] > cursor]
        else:
            selected = [r for r in self.rows if r["id"] <= cursor]
        return selected[:limit]


def test_emergent_drive_pressure_windows_rotate_beyond_first_500():
    rows = [
        {"id": i, "content": f"branch {i} is exploring emerging patterns",
         "branch_id": f"branch-{i}", "confidence": 0.8}
        for i in range(1, 502)
    ]
    detector = EmergentDriveDetector(dynamic_writer=None)
    reader = _Reader(rows)

    first, cursor = detector._load_pressure_candidates(reader, limit=500)
    assert [r["id"] for r in first] == list(range(1, 501))
    assert cursor == 500
    assert detector._belief_cursor == 0

    detector._belief_cursor = cursor
    second, cursor = detector._load_pressure_candidates(reader, limit=500)
    second_ids = {r["id"] for r in second}
    assert len(second) == 500
    assert 501 in second_ids
    assert 500 not in second_ids
    assert cursor == 499


def test_pressure_scan_commits_cursor_after_calculation():
    rows = [
        {"id": i, "content": "branch is exploring emerging patterns",
         "branch_id": f"branch-{i}", "confidence": 0.8}
        for i in range(1, 502)
    ]
    detector = EmergentDriveDetector(dynamic_writer=None)
    proposals = detector.scan_for_pressure(_Reader(rows), dynamic_state=None)
    assert proposals == []
    assert detector._belief_cursor == 500


def test_empty_emergent_drive_pressure_pool_keeps_cursor():
    detector = EmergentDriveDetector(dynamic_writer=None)
    detector._belief_cursor = 77
    rows, cursor = detector._load_pressure_candidates(_Reader([]), limit=500)
    assert rows == []
    assert cursor == 77
