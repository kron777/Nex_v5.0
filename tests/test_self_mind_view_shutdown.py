"""Shutdown regressions for SelfMindView snapshot preparation."""
import threading
from unittest.mock import MagicMock, patch

from theory_x.stage_tom.self_mind_view import SelfMindView


def _view():
    return SelfMindView(
        dynamic_reader=MagicMock(),
        dynamic_writer=MagicMock(),
        beliefs_reader=MagicMock(),
        conversations_reader=MagicMock(),
    )


def _state():
    return {
        "taken_at": 1.0,
        "beliefs": {"recent_sample": [], "total_count": 0, "t1_count": 0,
                    "t2_count": 0, "t3_count": 0, "t4_count": 0,
                    "avg_confidence": None},
        "intentions": {"current_problem": None, "current_drive": None,
                       "open_problem_count": 0, "active_drive_count": 0,
                       "intentions_sample": []},
        "knowledge": {"anchor_sample": [], "t1_count": 0, "t2_count": 0},
        "uncertainty": {"review_queue_count": 0, "t3_t4_count": 0,
                        "explicit_unknowns": []},
        "attention": {"current_drive_theme": None, "current_themes": [],
                      "recent_belief_count_5min": 0,
                      "recent_gate_decisions_5min": 0},
    }


def test_current_state_stops_between_aspect_reads():
    stop = threading.Event()
    view = _view()
    view._aspect_beliefs = MagicMock(side_effect=lambda: (stop.set() or {}))
    view._aspect_intentions = MagicMock()

    result = view.current_state(stop_event=stop)

    assert result is None
    view._aspect_intentions.assert_not_called()


def test_snapshot_does_not_write_after_stop_during_self_binding():
    started = threading.Event()
    release = threading.Event()
    stop = threading.Event()
    view = _view()
    view.current_state = MagicMock(return_value=_state())

    def blocked_bind(*_args, **_kwargs):
        started.set()
        release.wait(timeout=3.0)
        return {"synthesis": "Right now, I am steady.", "components": {}}

    with patch("theory_x.stage_tom.self_binding.bind", side_effect=blocked_bind):
        result = {}
        thread = threading.Thread(
            target=lambda: result.update(
                value=view._snapshot(stop_event=stop)
            )
        )
        thread.start()
        assert started.wait(timeout=2.0)
        stop.set()
        release.set()
        thread.join(timeout=2.0)

    assert not thread.is_alive()
    assert result.get("value") == 0
    view._dw.write.assert_not_called()


def test_self_mind_view_tick_does_not_start_when_already_stopped():
    stop = threading.Event()
    stop.set()
    view = _view()
    view._snapshot = MagicMock()

    view.tick(stop_event=stop)

    view._snapshot.assert_not_called()
