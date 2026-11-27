"""Regression coverage for FocusLoop's direct observation append guard."""

import json
import sqlite3

from theory_x.sustained.focus_loop import _append_observation


def test_focus_loop_does_not_repeat_identical_last_observation():
    cx = sqlite3.connect(":memory:")
    try:
        cx.execute(
            "CREATE TABLE open_problems ("
            "id INTEGER PRIMARY KEY, observations TEXT, last_touched_at REAL)"
        )
        cx.execute(
            "INSERT INTO open_problems (id, observations, last_touched_at) "
            "VALUES (1, '[]', 0)"
        )
        cx.commit()

        first_count = _append_observation(cx, 1, "same current observation")
        repeated_count = _append_observation(cx, 1, "same current observation")
        distinct_count = _append_observation(cx, 1, "a genuinely new observation")

        row = cx.execute(
            "SELECT observations FROM open_problems WHERE id=1"
        ).fetchone()
        observations = json.loads(row[0])

        assert first_count == 1
        assert repeated_count == 1
        assert distinct_count == 2
        assert [item["text"] for item in observations] == [
            "same current observation",
            "a genuinely new observation",
        ]
    finally:
        cx.close()
