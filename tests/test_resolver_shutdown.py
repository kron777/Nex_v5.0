"""Shutdown regressions for the LLM-backed HoldingZoneResolver reshape path."""
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock

from theory_x.stage_gate.resolver import HoldingZoneResolver


def _row():
    return {
        "id": 41,
        "content": "A held thought awaiting a careful reshape.",
        "source_node": "fountain",
        "confidence": 0.7,
        "reshape_depth": 0,
        "branch_id": "cognition",
    }


def test_resolver_discards_model_result_when_stop_arrives_during_voice_call():
    started = threading.Event()
    release = threading.Event()
    stop = threading.Event()
    zone = MagicMock()
    zone.find_reshape_pending.return_value = [_row()]

    def blocked_speak(_request):
        started.set()
        release.wait(timeout=3.0)
        return SimpleNamespace(text="A carefully restated thought that preserves the core meaning.")

    voice = SimpleNamespace(speak=blocked_speak)
    from theory_x.stage_gate.transformer import ReshapeTransformer

    gate = MagicMock()
    resolver = HoldingZoneResolver(
        zone,
        beliefs_writer=object(),
        transformer=ReshapeTransformer(voice),
        gate=gate,
    )

    thread = threading.Thread(
        target=resolver._process_reshape_pending,
        kwargs={"stop_event": stop},
    )
    thread.start()
    assert started.wait(timeout=2.0)
    stop.set()
    release.set()
    thread.join(timeout=2.0)

    assert not thread.is_alive()
    gate.check.assert_not_called()
    zone.mark_reshape_complete.assert_not_called()


def test_resolver_does_not_mark_reshape_complete_if_stop_arrives_during_gate_check():
    entered_gate = threading.Event()
    release_gate = threading.Event()
    stop = threading.Event()
    zone = MagicMock()
    zone.find_reshape_pending.return_value = [_row()]

    class Transformer:
        def transform(self, packet, original_thought_id, current_depth, **kwargs):
            return SimpleNamespace(content="A carefully restated thought.")

    def blocked_gate_check(_packet):
        entered_gate.set()
        release_gate.wait(timeout=3.0)

    gate = MagicMock()
    gate.check.side_effect = blocked_gate_check
    resolver = HoldingZoneResolver(
        zone,
        beliefs_writer=object(),
        transformer=Transformer(),
        gate=gate,
    )

    thread = threading.Thread(
        target=resolver._process_reshape_pending,
        kwargs={"stop_event": stop},
    )
    thread.start()
    assert entered_gate.wait(timeout=2.0)
    stop.set()
    release_gate.set()
    thread.join(timeout=2.0)

    assert not thread.is_alive()
    gate.check.assert_called_once()
    zone.mark_reshape_complete.assert_not_called()


def test_resolver_tick_does_not_start_reshape_after_stop_during_fade():
    stop = threading.Event()
    zone = MagicMock()
    zone.fade_stale.side_effect = lambda _now: stop.set()
    resolver = HoldingZoneResolver(
        zone,
        beliefs_writer=object(),
        transformer=MagicMock(),
        gate=MagicMock(),
    )

    resolver.tick(stop_event=stop)

    zone.find_reshape_pending.assert_not_called()
