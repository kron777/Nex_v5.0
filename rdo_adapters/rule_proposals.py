"""Provider-neutral, inert proposal lifecycle for novel Extrapolator rule kinds.

This store records candidate data and caller-attributed review decisions. It is
not an active rule registry: even approved_for_catalogue never changes the
EXPANSION_RULES mapping or causes a proposal to execute.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
from typing import Any, Dict, List, Optional

from watcher.evidence import utc_now

from rdo.extrapolator import (
    EXPANSION_RULES,
    TERMINAL_KINDS,
    expansion_catalogue_digest,
)
from rdo.model import CLASSIFICATIONS

REQUEST_SCHEMA_VERSION = 2
EVENT_SCHEMA_VERSION = 1
ACTIVATION_POLICY = "candidate_only_until_explicit_review"
REVIEW_DECISIONS = ("changes_requested", "approved_for_catalogue", "rejected")
_PROPOSAL_ID = re.compile(r"ruleprop_[0-9a-f]{24}\Z")
MAX_LEDGER_BYTES = 32 * 1024 * 1024
MAX_LEDGER_EVENTS = 10000

_CANDIDATE_FIELDS = {
    "proposal_rationale",
    "decomposition_steps",
    "alternative_interpretations",
    "applicability",
    "preconditions",
    "constraints",
    "exceptions",
    "anti_requirements",
    "assumptions",
    "evidence_references",
    "disconfirming_cases",
    "positive_tests",
    "negative_tests",
}


class RuleProposalError(ValueError):
    """Invalid, stale, conflicting or tampered rule proposal data."""


def _canonical(value: Any) -> str:
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise RuleProposalError(f"record is not canonical JSON: {exc}") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(value: Any, label: str, maximum: int = 2000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise RuleProposalError(f"{label} must be non-blank text of at most {maximum} characters")
    return value.strip()


def _text_list(value: Any, label: str, *, required: bool = False,
               maximum_items: int = 100) -> List[str]:
    if not isinstance(value, list) or len(value) > maximum_items:
        raise RuleProposalError(f"{label} must be a list of at most {maximum_items} items")
    out = []
    for item in value:
        out.append(_text(item, label, 2000))
    if len(out) != len(set(out)):
        raise RuleProposalError(f"{label} must not contain duplicates")
    if required and not out:
        raise RuleProposalError(f"{label} must not be empty")
    return out


def validate_rule_proposal_request(request: Any) -> dict:
    """Validate that a frontier request still describes the current rule catalogue."""
    if not isinstance(request, dict):
        raise RuleProposalError("rule proposal request must be an object")
    required = {
        "schema_version", "target_kind", "source_obligation", "known_rule_kinds",
        "terminal_kinds", "proposal_requirements", "activation_policy",
        "catalogue_digest",
    }
    if set(request) != required:
        raise RuleProposalError("rule proposal request has missing or unsupported fields")
    if request.get("schema_version") != REQUEST_SCHEMA_VERSION:
        raise RuleProposalError("unsupported or stale rule proposal request schema")
    target = _text(request.get("target_kind"), "target_kind", 256)
    source = request.get("source_obligation")
    if not isinstance(source, dict) or source.get("kind") != target:
        raise RuleProposalError("source obligation kind must match target_kind")
    if target in EXPANSION_RULES or target in TERMINAL_KINDS:
        raise RuleProposalError("proposal target is no longer a novel expandable kind")
    if request.get("known_rule_kinds") != sorted(EXPANSION_RULES):
        raise RuleProposalError("rule proposal request has stale known_rule_kinds")
    if request.get("terminal_kinds") != sorted(TERMINAL_KINDS):
        raise RuleProposalError("rule proposal request has stale terminal_kinds")
    if request.get("catalogue_digest") != expansion_catalogue_digest():
        raise RuleProposalError("rule proposal request was generated against a different catalogue")
    if request.get("activation_policy") != ACTIVATION_POLICY:
        raise RuleProposalError("rule proposal request has an unsupported activation policy")
    requirements = _text_list(
        request.get("proposal_requirements"), "proposal_requirements", required=True
    )
    expected = [
        "decomposition_steps",
        "applicability_and_scope",
        "preconditions_and_constraints",
        "exceptions_and_anti_requirements",
        "evidence_and_provenance",
        "disconfirming_cases",
        "positive_and_negative_tests",
    ]
    if requirements != expected:
        raise RuleProposalError("rule proposal request review requirements are incomplete or reordered")
    return json.loads(_canonical(request))


def _validate_steps(value: Any, target_kind: str) -> List[dict]:
    if not isinstance(value, list) or not value or len(value) > 100:
        raise RuleProposalError("decomposition_steps must be a non-empty list of at most 100 steps")
    out = []
    identities = set()
    for index, step in enumerate(value):
        if not isinstance(step, dict) or set(step) - {
            "child_kind", "classification", "rationale", "shared_target"
        }:
            raise RuleProposalError(f"decomposition step {index} has unsupported fields")
        child_kind = _text(step.get("child_kind"), f"decomposition_steps[{index}].child_kind", 256)
        classification = step.get("classification")
        if classification not in CLASSIFICATIONS:
            raise RuleProposalError(f"decomposition step {index} has an invalid classification")
        rationale = _text(step.get("rationale"), f"decomposition_steps[{index}].rationale")
        shared = step.get("shared_target")
        if shared is not None:
            shared = _text(shared, f"decomposition_steps[{index}].shared_target", 256)
        if child_kind == target_kind:
            raise RuleProposalError("decomposition step cannot directly recurse into its own target kind")
        identity = (child_kind, shared)
        if identity in identities:
            raise RuleProposalError("decomposition_steps contains duplicate child identities")
        identities.add(identity)
        out.append({
            "child_kind": child_kind,
            "classification": classification,
            "rationale": rationale,
            "shared_target": shared,
        })
    return out


def _validate_candidate(request: dict, candidate: Any, proposer_kind: str,
                        proposer_reference: str, source_reference: str,
                        supersedes_proposal_id: Optional[str]) -> dict:
    if not isinstance(candidate, dict) or set(candidate) != _CANDIDATE_FIELDS:
        raise RuleProposalError("candidate must contain exactly the documented proposal fields")
    if proposer_kind not in ("human", "external_llm"):
        raise RuleProposalError("proposer_kind must be human or external_llm")
    proposer_reference = _text(proposer_reference, "proposer_reference", 512)
    source_reference = _text(source_reference, "source_reference", 1000)
    rationale = _text(candidate["proposal_rationale"], "proposal_rationale")
    applicability = _text(candidate["applicability"], "applicability")
    steps = _validate_steps(candidate["decomposition_steps"], request["target_kind"])
    alternatives = _text_list(
        candidate["alternative_interpretations"], "alternative_interpretations", required=True
    )
    preconditions = _text_list(candidate["preconditions"], "preconditions")
    constraints = _text_list(candidate["constraints"], "constraints")
    exceptions = _text_list(candidate["exceptions"], "exceptions")
    anti_requirements = _text_list(candidate["anti_requirements"], "anti_requirements")
    assumptions = _text_list(candidate["assumptions"], "assumptions")
    evidence = _text_list(candidate["evidence_references"], "evidence_references", required=True)
    disconfirmations = _text_list(candidate["disconfirming_cases"], "disconfirming_cases")
    positive_tests = _text_list(candidate["positive_tests"], "positive_tests", required=True)
    negative_tests = _text_list(candidate["negative_tests"], "negative_tests", required=True)
    if supersedes_proposal_id is not None and (
        not isinstance(supersedes_proposal_id, str)
        or not _PROPOSAL_ID.fullmatch(supersedes_proposal_id)
    ):
        raise RuleProposalError("supersedes_proposal_id is invalid")
    body = {
        "schema_version": 1,
        "target_kind": request["target_kind"],
        "source_obligation": request["source_obligation"],
        "source_request": request,
        "source_request_sha256": _digest(request),
        "catalogue_digest": request["catalogue_digest"],
        "proposal_rationale": rationale,
        "decomposition_steps": steps,
        "alternative_interpretations": alternatives,
        "applicability": applicability,
        "preconditions": preconditions,
        "constraints": constraints,
        "exceptions": exceptions,
        "anti_requirements": anti_requirements,
        "assumptions": assumptions,
        "evidence_references": evidence,
        "disconfirming_cases": disconfirmations,
        "positive_tests": positive_tests,
        "negative_tests": negative_tests,
        "proposer_kind": proposer_kind,
        "proposer_reference": proposer_reference,
        "source_reference": source_reference,
        "supersedes_proposal_id": supersedes_proposal_id,
    }
    body["proposal_id"] = "ruleprop_" + _digest(body)[:24]
    body["created_at"] = utc_now()
    return body


def _reject_duplicate_keys(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise RuleProposalError(f"duplicate JSON property: {key}")
        out[key] = value
    return out


class RuleProposalStore:
    """Append-only candidate/review ledger; approved candidates remain inert.

    Each JSONL event is hash-chained and fsynced under an exclusive file lock.
    Reviewer/proposer identities are caller-attributed, not authenticated.
    """

    def __init__(self, path: str) -> None:
        self.path = os.path.abspath(path)

    @staticmethod
    def _parse_events(lines: List[str]) -> List[dict]:
        if len(lines) > MAX_LEDGER_EVENTS:
            raise RuleProposalError("rule-proposal ledger exceeds event limit")
        events = []
        previous = None
        for number, line in enumerate(lines, 1):
            if not line.strip():
                raise RuleProposalError(f"blank rule-proposal ledger line {number}")
            try:
                event = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
            except (json.JSONDecodeError, UnicodeError) as exc:
                raise RuleProposalError(f"invalid rule-proposal JSON on line {number}") from exc
            if not isinstance(event, dict) or set(event) != {
                "schema_version", "sequence", "previous_event_sha256",
                "event_kind", "proposal_id", "recorded_at", "record", "event_sha256",
            }:
                raise RuleProposalError(f"rule-proposal event shape is invalid on line {number}")
            if (event["schema_version"] != EVENT_SCHEMA_VERSION
                    or isinstance(event["sequence"], bool)
                    or not isinstance(event["sequence"], int)
                    or event["sequence"] != number):
                raise RuleProposalError(f"rule-proposal event version/sequence is invalid on line {number}")
            if event["previous_event_sha256"] != previous:
                raise RuleProposalError(f"rule-proposal event chain is broken on line {number}")
            body = dict(event)
            claimed = body.pop("event_sha256")
            if not isinstance(claimed, str) or claimed != _digest(body):
                raise RuleProposalError(f"rule-proposal event digest mismatch on line {number}")
            if event["event_kind"] not in ("proposal_submitted", "review_decision"):
                raise RuleProposalError(f"unsupported rule-proposal event kind on line {number}")
            if not _PROPOSAL_ID.fullmatch(str(event["proposal_id"])):
                raise RuleProposalError(f"invalid proposal identity on line {number}")
            _text(event.get("recorded_at"), "recorded_at", 128)
            if not isinstance(event["record"], dict):
                raise RuleProposalError(f"rule-proposal event record is invalid on line {number}")
            events.append(event)
            previous = claimed
        return events

    def _read_events(self) -> List[dict]:
        # Check symlink identity before exists(): exists() is false for a
        # dangling symlink, which must not be mistaken for an absent ledger.
        if os.path.islink(self.path):
            raise RuleProposalError("rule-proposal ledger path must not be a symlink")
        if not os.path.exists(self.path):
            return []
        if os.path.getsize(self.path) > MAX_LEDGER_BYTES:
            raise RuleProposalError("rule-proposal ledger exceeds byte limit")
        with open(self.path, "r", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_SH)
            try:
                lines = fh.readlines()
                if lines and not lines[-1].endswith("\n"):
                    raise RuleProposalError("rule-proposal ledger final event is not newline terminated")
                return self._parse_events(lines)
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _snapshot(events: List[dict]) -> Dict[str, dict]:
        proposals: Dict[str, dict] = {}
        for event in events:
            pid = event["proposal_id"]
            if event["event_kind"] == "proposal_submitted":
                record = event["record"]
                required_fields = {
                    "schema_version", "target_kind", "source_obligation", "source_request",
                    "source_request_sha256", "catalogue_digest", *_CANDIDATE_FIELDS,
                    "proposer_kind", "proposer_reference", "source_reference",
                    "supersedes_proposal_id", "proposal_id", "created_at",
                }
                if set(record) != required_fields or record.get("schema_version") != 1:
                    raise RuleProposalError("persisted proposal record has missing or unsupported fields")
                source_request = record.get("source_request")
                if (not isinstance(source_request, dict)
                        or _digest(source_request) != record.get("source_request_sha256")
                        or source_request.get("catalogue_digest") != record.get("catalogue_digest")
                        or source_request.get("target_kind") != record.get("target_kind")
                        or not isinstance(record.get("source_obligation"), dict)
                        or record["source_obligation"].get("kind") != record.get("target_kind")):
                    raise RuleProposalError("persisted proposal source/request binding is invalid")
                identity = dict(record)
                identity.pop("proposal_id", None)
                identity.pop("created_at", None)
                expected_id = "ruleprop_" + _digest(identity)[:24]
                if record.get("proposal_id") != pid or pid != expected_id or pid in proposals:
                    raise RuleProposalError("duplicate or mismatched proposal submission")
                _text(record.get("created_at"), "created_at", 128)
                proposals[pid] = {
                    "proposal": record,
                    "status": "candidate",
                    "latest_review": None,
                }
            else:
                if pid not in proposals:
                    raise RuleProposalError("review decision refers to an unknown proposal")
                current = proposals[pid]
                if current["latest_review"] is not None:
                    raise RuleProposalError("proposal has more than one review decision")
                review = event["record"]
                if set(review) != {
                    "decision", "reviewer", "source_reference", "rationale",
                    "evidence_references",
                }:
                    raise RuleProposalError("proposal review record has missing or unsupported fields")
                if review.get("decision") not in REVIEW_DECISIONS:
                    raise RuleProposalError("proposal review decision is invalid")
                _text(review.get("reviewer"), "reviewer", 256)
                _text(review.get("source_reference"), "source_reference", 1000)
                _text(review.get("rationale"), "rationale")
                _text_list(review.get("evidence_references"), "evidence_references", required=True)
                current["status"] = review["decision"]
                current["latest_review"] = review
        return proposals

    def _append(self, event_kind: str, proposal_id: str, record: dict) -> dict:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        if os.path.islink(self.path):
            raise RuleProposalError("rule-proposal ledger path must not be a symlink")
        created = not os.path.exists(self.path)
        with open(self.path, "a+", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                fh.seek(0, os.SEEK_END)
                if fh.tell() > MAX_LEDGER_BYTES:
                    raise RuleProposalError("rule-proposal ledger exceeds byte limit")
                fh.seek(0)
                lines = fh.readlines()
                if lines and not lines[-1].endswith("\n"):
                    raise RuleProposalError("rule-proposal ledger final event is not newline terminated")
                events = self._parse_events(lines)
                if len(events) >= MAX_LEDGER_EVENTS:
                    raise RuleProposalError("rule-proposal ledger exceeds event limit")
                snapshot = self._snapshot(events)
                if event_kind == "proposal_submitted" and proposal_id in snapshot:
                    raise RuleProposalError("proposal was submitted concurrently; reload before retrying")
                if event_kind == "review_decision":
                    current = snapshot.get(proposal_id)
                    if current is None:
                        raise RuleProposalError("cannot review an unknown proposal")
                    if current["latest_review"] is not None:
                        raise RuleProposalError("proposal already has a review decision")
                base = {
                    "schema_version": EVENT_SCHEMA_VERSION,
                    "sequence": len(events) + 1,
                    "previous_event_sha256": events[-1]["event_sha256"] if events else None,
                    "event_kind": event_kind,
                    "proposal_id": proposal_id,
                    "recorded_at": utc_now(),
                    "record": record,
                }
                event = dict(base)
                event["event_sha256"] = _digest(base)
                # Validate the prospective event against the complete ledger
                # while holding the lock. Never persist an event that makes
                # subsequent replay fail.
                self._snapshot(events + [event])
                encoded = _canonical(event) + "\n"
                fh.seek(0, os.SEEK_END)
                if fh.tell() + len(encoded.encode("utf-8")) > MAX_LEDGER_BYTES:
                    raise RuleProposalError("rule-proposal ledger exceeds byte limit")
                fh.write(encoded)
                fh.flush()
                os.fsync(fh.fileno())
                if created:
                    directory = os.path.dirname(os.path.abspath(self.path)) or "."
                    dir_fd = os.open(directory, os.O_RDONLY)
                    try:
                        os.fsync(dir_fd)
                    finally:
                        os.close(dir_fd)
                return event
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    def submit(self, request: dict, candidate: dict, *, proposer_kind: str,
               proposer_reference: str, source_reference: str,
               supersedes_proposal_id: Optional[str] = None) -> dict:
        validated_request = validate_rule_proposal_request(request)
        proposal = _validate_candidate(
            validated_request, candidate, proposer_kind, proposer_reference,
            source_reference, supersedes_proposal_id,
        )
        snapshot = self._snapshot(self._read_events())
        pid = proposal["proposal_id"]
        if pid in snapshot:
            existing = dict(snapshot[pid]["proposal"])
            incoming = dict(proposal)
            existing.pop("created_at", None)
            incoming.pop("created_at", None)
            if existing != incoming:
                raise RuleProposalError("proposal ID collision with different content")
            return snapshot[pid]
        if supersedes_proposal_id is not None:
            prior = snapshot.get(supersedes_proposal_id)
            if prior is None or prior["status"] not in ("changes_requested", "rejected"):
                raise RuleProposalError("superseded proposal must exist and be changes_requested or rejected")
        self._append("proposal_submitted", pid, proposal)
        return self.get(pid)

    def review(self, proposal_id: str, decision: str, *, reviewer: str,
               source_reference: str, rationale: str,
               evidence_references: List[str]) -> dict:
        if not _PROPOSAL_ID.fullmatch(str(proposal_id)):
            raise RuleProposalError("proposal_id is invalid")
        if decision not in REVIEW_DECISIONS:
            raise RuleProposalError(f"decision must be one of {REVIEW_DECISIONS}")
        snapshot = self._snapshot(self._read_events())
        current = snapshot.get(proposal_id)
        if current is None:
            raise RuleProposalError("cannot review an unknown proposal")
        if current["latest_review"] is not None:
            raise RuleProposalError("proposal already has a review decision; submit a new revision")
        record = {
            "decision": decision,
            "reviewer": _text(reviewer, "reviewer", 256),
            "source_reference": _text(source_reference, "source_reference", 1000),
            "rationale": _text(rationale, "rationale"),
            "evidence_references": _text_list(
                evidence_references, "evidence_references", required=True
            ),
        }
        self._append("review_decision", proposal_id, record)
        return self.get(proposal_id)

    def get(self, proposal_id: str) -> dict:
        snapshot = self._snapshot(self._read_events())
        if proposal_id not in snapshot:
            raise RuleProposalError("unknown proposal")
        item = snapshot[proposal_id]
        return {
            "proposal": json.loads(_canonical(item["proposal"])),
            "status": item["status"],
            "latest_review": json.loads(_canonical(item["latest_review"]))
            if item["latest_review"] is not None else None,
        }

    def proposals(self) -> List[dict]:
        snapshot = self._snapshot(self._read_events())
        return [
            {
                "proposal": json.loads(_canonical(item["proposal"])),
                "status": item["status"],
                "latest_review": json.loads(_canonical(item["latest_review"]))
                if item["latest_review"] is not None else None,
            }
            for item in snapshot.values()
        ]

    def events(self) -> List[dict]:
        return self._read_events()
