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
    if key.lower() in _TEXT_KEYS and isinstance(value, (str, bytes)):
        raw = value if isinstance(value, bytes) else value.encode("utf-8", errors="replace")
        return {"sha256": _digest(raw), "length": len(raw)}
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:160]
    if isinstance(value, bytes):
        return {"sha256": _digest(value), "length": len(value)}
    if isinstance(value, (list, tuple, set, frozenset)):
        items = list(value)
        return [_safe_metadata(item, depth=depth + 1) for item in items[:200]]
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
        self._last_event_id: Optional[str] = None
        self._sequence = 0
        self._events: list[dict] = []
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
                if parent_ids is None:
                    parents = [self._last_event_id] if self._last_event_id else []
                else:
                    parents = [str(item) for item in parent_ids if item][:100]
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
                self._last_event_id = event_id
                return event_id
        except Exception:
            # Observability must never break the path it observes.
            return None

    def input(self, text: str, *, source: str, metadata: Optional[dict] = None) -> Optional[str]:
        raw = (text or "").encode("utf-8", errors="replace")
        details = dict(metadata or {})
        details.update({"source": source, "sha256": _digest(raw), "length": len(raw)})
        return self.record("input_arrival", "received", metadata=details)

    def candidates(
        self,
        candidate_ids,
        *,
        source: str,
        candidate_kinds=None,
        metadata: Optional[dict] = None,
    ) -> Optional[str]:
        details = dict(metadata or {})
        details.update({
            "source": source,
            "candidate_ids": list(candidate_ids or []),
            "candidate_kinds": list(candidate_kinds or []),
            "candidate_count": len(candidate_ids or []),
        })
        return self.record("candidate_generation", "candidates_selected", metadata=details)

    def selection(
        self,
        *,
        source: str,
        candidate_order,
        selected_order,
        strategy: str,
        metadata: Optional[dict] = None,
    ) -> Optional[str]:
        details = dict(metadata or {})
        details.update({
            "source": source,
            "candidate_order": list(candidate_order or []),
            "selected_order": list(selected_order or []),
            "strategy": strategy,
        })
        return self.record("salience_workspace", "selection_recorded", metadata=details)

    def gate(
        self,
        decision: str,
        *,
        gate: str,
        reason_code: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[str]:
        details = dict(metadata or {})
        details.update({"gate": gate, "decision": decision, "reason_code": reason_code})
        return self.record("gate", "decision", metadata=details)

    def writer_delta(
        self,
        *,
        database: str,
        table: str,
        operation: str,
        row_id=None,
        status: str = "committed",
        metadata: Optional[dict] = None,
    ) -> Optional[str]:
        details = dict(metadata or {})
        details.update({
            "database": database,
            "table": table,
            "operation": operation,
            "row_id": row_id,
            "status": status,
            "transaction_scope": "single_statement_single_database",
        })
        return self.record("sqlite_writer_delta", "write_result", metadata=details)

    def output(
        self,
        text: Optional[str],
        *,
        output_kind: str,
        status: str = "produced",
        metadata: Optional[dict] = None,
    ) -> Optional[str]:
        details = dict(metadata or {})
        if text is not None:
            raw = str(text).encode("utf-8", errors="replace")
            details.update({"sha256": _digest(raw), "length": len(raw)})
        else:
            details.update({"sha256": None, "length": 0})
        details.update({"output_kind": output_kind, "status": status})
        return self.record("output", "result", metadata=details)


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
    return TraceContext(
        producer,
        sink_path=sink_path,
        context=capture_context,
        enabled=True,
    )
