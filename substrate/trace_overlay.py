"""Default-OFF, read-only influence tracing for Phase 0.

The overlay records bounded metadata to an explicitly selected JSONL artifact.
It never writes to NEX databases, changes prompts, ranks candidates, gates
thoughts, or retains raw payloads. It is inert unless BOTH
NEX5_TRACE_OVERLAY=1 and NEX5_TRACE_PATH are supplied.
"""
from __future__ import annotations

import contextvars
import dataclasses
import hashlib
import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional


@dataclasses.dataclass(frozen=True)
class TraceHandle:
    """A scoped trace context; reset restores any enclosing trace."""

    trace_id: str
    token: contextvars.Token


_CONTEXT: contextvars.ContextVar[Optional[dict[str, Any]]] = contextvars.ContextVar(
    "nex5_influence_trace_context", default=None
)
_LOCK = threading.Lock()


def enabled() -> bool:
    """Tracing requires an explicit ON flag and an explicit external artifact path."""
    return os.environ.get("NEX5_TRACE_OVERLAY", "0") == "1" and bool(
        os.environ.get("NEX5_TRACE_PATH", "").strip()
    )


def _digest(payload: Any) -> Optional[str]:
    if payload is None:
        return None
    try:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            default=str,
        ).encode("utf-8")
    except Exception:
        encoded = repr(type(payload)).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _append(path: str, record: dict[str, Any]) -> bool:
    try:
        line = json.dumps(record, sort_keys=True, ensure_ascii=False, default=str)
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)
        with _LOCK:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        return True
    except Exception:
        # Observability failure must never affect the cognitive path.
        return False


def begin_trace(
    trace_kind: str,
    *,
    source_ref: str,
    entity_ref: Optional[str] = None,
    payload: Any = None,
    path: Optional[str] = None,
) -> Optional[TraceHandle]:
    """Begin a trace only when explicitly enabled and an artifact path is known.

    The optional path parameter exists for isolated tests. Runtime callers should
    use NEX5_TRACE_PATH so the artifact destination is explicit and reviewable.
    """
    if os.environ.get("NEX5_TRACE_OVERLAY", "0") != "1":
        return None
    target = path or os.environ.get("NEX5_TRACE_PATH", "").strip()
    if not target:
        return None

    trace_id = uuid.uuid4().hex
    state = {
        "trace_id": trace_id,
        "trace_kind": str(trace_kind),
        "path": target,
        "last_record_id": None,
    }
    token = _CONTEXT.set(state)
    handle = TraceHandle(trace_id=trace_id, token=token)
    record(
        "trace_start",
        producer="trace_overlay",
        source_ref=source_ref,
        entity_ref=entity_ref,
        payload=payload,
        outcome="started",
    )
    return handle


def record(
    event_type: str,
    *,
    producer: str,
    source_ref: str,
    consumer: Optional[str] = None,
    outcome: Optional[str] = None,
    entity_ref: Optional[str] = None,
    payload: Any = None,
    parent_ids: Optional[list[str]] = None,
) -> Optional[str]:
    """Append one metadata-only observation and return its record ID.

    Payload is hashed and discarded. Parent IDs default to the previous
    successfully written record in this trace; callers may supply explicit
    parents when a real multi-parent dependency is known.
    """
    state = _CONTEXT.get()
    if state is None:
        return None
    record_id = uuid.uuid4().hex
    if parent_ids is None:
        last = state.get("last_record_id")
        parents = [last] if last else []
    else:
        parents = [str(value) for value in parent_ids if value]
    item = {
        "schema": "nex5/influence-record/v1",
        "trace_id": state["trace_id"],
        "trace_kind": state["trace_kind"],
        "record_id": record_id,
        "parent_ids": parents,
        "event_type": str(event_type),
        "producer": str(producer),
        "consumer": str(consumer) if consumer else None,
        "source_ref": str(source_ref),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "monotonic_ns": time.monotonic_ns(),
        "entity_ref": str(entity_ref) if entity_ref is not None else None,
        "outcome": str(outcome) if outcome is not None else None,
        "payload_digest": _digest(payload),
        "flag_state": True,
    }
    if not _append(state["path"], item):
        return None
    state["last_record_id"] = record_id
    return record_id


def end_trace(
    handle: Optional[TraceHandle],
    *,
    source_ref: str,
    entity_ref: Optional[str] = None,
    outcome: str = "completed",
    payload: Any = None,
) -> None:
    """Record a terminal observation and restore any enclosing context."""
    if handle is None:
        return
    try:
        record(
            "trace_end",
            producer="trace_overlay",
            source_ref=source_ref,
            entity_ref=entity_ref,
            outcome=outcome,
            payload=payload,
        )
    finally:
        try:
            _CONTEXT.reset(handle.token)
        except Exception:
            pass
