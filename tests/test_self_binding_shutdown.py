"""Shutdown regressions for the self-binding read/commit boundary."""
import threading
from unittest.mock import MagicMock, patch

from theory_x.stage_tom import self_binding


def test_bind_aborts_between_faculty_reads_when_stop_arrives():
    started = threading.Event()
    release = threading.Event()
    stop = threading.Event()
    writer = MagicMock()

    def blocked_emotion(_stop_event):
        started.set()
        release.wait(timeout=3.0)
        return {"emotion": "steady"}

    with patch.object(self_binding, "_ensure_table"), patch.object(
        self_binding, "_read_emotion", side_effect=blocked_emotion
    ), patch.object(self_binding, "_read_raga") as read_raga:
        result = {}
        thread = threading.Thread(
            target=lambda: result.update(
                value=self_binding.bind(writer, stop_event=stop)
            )
        )
        thread.start()
        assert started.wait(timeout=2.0)
        stop.set()
        release.set()
        thread.join(timeout=2.0)

    assert not thread.is_alive()
    assert result["value"]["aborted"] is True
    read_raga.assert_not_called()
    writer.write.assert_not_called()


def test_bind_does_not_start_schema_or_state_writes_when_already_stopped():
    stop = threading.Event()
    stop.set()
    writer = MagicMock()

    with patch.object(self_binding, "_ensure_table") as ensure_table:
        result = self_binding.bind(writer, stop_event=stop)

    assert result["aborted"] is True
    ensure_table.assert_not_called()
    writer.write.assert_not_called()


def test_bind_finishes_current_state_history_pair_if_stop_arrives_mid_commit():
    stop = threading.Event()
    writer = MagicMock()
    calls = []

    def write_and_signal(*_args, **_kwargs):
        calls.append(1)
        if len(calls) == 1:
            stop.set()
        return len(calls)

    writer.write.side_effect = write_and_signal
    with patch.object(self_binding, "_ensure_table"), patch.object(
        self_binding, "_read_emotion", return_value={"emotion": "steady"}
    ), patch.object(self_binding, "_read_raga", return_value={"raga": "free"}), patch.object(
        self_binding, "_read_dominant_drive", return_value="curiosity"
    ), patch.object(
        self_binding, "_read_attention", return_value={"readiness": 0.5}
    ), patch.object(
        self_binding, "_read_substrate", return_value={"cpu": 0.1, "tone": "humming quietly"}
    ):
        result = self_binding.bind(writer, stop_event=stop)

    assert result.get("aborted") is not True
    assert writer.write.call_count == 2
