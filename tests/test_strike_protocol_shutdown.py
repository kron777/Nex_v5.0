"""StrikeProtocol delayed catalogue writes participate in bounded AppState shutdown."""
from __future__ import annotations

from types import SimpleNamespace
import threading

import pytest

from gui.server import AppState
from strikes.protocols import StrikeProtocol, StrikeType


class _Dynamic:
    def status(self):
        return {"branches": [{"branch_id": "systems", "focus_num": 0.7}]}


class _Reader:
    def read(self, _sql, _params=()):
        return []


class _Voice:
    def speak(self, *_args, **_kwargs):
        return SimpleNamespace(text="observed")


class _Catalogue:
    def __init__(self):
        self.saved = 0
        self.updated = []
        self.updated_event = threading.Event()

    def save(self, _record):
        self.saved += 1
        return self.saved

    def update_beliefs_after(self, record_id, count):
        self.updated.append((record_id, count))
        self.updated_event.set()


def _protocol():
    catalogue = _Catalogue()
    protocol = StrikeProtocol(
        voice=_Voice(),
        dynamic_state=_Dynamic(),
        beliefs_reader=_Reader(),
        sense_writer=object(),
        catalogue=catalogue,
    )
    return protocol, catalogue


def test_appstate_stops_and_joins_all_delayed_strike_catalogue_writers():
    protocol, catalogue = _protocol()
    protocol.fire(StrikeType.NOVEL)
    protocol.fire(StrikeType.CONTRADICTION)
    assert len(protocol._threads) == 2
    assert all(thread.is_alive() for thread in protocol._threads)

    state = AppState(
        writers={}, readers={}, voice=None, strike_protocol=protocol,
    )
    report = state._quiesce_producers(timeout=1.0)

    assert report == {"alive": [], "errors": []}
    assert protocol._threads == []
    assert catalogue.updated == []

    with pytest.raises(RuntimeError, match="StrikeProtocol is stopping"):
        protocol.fire(StrikeType.NOVEL)


def test_delayed_belief_check_still_updates_when_its_delay_expires():
    protocol, catalogue = _protocol()
    # Make the 60-second wait expire immediately while preserving the worker path.
    protocol._stop_event.wait = lambda _timeout: False
    protocol.fire(StrikeType.NOVEL)

    assert catalogue.updated_event.wait(timeout=1.0)
    threads = list(protocol._threads)
    for thread in threads:
        thread.join(timeout=1.0)

    assert all(not thread.is_alive() for thread in threads)
    assert catalogue.updated == [(1, 0)]
    assert protocol._threads == []
    protocol.stop()


def test_appstate_reports_an_inflight_strike_request_that_exceeds_shutdown_budget():
    class BlockingCatalogue(_Catalogue):
        def __init__(self):
            super().__init__()
            self.started = threading.Event()
            self.release = threading.Event()

        def save(self, _record):
            self.started.set()
            self.release.wait()
            self.saved += 1
            return self.saved

    catalogue = BlockingCatalogue()
    protocol = StrikeProtocol(
        voice=_Voice(),
        dynamic_state=_Dynamic(),
        beliefs_reader=_Reader(),
        sense_writer=object(),
        catalogue=catalogue,
    )
    request_thread = threading.Thread(
        target=protocol.fire, args=(StrikeType.NOVEL,), name="in-flight-strike-request"
    )
    request_thread.start()
    assert catalogue.started.wait(timeout=1.0)

    state = AppState(
        writers={}, readers={}, voice=None, strike_protocol=protocol,
    )
    report = state._quiesce_producers(timeout=0.01)
    assert any("strike_protocol" in item or "in-flight-strike-request" in item
               for item in report["alive"])

    catalogue.release.set()
    request_thread.join(timeout=1.0)
    assert not request_thread.is_alive()
    assert protocol._threads == []
    assert catalogue.updated == []


def test_appstate_interrupts_silence_observation_without_claiming_sixty_seconds():
    protocol, _catalogue = _protocol()
    started = threading.Event()
    original_wait = protocol._stop_event.wait

    def observed_wait(timeout):
        started.set()
        return original_wait(timeout)

    protocol._stop_event.wait = observed_wait
    protocol._fountain_event_count = lambda: 0
    results = []
    request_thread = threading.Thread(
        target=lambda: results.append(protocol.fire(StrikeType.SILENCE)),
        name="in-flight-silence-observation",
    )
    request_thread.start()
    assert started.wait(timeout=1.0)

    state = AppState(
        writers={}, readers={}, voice=None, strike_protocol=protocol,
    )
    report = state._quiesce_producers(timeout=1.0)
    request_thread.join(timeout=1.0)

    assert report == {"alive": [], "errors": []}
    assert not request_thread.is_alive()
    assert len(results) == 1
    assert results[0].notes == "interrupted_by_shutdown"
    assert "60-second observation was not completed" in results[0].response_text
    assert "60s of quiet" not in results[0].response_text
    assert protocol._threads == []
