"""Evidence model for system-level feedback-loop stability.

A graph cycle is topology, not a stability verdict. This record captures the
measurements needed to investigate a loop without assuming that feedback is
harmful or that a loop should be removed. It deliberately performs no stability
calculation and defaults all conclusions to UNKNOWN.
"""
from __future__ import annotations

import dataclasses
import fcntl
import hashlib
import json
import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from watcher.evidence import utc_now

from .model import InterfaceEvidence, _has_traceable_evidence

STABILITY_STATES = ("stable", "unstable", "conditionally_stable")
UNKNOWN = "unknown"
MEASURED_DIMENSIONS = (
    "gain", "delay", "damping", "oscillation", "overshoot", "recovery",
    "observation_window",
)
OPERATING_ENVELOPES = ("normal", "busy", "degraded", "stress", "recovery", UNKNOWN)
_EVENT_SCHEMA = "rdo.feedback_loop_evidence.v1"


def _text(value: Any, name: str, maximum: int = 2000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{name} must be non-blank text of at most {maximum} characters")
    return value.strip()


def _references(value: Any, name: str) -> List[str]:
    if not _has_traceable_evidence(value):
        raise ValueError(f"{name} must contain non-blank evidence references")
    return list(dict.fromkeys(item.strip() for item in value))


def _finite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, TypeError, ValueError):
        return False


def _validate_measured_dimension(evidence: InterfaceEvidence, name: str) -> None:
    if not _finite_number(evidence.value):
        raise ValueError(f"measured feedback dimension {name!r} requires a finite numeric value")
    _text(evidence.unit, f"{name}.unit", 128)
    _references(evidence.evidence, f"{name}.evidence")
    _text(evidence.confidence, f"{name}.confidence", 128)


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _event_digest(event: dict) -> str:
    return hashlib.sha256(_canonical({
        key: value for key, value in event.items() if key != "event_sha256"
    })).hexdigest()


@dataclasses.dataclass
class FeedbackLoopAssessment:
    """Evidence record for one identified feedback loop.

    Members and relationships identify the loop under observation. Gain,
    delay, damping, oscillation, overshoot and recovery are independent evidence
    dimensions: absence of one must not be mistaken for a safe value. A recorded
    stability state is an assessor's conclusion, not an automatically derived
    result, and therefore requires traceable assessment evidence.
    """

    loop_id: str
    members: List[str] = dataclasses.field(default_factory=list)
    relationships: List[str] = dataclasses.field(default_factory=list)
    scope: Optional[str] = None
    gain: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    delay: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    damping: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    oscillation: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    overshoot: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    recovery: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    observation_window: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    operating_envelope: str = UNKNOWN
    stability_state: str = UNKNOWN
    assessment_evidence: List[str] = dataclasses.field(default_factory=list)
    provenance: List[str] = dataclasses.field(default_factory=list)
    confidence: Optional[str] = None
    note: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.loop_id, str) or not self.loop_id.strip():
            raise ValueError("loop_id must be non-blank")
        for field_name in ("members", "relationships", "assessment_evidence", "provenance"):
            values = getattr(self, field_name)
            if not isinstance(values, list) or any(
                not isinstance(value, str) or not value.strip() for value in values
            ):
                raise ValueError(f"{field_name} must contain non-blank references")
        for dimension in MEASURED_DIMENSIONS:
            evidence = getattr(self, dimension)
            if not isinstance(evidence, InterfaceEvidence):
                raise ValueError(f"feedback dimension {dimension!r} must be InterfaceEvidence")
            if evidence.status == "measured":
                _validate_measured_dimension(evidence, dimension)
        if not self.members:
            raise ValueError("a feedback loop requires at least one member")
        if not self.relationships:
            raise ValueError("a feedback loop requires at least one relationship")
        if len(set(self.members)) != len(self.members):
            raise ValueError("feedback loop members must be unique")
        if len(set(self.relationships)) != len(self.relationships):
            raise ValueError("feedback loop relationships must be unique")
        if self.stability_state not in (*STABILITY_STATES, UNKNOWN):
            raise ValueError(f"invalid feedback stability state: {self.stability_state!r}")
        if self.stability_state != UNKNOWN:
            if not _has_traceable_evidence(self.assessment_evidence):
                raise ValueError(
                    "a non-UNKNOWN stability state requires traceable assessment evidence"
                )
            if not isinstance(self.confidence, str) or not self.confidence.strip():
                raise ValueError(
                    "a non-UNKNOWN stability state requires a non-blank confidence label"
                )
            if not _has_traceable_evidence(self.provenance):
                raise ValueError(
                    "a non-UNKNOWN stability state requires traceable provenance"
                )
        if self.operating_envelope not in (
            "normal", "busy", "degraded", "stress", "recovery", UNKNOWN
        ):
            raise ValueError(f"invalid operating envelope: {self.operating_envelope!r}")

    @property
    def assessment_status(self) -> str:
        return "unknown" if self.stability_state == UNKNOWN else "evidence_recorded"

    def to_dict(self) -> dict:
        data = dataclasses.asdict(self)
        data["assessment_status"] = self.assessment_status
        return data



def _topology_digest(loop: dict) -> str:
    topology = {
        "loop_id": loop.get("loop_id"),
        "members": loop.get("members"),
        "relationships": loop.get("relationships"),
    }
    return hashlib.sha256(_canonical(topology)).hexdigest()


def _validate_loop_record(loop: dict) -> FeedbackLoopAssessment:
    fields = {field.name for field in dataclasses.fields(FeedbackLoopAssessment)}
    payload = {key: value for key, value in loop.items() if key in fields}
    for dimension in MEASURED_DIMENSIONS:
        if isinstance(payload.get(dimension), dict):
            payload[dimension] = InterfaceEvidence(**payload[dimension])
    assessment = FeedbackLoopAssessment(**payload)
    loop.update(assessment.to_dict())
    return assessment


class FeedbackLoopEvidenceStore:
    """Append-only evidence updates for an existing cycle feedback-loop record.

    Measurements and assessor reviews are separate events. Measurements never
    calculate stability; a new measurement after a stability review resets the
    current verdict to UNKNOWN until another explicit review is recorded.
    """

    def __init__(self, path: str) -> None:
        self.path = path

    def _read_unlocked(self, fh) -> List[dict]:
        fh.seek(0)
        events = []
        previous = None
        for number, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"feedback-loop evidence line {number} is invalid JSON") from exc
            if (not isinstance(event, dict) or event.get("schema_version") != _EVENT_SCHEMA
                    or event.get("sequence") != len(events) + 1
                    or event.get("previous_event_sha256") != previous):
                raise ValueError(f"feedback-loop evidence chain is invalid at line {number}")
            if event.get("event_sha256") != _event_digest(event):
                raise ValueError(f"feedback-loop evidence digest mismatch at line {number}")
            kind = event.get("event_kind")
            data = event.get("data")
            if kind not in {"measurement_recorded", "stability_reviewed"} or not isinstance(data, dict):
                raise ValueError(f"unsupported feedback-loop event at line {number}")
            if not all(isinstance(data.get(key), str) and data[key].strip()
                       for key in ("event_id", "cycle_id", "loop_id", "topology_sha256", "recorded_at")):
                raise ValueError(f"feedback-loop event identity is invalid at line {number}")
            if not re.fullmatch(r"[0-9a-f]{64}", data["topology_sha256"]):
                raise ValueError(f"feedback-loop topology digest is invalid at line {number}")
            if kind == "measurement_recorded":
                if (data.get("dimension") not in MEASURED_DIMENSIONS
                        or isinstance(data.get("value"), bool)
                        or not _finite_number(data.get("value"))
                        or not isinstance(data.get("unit"), str) or not data["unit"].strip()
                        or not _has_traceable_evidence(data.get("evidence"))
                        or not isinstance(data.get("confidence"), str) or not data["confidence"].strip()
                        or not _has_traceable_evidence(data.get("provenance"))
                        or data.get("operating_envelope") not in OPERATING_ENVELOPES):
                    raise ValueError(f"feedback-loop measurement is invalid at line {number}")
            else:
                if (data.get("stability_state") not in STABILITY_STATES
                        or not isinstance(data.get("reviewer"), str) or not data["reviewer"].strip()
                        or not isinstance(data.get("source_reference"), str) or not data["source_reference"].strip()
                        or not _has_traceable_evidence(data.get("assessment_evidence"))
                        or not isinstance(data.get("confidence"), str) or not data["confidence"].strip()):
                    raise ValueError(f"feedback-loop stability review is invalid at line {number}")
            events.append(event)
            previous = event["event_sha256"]
        return events

    def _append(self, event_kind: str, data: dict) -> dict:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "a+", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                events = self._read_unlocked(fh)
                if any(event["data"]["event_id"] == data["event_id"] for event in events):
                    raise ValueError("duplicate feedback-loop evidence event")
                event = {
                    "schema_version": _EVENT_SCHEMA,
                    "event_kind": event_kind,
                    "sequence": len(events) + 1,
                    "previous_event_sha256": events[-1]["event_sha256"] if events else None,
                    "data": data,
                }
                event["event_sha256"] = _event_digest(event)
                fh.seek(0, os.SEEK_END)
                fh.write(json.dumps(event, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
                return event
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    def events(self, cycle_id: Optional[str] = None) -> List[dict]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_SH)
            try:
                events = self._read_unlocked(fh)
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        if cycle_id is None:
            return events
        return [event for event in events if event["data"]["cycle_id"] == cycle_id]

    @staticmethod
    def _find_loop(cycle, loop_id: str) -> dict:
        matches = []
        for assessment in getattr(cycle, "tension", []):
            if not isinstance(assessment, dict):
                continue
            dimensions = assessment.get("dimensions")
            if not isinstance(dimensions, dict):
                continue
            loops = dimensions.get("feedback_loop_assessments")
            if not isinstance(loops, list):
                continue
            matches.extend(
                loop for loop in loops
                if isinstance(loop, dict) and loop.get("loop_id") == loop_id
            )
        if not matches:
            raise ValueError(f"feedback loop {loop_id!r} is not present in cycle {cycle.id!r}")
        if len(matches) != 1:
            raise ValueError(f"feedback loop ID {loop_id!r} is not unique in cycle {cycle.id!r}")
        return matches[0]

    def record_measurement(self, cycle, loop_id: str, dimension: str, value: float,
                           unit: str, evidence: List[str], confidence: str,
                           provenance: List[str], operating_envelope: str = UNKNOWN) -> dict:
        loop_id = _text(loop_id, "loop_id", 256)
        if dimension not in MEASURED_DIMENSIONS:
            raise ValueError(f"dimension must be one of {MEASURED_DIMENSIONS}")
        measured = InterfaceEvidence(
            status="measured", value=value, unit=unit,
            evidence=_references(evidence, "evidence"),
            confidence=_text(confidence, "confidence", 128),
        )
        _validate_measured_dimension(measured, dimension)
        provenance = _references(provenance, "provenance")
        if operating_envelope not in OPERATING_ENVELOPES:
            raise ValueError(f"operating_envelope must be one of {OPERATING_ENVELOPES}")
        loop = self._find_loop(cycle, loop_id)
        recorded_at = utc_now()
        identity = {
            "cycle_id": cycle.id, "loop_id": loop_id, "dimension": dimension,
            "value": measured.value, "unit": measured.unit, "evidence": measured.evidence,
            "confidence": measured.confidence, "provenance": provenance,
            "operating_envelope": operating_envelope, "recorded_at": recorded_at,
        }
        data = {
            "event_id": "fle_" + hashlib.sha256(_canonical(identity)).hexdigest()[:24],
            "cycle_id": cycle.id, "loop_id": loop_id,
            "topology_sha256": _topology_digest(loop),
            **{key: value for key, value in identity.items()
               if key not in {"cycle_id", "loop_id"}},
        }
        event = self._append("measurement_recorded", data)
        self.apply(cycle)
        return event

    def record_stability_review(self, cycle, loop_id: str, stability_state: str,
                                reviewer: str, source_reference: str,
                                assessment_evidence: List[str], confidence: str,
                                note: str = "") -> dict:
        loop_id = _text(loop_id, "loop_id", 256)
        if stability_state not in STABILITY_STATES:
            raise ValueError(f"stability_state must be one of {STABILITY_STATES}")
        reviewer = _text(reviewer, "reviewer", 256)
        source_reference = _text(source_reference, "source_reference", 1000)
        evidence = _references(assessment_evidence, "assessment_evidence")
        confidence = _text(confidence, "confidence", 128)
        if not isinstance(note, str) or len(note) > 2000:
            raise ValueError("note must be text of at most 2000 characters")
        loop = self._find_loop(cycle, loop_id)
        recorded_at = utc_now()
        identity = {
            "cycle_id": cycle.id, "loop_id": loop_id,
            "stability_state": stability_state, "reviewer": reviewer,
            "source_reference": source_reference, "assessment_evidence": evidence,
            "confidence": confidence, "note": note, "recorded_at": recorded_at,
        }
        data = {
            "event_id": "flr_" + hashlib.sha256(_canonical(identity)).hexdigest()[:24],
            **identity,
            "topology_sha256": _topology_digest(loop),
        }
        event = self._append("stability_reviewed", data)
        self.apply(cycle)
        return event

    def apply(self, cycle):
        """Replay this cycle's ledger events into its existing loop records."""
        cycle_events = self.events(cycle.id)
        for event in cycle_events:
            data = event["data"]
            loop = self._find_loop(cycle, data["loop_id"])
            if _topology_digest(loop) != data["topology_sha256"]:
                raise ValueError("feedback-loop topology changed since evidence was recorded")
            if event["event_kind"] == "measurement_recorded":
                loop[data["dimension"]] = InterfaceEvidence(
                    status="measured", value=data["value"], unit=data["unit"],
                    evidence=list(data["evidence"]), confidence=data["confidence"],
                ).__dict__
                # New measurements invalidate any older stability review.
                loop["stability_state"] = UNKNOWN
                loop["assessment_evidence"] = []
                loop["provenance"] = []
                loop["confidence"] = None
                loop["note"] = ""
            else:
                loop["stability_state"] = data["stability_state"]
                loop["assessment_evidence"] = list(data["assessment_evidence"])
                loop["provenance"] = [
                    f"reviewer:{data['reviewer']}",
                    f"source:{data['source_reference']}",
                ]
                loop["confidence"] = data["confidence"]
                loop["note"] = data["note"]
            _validate_loop_record(loop)
        cycle.feedback_loop_evidence_events = [
            {
                "sequence": event["sequence"],
                "event_kind": event["event_kind"],
                "event_sha256": event["event_sha256"],
                **event["data"],
            }
            for event in cycle_events
        ]
        return cycle
