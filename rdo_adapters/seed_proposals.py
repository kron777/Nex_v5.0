"""Provider-neutral, review-gated seed graph proposals for raw objectives.

Candidate alternatives remain inert until an attributed review selects one.
The approved result is converted to objective.v1 only by explicit seed-intake.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
from typing import Any, Dict, List, Optional

from watcher.evidence import utc_now

from .objective_intake import (
    ObjectiveInputError, RAW_OBJECTIVE_SCHEMA_VERSION, SCHEMA_VERSION,
    _canonical_json, _digest, _object, _text, _text_list,
    validate_objective, validate_raw_objective,
)

EVENT_SCHEMA = "rdo.seed_proposal_event.v1"
MAX_LEDGER_BYTES = 32 * 1024 * 1024
MAX_LEDGER_EVENTS = 10000
_PROPOSAL_ID = re.compile(r"seedprop_[0-9a-f]{24}\Z")
_ALT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_EVENT_KINDS = {"proposal_submitted", "proposal_reviewed"}
_DECISIONS = {"changes_requested", "approved", "rejected"}


class SeedProposalError(ValueError):
    """Invalid, conflicting, unreviewed or tampered seed proposal."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise SeedProposalError(f"seed proposal is not canonical JSON: {exc}") from exc


def _event_digest(event: dict) -> str:
    return hashlib.sha256(_canonical({
        key: value for key, value in event.items() if key != "event_sha256"
    })).hexdigest()


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SeedProposalError(f"duplicate JSON property: {key}")
        result[key] = value
    return result


def _references(value: Any, name: str) -> List[str]:
    return _text_list(value, name, max_items=1000, max_length=1000, allow_empty=False)


def _build_objective(raw: dict, alternative: dict, revision: int = 1,
                     supersedes_sha256: Optional[str] = None) -> dict:
    return validate_objective({
        "schema_version": SCHEMA_VERSION,
        "objective_id": raw["objective_id"],
        "revision": revision,
        "supersedes_sha256": supersedes_sha256,
        "original_text": raw["original_text"],
        "intent": raw["intent"],
        "owner": raw["owner"],
        "source": raw["source"],
        "scope": raw["scope"],
        "constraints": raw["constraints"],
        "exclusions": raw["exclusions"],
        "assumptions": list(dict.fromkeys(raw["assumptions"] + alternative["assumptions"])),
        "acceptance_criteria": raw["acceptance_criteria"],
        "seed_obligations": alternative["seed_obligations"],
        "relationships": alternative["relationships"],
        "reconciliation_signatures": alternative["reconciliation_signatures"],
        "max_depth": raw["max_depth"],
    })


def _validate_alternative(raw: dict, value: Any, index: int) -> dict:
    name = f"alternatives[{index}]"
    alt = _object(value, name, {
        "id", "label", "interpretation", "seed_obligations", "relationships",
        "reconciliation_signatures", "assumptions", "evidence_needs",
        "acceptance_coverage", "open_questions", "disconfirming_cases", "provenance",
    }, optional={"candidate_objective_sha256"})
    alt_id = _text(alt["id"], f"{name}.id", max_length=64)
    if not _ALT_ID.fullmatch(alt_id):
        raise SeedProposalError(f"{name}.id must use portable identifier characters")
    label = _text(alt["label"], f"{name}.label", max_length=256)
    interpretation = _text(alt["interpretation"], f"{name}.interpretation", max_length=4000)
    assumptions = _text_list(alt["assumptions"], f"{name}.assumptions")
    evidence_needs = _text_list(
        alt["evidence_needs"], f"{name}.evidence_needs", allow_empty=False
    )
    open_questions = _text_list(alt["open_questions"], f"{name}.open_questions")
    disconfirming_cases = _text_list(
        alt["disconfirming_cases"], f"{name}.disconfirming_cases", allow_empty=False
    )
    provenance = _references(alt["provenance"], f"{name}.provenance")
    if not isinstance(alt["seed_obligations"], list) or not alt["seed_obligations"]:
        raise SeedProposalError(f"{name}.seed_obligations must contain at least one seed")
    if not isinstance(alt["relationships"], list):
        raise SeedProposalError(f"{name}.relationships must be a list")
    if not isinstance(alt["reconciliation_signatures"], dict):
        raise SeedProposalError(f"{name}.reconciliation_signatures must be an object")

    candidate = _build_objective(raw, {
        "assumptions": assumptions,
        "seed_obligations": alt["seed_obligations"],
        "relationships": alt["relationships"],
        "reconciliation_signatures": alt["reconciliation_signatures"],
    })
    seed_keys = {seed["key"] for seed in candidate["seed_obligations"]}
    coverage = alt["acceptance_coverage"]
    if not isinstance(coverage, list) or len(coverage) != len(raw["acceptance_criteria"]):
        raise SeedProposalError(
            f"{name}.acceptance_coverage must map every acceptance criterion exactly once"
        )
    normalized_coverage = []
    seen_criteria = set()
    criteria = set(raw["acceptance_criteria"])
    for ci, item in enumerate(coverage):
        item = _object(item, f"{name}.acceptance_coverage[{ci}]",
                       {"criterion", "obligation_keys"})
        criterion = _text(item["criterion"], f"{name}.acceptance_coverage[{ci}].criterion",
                           max_length=2000)
        if criterion not in criteria or criterion in seen_criteria:
            raise SeedProposalError(f"{name}.acceptance_coverage contains an unknown or duplicate criterion")
        keys = _text_list(item["obligation_keys"],
                          f"{name}.acceptance_coverage[{ci}].obligation_keys",
                          max_items=200, max_length=128, allow_empty=False)
        unknown = sorted(set(keys) - seed_keys)
        if unknown:
            raise SeedProposalError(f"{name}.acceptance_coverage references unknown seed keys: {unknown}")
        seen_criteria.add(criterion)
        normalized_coverage.append({"criterion": criterion, "obligation_keys": keys})
    if seen_criteria != criteria:
        raise SeedProposalError(f"{name}.acceptance_coverage does not cover every acceptance criterion")

    candidate_digest = _digest(candidate)
    supplied_digest = alt.get("candidate_objective_sha256")
    if supplied_digest is not None and supplied_digest != candidate_digest:
        raise SeedProposalError(f"{name}.candidate_objective_sha256 does not match the validated objective")
    return {
        "id": alt_id,
        "label": label,
        "interpretation": interpretation,
        "seed_obligations": candidate["seed_obligations"],
        "relationships": candidate["relationships"],
        "reconciliation_signatures": candidate["reconciliation_signatures"],
        "assumptions": assumptions,
        "evidence_needs": evidence_needs,
        "acceptance_coverage": normalized_coverage,
        "open_questions": open_questions,
        "disconfirming_cases": disconfirming_cases,
        "provenance": provenance,
        "candidate_objective_sha256": candidate_digest,
    }


def _proposal_identity(record: dict) -> dict:
    return {
        "raw_objective_sha256": record["raw_objective_sha256"],
        "alternatives": record["alternatives"],
        "proposer_kind": record["proposer_kind"],
        "proposer_reference": record["proposer_reference"],
        "source_reference": record["source_reference"],
        "supersedes_proposal_id": record["supersedes_proposal_id"],
    }


class SeedProposalStore:
    """Append-only candidate/review ledger. Approval is required before seed intake."""

    def __init__(self, path: str) -> None:
        self.path = os.path.abspath(path)

    def _read_unlocked(self, fh) -> List[dict]:
        fh.seek(0)
        events = []
        previous = None
        for number, line in enumerate(fh, 1):
            if not line.strip():
                raise SeedProposalError(f"blank seed proposal ledger line {number}")
            try:
                event = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
            except (json.JSONDecodeError, SeedProposalError) as exc:
                raise SeedProposalError(f"invalid seed proposal ledger JSON on line {number}: {exc}") from exc
            if not isinstance(event, dict) or set(event) != {
                "schema_version", "sequence", "previous_event_sha256",
                "event_kind", "proposal_id", "recorded_at", "record", "event_sha256",
            }:
                raise SeedProposalError(f"seed proposal ledger event shape is invalid on line {number}")
            if event["schema_version"] != EVENT_SCHEMA or event["event_kind"] not in _EVENT_KINDS:
                raise SeedProposalError(f"unsupported seed proposal event on line {number}")
            if (isinstance(event["sequence"], bool) or not isinstance(event["sequence"], int)
                    or event["sequence"] != number or event["previous_event_sha256"] != previous):
                raise SeedProposalError(f"seed proposal event chain is invalid on line {number}")
            if (not isinstance(event["proposal_id"], str)
                    or not _PROPOSAL_ID.fullmatch(event["proposal_id"])
                    or not isinstance(event["recorded_at"], str) or not event["recorded_at"].strip()):
                raise SeedProposalError(f"seed proposal event identity is invalid on line {number}")
            if event["event_sha256"] != _event_digest(event):
                raise SeedProposalError(f"seed proposal event digest mismatch on line {number}")
            if not isinstance(event["record"], dict):
                raise SeedProposalError(f"seed proposal event record is invalid on line {number}")
            events.append(event)
            previous = event["event_sha256"]
            if len(events) > MAX_LEDGER_EVENTS:
                raise SeedProposalError("seed proposal ledger event limit exceeded")
        return events

    def events(self) -> List[dict]:
        if not os.path.exists(self.path):
            return []
        if os.path.islink(self.path):
            raise SeedProposalError("seed proposal ledger must not be a symlink")
        if os.path.getsize(self.path) > MAX_LEDGER_BYTES:
            raise SeedProposalError("seed proposal ledger size limit exceeded")
        with open(self.path, "r", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_SH)
            try:
                return self._read_unlocked(fh)
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    def _append(self, event_kind: str, proposal_id: str, record: dict) -> dict:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        if os.path.islink(self.path):
            raise SeedProposalError("seed proposal ledger must not be a symlink")
        with open(self.path, "a+", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                if os.fstat(fh.fileno()).st_size > MAX_LEDGER_BYTES:
                    raise SeedProposalError("seed proposal ledger size limit exceeded")
                events = self._read_unlocked(fh)
                if len(events) >= MAX_LEDGER_EVENTS:
                    raise SeedProposalError("seed proposal ledger event limit exceeded")
                event = {
                    "schema_version": EVENT_SCHEMA,
                    "sequence": len(events) + 1,
                    "previous_event_sha256": events[-1]["event_sha256"] if events else None,
                    "event_kind": event_kind,
                    "proposal_id": proposal_id,
                    "recorded_at": utc_now(),
                    "record": record,
                }
                event["event_sha256"] = _event_digest(event)
                fh.seek(0, os.SEEK_END)
                encoded = json.dumps(event, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False) + "\n"
                if fh.tell() + len(encoded.encode("utf-8")) > MAX_LEDGER_BYTES:
                    raise SeedProposalError("seed proposal ledger size limit exceeded")
                fh.write(encoded)
                fh.flush()
                os.fsync(fh.fileno())
                return event
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    def _state(self) -> dict:
        events = self.events()
        proposals = {}
        proposal_events = {}
        reviews = {}
        superseded = {}
        for event in events:
            proposal_id = event["proposal_id"]
            record = event["record"]
            if event["event_kind"] == "proposal_submitted":
                if proposal_id in proposals:
                    raise SeedProposalError("duplicate seed proposal ID in ledger")
                if set(record) != {
                    "proposal_id", "raw_objective", "raw_objective_sha256", "alternatives",
                    "proposer_kind", "proposer_reference", "source_reference",
                    "supersedes_proposal_id", "created_at",
                } or record.get("proposal_id") != proposal_id:
                    raise SeedProposalError("seed proposal record shape or identity is invalid")
                raw = validate_raw_objective(record["raw_objective"])
                if record["raw_objective"] != raw:
                    raise SeedProposalError("raw objective record is not in canonical validated form")
                raw_hash = _digest(raw)
                if record.get("raw_objective_sha256") != raw_hash:
                    raise SeedProposalError("raw objective digest mismatch in proposal ledger")
                alternatives = record.get("alternatives")
                if not isinstance(alternatives, list) or not 1 <= len(alternatives) <= 8:
                    raise SeedProposalError("proposal must preserve 1-8 seed alternatives")
                normalized = [
                    _validate_alternative(raw, alternative, index)
                    for index, alternative in enumerate(alternatives)
                ]
                if len({item["id"] for item in normalized}) != len(normalized):
                    raise SeedProposalError("seed alternative IDs must be unique")
                if record.get("alternatives") != normalized:
                    raise SeedProposalError("seed proposal alternatives are not canonical")
                if (not isinstance(record.get("proposer_kind"), str)
                        or record["proposer_kind"] not in {"human", "external_llm", "imported"}):
                    raise SeedProposalError("invalid seed proposal proposer_kind")
                for key in ("proposer_reference", "source_reference", "created_at"):
                    if not isinstance(record.get(key), str) or not record[key].strip():
                        raise SeedProposalError(f"seed proposal {key} must be non-empty text")
                supersedes_id = record.get("supersedes_proposal_id")
                if supersedes_id is not None and (
                    not isinstance(supersedes_id, str) or not _PROPOSAL_ID.fullmatch(supersedes_id)
                ):
                    raise SeedProposalError("invalid supersedes_proposal_id")
                identity = _proposal_identity(record)
                expected_id = "seedprop_" + hashlib.sha256(_canonical(identity)).hexdigest()[:24]
                if proposal_id != expected_id:
                    raise SeedProposalError("seed proposal ID does not match its content")
                proposals[proposal_id] = record
                proposal_events[proposal_id] = event
                reviews[proposal_id] = []
                if supersedes_id:
                    prior = proposals.get(supersedes_id)
                    if prior is None:
                        raise SeedProposalError("superseded seed proposal must precede its revision")
                    if prior["raw_objective_sha256"] != raw_hash:
                        raise SeedProposalError("seed proposal revision must preserve the exact raw objective")
                    if superseded.get(supersedes_id):
                        raise SeedProposalError("seed proposal revision target is already superseded")
                    prior_reviews = reviews[supersedes_id]
                    if prior_reviews and prior_reviews[-1]["record"]["decision"] == "approved":
                        raise SeedProposalError(
                            "an approved seed proposal cannot be superseded in place; create a new raw revision"
                        )
                    superseded[supersedes_id] = proposal_id
            else:
                if proposal_id not in proposals:
                    raise SeedProposalError("seed proposal review precedes its candidate")
                if superseded.get(proposal_id):
                    raise SeedProposalError("a superseded seed proposal cannot be reviewed")
                review = _object(record, "seed proposal review", {
                    "decision", "reviewer", "source_reference", "rationale",
                    "evidence_references", "selected_alternative_id",
                })
                decision = review["decision"]
                if not isinstance(decision, str) or decision not in _DECISIONS:
                    raise SeedProposalError("invalid seed proposal review decision")
                for key in ("reviewer", "source_reference", "rationale"):
                    if not isinstance(review[key], str) or not review[key].strip():
                        raise SeedProposalError(f"review {key} must be non-empty text")
                _references(review["evidence_references"], "review.evidence_references")
                selected = review["selected_alternative_id"]
                alternatives = {alt["id"] for alt in proposals[proposal_id]["alternatives"]}
                if decision == "approved":
                    if not isinstance(selected, str) or selected not in alternatives:
                        raise SeedProposalError("approval must select one declared seed alternative")
                    prior_reviews = reviews[proposal_id]
                    if prior_reviews and prior_reviews[-1]["record"]["decision"] in {"approved", "rejected"}:
                        raise SeedProposalError("terminal seed proposal decision cannot be overwritten")
                    for other_id, other in proposals.items():
                        if other_id == proposal_id or other["raw_objective_sha256"] != proposals[proposal_id]["raw_objective_sha256"]:
                            continue
                        if reviews[other_id] and reviews[other_id][-1]["record"]["decision"] == "approved" and not superseded.get(other_id):
                            raise SeedProposalError("raw objective already has an approved seed proposal; supersede it explicitly")
                elif selected is not None:
                    raise SeedProposalError("only an approved seed proposal may select an alternative")
                if reviews[proposal_id] and reviews[proposal_id][-1]["record"]["decision"] in {"approved", "rejected"}:
                    raise SeedProposalError("terminal seed proposal decision cannot be overwritten")
                reviews[proposal_id].append(event)

        # Raw objective revisions are immutable and sequential within an objective ID.
        raw_versions = {}
        for record in proposals.values():
            raw = record["raw_objective"]
            key = (raw["objective_id"], raw["raw_revision"])
            prior_hash = raw_versions.get(key)
            if prior_hash is not None and prior_hash != record["raw_objective_sha256"]:
                raise SeedProposalError("raw objective revision already exists with different content")
            raw_versions[key] = record["raw_objective_sha256"]
        for (objective_id, raw_revision), raw_hash in raw_versions.items():
            if raw_revision == 1:
                continue
            prior_hash = raw_versions.get((objective_id, raw_revision - 1))
            if prior_hash is None:
                raise SeedProposalError("raw objective revision is missing its predecessor")
            records = [
                p["raw_objective"] for p in proposals.values()
                if p["raw_objective"]["objective_id"] == objective_id
                and p["raw_objective"]["raw_revision"] == raw_revision
            ]
            if any(r["supersedes_raw_sha256"] != prior_hash for r in records):
                raise SeedProposalError("raw objective revision does not cite the previous raw digest")
        return {
            "events": events, "proposals": proposals, "proposal_events": proposal_events,
            "reviews": reviews, "superseded": superseded,
        }

    def submit(self, raw_objective: Any, alternatives: Any, proposer_kind: str,
               proposer_reference: str, source_reference: str,
               supersedes_proposal_id: Optional[str] = None) -> dict:
        raw = validate_raw_objective(raw_objective)
        if not isinstance(alternatives, list) or not 1 <= len(alternatives) <= 8:
            raise SeedProposalError("alternatives must contain 1-8 competing seed graphs")
        normalized = [
            _validate_alternative(raw, alternative, index)
            for index, alternative in enumerate(alternatives)
        ]
        if len({item["id"] for item in normalized}) != len(normalized):
            raise SeedProposalError("seed alternative IDs must be unique")
        if not isinstance(proposer_kind, str) or proposer_kind not in {"human", "external_llm", "imported"}:
            raise SeedProposalError("proposer_kind must be human, external_llm or imported")
        proposer_reference = _text(proposer_reference, "proposer_reference", max_length=512)
        source_reference = _text(source_reference, "source_reference", max_length=512)
        state = self._state()
        raw_hash = _digest(raw)
        prior_raws = [
            p["raw_objective"] for p in state["proposals"].values()
            if p["raw_objective"]["objective_id"] == raw["objective_id"]
            and p["raw_objective"]["raw_revision"] == raw["raw_revision"]
        ]
        if prior_raws and any(_digest(item) != raw_hash for item in prior_raws):
            raise SeedProposalError("raw objective revision is immutable; increment raw_revision")
        if raw["raw_revision"] > 1:
            prior_hashes = {
                p["raw_objective_sha256"] for p in state["proposals"].values()
                if p["raw_objective"]["objective_id"] == raw["objective_id"]
                and p["raw_objective"]["raw_revision"] == raw["raw_revision"] - 1
            }
            if raw["supersedes_raw_sha256"] not in prior_hashes:
                raise SeedProposalError("raw revision must cite the preceding raw objective digest")
        elif raw["supersedes_raw_sha256"] is not None:
            raise SeedProposalError("raw revision 1 must not supersede another raw record")
        if supersedes_proposal_id is not None:
            if not isinstance(supersedes_proposal_id, str) or not _PROPOSAL_ID.fullmatch(supersedes_proposal_id):
                raise SeedProposalError("invalid supersedes_proposal_id")
            prior = state["proposals"].get(supersedes_proposal_id)
            if prior is None or state["superseded"].get(supersedes_proposal_id):
                raise SeedProposalError("supersedes_proposal_id must identify an active prior proposal")
            prior_reviews = state["reviews"][supersedes_proposal_id]
            if prior_reviews and prior_reviews[-1]["record"]["decision"] == "approved":
                raise SeedProposalError(
                    "an approved seed proposal cannot be superseded in place; create a new raw revision"
                )
            if prior["raw_objective_sha256"] != raw_hash:
                raise SeedProposalError("candidate revision must retain the exact raw objective digest")
        record = {
            "proposal_id": "",
            "raw_objective": raw,
            "raw_objective_sha256": raw_hash,
            "alternatives": normalized,
            "proposer_kind": proposer_kind,
            "proposer_reference": proposer_reference,
            "source_reference": source_reference,
            "supersedes_proposal_id": supersedes_proposal_id,
            "created_at": utc_now(),
        }
        proposal_id = "seedprop_" + hashlib.sha256(_canonical(_proposal_identity(record))).hexdigest()[:24]
        record["proposal_id"] = proposal_id
        existing = state["proposals"].get(proposal_id)
        if existing is not None:
            if _proposal_identity(existing) != _proposal_identity(record):
                raise SeedProposalError("seed proposal ID collision with different content")
            return {"proposal_id": proposal_id, "proposal": existing, "replayed": True}
        event = self._append("proposal_submitted", proposal_id, record)
        return {"proposal_id": proposal_id, "proposal": record, "event": event, "replayed": False}

    def get_proposal(self, proposal_id: str) -> dict:
        if not isinstance(proposal_id, str) or not _PROPOSAL_ID.fullmatch(proposal_id):
            raise SeedProposalError("invalid proposal_id")
        state = self._state()
        proposal = state["proposals"].get(proposal_id)
        if proposal is None:
            raise SeedProposalError("seed proposal does not exist")
        return proposal

    def review(self, proposal_id: str, decision: str, reviewer: str,
               source_reference: str, rationale: str,
               evidence_references: List[str],
               selected_alternative_id: Optional[str] = None) -> dict:
        proposal = self.get_proposal(proposal_id)
        state = self._state()
        if state["superseded"].get(proposal_id):
            raise SeedProposalError("a superseded seed proposal cannot be reviewed")
        if not isinstance(decision, str) or decision not in _DECISIONS:
            raise SeedProposalError(f"decision must be one of {sorted(_DECISIONS)}")
        reviewer = _text(reviewer, "reviewer", max_length=256)
        source_reference = _text(source_reference, "source_reference", max_length=512)
        rationale = _text(rationale, "rationale", max_length=4000)
        evidence = _references(evidence_references, "evidence_references")
        alternatives = {alt["id"] for alt in proposal["alternatives"]}
        if decision == "approved":
            if not isinstance(selected_alternative_id, str) or selected_alternative_id not in alternatives:
                raise SeedProposalError("approval must explicitly select one alternative")
            prior_reviews = state["reviews"][proposal_id]
            if prior_reviews and prior_reviews[-1]["record"]["decision"] in {"approved", "rejected"}:
                raise SeedProposalError("terminal seed proposal decision cannot be overwritten")
            for other_id, other in state["proposals"].items():
                if other_id == proposal_id or other["raw_objective_sha256"] != proposal["raw_objective_sha256"]:
                    continue
                if (state["reviews"][other_id]
                        and state["reviews"][other_id][-1]["record"]["decision"] == "approved"
                        and not state["superseded"].get(other_id)):
                    raise SeedProposalError("raw objective already has an approved seed proposal; supersede it explicitly")
        elif selected_alternative_id is not None:
            raise SeedProposalError("only an approved proposal may select a seed alternative")
        if state["reviews"][proposal_id] and state["reviews"][proposal_id][-1]["record"]["decision"] in {"approved", "rejected"}:
            raise SeedProposalError("terminal seed proposal decision cannot be overwritten")
        record = {
            "decision": decision,
            "reviewer": reviewer,
            "source_reference": source_reference,
            "rationale": rationale,
            "evidence_references": evidence,
            "selected_alternative_id": selected_alternative_id,
        }
        return self._append("proposal_reviewed", proposal_id, record)

    def approved_objective(self, proposal_id: str, revision: int = 1,
                           supersedes_sha256: Optional[str] = None) -> dict:
        state = self._state()
        proposal = state["proposals"].get(proposal_id)
        if proposal is None:
            raise SeedProposalError("seed proposal does not exist")
        if state["superseded"].get(proposal_id):
            raise SeedProposalError("seed proposal has been superseded")
        reviews = state["reviews"][proposal_id]
        if not reviews or reviews[-1]["record"]["decision"] != "approved":
            raise SeedProposalError("seed proposal is not explicitly approved for intake")
        review_event = reviews[-1]
        selected_id = review_event["record"]["selected_alternative_id"]
        alternative = next(alt for alt in proposal["alternatives"] if alt["id"] == selected_id)
        objective = _build_objective(
            proposal["raw_objective"], alternative, revision=revision,
            supersedes_sha256=supersedes_sha256,
        )
        proposal_event = state["proposal_events"][proposal_id]
        reference = {
            "proposal_id": proposal_id,
            "proposal_sha256": proposal_event["event_sha256"],
            "raw_objective_sha256": proposal["raw_objective_sha256"],
            "raw_revision": proposal["raw_objective"]["raw_revision"],
            "selected_alternative_id": selected_id,
            "review_event_sha256": review_event["event_sha256"],
        }
        return {
            "objective": objective,
            "reference": reference,
            "raw_objective": proposal["raw_objective"],
            "alternative": alternative,
        }

    def verify_reference(self, reference: Any) -> dict:
        ref = _object(reference, "seed_proposal_reference", {
            "proposal_id", "proposal_sha256", "raw_objective_sha256",
            "raw_revision", "selected_alternative_id", "review_event_sha256",
        })
        if not isinstance(ref["proposal_id"], str) or not _PROPOSAL_ID.fullmatch(ref["proposal_id"]):
            raise SeedProposalError("seed proposal reference proposal_id is invalid")
        if not isinstance(ref["selected_alternative_id"], str) or not _ALT_ID.fullmatch(ref["selected_alternative_id"]):
            raise SeedProposalError("seed proposal reference selected_alternative_id is invalid")
        for key in ("proposal_sha256", "raw_objective_sha256", "review_event_sha256"):
            if not isinstance(ref[key], str) or not _SHA256.fullmatch(ref[key]):
                raise SeedProposalError(f"seed proposal reference {key} must be a SHA-256 digest")
        if isinstance(ref["raw_revision"], bool) or not isinstance(ref["raw_revision"], int) or ref["raw_revision"] < 1:
            raise SeedProposalError("seed proposal reference raw_revision must be positive")
        approved = self.approved_objective(ref["proposal_id"])
        if approved["reference"] != ref:
            raise SeedProposalError("seed proposal reference does not match the current approved review")
        return approved

    def list_proposals(self) -> List[dict]:
        state = self._state()
        result = []
        for proposal_id, proposal in state["proposals"].items():
            reviews = state["reviews"][proposal_id]
            status = "superseded" if state["superseded"].get(proposal_id) else (
                reviews[-1]["record"]["decision"] if reviews else "candidate"
            )
            result.append({
                "proposal_id": proposal_id,
                "objective_id": proposal["raw_objective"]["objective_id"],
                "raw_revision": proposal["raw_objective"]["raw_revision"],
                "raw_objective_sha256": proposal["raw_objective_sha256"],
                "alternatives": [alt["id"] for alt in proposal["alternatives"]],
                "status": status,
                "supersedes_proposal_id": proposal["supersedes_proposal_id"],
            })
        return result



def load_seed_proposal_file(path: str) -> dict:
    """Load a bounded provider-neutral seed proposal JSON document."""
    if os.path.islink(path):
        raise SeedProposalError("seed proposal input must not be a symlink")
    if os.path.getsize(path) > 1_048_576:
        raise SeedProposalError("seed proposal input exceeds 1 MiB")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh, object_pairs_hook=_reject_duplicate_keys)
    except (json.JSONDecodeError, SeedProposalError) as exc:
        raise SeedProposalError(f"invalid seed proposal JSON: {exc}") from exc
    return _object(payload, "seed_proposal_input", {
        "raw_objective", "alternatives", "proposer_kind",
        "proposer_reference", "source_reference",
    }, optional={"supersedes_proposal_id"})
