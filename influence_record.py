"""InfluenceRecord — Phase 0 default-OFF causal-trace overlay.

Master Roadmap v3.0 Phase 0 (Reality Audit & End-to-End Causal Trace), deliverable
M0.5. Records, for a single produced output — a Fountain *fire* or a Chat *turn* —
the observable inputs that influenced it, as an append-only JSONL trace, so a
produced output can later be read back to the inputs that shaped it.

GOVERNING-DOCUMENT NOTE
-----------------------
The "NEX v5.0 Master Technical, Research & Commercialization Roadmap v3.0" is NOT
resident in this repository. This module therefore implements the *stated*
Phase-0 constraints (minimal, default-OFF, zero behavioural delta, runtime
evidence kept explicitly UNKNOWN) and reuses the existing Watcher evidence
vocabulary for its L-ladder, rather than reproducing a spec text we do not hold.
Field-level requirements that would come from the governing PDF are flagged
`unresolved` in each record, not invented.

CONTRACT (the whole point of a Phase-0 instrumentation overlay)
---------------------------------------------------------------
  * DEFAULT OFF.  With ``NEX5_INFLUENCE_TRACE`` unset or false, every entry point
    is a no-op that touches nothing, writes nothing, and returns ``None``
    immediately.  => zero behavioural delta against the un-instrumented system.
  * SIDE-CHANNEL ONLY.  It never writes to a live NEX database, never mutates any
    value it observes, never reads a flag or live table, never changes behaviour.
    Its ONLY effect, and ONLY when enabled, is appending one line to a dedicated
    trace file (``NEX5_INFLUENCE_TRACE_PATH``, default ``<repo>/logs/
    influence_trace.jsonl``) — never one of the six substrate DBs.
  * NO NEW READS.  The producer seam hands the tracer values it already has in
    scope (the output text, the input prompt, mode/readiness scalars).  The
    tracer does not traverse readers or call back into the system, so it cannot
    add a query, a cost, or a side effect to the traced path.
  * FAIL-SAFE.  Any error inside the overlay is swallowed; it can never break the
    path it observes.

EVIDENCE LADDER (L0–L4), grounded in the Watcher ``evidence_class`` vocabulary
-----------------------------------------------------------------------------
  L0 UNKNOWN   — no evidence (Watcher: unknown)
  L1 INFERRED  — indirect / heuristic (Watcher: inferred)
  L2 STATIC    — present in source/state, not observed acting (Watcher: static)
  L3 OBSERVED  — observed in an instrumented/controlled path, e.g. a test fixture
                 (Watcher: implemented / measured-in-test)
  L4 RUNTIME   — observed in the LIVE runtime (Watcher: measured / runtime_observed)

L4 is asserted ONLY when the live process runs the overlay with
``NEX5_INFLUENCE_TRACE_CONTEXT=runtime`` (which requires founder authorisation to
enable on the live NEX).  Until then every value this overlay can capture is at
most L3, and L4 is explicitly UNKNOWN — consistent with "keep unknown runtime
evidence explicitly UNKNOWN".
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

THEORY_X_STAGE = None  # cross-cutting overlay; not a Theory-X stage node

SCHEMA = "influence_record/v1"

_REPO_ROOT = Path(__file__).resolve().parent

# ---- evidence ladder -------------------------------------------------------
L0_UNKNOWN = "L0"
L1_INFERRED = "L1"
L2_STATIC = "L2"
L3_OBSERVED = "L3"
L4_RUNTIME = "L4"

# L-level <-> Watcher evidence_class, so the two taxonomies stay reconcilable.
L_TO_EVIDENCE_CLASS = {
    L0_UNKNOWN: "unknown",
    L1_INFERRED: "inferred",
    L2_STATIC: "static",
    L3_OBSERVED: "implemented",
    L4_RUNTIME: "measured",
}

_TRUTHY = frozenset({"1", "true", "on", "yes", "y"})


def _env_enabled() -> bool:
    return str(os.environ.get("NEX5_INFLUENCE_TRACE", "")).strip().lower() in _TRUTHY


def _env_context() -> str:
    """'runtime' only when the live process declares it; else 'fixture'."""
    ctx = str(os.environ.get("NEX5_INFLUENCE_TRACE_CONTEXT", "fixture")).strip().lower()
    return "runtime" if ctx == "runtime" else "fixture"


def _default_sink_path() -> Path:
    override = os.environ.get("NEX5_INFLUENCE_TRACE_PATH")
    if override:
        return Path(override)
    return _REPO_ROOT / "logs" / "influence_trace.jsonl"


def _digest(value) -> str:
    """Short, stable content digest. Never stores the raw value for large text."""
    try:
        raw = value if isinstance(value, (bytes, bytearray)) else str(value).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()[:16]
    except Exception:
        return "sha256:unknown"


def _preview(text, limit: int = 160) -> str:
    try:
        s = str(text).replace("\n", " ").strip()
        return s if len(s) <= limit else s[:limit] + "…"
    except Exception:
        return ""


@dataclass
class InfluenceEntry:
    """One input that influenced the output."""
    source: str                       # e.g. "fountain.beliefs_store", "chat.prompt"
    kind: str                         # e.g. "retrieval_surface", "user_message", "mode"
    evidence_level: str               # L0..L4
    value_digest: str = ""            # content digest of the observed value
    value_preview: str = ""           # short, human-readable preview (may be "")
    source_ref: str = ""              # file:line or table that produced it
    note: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["evidence_class"] = L_TO_EVIDENCE_CLASS.get(self.evidence_level, "unknown")
        return d


@dataclass
class InfluenceRecord:
    produced: str                     # "fountain_fire" | "chat_turn"
    output_kind: str                  # "thought" | "reply"
    output_digest: str
    output_length: int
    output_preview: str
    inputs: list                      # list[InfluenceEntry]
    cycle_id: Optional[str] = None
    capture_context: str = "fixture"  # "fixture" | "runtime"
    timestamp: float = field(default_factory=time.time)
    schema: str = SCHEMA
    unresolved: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "schema": self.schema,
            "produced": self.produced,
            "cycle_id": self.cycle_id,
            "capture_context": self.capture_context,
            "timestamp": self.timestamp,
            "output": {
                "kind": self.output_kind,
                "digest": self.output_digest,
                "length": self.output_length,
                "preview": self.output_preview,
            },
            "inputs": [e.to_dict() for e in self.inputs],
            "unresolved": list(self.unresolved),
        }


class InfluenceTracer:
    """Default-OFF, side-channel, fail-safe causal-trace recorder.

    All public ``record_*`` methods return ``None`` and do nothing when disabled.
    When enabled they append exactly one JSONL line to the sink and return the
    record dict (handy for tests / live capture); they never raise.
    """

    def __init__(self, sink_path=None, enabled: Optional[bool] = None,
                 context: Optional[str] = None, clock=None):
        self._sink_path = Path(sink_path) if sink_path is not None else None
        self._enabled_override = enabled
        self._context_override = context
        self._clock = clock or time.time
        self._lock = threading.Lock()

    # -- configuration (read at use time, so env can flip without re-import) --
    @property
    def enabled(self) -> bool:
        if self._enabled_override is not None:
            return bool(self._enabled_override)
        return _env_enabled()

    @property
    def context(self) -> str:
        if self._context_override is not None:
            return self._context_override
        return _env_context()

    @property
    def sink_path(self) -> Path:
        return self._sink_path if self._sink_path is not None else _default_sink_path()

    def _observed_level(self) -> str:
        """The strongest level this overlay may assert for a directly-observed
        value: L4 only in the declared live runtime, else L3."""
        return L4_RUNTIME if self.context == "runtime" else L3_OBSERVED

    def _append(self, record: InfluenceRecord) -> Optional[dict]:
        try:
            payload = record.to_dict()
            path = self.sink_path
            path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(payload, ensure_ascii=False, default=str)
            with self._lock:
                with open(path, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            return payload
        except Exception:
            return None  # fail-safe: never break the traced path

    # ---------------------------------------------------------------- fountain
    def record_fountain_fire(self, output, *, cycle_id=None, mode_name=None,
                             readiness=None, last_fire_ts=None, total_fires=None,
                             extra_inputs=None) -> Optional[dict]:
        """Record one Fountain fire. ``output`` is the thought string the
        generator returned (may be None when no fire happened — then we skip)."""
        if not self.enabled:
            return None
        try:
            if output is None:
                return None  # no fire this tick -> nothing was produced
            lvl = self._observed_level()
            inputs = [
                InfluenceEntry(
                    source="fountain.mode_state", kind="mode",
                    evidence_level=(lvl if mode_name is not None else L0_UNKNOWN),
                    value_preview=_preview(mode_name),
                    source_ref="theory_x/stage6_fountain/__init__.py:fountain_loop",
                ),
                InfluenceEntry(
                    source="fountain.readiness", kind="readiness_score",
                    evidence_level=(lvl if readiness is not None else L0_UNKNOWN),
                    value_preview=_preview(readiness),
                    source_ref="theory_x/stage6_fountain/readiness.py",
                ),
                InfluenceEntry(
                    source="fountain.timing", kind="last_fire_ts",
                    evidence_level=(lvl if last_fire_ts is not None else L0_UNKNOWN),
                    value_preview=_preview(last_fire_ts),
                    source_ref="theory_x/stage6_fountain/generator.py",
                ),
            ]
            for e in (extra_inputs or []):
                if isinstance(e, InfluenceEntry):
                    inputs.append(e)
            rec = InfluenceRecord(
                produced="fountain_fire",
                output_kind="thought",
                output_digest=_digest(output),
                output_length=len(str(output)),
                output_preview=_preview(output),
                inputs=inputs,
                cycle_id=cycle_id if cycle_id is not None else _fire_cycle_id(total_fires),
                capture_context=self.context,
                timestamp=self._clock(),
                unresolved=[
                    "belief-level attribution (which stored beliefs the generator "
                    "retrieved for this fire) requires a deeper hook inside "
                    "FountainGenerator.generate(); recorded here as L0/UNKNOWN.",
                ],
            )
            return self._append(rec)
        except Exception:
            return None

    # -------------------------------------------------------------------- chat
    def record_chat_turn(self, *, prompt, reply, register=None, session_id=None,
                         voice_ok=None, tool_used=None, cycle_id=None,
                         extra_inputs=None) -> Optional[dict]:
        """Record one Chat turn. ``reply`` is the final sanitised reply text."""
        if not self.enabled:
            return None
        try:
            if reply is None:
                return None
            lvl = self._observed_level()
            inputs = [
                InfluenceEntry(
                    source="chat.prompt", kind="user_message",
                    evidence_level=lvl,
                    value_digest=_digest(prompt), value_preview=_preview(prompt),
                    source_ref="gui/server.py:api_chat",
                ),
                InfluenceEntry(
                    source="chat.register", kind="register",
                    evidence_level=(lvl if register is not None else L0_UNKNOWN),
                    value_preview=_preview(register),
                    source_ref="gui/server.py:api_chat",
                ),
                InfluenceEntry(
                    source="chat.tool_used", kind="tool_result",
                    evidence_level=(lvl if tool_used is not None else L0_UNKNOWN),
                    value_preview=_preview(tool_used),
                    source_ref="gui/server.py:api_chat",
                ),
                InfluenceEntry(
                    source="chat.voice_ok", kind="voice_reachable",
                    evidence_level=(lvl if voice_ok is not None else L0_UNKNOWN),
                    value_preview=_preview(voice_ok),
                    source_ref="voice/llm.py",
                ),
            ]
            for e in (extra_inputs or []):
                if isinstance(e, InfluenceEntry):
                    inputs.append(e)
            rec = InfluenceRecord(
                produced="chat_turn",
                output_kind="reply",
                output_digest=_digest(reply),
                output_length=len(str(reply)),
                output_preview=_preview(reply),
                inputs=inputs,
                cycle_id=cycle_id if cycle_id is not None else (
                    f"chat:{session_id}" if session_id is not None else None),
                capture_context=self.context,
                timestamp=self._clock(),
                unresolved=[
                    "faculty-block attribution (which of the ~13 assembled chat "
                    "blocks shaped the reply) requires a deeper hook in "
                    "_assemble_chat_blocks(); recorded here as L0/UNKNOWN.",
                ],
            )
            return self._append(rec)
        except Exception:
            return None


def _fire_cycle_id(total_fires) -> Optional[str]:
    try:
        return f"fire:{int(total_fires)}" if total_fires is not None else None
    except Exception:
        return None


# ---- module-level singleton (what the producer seams call) -----------------
_singleton: Optional[InfluenceTracer] = None
_singleton_lock = threading.Lock()


def tracer() -> InfluenceTracer:
    """The process-wide tracer. Cheap to call on every fire/turn; config is read
    at use time so the env flag governs behaviour without a re-import."""
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = InfluenceTracer()
    return _singleton


def set_tracer(t: Optional[InfluenceTracer]) -> None:
    """Install a tracer (tests). ``None`` resets to a fresh default."""
    global _singleton
    with _singleton_lock:
        _singleton = t


def reset_tracer() -> None:
    set_tracer(None)
