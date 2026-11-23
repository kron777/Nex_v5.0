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
# Bounded hand-off registry for asynchronous consumers (e.g. speech queue).
# It stores trace provenance only; it never touches NEX databases.
_EXTERNAL_PARENTS: dict[str, dict[str, str]] = {}
_EXTERNAL_PARENT_LIMIT = 4096
_REPO_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))


def enabled() -> bool:
    """Tracing requires an explicit ON flag and an explicit external artifact path."""
    return os.environ.get("NEX5_TRACE_OVERLAY", "0") == "1" and bool(
        os.environ.get("NEX5_TRACE_PATH", "").strip()
    )


def _external_jsonl_path(path: str) -> Optional[str]:
    """Reject non-JSONL paths and artifacts inside the configured NEX data tree."""
    try:
        target = os.path.realpath(path)
        if not target.lower().endswith(".jsonl"):
            return None
        data_root = os.path.realpath(os.environ.get(
            "NEX5_DATA_DIR", os.path.join(_REPO_ROOT, "data")
        ))
        protected_roots = [data_root, _REPO_ROOT]
        for flag in ("NEX5_BELIEFS_DB", "NEX5_DYNAMIC_DB", "NEX5_CONV_DB"):
            db_path = os.environ.get(flag)
            if db_path:
                protected_roots.append(os.path.realpath(os.path.dirname(db_path)))
        for root in protected_roots:
            if os.path.commonpath((target, root)) == root:
                return None
        return target
    except (OSError, ValueError):
        return None


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
            # Trace artifacts may contain stable entity IDs and timing metadata.
            # Create and retain them as owner-only files, independent of umask.
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            try:
                os.fchmod(fd, 0o600)
                with os.fdopen(fd, "a", encoding="utf-8") as fh:
                    fd = -1
                    fh.write(line + "\n")
            finally:
                if fd >= 0:
                    os.close(fd)
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
    parent_record_id: Optional[str] = None,
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
    target = _external_jsonl_path(target)
    if target is None:
        return None

    trace_id = uuid.uuid4().hex
    state = {
        "parent_context": _CONTEXT.get(),
        "trace_id": trace_id,
        "trace_kind": str(trace_kind),
        "path": target,
        "initial_parent_record_id": str(parent_record_id) if parent_record_id else None,
    }
    token = _CONTEXT.set(state)
    handle = TraceHandle(trace_id=trace_id, token=token)
    start_parents = [str(parent_record_id)] if parent_record_id else []
    record(
        "trace_start",
        producer="trace_overlay",
        source_ref=source_ref,
        entity_ref=entity_ref,
        payload=payload,
        outcome="started",
        parent_ids=start_parents,
    )
    return handle


def link_entity(entity_ref: str, record_id: str) -> bool:
    """Attach a persisted entity identity to its producing trace record.

    Used only to bridge an asynchronous boundary where ContextVars do not
    propagate (for example, Fountain enqueue -> SpeechQueueConsumer thread).
    The consumer later opens a new trace whose first record names this record
    as its parent. The hand-off is process-local, bounded, and observational.
    """
    state = _CONTEXT.get()
    if (not enabled() or state is None or not entity_ref or not record_id):
        return False
    try:
        with _LOCK:
            _EXTERNAL_PARENTS[str(entity_ref)] = {
                "record_id": str(record_id),
                "path": str(state["path"]),
            }
            while len(_EXTERNAL_PARENTS) > _EXTERNAL_PARENT_LIMIT:
                _EXTERNAL_PARENTS.pop(next(iter(_EXTERNAL_PARENTS)))
        return True
    except Exception:
        return False


def begin_linked_trace(
    trace_kind: str,
    *,
    source_ref: str,
    entity_ref: str,
    payload: Any = None,
) -> Optional[TraceHandle]:
    """Begin a consumer trace linked to a producer record by entity identity.

    If no in-process producer link exists (e.g. the queue survived a restart),
    fall back to an ordinary root trace rather than inventing provenance.
    """
    if not enabled():
        return None
    try:
        with _LOCK:
            parent = _EXTERNAL_PARENTS.pop(str(entity_ref), None)
        if parent is None:
            return begin_trace(
                trace_kind,
                source_ref=source_ref,
                entity_ref=entity_ref,
                payload=payload,
            )
        return begin_trace(
            trace_kind,
            source_ref=source_ref,
            entity_ref=entity_ref,
            payload=payload,
            path=parent["path"],
            parent_record_id=parent["record_id"],
        )
    except Exception:
        return None


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

    Payload is hashed and discarded. Parent IDs are explicit: when omitted,
    the observation has no asserted causal parent. Chronological ordering is
    represented by the artifact's record order and timestamps, not by
    manufacturing a causal edge to the preceding observation.
    """
    state = _CONTEXT.get()
    if state is None or os.environ.get("NEX5_TRACE_OVERLAY", "0") != "1":
        return None
    record_id = uuid.uuid4().hex
    parents = [str(value) for value in (parent_ids or []) if value]
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
    return record_id


def close_current_trace(
    *,
    source_ref: str,
    outcome: str = "request_teardown",
) -> None:
    """Fail-safe cleanup for request/thread teardown after an unexpected exit."""
    state = _CONTEXT.get()
    if state is None:
        return
    try:
        record(
            "trace_end",
            producer="trace_overlay",
            source_ref=source_ref,
            outcome=outcome,
        )
    finally:
        _CONTEXT.set(state.get("parent_context"))


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
