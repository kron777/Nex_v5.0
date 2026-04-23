"""Sense stream adapter base class and SenseEvent dataclass.

Every feed adapter subclasses Adapter and implements poll(). The
scheduler calls poll() on each adapter's interval; the adapter returns
a list of SenseEvent objects; submit() persists them to sense.db via
the one-pen Writer — never direct sqlite3.

External adapters receive an injectable request_fn (default:
requests.get) so tests can drive them without live network calls.

See SPECIFICATION.md §4 — Sense Streams.
"""
from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Sequence

import requests

import errors as error_channel
from alpha import ALPHA  # noqa: F401 — architectural reference
from substrate import Writer

THEORY_X_STAGE = 1

# RequestFn: (url: str, params: dict | None) -> str  (raw response body)
RequestFn = Callable[[str, Optional[dict]], str]


def _default_fetch(url: str, params: Optional[dict] = None) -> str:
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.text


@dataclass
class SenseEvent:
    stream: str
    payload: str        # JSON-serialised content
    provenance: str     # source URL or identifier
    timestamp: int      # unix epoch


class Adapter(ABC):
    """Abstract base for all 23 sense-stream adapters.

    Class-level attributes (override in subclass):
        id                   — unique feed identifier, matches spec §4 numbering
        stream               — value written to sense_events.stream column
        poll_interval_seconds — scheduler cadence
        provenance           — source URL or descriptor
        is_internal          — True for internal sensors (feeds 20–23)
    """

    id: str = ""
    stream: str = ""
    poll_interval_seconds: int = 3600
    provenance: str = ""
    is_internal: bool = False

    def __init__(
        self,
        writer: Writer,
        *,
        request_fn: Optional[RequestFn] = None,
    ) -> None:
        # Validate required class attributes on every concrete instantiation.
        for attr in ("id", "stream", "poll_interval_seconds", "provenance"):
            if not getattr(type(self), attr, None):
                raise TypeError(
                    f"{type(self).__name__} must define class attribute {attr!r}"
                )
        self._writer = writer
        self._request_fn: RequestFn = request_fn or _default_fetch
        self.enabled: bool = False

    # -- network helper ----------------------------------------------------

    def _fetch(self, url: str, params: Optional[dict] = None) -> str:
        """Route all HTTP through the injected function."""
        return self._request_fn(url, params)

    def _fetch_json(self, url: str, params: Optional[dict] = None) -> Any:
        return json.loads(self._fetch(url, params))

    # -- abstract ----------------------------------------------------------

    @abstractmethod
    def poll(self) -> list[SenseEvent]:
        """Fetch new events. Called by the scheduler on each tick.

        Must not raise — errors are caught by the scheduler. Return an
        empty list when there is nothing new or when the source is
        temporarily unavailable.
        """

    # -- submission --------------------------------------------------------

    def submit(self, events: Sequence[SenseEvent]) -> int:
        """Write events to sense.db via the one-pen Writer.

        Returns the count of events written. Adapters must call this
        method rather than touching the Writer or sqlite3 directly.
        """
        if not events:
            return 0
        count = 0
        for ev in events:
            try:
                self._writer.write(
                    "INSERT INTO sense_events "
                    "(stream, payload, provenance, timestamp) "
                    "VALUES (?, ?, ?, ?)",
                    (ev.stream, ev.payload, ev.provenance, ev.timestamp),
                )
                count += 1
            except Exception as e:
                error_channel.record(
                    f"sense.submit failed for stream={ev.stream}: {e}",
                    source=f"adapter[{self.id}]",
                    exc=e,
                )
        return count

    # -- helpers for subclasses --------------------------------------------

    @staticmethod
    def now() -> int:
        return int(time.time())

    @staticmethod
    def pack(**kwargs: Any) -> str:
        """JSON-serialise a payload dict."""
        return json.dumps(kwargs, ensure_ascii=False)
