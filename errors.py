"""Central error channel.

Every module logs to this channel. The GUI error tab reads from it.
Ring-buffered in memory; bounded size keeps it cheap.

A logging Handler is provided for Python logging → central channel;
direct `record(...)` calls are also supported.

See SPECIFICATION.md §8 — Graceful Degradation with Error Reporting.

2026-08-07 (round 33): every event is ALSO appended to a rotating file at
`logs/errors.log`. The in-memory deque is `maxlen=500` and silently discards,
and the only other on-disk trace was stderr redirected to `/tmp/nex5_soak.log`
— unrotated and lost on reboot. So "no new traceback signatures" checks across
ten rounds were reading a buffer that drops what it does not have room for.
The file is the durable record; the deque is unchanged and still what the GUI
reads. Disk writes are wrapped and can never raise into a caller: this module
is called from the fire path.
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import threading
import time
import traceback as _tb
from collections import deque
from dataclasses import asdict, dataclass
from typing import Optional

THEORY_X_STAGE = None

_MAX_RECENT = 500

# ---------------------------------------------------------------- disk sink
# WARNING+ only, measured at 29 records/day (~5.7 KiB/day) — 2 MiB x 5 files
# is roughly a year of history and still absorbs a pathological burst.
_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
_LOG_PATH = os.path.join(_LOG_DIR, "errors.log")
_MAX_BYTES = 2 * 1024 * 1024
_BACKUPS = 5

_disk_lock = threading.Lock()
_disk: Optional[logging.Logger] = None
_disk_failed = False


def _disk_sink() -> Optional[logging.Logger]:
    """Lazily build a private logger owning the rotating file.

    Private (propagate=False) so it cannot loop back through the root logger
    into CentralHandler. Returns None and latches off on any failure — a
    missing or unwritable logs/ must never take the fire path down.
    """
    global _disk, _disk_failed
    if _disk is not None or _disk_failed:
        return _disk
    with _disk_lock:
        if _disk is not None or _disk_failed:
            return _disk
        try:
            os.makedirs(_LOG_DIR, exist_ok=True)
            h = logging.handlers.RotatingFileHandler(
                _LOG_PATH, maxBytes=_MAX_BYTES, backupCount=_BACKUPS,
                encoding="utf-8", delay=True,
            )
            h.setFormatter(logging.Formatter(
                "%(asctime)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S"))
            lg = logging.getLogger("nex5._error_channel_disk")
            lg.setLevel(logging.INFO)
            lg.propagate = False
            lg.handlers = [h]
            _disk = lg
        except Exception:
            _disk_failed = True
        return _disk


def _to_disk(ev: "ErrorEvent") -> None:
    """Append one event. Swallows everything — never raises into a caller."""
    try:
        lg = _disk_sink()
        if lg is None:
            return
        line = f"{ev.level} {ev.source} {ev.message}"
        if ev.traceback:
            line += "\n" + ev.traceback.rstrip()
        lg.info(line)
    except Exception:
        pass


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
    ev = ErrorEvent(
        timestamp=int(time.time()),
        source=source,
        level=level,
        message=message,
        traceback=tb,
    )
    with _lock:
        _events.append(ev)
    _to_disk(ev)


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
        ev = ErrorEvent(
            timestamp=int(record_.created),
            source=record_.name,
            level=record_.levelname,
            message=record_.getMessage(),
            traceback=tb,
        )
        with _lock:
            _events.append(ev)
        _to_disk(ev)


def install_handler(root_logger: Optional[logging.Logger] = None) -> None:
    root = root_logger or logging.getLogger()
    for h in root.handlers:
        if isinstance(h, CentralHandler):
            return
    root.addHandler(CentralHandler())
