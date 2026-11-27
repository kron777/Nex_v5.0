"""Phase 0 read-only causal trace overlay (M0.5).

The overlay is explicitly default-OFF under NEX5_TRACE_OVERLAY=0. When enabled,
it writes append-only JSONL events to a dedicated .jsonl sidecar (never a NEX
SQLite database). It does not read databases, mutate prompts/candidates, change
selection order, or participate in any decision.

Each trace event has a trace_id, event_id and parent_ids. Callers pass values
already in scope. Text is represented by a SHA-256 digest and UTF-8 byte length;
raw prompt, belief, output and payload text are never persisted.

Evidence is L3 (observed in a fixture/test) by default. L4 is emitted only when
NEX5_TRACE_OVERLAY_CONTEXT=runtime is explicitly set by an authorised live run.
This module does not enable that setting or assert that a live run occurred.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Optional

SCHEMA = "nex_causal_trace/v1"
_REPO_ROOT = Path(__file__).resolve().parent
_FILE_LOCK = threading.Lock()
_TRUTHY = frozenset({"1", "true", "on", "yes", "y"})

# Generic event metadata is deliberately defensive. These keys are always
# replaced with digest/length pairs when a caller accidentally passes text.
_TEXT_KEYS = frozenset({
    "prompt", "thought", "content", "text", "reply", "output", "payload",
    "belief_text", "raw", "raw_output", "system_prompt",
    "voice_prompt", "before", "after", "query", "message", "answer",
    "input", "output", "focal_item", "tool_output", "result_text",
    "candidate_texts", "prompt_text",
})

# Metadata strings are private by default. Preserve only bounded categorical
# labels and identifiers whose semantics are defined by the trace contract.
_SAFE_LABEL_KEYS = frozenset({
    "source", "database", "table", "operation", "status", "transaction_scope",
    "gate", "decision", "reason_code", "strategy", "stage", "event",
    "candidate_kinds", "candidate_order", "selected_order", "retrieval_slots",
    "branch_hints", "side", "register", "register_hint", "mode", "path",
    "stream", "selection_rule", "purpose", "output_kind", "capture_context",
    "error_type", "trigger_type", "role", "tool_name", "category",
    "sha256", "value_type", "winner_kind", "crystallizer_path", "source_node",
    "assistant_store_status",
})


def overlay_enabled() -> bool:
    """Return the explicit overlay switch; unset and '0' are OFF."""
    value = str(os.environ.get("NEX5_TRACE_OVERLAY", "0")).strip().lower()
    return value in _TRUTHY


def _digest(value: Any) -> str:
    try:
        raw = value if isinstance(value, bytes) else str(value).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()
    except Exception:
        return "sha256:unavailable"


def _safe_metadata(value: Any, key: str = "", depth: int = 0) -> Any:
    """Bound metadata size and hash any value under a text-bearing key."""
    if depth > 5:
        return "[depth-limited]"
    if key.lower() in _TEXT_KEYS and value is not None:
        if isinstance(value, bytes):
            raw = value
        elif isinstance(value, str):
            raw = value.encode("utf-8", errors="replace")
        else:
            raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode(
                "utf-8", errors="replace"
            )
        return {"sha256": _digest(raw), "length": len(raw),
                "value_type": type(value).__name__}
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        if key.lower() in _SAFE_LABEL_KEYS:
            return value[:160]
        raw = value.encode("utf-8", errors="replace")
        return {"sha256": _digest(raw), "length": len(raw), "value_type": "str"}
    if isinstance(value, bytes):
        return {"sha256": _digest(value), "length": len(value), "value_type": "bytes"}
    if isinstance(value, (list, tuple, set, frozenset)):
        items = list(value)
        return [
            _safe_metadata(item, key=key, depth=depth + 1)
            for item in items[:200]
        ]
    if isinstance(value, dict):
        result = {}
        for index, (child_key, child_value) in enumerate(value.items()):
            if index >= 100:
                result["_truncated"] = True
                break
            safe_key = str(child_key)[:100]
            result[safe_key] = _safe_metadata(child_value, safe_key, depth + 1)
        return result
    # Do not repr arbitrary objects: repr can expose large or sensitive content.
    return {"type": type(value).__name__}


class TraceContext:
    """Parent-linked, fail-safe trace writer for one Fountain cycle or Chat turn."""

    def __init__(
        self,
        producer: str,
        *,
        sink_path: Optional[str | Path] = None,
        context: str = "fixture",
        enabled: bool = True,
        trace_id: Optional[str] = None,
        clock=None,
    ) -> None:
        self.producer = str(producer)[:80]
        self.trace_id = trace_id or uuid.uuid4().hex
        self.context = "runtime" if context == "runtime" else "fixture"
        self.evidence_level = "L4" if self.context == "runtime" else "L3"
        self._enabled = bool(enabled)
        self._clock = clock or time.time
        self._sink_path = Path(sink_path) if sink_path is not None else self._default_sink()
        self._sequence = 0
        self._events: list[dict] = []
        self._references: dict[str, str] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _default_sink() -> Path:
        override = os.environ.get("NEX5_TRACE_OVERLAY_PATH")
        if override:
            return Path(override)
        return _REPO_ROOT / "logs" / "nex_causal_trace.jsonl"

    def _safe_sink(self) -> bool:
        """Reject non-JSONL paths, symlinks, and paths aliasing a substrate DB.

        Path metadata checks do not open or query any database. Refusing
        symlinks also prevents an innocently named .jsonl path from following
        a link into one of the six live substrate files.
        """
        try:
            if self._sink_path.suffix.lower() != ".jsonl" or self._sink_path.is_symlink():
                return False
            from substrate.paths import db_paths
            target = self._sink_path.resolve(strict=False)
            for database_path in db_paths().values():
                database = Path(database_path)
                if target == database.resolve(strict=False):
                    return False
                if self._sink_path.exists() and database.exists():
                    if self._sink_path.samefile(database):
                        return False
            return True
        except Exception:
            # Unknown path-safety state is not permission to write.
            return False

    @property
    def events(self) -> tuple[dict, ...]:
        """An immutable snapshot of events recorded by this context."""
        with self._lock:
            return tuple(dict(item) for item in self._events)

    def remember(self, name: str, event_id: Optional[str]) -> None:
        """Retain an explicitly named event reference for a later causal edge."""
        if not self._enabled or not event_id:
            return
        try:
            key = str(name).strip()[:80]
            if key:
                with self._lock:
                    self._references[key] = str(event_id)
        except Exception:
            return

    def reference(self, name: str) -> Optional[str]:
        """Return a previously remembered event ID; no parent is inferred."""
        if not self._enabled:
            return None
        try:
            with self._lock:
                return self._references.get(str(name).strip()[:80])
        except Exception:
            return None

    def record(
        self,
        stage: str,
        event: str,
        *,
        parent_ids: Optional[list[str] | tuple[str, ...]] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[str]:
        """Append one event and return its ID; fail-safe and no-op when disabled."""
        if not self._enabled:
            return None
        try:
            with self._lock:
                self._sequence += 1
                event_id = uuid.uuid4().hex
                parents = [str(item) for item in (parent_ids or []) if item][:100]
                safe = _safe_metadata(metadata or {})
                record = {
                    "schema": SCHEMA,
                    "trace_id": self.trace_id,
                    "event_id": event_id,
                    "parent_ids": parents,
                    "sequence": self._sequence,
                    "producer": self.producer,
                    "stage": str(stage)[:80],
                    "event": str(event)[:100],
                    "timestamp": float(self._clock()),
                    "evidence_level": self.evidence_level,
                    "evidence_class": "measured" if self.evidence_level == "L4" else "implemented",
                    "capture_context": self.context,
                    "metadata": safe if isinstance(safe, dict) else {"value": safe},
                }
                # Sidecar-only path guard: extension, symlink and substrate identity.
                if not self._safe_sink():
                    return None
                line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
                self._sink_path.parent.mkdir(parents=True, exist_ok=True)
                with _FILE_LOCK:
                    with self._sink_path.open("a", encoding="utf-8") as stream:
                        stream.write(line)
                self._events.append(record)
                if stage == "input_arrival" and "input_arrival" not in self._references:
                    self._references["input_arrival"] = event_id
                return event_id
        except Exception:
            # Observability must never break the path it observes.
            return None

    def input(self, text: str, *, source: str, metadata: Optional[dict] = None,
              parent_ids: Optional[list[str] | tuple[str, ...]] = None) -> Optional[str]:
        if not self._enabled:
            return None
        raw = (text or "").encode("utf-8", errors="replace")
        details = dict(metadata or {})
        details.update({"source": source, "sha256": _digest(raw), "length": len(raw)})
        return self.record("input_arrival", "received", metadata=details,
                           parent_ids=parent_ids)

    def candidates(
        self,
        candidate_ids,
        *,
        source: str,
        candidate_kinds=None,
        metadata: Optional[dict] = None,
        parent_ids: Optional[list[str] | tuple[str, ...]] = None,
    ) -> Optional[str]:
        if not self._enabled:
            return None
        details = dict(metadata or {})
        details.update({
            "source": source,
            "candidate_ids": list(candidate_ids or []),
            "candidate_kinds": list(candidate_kinds or []),
            "candidate_count": len(candidate_ids or []),
        })
        return self.record("candidate_generation", "candidates_selected",
                           metadata=details, parent_ids=parent_ids)

    def selection(
        self,
        *,
        source: str,
        candidate_order,
        selected_order,
        strategy: str,
        metadata: Optional[dict] = None,
        parent_ids: Optional[list[str] | tuple[str, ...]] = None,
    ) -> Optional[str]:
        if not self._enabled:
            return None
        details = dict(metadata or {})
        details.update({
            "source": source,
            "candidate_order": list(candidate_order or []),
            "selected_order": list(selected_order or []),
            "strategy": strategy,
        })
        return self.record("salience_workspace", "selection_recorded",
                           metadata=details, parent_ids=parent_ids)

    def gate(
        self,
        decision: str,
        *,
        gate: str,
        reason_code: Optional[str] = None,
        metadata: Optional[dict] = None,
        parent_ids: Optional[list[str] | tuple[str, ...]] = None,
    ) -> Optional[str]:
        if not self._enabled:
            return None
        details = dict(metadata or {})
        details.update({"gate": gate, "decision": decision, "reason_code": reason_code})
        return self.record("gate", "decision", metadata=details,
                           parent_ids=parent_ids)

    def writer_delta(
        self,
        *,
        database: str,
        table: str,
        operation: str,
        row_id=None,
        status: str = "committed",
        metadata: Optional[dict] = None,
        parent_ids: Optional[list[str] | tuple[str, ...]] = None,
    ) -> Optional[str]:
        if not self._enabled:
            return None
        details = dict(metadata or {})
        details.update({
            "database": database,
            "table": table,
            "operation": operation,
            "row_id": row_id,
            "status": status,
            "transaction_scope": (
                "single_database_atomic_write_many"
                if operation == "WRITE_MANY"
                else "single_statement_single_database"
            ),
        })
        return self.record("sqlite_writer_delta", "write_result",
                           metadata=details, parent_ids=parent_ids)

    def output(
        self,
        text: Optional[str],
        *,
        output_kind: str,
        status: str = "produced",
        metadata: Optional[dict] = None,
        parent_ids: Optional[list[str] | tuple[str, ...]] = None,
    ) -> Optional[str]:
        if not self._enabled:
            return None
        details = dict(metadata or {})
        if text is not None:
            raw = str(text).encode("utf-8", errors="replace")
            details.update({"sha256": _digest(raw), "length": len(raw)})
        else:
            details.update({"sha256": None, "length": 0})
        details.update({"output_kind": output_kind, "status": status})
        return self.record("output", "result", metadata=details,
                           parent_ids=parent_ids)


def new_trace(
    producer: str,
    *,
    context: Optional[str] = None,
    sink_path: Optional[str | Path] = None,
) -> Optional[TraceContext]:
    """Create a trace context only when NEX5_TRACE_OVERLAY is explicitly truthy."""
    if not overlay_enabled():
        return None
    capture_context = context or os.environ.get("NEX5_TRACE_OVERLAY_CONTEXT", "fixture")
    context_obj = TraceContext(
        producer,
        sink_path=sink_path,
        context=capture_context,
        enabled=True,
    )
    # Reject unsafe sinks before a producer sees a non-None trace context.
    # This preserves the original call shape when instrumentation cannot write.
    return context_obj if context_obj._safe_sink() else None
