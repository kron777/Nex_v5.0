"""StrikeProtocol delayed catalogue writes participate in bounded AppState shutdown."""
from __future__ import annotations

from types import SimpleNamespace

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

    def save(self, _record):
        self.saved += 1
        return self.saved

    def update_beliefs_after(self, record_id, count):
        self.updated.append((record_id, count))


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

    threads = list(protocol._threads)
    for thread in threads:
        thread.join(timeout=1.0)

    assert all(not thread.is_alive() for thread in threads)
    assert catalogue.updated == [(1, 0)]
    assert protocol._threads == []
    protocol.stop()
