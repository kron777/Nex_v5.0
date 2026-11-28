"""Provider-neutral, candidate-only first-level seed proposals for RDO objectives.

A proposal preserves the exact raw-objective revision and several competing
seed-graph interpretations. Only an explicit review can select one alternative.
This adapter never runs objective intake, recursive expansion, a planning cycle,
or Stage-7 handoff; it creates no executable rules and grants no authority.
"""
from __future__ import annotations

import fcntl
import hashlib
from datetime import datetime
import json
import os
import re
from typing import Any, Dict, List, Optional

from watcher.evidence import utc_now

SCHEMA_VERSION = 1
RAW_OBJECTIVE_SCHEMA = "rdo.raw_objective.v1"
EVENT_SCHEMA_VERSION = 1
MAX_LEDGER_BYTES = 32 * 1024 * 1024
MAX_LEDGER_EVENTS = 10000
MAX_ALTERNATIVES = 12
MAX_SEEDS = 200
MAX_RELATIONSHIPS = 1000

_PROPOSAL_ID = re.compile(r"seedprop_[0-9a-f]{24}\Z")
_OBJECTIVE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
_KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SOURCE_KINDS = {"human", "external_llm", "imported"}
_CLASSIFICATIONS = {
    "necessary", "conditional", "optional", "future", "hypothesis",
    "unknown", "anti_requirement",
}
_RELATIONSHIP_KINDS = {"depends_on", "produces_for", "reuses", "duplicates", "influences"}
_AUTHORITY_LEVELS = {"none", "bounded", "strong"}
_REVIEW_DECISIONS = {"changes_requested", "approved", "rejected"}

_RAW_FIELDS = {
    "schema_version", "objective_id", "revision", "supersedes_sha256",
    "original_text", "intent", "owner", "source", "scope", "constraints",
    "exclusions", "assumptions", "acceptance_criteria",
    "reconciliation_signatures", "max_depth",
}
_ALTERNATIVE_FIELDS = {
    "alternative_id", "interpretation", "seed_obligations", "relationships",
    "reconciliation_signatures", "assumptions", "constraints", "exclusions",
    "acceptance_criterion_coverage", "open_questions", "disconfirming_cases",
    "evidence_needs",
}
_SEED_FIELDS = {
    "key", "title", "kind", "classification", "rationale", "impact",
    "evidence_needs", "assumptions", "confidence",
}


class SeedProposalError(ValueError):
    """Invalid, stale, conflicting, or tampered seed proposal data."""


def _canonical(value: Any) -> str:
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise SeedProposalError(f"record is not canonical JSON: {exc}") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(value: Any, label: str, maximum: int = 4000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise SeedProposalError(f"{label} must be non-blank text of at most {maximum} characters")
    return value


def _text_list(value: Any, label: str, *, required: bool = False,
               maximum_items: int = 200, maximum_length: int = 2000) -> List[str]:
    if not isinstance(value, list) or len(value) > maximum_items:
        raise SeedProposalError(f"{label} must be a list of at most {maximum_items} items")
    result = [_text(item, f"{label}[{i}]", maximum_length)
              for i, item in enumerate(value)]
    if len(result) != len(set(result)):
        raise SeedProposalError(f"{label} must not contain duplicates")
    if required and not result:
        raise SeedProposalError(f"{label} must not be empty")
    return result


def _object(value: Any, label: str, fields: set) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        raise SeedProposalError(f"{label} must contain exactly the documented fields")
    return value


def _safe_path(value: Any, label: str) -> str:
    path = _text(value, label, 512)
    if (path.startswith("/") or "\\" in path or ":" in path
            or any(ord(char) < 32 for char in path)
            or any(part in ("", ".", "..") for part in path.split("/"))):
        raise SeedProposalError(f"{label} must be a clean repository-relative path")
    return path


def validate_raw_objective(raw: Any) -> dict:
    """Validate the immutable source/context snapshot to which proposals bind."""
    raw = _object(raw, "raw_objective", _RAW_FIELDS)
    if raw["schema_version"] != RAW_OBJECTIVE_SCHEMA:
        raise SeedProposalError(f"raw objective schema must be {RAW_OBJECTIVE_SCHEMA!r}")
    objective_id = _text(raw["objective_id"], "objective_id", 64)
    if not _OBJECTIVE_ID.fullmatch(objective_id):
        raise SeedProposalError("objective_id must use portable filename characters")
    revision = raw["revision"]
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise SeedProposalError("raw objective revision must be a positive integer")
    previous = raw["supersedes_sha256"]
    if revision == 1:
        if previous is not None:
            raise SeedProposalError("raw objective revision 1 must not supersede another revision")
    elif not isinstance(previous, str) or not _SHA256.fullmatch(previous):
        raise SeedProposalError("later raw objective revisions must cite the previous sha256 digest")

    source = _object(raw["source"], "raw_objective.source", {"kind", "reference"})
    if not isinstance(source["kind"], str) or source["kind"] not in _SOURCE_KINDS:
        raise SeedProposalError("raw objective source.kind is unsupported")
    source = {"kind": source["kind"],
              "reference": _text(source["reference"], "source.reference", 512)}
    scope = _object(raw["scope"], "raw_objective.scope", {"in_scope", "affected_paths"})
    in_scope = _text_list(scope["in_scope"], "scope.in_scope")
    paths = _text_list(scope["affected_paths"], "scope.affected_paths", maximum_items=200,
                       maximum_length=512)
    paths = [_safe_path(path, f"scope.affected_paths[{i}]") for i, path in enumerate(paths)]
    criteria = _text_list(raw["acceptance_criteria"], "acceptance_criteria",
                          required=True, maximum_items=100)
    depth = raw["max_depth"]
    if isinstance(depth, bool) or not isinstance(depth, int) or not 0 <= depth <= 4:
        raise SeedProposalError("max_depth must be an integer from 0 through 4")

    signatures = raw["reconciliation_signatures"]
    if not isinstance(signatures, dict):
        raise SeedProposalError("reconciliation_signatures must be an object")
    checked_signatures = {}
    for key, items in signatures.items():
        if not isinstance(key, str) or not _KEY.fullmatch(key):
            raise SeedProposalError("reconciliation signature keys must be canonical obligation keys")
        if not isinstance(items, list) or not 1 <= len(items) <= 20:
            raise SeedProposalError(f"signatures for {key!r} must contain 1-20 entries")
        checked = []
        for index, item in enumerate(items):
            item = _object(item, f"reconciliation_signatures.{key}[{index}]",
                           {"pattern", "path", "label"})
            path = item["path"]
            if path is not None:
                path = _safe_path(path, "reconciliation signature path")
            label = item["label"]
            if not isinstance(label, str) or len(label) > 256:
                raise SeedProposalError("reconciliation signature label must be text of at most 256 characters")
            checked.append({
                "pattern": _text(item["pattern"], "reconciliation signature pattern", 512),
                "path": path,
                "label": label,
            })
        checked_signatures[key] = checked

    return {
        "schema_version": RAW_OBJECTIVE_SCHEMA,
        "objective_id": objective_id,
        "revision": revision,
        "supersedes_sha256": previous,
        "original_text": _text(raw["original_text"], "original_text", 10000),
        "intent": _text(raw["intent"], "intent", 4000),
        "owner": _text(raw["owner"], "owner", 256),
        "source": source,
        "scope": {"in_scope": in_scope, "affected_paths": paths},
        "constraints": _text_list(raw["constraints"], "constraints"),
        "exclusions": _text_list(raw["exclusions"], "exclusions"),
        "assumptions": _text_list(raw["assumptions"], "assumptions"),
        "acceptance_criteria": criteria,
        "reconciliation_signatures": checked_signatures,
        "max_depth": depth,
    }


def _validate_seed_list(value: Any, proposer_kind: str, label: str) -> List[dict]:
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_SEEDS:
        raise SeedProposalError(f"{label} must contain 1-{MAX_SEEDS} seed obligations")
    result, keys = [], set()
    for index, item in enumerate(value):
        item = _object(item, f"{label}[{index}]", _SEED_FIELDS)
        key = _text(item["key"], f"{label}[{index}].key", 128)
        if not _KEY.fullmatch(key) or key in keys:
            raise SeedProposalError(f"{label} contains an invalid or duplicate canonical key: {key!r}")
        keys.add(key)
        kind = _text(item["kind"], f"{label}[{index}].kind", 64)
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", kind):
            raise SeedProposalError(f"{label}[{index}].kind must be lower_snake_case")
        classification = item["classification"]
        if not isinstance(classification, str) or classification not in _CLASSIFICATIONS:
            raise SeedProposalError(f"{label}[{index}] has an unsupported classification")
        confidence = item["confidence"]
        if not isinstance(confidence, str) or confidence not in ("stated", "inferred"):
            raise SeedProposalError(f"{label}[{index}].confidence must be stated or inferred")
        if proposer_kind == "external_llm" and confidence != "inferred":
            raise SeedProposalError("external-LLM seed obligations must remain inferred")
        result.append({
            "key": key,
            "title": _text(item["title"], f"{label}[{index}].title", 512),
            "kind": kind,
            "classification": classification,
            "rationale": _text(item["rationale"], f"{label}[{index}].rationale"),
            "impact": _text(item["impact"], f"{label}[{index}].impact"),
            "evidence_needs": _text_list(item["evidence_needs"],
                                         f"{label}[{index}].evidence_needs", required=True),
            "assumptions": _text_list(item["assumptions"], f"{label}[{index}].assumptions"),
            "confidence": confidence,
        })
    return result


def _validate_alternative(value: Any, raw: dict, label: str, proposer_kind: str) -> dict:
    item = _object(value, label, _ALTERNATIVE_FIELDS)
    alt_id = _text(item["alternative_id"], f"{label}.alternative_id", 64)
    if not _KEY.fullmatch(alt_id):
        raise SeedProposalError(f"{label}.alternative_id must use portable identifier characters")
    seeds = _validate_seed_list(item["seed_obligations"], proposer_kind,
                                f"{label}.seed_obligations")
    keys = {seed["key"] for seed in seeds}

    raw_edges = item["relationships"]
    if not isinstance(raw_edges, list) or len(raw_edges) > MAX_RELATIONSHIPS:
        raise SeedProposalError(f"{label}.relationships must be a list of at most {MAX_RELATIONSHIPS} edges")
    edges, seen = [], set()
    for index, edge in enumerate(raw_edges):
        edge = _object(edge, f"{label}.relationships[{index}]",
                       {"src", "dst", "kind", "authority", "reversible", "note"})
        src = _text(edge["src"], "relationship.src", 128)
        dst = _text(edge["dst"], "relationship.dst", 128)
        kind = edge["kind"]
        authority = edge["authority"]
        reversible = edge["reversible"]
        note = edge["note"]
        if src not in keys or dst not in keys:
            raise SeedProposalError("candidate relationships must connect declared seed keys")
        if (not isinstance(kind, str) or kind not in _RELATIONSHIP_KINDS
                or not isinstance(authority, str) or authority not in _AUTHORITY_LEVELS):
            raise SeedProposalError("candidate relationship kind or authority is unsupported")
        if reversible is not None and not isinstance(reversible, bool):
            raise SeedProposalError("relationship.reversible must be true, false, or null")
        if not isinstance(note, str) or len(note) > 2000:
            raise SeedProposalError("relationship.note must be text of at most 2000 characters")
        identity = (src, dst, kind)
        if identity in seen:
            raise SeedProposalError(f"duplicate candidate relationship: {identity!r}")
        seen.add(identity)
        edges.append({"src": src, "dst": dst, "kind": kind, "authority": authority,
                      "reversible": reversible, "note": note})

    signatures = item["reconciliation_signatures"]
    if not isinstance(signatures, dict) or set(signatures) - keys:
        raise SeedProposalError("candidate reconciliation signatures must refer only to its seed keys")
    checked_signatures = {}
    for key, entries in signatures.items():
        if not isinstance(entries, list) or not 1 <= len(entries) <= 20:
            raise SeedProposalError(f"candidate signatures for {key!r} must contain 1-20 entries")
        checked_signatures[key] = []
        for index, sig in enumerate(entries):
            sig = _object(sig, f"{label}.reconciliation_signatures.{key}[{index}]",
                          {"pattern", "path", "label"})
            path = sig["path"]
            if path is not None:
                path = _safe_path(path, "candidate signature path")
            if not isinstance(sig["label"], str) or len(sig["label"]) > 256:
                raise SeedProposalError("candidate signature label must be bounded text")
            checked_signatures[key].append({
                "pattern": _text(sig["pattern"], "candidate signature pattern", 512),
                "path": path, "label": sig["label"],
            })

    coverage = item["acceptance_criterion_coverage"]
    if not isinstance(coverage, list) or len(coverage) != len(raw["acceptance_criteria"]):
        raise SeedProposalError(f"{label}.acceptance_criterion_coverage must be a bounded list")
    covered = set()
    checked_coverage = []
    for index, entry in enumerate(coverage):
        entry = _object(entry, f"{label}.acceptance_criterion_coverage[{index}]",
                        {"criterion_index", "obligation_keys", "rationale"})
        criterion_index = entry["criterion_index"]
        if (isinstance(criterion_index, bool) or not isinstance(criterion_index, int)
                or not 0 <= criterion_index < len(raw["acceptance_criteria"])
                or criterion_index in covered):
            raise SeedProposalError("acceptance criterion coverage has an invalid or duplicate index")
        covered.add(criterion_index)
        obligation_keys = _text_list(entry["obligation_keys"], "coverage.obligation_keys",
                                     required=True, maximum_items=MAX_SEEDS, maximum_length=128)
        if set(obligation_keys) - keys:
            raise SeedProposalError("acceptance criterion coverage references an unknown seed key")
        checked_coverage.append({
            "criterion_index": criterion_index,
            "obligation_keys": obligation_keys,
            "rationale": _text(entry["rationale"], "coverage.rationale"),
        })

    return {
        "alternative_id": alt_id,
        "interpretation": _text(item["interpretation"], f"{label}.interpretation"),
        "seed_obligations": seeds,
        "relationships": edges,
        "reconciliation_signatures": checked_signatures,
        "assumptions": _text_list(item["assumptions"], f"{label}.assumptions"),
        "constraints": _text_list(item["constraints"], f"{label}.constraints"),
        "exclusions": _text_list(item["exclusions"], f"{label}.exclusions"),
        "acceptance_criterion_coverage": checked_coverage,
        "open_questions": _text_list(item["open_questions"], f"{label}.open_questions"),
        "disconfirming_cases": _text_list(item["disconfirming_cases"], f"{label}.disconfirming_cases"),
        "evidence_needs": _text_list(item["evidence_needs"], f"{label}.evidence_needs"),
    }


def _validate_proposal(raw_objective: Any, alternatives: Any, proposer_kind: str,
                       proposer_reference: str, source_reference: str,
                       supersedes_proposal_id: Optional[str]) -> dict:
    raw = validate_raw_objective(raw_objective)
    if proposer_kind not in ("human", "external_llm"):
        raise SeedProposalError("proposer_kind must be human or external_llm")
    proposer_reference = _text(proposer_reference, "proposer_reference", 512)
    source_reference = _text(source_reference, "source_reference", 1000)
    if not isinstance(alternatives, list) or not 2 <= len(alternatives) <= MAX_ALTERNATIVES:
        raise SeedProposalError(f"alternatives must contain 2-{MAX_ALTERNATIVES} competing interpretations")
    checked = [_validate_alternative(alt, raw, f"alternatives[{i}]", proposer_kind)
               for i, alt in enumerate(alternatives)]
    ids = [alt["alternative_id"] for alt in checked]
    if len(ids) != len(set(ids)):
        raise SeedProposalError("alternative_id values must be unique")
    interpretations = [" ".join(alt["interpretation"].split()).casefold() for alt in checked]
    if len(interpretations) != len(set(interpretations)):
        raise SeedProposalError("competing alternatives must preserve distinct interpretations")
    graph_digests = {_digest({"seed_obligations": alt["seed_obligations"],
                              "relationships": alt["relationships"]}) for alt in checked}
    if len(graph_digests) != len(checked):
        raise SeedProposalError("competing alternatives must contain distinct seed graphs")
    if supersedes_proposal_id is not None and (
        not isinstance(supersedes_proposal_id, str)
        or not _PROPOSAL_ID.fullmatch(supersedes_proposal_id)
    ):
        raise SeedProposalError("supersedes_proposal_id is invalid")
    body = {
        "schema_version": SCHEMA_VERSION,
        "raw_objective": raw,
        "raw_objective_sha256": _digest(raw),
        "alternatives": checked,
        "proposer_kind": proposer_kind,
        "proposer_reference": proposer_reference,
        "source_reference": source_reference,
        "supersedes_proposal_id": supersedes_proposal_id,
    }
    body["proposal_id"] = "seedprop_" + _digest(body)[:24]
    body["created_at"] = utc_now()
    return body


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SeedProposalError(f"duplicate JSON property: {key}")
        result[key] = value
    return result


class SeedProposalStore:
    """Append-only proposal/review ledger; approvals select but never execute seeds.

    Each proposal binds its alternatives to an exact raw-objective revision/hash.
    Reviewer and proposer identities are caller-attributed, not authenticated.
    """

    def __init__(self, path: str) -> None:
        self.path = os.path.abspath(path)

    @staticmethod
    def _snapshot(events: List[dict]) -> Dict[str, dict]:
        proposals: Dict[str, dict] = {}
        raw_revisions: Dict[tuple, str] = {}
        first_raw_objectives: Dict[str, dict] = {}
        for event in events:
            pid = event["proposal_id"]
            if event["event_kind"] == "proposal_submitted":
                record = event["record"]
                required = {
                    "schema_version", "raw_objective", "raw_objective_sha256",
                    "alternatives", "proposer_kind", "proposer_reference",
                    "source_reference", "supersedes_proposal_id", "proposal_id", "created_at",
                }
                if set(record) != required or record["schema_version"] != SCHEMA_VERSION:
                    raise SeedProposalError("persisted seed proposal has missing or unsupported fields")
                raw = validate_raw_objective(record["raw_objective"])
                raw_digest = _digest(raw)
                if record["raw_objective_sha256"] != raw_digest:
                    raise SeedProposalError("persisted raw-objective digest mismatch")
                identity = (raw["objective_id"], raw["revision"])
                previous_hash = raw_revisions.get((raw["objective_id"], raw["revision"] - 1))
                if raw["revision"] == 1:
                    if raw["supersedes_sha256"] is not None:
                        raise SeedProposalError("raw objective revision 1 has invalid predecessor")
                elif previous_hash is None or raw["supersedes_sha256"] != previous_hash:
                    raise SeedProposalError("raw objective revision chain is missing or broken")
                old_hash = raw_revisions.get(identity)
                if old_hash is not None and old_hash != raw_digest:
                    raise SeedProposalError("one raw-objective revision is bound to conflicting content")
                first_raw = first_raw_objectives.setdefault(raw["objective_id"], raw)
                if (raw["original_text"] != first_raw["original_text"]
                        or raw["intent"] != first_raw["intent"]):
                    raise SeedProposalError(
                        "raw objective original_text and intent are immutable across revisions"
                    )
                raw_revisions[identity] = raw_digest
                alternatives = record["alternatives"]
                if not isinstance(alternatives, list) or not 2 <= len(alternatives) <= MAX_ALTERNATIVES:
                    raise SeedProposalError("persisted proposal alternatives are invalid")
                checked = [_validate_alternative(alt, raw, f"persisted alternatives[{i}]", record["proposer_kind"])
                           for i, alt in enumerate(alternatives)]
                if checked != alternatives:
                    raise SeedProposalError("persisted seed proposal alternative is not canonical")
                alt_ids = [alt["alternative_id"] for alt in checked]
                interpretations = [" ".join(alt["interpretation"].split()).casefold() for alt in checked]
                graph_digests = {_digest({"seed_obligations": alt["seed_obligations"],
                                          "relationships": alt["relationships"]}) for alt in checked}
                if (len(alt_ids) != len(set(alt_ids))
                        or len(interpretations) != len(set(interpretations))
                        or len(graph_digests) != len(checked)):
                    raise SeedProposalError("persisted alternatives are not distinct competing seed graphs")
                identity_body = dict(record)
                identity_body.pop("proposal_id", None)
                identity_body.pop("created_at", None)
                expected = "seedprop_" + _digest(identity_body)[:24]
                if pid != expected or record["proposal_id"] != pid or pid in proposals:
                    raise SeedProposalError("duplicate or mismatched seed proposal identity")
                predecessor_id = record["supersedes_proposal_id"]
                if predecessor_id is not None:
                    if not isinstance(predecessor_id, str) or not _PROPOSAL_ID.fullmatch(predecessor_id):
                        raise SeedProposalError("seed proposal supersession lineage is invalid")
                    predecessor = proposals.get(predecessor_id)
                    if (predecessor is None
                            or predecessor["status"] not in ("changes_requested", "rejected")
                            or predecessor["proposal"]["raw_objective_sha256"] != raw_digest):
                        raise SeedProposalError("seed proposal supersession lineage is invalid")
                _text(record["proposer_reference"], "proposer_reference", 512)
                _text(record["source_reference"], "source_reference", 1000)
                if record["proposer_kind"] not in ("human", "external_llm"):
                    raise SeedProposalError("persisted proposer_kind is invalid")
                _text(record["created_at"], "created_at", 128)
                proposals[pid] = {"proposal": record, "status": "candidate",
                                  "latest_review": None}
            else:
                current = proposals.get(pid)
                if current is None:
                    raise SeedProposalError("review decision refers to an unknown seed proposal")
                if current["latest_review"] is not None:
                    raise SeedProposalError("seed proposal has more than one review decision")
                review = event["record"]
                if not isinstance(review, dict) or set(review) != {
                    "decision", "selected_alternative_id", "reviewer",
                    "source_reference", "rationale", "evidence_references",
                }:
                    raise SeedProposalError("seed proposal review record has invalid fields")
                decision = review["decision"]
                selected = review["selected_alternative_id"]
                alt_ids = {a["alternative_id"] for a in current["proposal"]["alternatives"]}
                if not isinstance(decision, str) or decision not in _REVIEW_DECISIONS:
                    raise SeedProposalError("seed proposal review decision is invalid")
                if decision == "approved":
                    if not isinstance(selected, str) or selected not in alt_ids:
                        raise SeedProposalError("approval must select one existing alternative explicitly")
                elif selected is not None:
                    raise SeedProposalError("only approval may select an alternative")
                _text(review["reviewer"], "reviewer", 256)
                _text(review["source_reference"], "source_reference", 1000)
                _text(review["rationale"], "rationale")
                _text_list(review["evidence_references"], "evidence_references", required=True)
                current["status"] = decision
                current["latest_review"] = review
        return proposals

    @staticmethod
    def _parse_events(lines: List[str]) -> List[dict]:
        if len(lines) > MAX_LEDGER_EVENTS:
            raise SeedProposalError("seed-proposal ledger exceeds event limit")
        events, previous = [], None
        for number, line in enumerate(lines, 1):
            if not line.endswith("\n") or not line.strip():
                raise SeedProposalError(f"seed-proposal ledger line {number} is blank or unterminated")
            try:
                event = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
            except (json.JSONDecodeError, ValueError) as exc:
                raise SeedProposalError(f"invalid seed-proposal JSON on line {number}: {exc}") from exc
            if not isinstance(event, dict) or set(event) != {
                "schema_version", "sequence", "previous_event_sha256", "event_kind",
                "proposal_id", "recorded_at", "record", "event_sha256",
            }:
                raise SeedProposalError(f"seed-proposal event shape is invalid on line {number}")
            if (event["schema_version"] != EVENT_SCHEMA_VERSION
                    or isinstance(event["sequence"], bool)
                    or not isinstance(event["sequence"], int)
                    or event["sequence"] != number
                    or event["previous_event_sha256"] != previous):
                raise SeedProposalError(f"seed-proposal event chain is invalid on line {number}")
            if event["event_kind"] not in ("proposal_submitted", "review_decision"):
                raise SeedProposalError(f"unsupported seed-proposal event kind on line {number}")
            if not isinstance(event["proposal_id"], str) or not _PROPOSAL_ID.fullmatch(event["proposal_id"]):
                raise SeedProposalError(f"invalid seed-proposal identity on line {number}")
            recorded_at = _text(event["recorded_at"], "recorded_at", 128)
            try:
                parsed = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
            except ValueError as exc:
                raise SeedProposalError("recorded_at must be ISO-8601") from exc
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise SeedProposalError("recorded_at must include a timezone offset")
            body = dict(event)
            claimed = body.pop("event_sha256")
            if not isinstance(claimed, str) or not _SHA256.fullmatch(claimed) or claimed != _digest(body):
                raise SeedProposalError(f"seed-proposal event digest mismatch on line {number}")
            if not isinstance(event["record"], dict):
                raise SeedProposalError(f"seed-proposal event record is invalid on line {number}")
            events.append(event)
            previous = claimed
        return events

    def _read_events(self) -> List[dict]:
        # Check symlink identity before exists(): exists() is false for a
        # dangling symlink, which must not be mistaken for an absent ledger.
        if os.path.islink(self.path):
            raise SeedProposalError("seed-proposal ledger path must not be a symlink")
        if not os.path.exists(self.path):
            return []
        if os.path.getsize(self.path) > MAX_LEDGER_BYTES:
            raise SeedProposalError("seed-proposal ledger exceeds byte limit")
        with open(self.path, "r", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_SH)
            try:
                lines = fh.readlines()
                if lines and not lines[-1].endswith("\n"):
                    raise SeedProposalError("seed-proposal ledger final event is not newline terminated")
                events = self._parse_events(lines)
                self._snapshot(events)
                return events
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    def _append(self, kind: str, proposal_id: str, record: dict) -> dict:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        if os.path.islink(self.path):
            raise SeedProposalError("seed-proposal ledger path must not be a symlink")
        created = not os.path.exists(self.path)
        with open(self.path, "a+", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                fh.seek(0, os.SEEK_END)
                if fh.tell() > MAX_LEDGER_BYTES:
                    raise SeedProposalError("seed-proposal ledger exceeds byte limit")
                fh.seek(0)
                lines = fh.readlines()
                if lines and not lines[-1].endswith("\n"):
                    raise SeedProposalError("seed-proposal ledger final event is not newline terminated")
                events = self._parse_events(lines)
                snapshot = self._snapshot(events)
                if len(events) >= MAX_LEDGER_EVENTS:
                    raise SeedProposalError("seed-proposal ledger exceeds event limit")
                if kind == "proposal_submitted":
                    if proposal_id in snapshot:
                        raise SeedProposalError("seed proposal was submitted concurrently; reload before retrying")
                else:
                    current = snapshot.get(proposal_id)
                    if current is None:
                        raise SeedProposalError("cannot review an unknown seed proposal")
                    if current["latest_review"] is not None:
                        raise SeedProposalError("seed proposal already has a review decision")
                base = {
                    "schema_version": EVENT_SCHEMA_VERSION,
                    "sequence": len(events) + 1,
                    "previous_event_sha256": events[-1]["event_sha256"] if events else None,
                    "event_kind": kind,
                    "proposal_id": proposal_id,
                    "recorded_at": utc_now(),
                    "record": record,
                }
                event = dict(base)
                event["event_sha256"] = _digest(base)
                # Validate the prospective event against the entire ledger while
                # still holding the lock; never persist an event that poisons replay.
                self._snapshot(events + [event])
                encoded = _canonical(event) + "\n"
                fh.seek(0, os.SEEK_END)
                if fh.tell() + len(encoded.encode("utf-8")) > MAX_LEDGER_BYTES:
                    raise SeedProposalError("seed-proposal ledger exceeds byte limit")
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

    def submit(self, raw_objective: dict, alternatives: list, *, proposer_kind: str,
               proposer_reference: str, source_reference: str,
               supersedes_proposal_id: Optional[str] = None) -> dict:
        proposal = _validate_proposal(
            raw_objective, alternatives, proposer_kind, proposer_reference,
            source_reference, supersedes_proposal_id,
        )
        snapshot = self._snapshot(self._read_events())
        pid = proposal["proposal_id"]
        if pid in snapshot:
            old = dict(snapshot[pid]["proposal"])
            new = dict(proposal)
            old.pop("created_at", None)
            new.pop("created_at", None)
            if old != new:
                raise SeedProposalError("seed proposal ID collision with different content")
            return self.get(pid)
        if supersedes_proposal_id is not None:
            prior = snapshot.get(supersedes_proposal_id)
            if prior is None or prior["status"] not in ("changes_requested", "rejected"):
                raise SeedProposalError("superseded proposal must be changes_requested or rejected")
            if prior["proposal"]["raw_objective_sha256"] != proposal["raw_objective_sha256"]:
                raise SeedProposalError("revised proposal must remain bound to the same raw-objective revision")
        self._append("proposal_submitted", pid, proposal)
        return self.get(pid)

    def review(self, proposal_id: str, decision: str, *, reviewer: str,
               source_reference: str, rationale: str,
               evidence_references: List[str],
               selected_alternative_id: Optional[str] = None) -> dict:
        if not isinstance(proposal_id, str) or not _PROPOSAL_ID.fullmatch(proposal_id):
            raise SeedProposalError("proposal_id is invalid")
        if not isinstance(decision, str) or decision not in _REVIEW_DECISIONS:
            raise SeedProposalError(f"decision must be one of {sorted(_REVIEW_DECISIONS)}")
        snapshot = self._snapshot(self._read_events())
        current = snapshot.get(proposal_id)
        if current is None:
            raise SeedProposalError("cannot review an unknown seed proposal")
        if current["latest_review"] is not None:
            raise SeedProposalError("seed proposal already has a review decision; submit a new revision")
        alt_ids = {a["alternative_id"] for a in current["proposal"]["alternatives"]}
        if decision == "approved" and (not isinstance(selected_alternative_id, str) or selected_alternative_id not in alt_ids):
            raise SeedProposalError("approval must select one existing alternative explicitly")
        if decision != "approved" and selected_alternative_id is not None:
            raise SeedProposalError("only approval may select an alternative")
        record = {
            "decision": decision,
            "selected_alternative_id": selected_alternative_id,
            "reviewer": _text(reviewer, "reviewer", 256),
            "source_reference": _text(source_reference, "source_reference", 1000),
            "rationale": _text(rationale, "rationale"),
            "evidence_references": _text_list(evidence_references, "evidence_references", required=True),
        }
        self._append("review_decision", proposal_id, record)
        return self.get(proposal_id)

    def get(self, proposal_id: str) -> dict:
        if not isinstance(proposal_id, str) or not _PROPOSAL_ID.fullmatch(proposal_id):
            raise SeedProposalError("proposal_id is invalid")
        snapshot = self._snapshot(self._read_events())
        if proposal_id not in snapshot:
            raise SeedProposalError("unknown seed proposal")
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

    def history(self, proposal_id: Optional[str] = None) -> dict:
        """Return proposals and events derived from one locked ledger snapshot."""
        events = self._read_events()
        snapshot = self._snapshot(events)
        if proposal_id is not None:
            if not isinstance(proposal_id, str) or not _PROPOSAL_ID.fullmatch(proposal_id):
                raise SeedProposalError("proposal_id is invalid")
            if proposal_id not in snapshot:
                raise SeedProposalError("unknown seed proposal")
            snapshot = {proposal_id: snapshot[proposal_id]}
        proposal_ids = set(snapshot)
        proposals = [
            {
                "proposal": json.loads(_canonical(item["proposal"])),
                "status": item["status"],
                "latest_review": json.loads(_canonical(item["latest_review"]))
                if item["latest_review"] is not None else None,
            }
            for item in snapshot.values()
        ]
        return {
            "proposal_count": len(proposals),
            "proposals": proposals,
            "events": [
                event for event in events
                if event.get("proposal_id") in proposal_ids
            ],
        }

    def approved_selection(self, proposal_id: str) -> dict:
        """Return the selected candidate only after an explicit recorded approval."""
        item = self.get(proposal_id)
        if item["status"] != "approved" or item["latest_review"] is None:
            raise SeedProposalError("seed proposal has no explicit approval")
        selected_id = item["latest_review"]["selected_alternative_id"]
        alternative = next(
            alt for alt in item["proposal"]["alternatives"]
            if alt["alternative_id"] == selected_id
        )
        return {
            "proposal_id": proposal_id,
            "raw_objective": item["proposal"]["raw_objective"],
            "raw_objective_sha256": item["proposal"]["raw_objective_sha256"],
            "selected_alternative_id": selected_id,
            "alternative": alternative,
            "approval": item["latest_review"],
        }
