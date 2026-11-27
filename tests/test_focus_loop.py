"""Regression tests for FocusLoop's one-pen database mutations."""

from substrate import Reader, Writer, connect
from theory_x.sustained.focus_loop import _append_observation, _surface_to_chat, _update_current_focus


def _open_problem_db(path):
    cx = connect(path)
    cx.execute(
        "CREATE TABLE open_problems ("
        "id INTEGER PRIMARY KEY, title TEXT, state TEXT, "
        "observations TEXT, last_touched_at REAL)"
    )
    cx.execute(
        "INSERT INTO open_problems "
        "(id, title, state, observations, last_touched_at) "
        "VALUES (1, 'test focus', 'open', '[]', 0)"
    )
    cx.commit()
    cx.close()


def test_focus_loop_does_not_repeat_identical_last_observation(tmp_path):
    db_path = tmp_path / "conversations.db"
    _open_problem_db(db_path)
    reader = Reader(db_path)
    writer = Writer(db_path, name="focus-loop-observation-test")
    try:
        first_count = _append_observation(
            reader, writer, 1, "same current observation"
        )
        repeated_count = _append_observation(
            reader, writer, 1, "same current observation"
        )
        distinct_count = _append_observation(
            reader, writer, 1, "a genuinely new observation"
        )

        row = reader.read_one(
            "SELECT observations FROM open_problems WHERE id=1"
        )
        observations = __import__("json").loads(row["observations"])

        assert first_count == 1
        assert repeated_count == 1
        assert distinct_count == 2
        assert [item["text"] for item in observations] == [
            "same current observation",
            "a genuinely new observation",
        ]
    finally:
        writer.close()


def test_focus_loop_surface_to_chat_uses_one_atomic_writer_batch(tmp_path):
    db_path = tmp_path / "conversations-ping.db"
    _open_problem_db(db_path)
    cx = connect(db_path)
    cx.execute(
        "CREATE TABLE sessions ("
        "id TEXT PRIMARY KEY, started_at INTEGER, admin INTEGER, user_label TEXT)"
    )
    cx.execute(
        "CREATE TABLE messages ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, "
        "content TEXT, register TEXT, timestamp INTEGER)"
    )
    cx.commit()
    cx.close()

    reader = Reader(db_path)
    writer = Writer(db_path, name="focus-loop-ping-test")
    try:
        _surface_to_chat(writer, 1, "test focus")
        message = reader.read_one(
            "SELECT content FROM messages WHERE role='nex' ORDER BY id DESC LIMIT 1"
        )
        problem = reader.read_one(
            "SELECT state FROM open_problems WHERE id=1"
        )
        session = reader.read_one(
            "SELECT id FROM sessions WHERE id='internal_focus_loop'"
        )
        assert message is not None
        assert "test focus" in message["content"]
        assert problem["state"] == "stuck"
        assert session is not None
    finally:
        writer.close()


def test_focus_loop_current_focus_uses_dynamic_writer(tmp_path):
    db_path = tmp_path / "dynamic.db"
    cx = connect(db_path)
    cx.execute(
        "CREATE TABLE current_focus ("
        "id INTEGER PRIMARY KEY, problem_id INTEGER, picked_at REAL, "
        "observations_at_pick INTEGER)"
    )
    cx.commit()
    cx.close()

    reader = Reader(db_path)
    writer = Writer(db_path, name="focus-loop-dynamic-test")
    try:
        _update_current_focus(writer, 1, 2)
        first = reader.read_one("SELECT problem_id, observations_at_pick FROM current_focus")
        assert first["problem_id"] == 1
        assert first["observations_at_pick"] == 2
        _update_current_focus(writer, 1, 7)
        second = reader.read_one("SELECT problem_id, observations_at_pick FROM current_focus")
        # Same problem is not rewritten; the existing WHERE condition remains.
        assert second["observations_at_pick"] == 2
        _update_current_focus(writer, 2, 7)
        third = reader.read_one("SELECT problem_id, observations_at_pick FROM current_focus")
        assert third["problem_id"] == 2
        assert third["observations_at_pick"] == 7
    finally:
        writer.close()
