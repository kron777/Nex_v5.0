"""Governed proposal lifecycle for novel Extrapolator rule kinds.

Candidates are advisory records. Repetition in PatternMemory never activates a
rule. Only an explicit, evidence-referenced approval event can place one selected
alternative in the versioned catalogue consumed by expand().
"""
from __future__ import annotations

import dataclasses
import fcntl
import hashlib
import json
import os
import re
from typing import Dict, List, Optional, Tuple

from .model import CLASSIFICATIONS

EVENT_SCHEMA = "rdo.rule_proposal_event.v1"
_TOKEN = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
_ALT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")


@dataclasses.dataclass(frozen=True)
class ApprovedRuleCatalogue:
    """Validated, explicitly approved additional rules for one deterministic cycle."""

    version: int
    sha256: str
    rules: Dict[str, List[Tuple[str, str, str, Optional[str]]]]
    provenance: Dict[str, dict]

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "sha256": self.sha256,
            "rules": {
                key: [
                    {"child_kind": child, "classification": classification,
                     "rationale": rationale, "shared_target": shared}
                    for child, classification, rationale, shared in values
                ]
                for key, values in sorted(self.rules.items())
            },
            "provenance": self.provenance,
        }


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _text(value, name: str, limit: int = 2000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{name} must be non-blank text of at most {limit} characters")
    return value.strip()


def _text_list(value, name: str, *, required: bool = False, limit: int = 64) -> List[str]:
    if not isinstance(value, list) or len(value) > limit:
        raise ValueError(f"{name} must be a list with at most {limit} entries")
    result = []
    for item in value:
        item = _text(item, name)
        if item not in result:
            result.append(item)
    if required and not result:
        raise ValueError(f"{name} must contain at least one evidence item")
    return result


def _normalise_proposal(raw: dict) -> dict:
    required = {
        "target_kind", "source_obligation", "alternatives", "assumptions",
        "applicability", "preconditions", "exceptions", "anti_requirements",
        "evidence_needs", "disconfirming_cases", "provenance",
        "positive_tests", "negative_tests",
    }
    if not isinstance(raw, dict) or set(raw) != required:
        missing = sorted(required - set(raw)) if isinstance(raw, dict) else sorted(required)
        extra = sorted(set(raw) - required) if isinstance(raw, dict) else []
        raise ValueError(f"proposal fields mismatch; missing={missing}, extra={extra}")
    target = _text(raw["target_kind"], "target_kind", 64)
    if not _TOKEN.fullmatch(target):
        raise ValueError("target_kind must be a lowercase snake_case kind")
    source = raw["source_obligation"]
    if not isinstance(source, dict) or source.get("kind") != target:
        raise ValueError("source_obligation must be an object whose kind matches target_kind")
    for field in ("key", "title"):
        _text(source.get(field), f"source_obligation.{field}", 256)
    alternatives = raw["alternatives"]
    if not isinstance(alternatives, list) or not 1 <= len(alternatives) <= 8:
        raise ValueError("alternatives must contain 1-8 competing decompositions")
    checked_alternatives = []
    seen_alt_ids = set()
    for index, alternative in enumerate(alternatives):
        if not isinstance(alternative, dict) or set(alternative) != {"id", "description", "steps"}:
            raise ValueError(f"alternatives[{index}] must contain id, description and steps")
        alt_id = _text(alternative["id"], f"alternatives[{index}].id", 64)
        if not _ALT_ID.fullmatch(alt_id) or alt_id in seen_alt_ids:
            raise ValueError("alternative IDs must be unique portable tokens")
        seen_alt_ids.add(alt_id)
        description = _text(alternative["description"], f"alternatives[{index}].description")
        steps = alternative["steps"]
        if not isinstance(steps, list) or not 1 <= len(steps) <= 32:
            raise ValueError("each alternative must contain 1-32 decomposition steps")
        checked_steps = []
        seen_children = set()
        for step_index, step in enumerate(steps):
            if not isinstance(step, dict) or set(step) != {
                "child_kind", "classification", "rationale", "shared_target"
            }:
                raise ValueError(f"alternatives[{index}].steps[{step_index}] has invalid fields")
            child = _text(step["child_kind"], "child_kind", 64)
            if not _TOKEN.fullmatch(child) or child in seen_children:
                raise ValueError("child kinds must be unique lowercase snake_case tokens per alternative")
            seen_children.add(child)
            classification = step["classification"]
            if classification not in CLASSIFICATIONS:
                raise ValueError(f"unsupported child classification: {classification!r}")
            rationale = _text(step["rationale"], "step rationale")
            shared = step["shared_target"]
            if shared is not None:
                shared = _text(shared, "shared_target", 128)
                if not _ALT_ID.fullmatch(shared):
                    raise ValueError("shared_target must be a portable token")
            checked_steps.append({
                "child_kind": child, "classification": classification,
                "rationale": rationale, "shared_target": shared,
            })
        checked_alternatives.append({
            "id": alt_id, "description": description, "steps": checked_steps,
        })
    checked_source = {
        key: value for key, value in source.items()
        if key in {"key", "title", "kind", "classification", "rationale", "impact",
                   "evidence_needs", "assumptions", "confidence", "provenance"}
    }
    checked_source["key"] = _text(source["key"], "source_obligation.key", 256)
    checked_source["title"] = _text(source["title"], "source_obligation.title", 256)
    checked_source["kind"] = target
    result = {
        "schema_version": 1,
        "target_kind": target,
        "source_obligation": checked_source,
        "alternatives": checked_alternatives,
    }
    for field in (
        "assumptions", "applicability", "preconditions", "exceptions",
        "anti_requirements", "evidence_needs", "disconfirming_cases",
        "provenance", "positive_tests", "negative_tests",
    ):
        result[field] = _text_list(
            raw[field], field,
            required=field in {"applicability", "provenance", "disconfirming_cases",
                               "positive_tests", "negative_tests"},
        )
    return result


def _event_digest(event: dict) -> str:
    return hashlib.sha256(_canonical({
        key: value for key, value in event.items() if key != "event_sha256"
    })).hexdigest()


class RuleProposalStore:
    """Append-only hash-chained candidate/review ledger with an approved-only view."""

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
                raise ValueError(f"rule proposal ledger line {number} is invalid JSON") from exc
            if not isinstance(event, dict) or event.get("schema_version") != EVENT_SCHEMA:
                raise ValueError(f"unsupported rule proposal event on line {number}")
            if event.get("sequence") != len(events) + 1 or event.get("previous_event_sha256") != previous:
                raise ValueError(f"rule proposal ledger chain is broken at line {number}")
            if event.get("event_sha256") != _event_digest(event):
                raise ValueError(f"rule proposal ledger digest mismatch at line {number}")
            if event.get("event_kind") not in {"proposal_created", "proposal_reviewed"}:
                raise ValueError(f"unsupported rule proposal event kind on line {number}")
            events.append(event)
            previous = event["event_sha256"]
        return events

    def _append(self, event_kind: str, data: dict) -> dict:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "a+", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                events = self._read_unlocked(fh)
                event = {
                    "schema_version": EVENT_SCHEMA,
                    "event_kind": event_kind,
                    "sequence": len(events) + 1,
                    "previous_event_sha256": events[-1]["event_sha256"] if events else None,
                    "data": data,
                }
                event["event_sha256"] = _event_digest(event)
                fh.seek(0, os.SEEK_END)
                fh.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
                return event
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    def events(self) -> List[dict]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_SH)
            try:
                return self._read_unlocked(fh)
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    def propose(self, raw: dict) -> dict:
        proposal = _normalise_proposal(raw)
        # Novel kinds only: built-in and terminal rules are not shadowed.
        from .extrapolator import EXPANSION_RULES, TERMINAL_KINDS
        target = proposal["target_kind"]
        if target in EXPANSION_RULES or target in TERMINAL_KINDS:
            raise ValueError(f"kind {target!r} already has a built-in expansion/terminal rule")
        proposal_id = "rp_" + hashlib.sha256(_canonical(proposal)).hexdigest()[:24]
        for event in self.events():
            if (event["event_kind"] == "proposal_created"
                    and event["data"]["proposal_id"] == proposal_id):
                raise ValueError("identical rule proposal already exists")
        return self._append("proposal_created", {
            "proposal_id": proposal_id, "proposal": proposal,
        })

    def review(self, proposal_id: str, decision: str, reviewer: str,
               source_reference: str, evidence_references: List[str],
               selected_alternative: Optional[str] = None,
               positive_test_evidence: Optional[List[str]] = None,
               negative_test_evidence: Optional[List[str]] = None,
               note: str = "") -> dict:
        proposal_id = _text(proposal_id, "proposal_id", 64)
        reviewer = _text(reviewer, "reviewer", 256)
        source_reference = _text(source_reference, "source_reference", 1000)
        evidence = _text_list(evidence_references, "evidence_references", required=True)
        note = note if isinstance(note, str) and len(note) <= 2000 else None
        if note is None:
            raise ValueError("note must be text of at most 2000 characters")
        if not isinstance(decision, str) or decision not in {"approved", "rejected", "changes_requested"}:
            raise ValueError("decision must be approved, rejected or changes_requested")

        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "a+", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                events = self._read_unlocked(fh)
                created = next((e["data"]["proposal"] for e in events
                                if e["event_kind"] == "proposal_created"
                                and e["data"]["proposal_id"] == proposal_id), None)
                if created is None:
                    raise ValueError("rule proposal does not exist")
                prior = [e["data"] for e in events
                         if e["event_kind"] == "proposal_reviewed"
                         and e["data"]["proposal_id"] == proposal_id]
                if prior and prior[-1]["decision"] in {"approved", "rejected"}:
                    raise ValueError("approved/rejected proposals are terminal")
                selected = None
                positive = []
                negative = []
                version = None
                if decision == "approved":
                    selected = _text(selected_alternative, "selected_alternative", 64)
                    alternatives = {a["id"] for a in created["alternatives"]}
                    if selected not in alternatives:
                        raise ValueError("selected alternative is not part of this proposal")
                    positive = _text_list(positive_test_evidence, "positive_test_evidence", required=True)
                    negative = _text_list(negative_test_evidence, "negative_test_evidence", required=True)
                    if set(positive) != set(created["positive_tests"]):
                        raise ValueError("approval must review every declared positive test")
                    if set(negative) != set(created["negative_tests"]):
                        raise ValueError("approval must review every declared negative test")
                    # Do not silently replace an existing built-in or approved kind.
                    from .extrapolator import EXPANSION_RULES, TERMINAL_KINDS
                    if created["target_kind"] in EXPANSION_RULES or created["target_kind"] in TERMINAL_KINDS:
                        raise ValueError("target kind now conflicts with a built-in rule")
                    if any(
                        e["event_kind"] == "proposal_reviewed"
                        and e["data"]["decision"] == "approved"
                        and next((p["target_kind"] for p in events
                                  if p["event_kind"] == "proposal_created"
                                  and p["data"]["proposal_id"] == e["data"]["proposal_id"]), None)
                            == created["target_kind"]
                        for e in events
                    ):
                        raise ValueError("target kind already has an approved rule")
                    version = 1 + max(
                        (e["data"].get("catalogue_version", 0) for e in events
                         if e["event_kind"] == "proposal_reviewed"), default=0
                    )
                event = {
                    "schema_version": EVENT_SCHEMA,
                    "event_kind": "proposal_reviewed",
                    "sequence": len(events) + 1,
                    "previous_event_sha256": events[-1]["event_sha256"] if events else None,
                    "data": {
                        "proposal_id": proposal_id, "decision": decision,
                        "selected_alternative": selected, "reviewer": reviewer,
                        "source_reference": source_reference,
                        "evidence_references": evidence,
                        "positive_test_evidence": positive,
                        "negative_test_evidence": negative,
                        "catalogue_version": version, "note": note,
                    },
                }
                event["event_sha256"] = _event_digest(event)
                fh.seek(0, os.SEEK_END)
                fh.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
                return event
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    def approved_catalogue(self) -> Optional[ApprovedRuleCatalogue]:
        events = self.events()
        proposals = {
            e["data"]["proposal_id"]: e["data"]["proposal"]
            for e in events if e["event_kind"] == "proposal_created"
        }
        latest = {}
        for event in events:
            if event["event_kind"] == "proposal_reviewed":
                latest[event["data"]["proposal_id"]] = event["data"]
        rules = {}
        provenance = {}
        version = 0
        for proposal_id, review in latest.items():
            if review["decision"] != "approved":
                continue
            proposal = proposals[proposal_id]
            kind = proposal["target_kind"]
            if kind in rules:
                raise ValueError(f"multiple approved rules exist for kind {kind!r}")
            alternative = next(a for a in proposal["alternatives"]
                               if a["id"] == review["selected_alternative"])
            rules[kind] = [
                (step["child_kind"], step["classification"], step["rationale"],
                 step["shared_target"])
                for step in alternative["steps"]
            ]
            provenance[kind] = {
                "proposal_id": proposal_id,
                "alternative_id": alternative["id"],
                "catalogue_version": review["catalogue_version"],
                "reviewer": review["reviewer"],
                "source_reference": review["source_reference"],
                "evidence_references": review["evidence_references"],
                "positive_test_evidence": review["positive_test_evidence"],
                "negative_test_evidence": review["negative_test_evidence"],
                "assumptions": proposal["assumptions"],
                "applicability": proposal["applicability"],
                "preconditions": proposal["preconditions"],
                "exceptions": proposal["exceptions"],
                "anti_requirements": proposal["anti_requirements"],
                "disconfirming_cases": proposal["disconfirming_cases"],
                "provenance": proposal["provenance"],
            }
            version = max(version, review["catalogue_version"])
        if not rules:
            return None
        snapshot = {
            "version": version,
            "rules": {
                key: [list(item) for item in value]
                for key, value in sorted(rules.items())
            },
            "provenance": provenance,
        }
        digest = hashlib.sha256(_canonical(snapshot)).hexdigest()
        return ApprovedRuleCatalogue(version, digest, rules, provenance)
