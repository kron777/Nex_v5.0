"""Shutdown regression for the enabled persona responder producer."""
import threading
from unittest.mock import patch

from theory_x.stage_tom import persona_responder as pr


def test_persona_responder_does_not_write_after_stop_during_model_call():
    started = threading.Event()
    release = threading.Event()
    stop = threading.Event()
    result = {}

    def blocked_persona(*_args, **_kwargs):
        started.set()
        release.wait(timeout=3.0)
        return "I wonder what lies beyond the next horizon."

    def run():
        result.update(pr.one_exchange(
            dynamic_writer=object(),
            sense_writer=object(),
            conversations_writer=object(),
            conversations_reader=object(),
            stop_event=stop,
        ))

    with patch.object(pr, "_load_interlocutor_state", return_value=None), patch.object(
        pr, "_recent_thoughts", return_value=["NEX has been thinking about the world."]
    ), patch.object(pr, "_ask_persona", side_effect=blocked_persona), patch.object(
        pr, "_write_other_mind"
    ) as write_other, patch.object(pr, "_write_persona_reject") as write_reject:
        thread = threading.Thread(target=run)
        thread.start()
        assert started.wait(timeout=2.0)
        stop.set()
        release.set()
        thread.join(timeout=2.0)

    assert not thread.is_alive()
    assert result.get("error") == "shutdown_requested"
    write_other.assert_not_called()
    write_reject.assert_not_called()


def test_persona_model_call_does_not_start_when_already_stopped():
    stop = threading.Event()
    stop.set()

    with patch.object(pr.urllib.request, "urlopen") as urlopen:
        result = pr._ask_persona(
            ["NEX has been thinking about the world."],
            stop_event=stop,
        )

    assert result is None
    urlopen.assert_not_called()
