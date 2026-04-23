"""Central error channel.

Every module logs to this channel. The GUI error tab reads from it.
Ring-buffered in memory; bounded size keeps it cheap.

A logging Handler is provided for Python logging → central channel;
direct `record(...)` calls are also supported.

See SPECIFICATION.md §8 — Graceful Degradation with Error Reporting.
"""
from __future__ import annotations

import logging
import threading
import time
import traceback as _tb
from collections import deque
from dataclasses import asdict, dataclass
from typing import Optional

THEORY_X_STAGE = None

_MAX_RECENT = 500


@dataclass
class ErrorEvent:
    timestamp: int
    source: str
    level: str
    message: str
    traceback: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


_lock = threading.Lock()
_events: "deque[ErrorEvent]" = deque(maxlen=_MAX_RECENT)


def record(
    message: str,
    *,
    source: str = "unknown",
    level: str = "ERROR",
    exc: Optional[BaseException] = None,
) -> None:
    tb = None
    if exc is not None:
        tb = "".join(_tb.format_exception(type(exc), exc, exc.__traceback__))
    with _lock:
        _events.append(
            ErrorEvent(
                timestamp=int(time.time()),
                source=source,
                level=level,
                message=message,
                traceback=tb,
            )
        )


def recent(limit: int = 100) -> list[ErrorEvent]:
    with _lock:
        return list(_events)[-limit:]


def clear() -> None:
    with _lock:
        _events.clear()


class CentralHandler(logging.Handler):
    """Forwards WARNING+ log records into the central channel."""

    def emit(self, record_: logging.LogRecord) -> None:
        if record_.levelno < logging.WARNING:
            return
        tb = self.format(record_) if record_.exc_info else None
        with _lock:
            _events.append(
                ErrorEvent(
                    timestamp=int(record_.created),
                    source=record_.name,
                    level=record_.levelname,
                    message=record_.getMessage(),
                    traceback=tb,
                )
            )


def install_handler(root_logger: Optional[logging.Logger] = None) -> None:
    root = root_logger or logging.getLogger()
    for h in root.handlers:
        if isinstance(h, CentralHandler):
            return
    root.addHandler(CentralHandler())
