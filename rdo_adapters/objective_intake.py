"""Versioned, provenance-preserving objective intake for the external RDO.

The intake layer validates a provider-neutral JSON contract, retains every
objective revision append-only, and feeds the existing deterministic cycle
driver. Supplied obligations remain proposals; repository reconciliation is
fresh, and experiment eligibility is still read from the Watcher registry.
"""
from __future__ import annotations

import errno
import fcntl
import hashlib
import json
import os
import re
import subprocess
import stat
from typing import Any, Dict, List, Optional

from rdo.memory import CycleStore, PatternMemory
from rdo.model import (
    ANTI_REQUIREMENT, CLASSIFICATIONS, CONDITIONAL, FUTURE, HYPOTHESIS,
    NECESSARY, OPTIONAL, UNKNOWN, Obligation, Relationship,
)
from rdo.reconcile import Signature

SCHEMA_VERSION = "rdo.objective.v1"
MAX_INPUT_BYTES = 1_048_576
MAX_EXPANSION_DEPTH = 4
_OBJECTIVE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
_OBLIGATION_KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_GIT_SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_RELATIONSHIP_KINDS = {"depends_on", "produces_for", "reuses", "duplicates", "influences"}
_AUTHORITY_LEVELS = {"none", "bounded", "strong"}
_SOURCE_KINDS = {"human", "external_llm", "imported"}
_IMMUTABLE_REVISION_FIELDS = {"schema_version", "objective_id", "revision",
                              "original_text", "intent", "supersedes_sha256"}


class ObjectiveInputError(ValueError):
    """Invalid, conflicting, or unsafe objective input."""


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ObjectiveInputError(f"objective input is not canonical JSON: {exc}") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _open_regular_store_file(path: str, flags: int, *, label: str,
                             mode: int = 0o666) -> int:
    """Open one store file without following symlinks or blocking on special files."""
    if os.path.islink(path):
        raise ObjectiveInputError(f"{label} must not be a symlink")
    safe_flags = (
        flags
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    try:
        fd = os.open(path, safe_flags, mode)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise ObjectiveInputError(f"{label} must not be a symlink") from exc
        raise
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ObjectiveInputError(f"{label} must be a regular file")
    except BaseException:
        os.close(fd)
        raise
    return fd


def _object(value: Any, name: str, required: set, optional: set = frozenset()) -> dict:
    if not isinstance(value, dict):
        raise ObjectiveInputError(f"{name} must be an object")
    keys = set(value)
    missing = required - keys
    unknown = keys - required - optional
    if missing:
        raise ObjectiveInputError(f"{name} is missing required fields: {', '.join(sorted(missing))}")
    if unknown:
        raise ObjectiveInputError(f"{name} has unsupported fields: {', '.join(sorted(unknown))}")
    return value


def _text(value: Any, name: str, *, max_length: int = 10000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ObjectiveInputError(f"{name} must be non-empty text")
    if len(value) > max_length:
        raise ObjectiveInputError(f"{name} exceeds {max_length} characters")
    return value


def _text_list(value: Any, name: str, *, max_items: int = 200,
               max_length: int = 2000, allow_empty: bool = True) -> List[str]:
    if not isinstance(value, list):
        raise ObjectiveInputError(f"{name} must be a list of strings")
    if len(value) > max_items:
        raise ObjectiveInputError(f"{name} exceeds {max_items} items")
    if not allow_empty and not value:
        raise ObjectiveInputError(f"{name} must contain at least one item")
    out = []
    seen = set()
    for i, item in enumerate(value):
        item = _text(item, f"{name}[{i}]", max_length=max_length)
        if item in seen:
            raise ObjectiveInputError(f"{name} contains a duplicate item: {item!r}")
        seen.add(item)
        out.append(item)
    return out


def _safe_repo_path(value: Any, name: str) -> str:
    path = _text(value, name, max_length=512)
    # Paths are repository-relative POSIX paths. Reject traversal, absolute,
    # drive-qualified and platform-ambiguous paths before they reach the scanner.
    if (path.startswith("/") or "\\" in path or ":" in path
            or any(ord(char) < 32 for char in path)
            or any(part in ("", ".", "..") for part in path.split("/"))):
        raise ObjectiveInputError(f"{name} must be a clean repository-relative path")
    return path


def validate_objective(payload: Any) -> dict:
    """Validate and detach one provider-neutral objective revision.

    Only source/proposal fields are accepted. Reconciliation outcomes, evidence
    claims, approval flags and arbitrary execution instructions are deliberately
    absent from the schema and cannot be smuggled into Obligation records.
    """
    top = _object(payload, "objective", {
        "schema_version", "objective_id", "revision", "supersedes_sha256",
        "original_text", "intent", "owner", "source", "scope", "constraints",
        "exclusions", "assumptions", "acceptance_criteria", "seed_obligations",
        "relationships", "reconciliation_signatures", "max_depth",
    })
    if not isinstance(top["schema_version"], str) or top["schema_version"] != SCHEMA_VERSION:
        raise ObjectiveInputError(f"schema_version must be {SCHEMA_VERSION!r}")

    objective_id = _text(top["objective_id"], "objective_id", max_length=64)
    if not _OBJECTIVE_ID.fullmatch(objective_id):
        raise ObjectiveInputError("objective_id must use 1-64 portable filename characters")
    revision = top["revision"]
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise ObjectiveInputError("revision must be a positive integer")

    supersedes = top["supersedes_sha256"]
    if revision == 1 and supersedes is not None:
        raise ObjectiveInputError("revision 1 must have supersedes_sha256=null")
    if revision > 1 and (not isinstance(supersedes, str) or not _SHA256.fullmatch(supersedes)):
        raise ObjectiveInputError("revisions after 1 must cite the previous sha256 digest")

    original_text = _text(top["original_text"], "original_text")
    intent = _text(top["intent"], "intent", max_length=4000)
    owner = _text(top["owner"], "owner", max_length=256)

    source = _object(top["source"], "source", {"kind", "reference"})
    source_kind = source["kind"]
    if not isinstance(source_kind, str) or source_kind not in _SOURCE_KINDS:
        raise ObjectiveInputError(f"source.kind must be one of {sorted(_SOURCE_KINDS)}")
    source_reference = _text(source["reference"], "source.reference", max_length=512)

    scope = _object(top["scope"], "scope", {"in_scope", "affected_paths"})
    in_scope = _text_list(scope["in_scope"], "scope.in_scope")
    affected_paths = [_safe_repo_path(p, f"scope.affected_paths[{i}]")
                      for i, p in enumerate(_text_list(scope["affected_paths"],
                                                       "scope.affected_paths"))]

    constraints = _text_list(top["constraints"], "constraints")
    exclusions = _text_list(top["exclusions"], "exclusions")
    assumptions = _text_list(top["assumptions"], "assumptions")
    acceptance_criteria = _text_list(top["acceptance_criteria"], "acceptance_criteria",
                                     allow_empty=False)

    max_depth = top["max_depth"]
    if (isinstance(max_depth, bool) or not isinstance(max_depth, int)
            or not 0 <= max_depth <= MAX_EXPANSION_DEPTH):
        raise ObjectiveInputError(f"max_depth must be an integer from 0 to {MAX_EXPANSION_DEPTH}")

    raw_seeds = top["seed_obligations"]
    if not isinstance(raw_seeds, list) or not raw_seeds or len(raw_seeds) > 200:
        raise ObjectiveInputError("seed_obligations must contain 1-200 records")
    seeds = []
    seed_keys = set()
    for i, raw in enumerate(raw_seeds):
        name = f"seed_obligations[{i}]"
        seed = _object(raw, name, {
            "key", "title", "kind", "classification", "rationale", "impact",
            "evidence_needs", "assumptions", "confidence",
        })
        key = _text(seed["key"], f"{name}.key", max_length=128)
        if not _OBLIGATION_KEY.fullmatch(key):
            raise ObjectiveInputError(f"{name}.key must use portable canonical-key characters")
        if key in seed_keys:
            raise ObjectiveInputError(f"duplicate seed obligation key: {key}")
        seed_keys.add(key)
        title = _text(seed["title"], f"{name}.title", max_length=512)
        kind = _text(seed["kind"], f"{name}.kind", max_length=64)
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", kind):
            raise ObjectiveInputError(f"{name}.kind must be a lower_snake_case identifier")
        classification = seed["classification"]
        if not isinstance(classification, str) or classification not in CLASSIFICATIONS:
            raise ObjectiveInputError(f"{name}.classification is not a supported obligation class")
        rationale = _text(seed["rationale"], f"{name}.rationale", max_length=4000)
        impact = _text(seed["impact"], f"{name}.impact", max_length=4000)
        evidence_needs = _text_list(seed["evidence_needs"], f"{name}.evidence_needs",
                                    allow_empty=False)
        seed_assumptions = _text_list(seed["assumptions"], f"{name}.assumptions")
        confidence = seed["confidence"]
        if not isinstance(confidence, str) or confidence not in ("stated", "inferred"):
            raise ObjectiveInputError(
                f"{name}.confidence must be 'stated' or 'inferred'; measured is reserved for evidence"
            )
        if source_kind == "external_llm" and confidence != "inferred":
            raise ObjectiveInputError("external LLM proposals must remain inferred, not stated or measured")
        seeds.append({
            "key": key, "title": title, "kind": kind, "classification": classification,
            "rationale": rationale, "impact": impact, "evidence_needs": evidence_needs,
            "assumptions": seed_assumptions, "confidence": confidence,
        })

    raw_relationships = top["relationships"]
    if not isinstance(raw_relationships, list) or len(raw_relationships) > 1000:
        raise ObjectiveInputError("relationships must be a list with at most 1000 records")
    relationships = []
    seen_edges = set()
    for i, raw in enumerate(raw_relationships):
        name = f"relationships[{i}]"
        edge = _object(raw, name, {"src", "dst", "kind", "authority", "reversible", "note"})
        src = _text(edge["src"], f"{name}.src", max_length=128)
        dst = _text(edge["dst"], f"{name}.dst", max_length=128)
        if src not in seed_keys or dst not in seed_keys:
            raise ObjectiveInputError(f"{name} must connect two declared seed obligation keys")
        kind = edge["kind"]
        if not isinstance(kind, str) or kind not in _RELATIONSHIP_KINDS:
            raise ObjectiveInputError(f"{name}.kind is not a supported relationship type")
        authority = edge["authority"]
        if not isinstance(authority, str) or authority not in _AUTHORITY_LEVELS:
            raise ObjectiveInputError(f"{name}.authority is not a supported authority level")
        reversible = edge["reversible"]
        if reversible is not None and not isinstance(reversible, bool):
            raise ObjectiveInputError(f"{name}.reversible must be true, false or null")
        note = edge["note"]
        if not isinstance(note, str) or len(note) > 2000:
            raise ObjectiveInputError(f"{name}.note must be text of at most 2000 characters")
        signature = (src, dst, kind)
        if signature in seen_edges:
            raise ObjectiveInputError(f"duplicate relationship: {signature!r}")
        seen_edges.add(signature)
        relationships.append({
            "src": src, "dst": dst, "kind": kind, "authority": authority,
            "reversible": reversible, "note": note,
        })

    raw_signatures = _object(top["reconciliation_signatures"],
                             "reconciliation_signatures", set(), seed_keys)
    signatures: Dict[str, List[dict]] = {}
    for key, raw_list in raw_signatures.items():
        if not isinstance(raw_list, list) or not raw_list or len(raw_list) > 20:
            raise ObjectiveInputError(f"signatures for {key!r} must contain 1-20 entries")
        checked = []
        for i, raw in enumerate(raw_list):
            name = f"reconciliation_signatures.{key}[{i}]"
            sig = _object(raw, name, {"pattern", "path", "label"})
            pattern = _text(sig["pattern"], f"{name}.pattern", max_length=512)
            path = sig["path"]
            if path is not None:
                path = _safe_repo_path(path, f"{name}.path")
            label = sig["label"]
            if not isinstance(label, str) or len(label) > 256:
                raise ObjectiveInputError(f"{name}.label must be text of at most 256 characters")
            checked.append({"pattern": pattern, "path": path, "label": label})
        signatures[key] = checked

    return {
        "schema_version": SCHEMA_VERSION,
        "objective_id": objective_id,
        "revision": revision,
        "supersedes_sha256": supersedes,
        "original_text": original_text,
        "intent": intent,
        "owner": owner,
        "source": {"kind": source_kind, "reference": source_reference},
        "scope": {"in_scope": in_scope, "affected_paths": affected_paths},
        "constraints": constraints,
        "exclusions": exclusions,
        "assumptions": assumptions,
        "acceptance_criteria": acceptance_criteria,
        "seed_obligations": seeds,
        "relationships": relationships,
        "reconciliation_signatures": signatures,
        "max_depth": max_depth,
    }


def _reject_duplicate_keys(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ObjectiveInputError(f"duplicate JSON property: {key}")
        out[key] = value
    return out


def load_objective_file(path: str) -> dict:
    """Read a bounded JSON file; reject duplicate keys and oversized inputs."""
    size = os.path.getsize(path)
    if size > MAX_INPUT_BYTES:
        raise ObjectiveInputError(f"objective input exceeds {MAX_INPUT_BYTES} bytes")
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh, object_pairs_hook=_reject_duplicate_keys)
    return validate_objective(payload)


def _validate_objective_lineage(record: dict, value: Any) -> Optional[dict]:
    """Validate reviewed seed provenance stored beside, not inside, objective.v1."""
    if value is None:
        return None
    fields = {
        "schema_version", "proposal_id", "selected_alternative_id",
        "proposer_kind", "proposer_reference", "proposal_source_reference",
        "raw_objective_id", "raw_objective_revision", "raw_objective_sha256",
        "raw_objective_supersedes_sha256", "raw_reconciliation_signatures",
        "acceptance_criterion_coverage", "approval", "objective_id",
        "objective_revision", "objective_supersedes_sha256",
        "objective_input_sha256",
    }
    lineage = _object(value, "objective lineage", fields)
    if lineage["schema_version"] != "rdo.reviewed_seed_bridge.v2":
        raise ObjectiveInputError("unsupported objective lineage schema")
    if not isinstance(lineage["proposal_id"], str) or not re.fullmatch(
        r"seedprop_[0-9a-f]{24}", lineage["proposal_id"]
    ):
        raise ObjectiveInputError("objective lineage proposal_id is invalid")
    if not isinstance(lineage["selected_alternative_id"], str) or not _OBLIGATION_KEY.fullmatch(
        lineage["selected_alternative_id"]
    ):
        raise ObjectiveInputError("objective lineage selected alternative is invalid")
    if lineage["proposer_kind"] not in ("human", "external_llm"):
        raise ObjectiveInputError("objective lineage proposer_kind is invalid")
    _text(lineage["proposer_reference"], "lineage.proposer_reference", max_length=512)
    _text(lineage["proposal_source_reference"], "lineage.proposal_source_reference", max_length=1000)
    if lineage["raw_objective_id"] != record["objective_id"]:
        raise ObjectiveInputError("objective lineage raw objective ID does not match intake")
    for name in ("raw_objective_revision", "objective_revision"):
        number = lineage[name]
        if isinstance(number, bool) or not isinstance(number, int) or number < 1:
            raise ObjectiveInputError(f"objective lineage {name} must be a positive integer")
    for name in ("raw_objective_sha256", "objective_input_sha256"):
        if not isinstance(lineage[name], str) or not _SHA256.fullmatch(lineage[name]):
            raise ObjectiveInputError(f"objective lineage {name} is invalid")
    raw_previous = lineage["raw_objective_supersedes_sha256"]
    if raw_previous is not None and (
        not isinstance(raw_previous, str) or not _SHA256.fullmatch(raw_previous)
    ):
        raise ObjectiveInputError("objective lineage raw revision predecessor is invalid")
    if not isinstance(lineage["raw_reconciliation_signatures"], dict):
        raise ObjectiveInputError("objective lineage raw reconciliation signatures must be an object")
    if not isinstance(lineage["acceptance_criterion_coverage"], list):
        raise ObjectiveInputError("objective lineage acceptance coverage must be a list")
    if (lineage["objective_id"] != record["objective_id"]
            or lineage["objective_revision"] != record["revision"]
            or lineage["objective_supersedes_sha256"] != record["supersedes_sha256"]
            or lineage["objective_input_sha256"] != _digest(record)):
        raise ObjectiveInputError("objective lineage does not bind to this exact objective revision/digest")
    approval = _object(lineage["approval"], "objective lineage approval", {
        "sequence", "event_sha256", "record", "event",
    })
    sequence = approval["sequence"]
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise ObjectiveInputError("objective lineage approval sequence is invalid")
    if not isinstance(approval["event_sha256"], str) or not _SHA256.fullmatch(
        approval["event_sha256"]
    ):
        raise ObjectiveInputError("objective lineage approval event digest is invalid")
    review = _object(approval["record"], "objective lineage approval record", {
        "decision", "selected_alternative_id", "reviewer", "source_reference",
        "rationale", "evidence_references",
    })
    if (review["decision"] != "approved"
            or review["selected_alternative_id"] != lineage["selected_alternative_id"]):
        raise ObjectiveInputError("objective lineage approval does not select this alternative")
    _text(review["reviewer"], "lineage.approval.reviewer", max_length=256)
    _text(review["source_reference"], "lineage.approval.source_reference", max_length=1000)
    _text(review["rationale"], "lineage.approval.rationale")
    _text_list(review["evidence_references"], "lineage.approval.evidence_references",
               max_items=200, max_length=1000, allow_empty=False)
    event = _object(approval["event"], "objective lineage approval event", {
        "schema_version", "sequence", "previous_event_sha256", "event_kind",
        "proposal_id", "recorded_at", "record", "event_sha256",
    })
    if (event["schema_version"] != 1
            or event["event_kind"] != "review_decision"
            or event["proposal_id"] != lineage["proposal_id"]
            or event["sequence"] != sequence
            or event["record"] != review
            or event["event_sha256"] != approval["event_sha256"]):
        raise ObjectiveInputError("objective lineage approval event fields do not match the review")
    previous_event = event["previous_event_sha256"]
    if previous_event is not None and (
        not isinstance(previous_event, str) or not _SHA256.fullmatch(previous_event)
    ):
        raise ObjectiveInputError("objective lineage previous approval-event digest is invalid")
    _text(event["recorded_at"], "lineage.approval.event.recorded_at", max_length=128)
    event_body = {key: event[key] for key in (
        "schema_version", "sequence", "previous_event_sha256", "event_kind",
        "proposal_id", "recorded_at", "record",
    )}
    if _digest(event_body) != event["event_sha256"]:
        raise ObjectiveInputError("objective lineage approval event digest does not verify")
    return json.loads(_canonical_json(lineage))


class ObjectiveInputStore:
    """Append-only revision ledger; original wording/intent cannot be rewritten."""

    def __init__(self, directory: str) -> None:
        self.directory = directory
        os.makedirs(directory, exist_ok=True)

    def _path(self, objective_id: str) -> str:
        if not isinstance(objective_id, str) or not _OBJECTIVE_ID.fullmatch(objective_id):
            raise ObjectiveInputError("invalid objective_id for revision storage")
        return os.path.join(self.directory, f"{objective_id}.jsonl")

    def _history_unlocked(self, objective_id: str) -> List[dict]:
        path = self._path(objective_id)
        if os.path.islink(path):
            raise ObjectiveInputError("objective revision ledger path must not be a symlink")
        try:
            fd = _open_regular_store_file(
                path, os.O_RDONLY, label="objective revision ledger path",
            )
        except FileNotFoundError:
            return []
        records = []
        with os.fdopen(fd, "r", encoding="utf-8") as fh:
            for number, line in enumerate(fh, 1):
                if not line.strip():
                    raise ObjectiveInputError(f"blank revision-ledger line {number}")
                try:
                    wrapper = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
                except json.JSONDecodeError as exc:
                    raise ObjectiveInputError(f"invalid revision-ledger JSON on line {number}: {exc}") from exc
                wrapper = _object(
                    wrapper, f"revision-ledger line {number}",
                    {"record", "sha256"}, {"lineage"},
                )
                record = validate_objective(wrapper["record"])
                digest = _digest(record)
                if wrapper["sha256"] != digest:
                    raise ObjectiveInputError(f"revision-ledger integrity failure on line {number}")
                lineage = _validate_objective_lineage(record, wrapper.get("lineage"))
                if record["objective_id"] != objective_id:
                    raise ObjectiveInputError(f"objective_id mismatch on revision-ledger line {number}")
                expected_revision = number
                if record["revision"] != expected_revision:
                    raise ObjectiveInputError(f"non-sequential revision on line {number}")
                if number == 1:
                    if record["supersedes_sha256"] is not None:
                        raise ObjectiveInputError("first stored revision must not supersede another record")
                else:
                    previous = records[-1]
                    if record["supersedes_sha256"] != previous["sha256"]:
                        raise ObjectiveInputError(f"broken revision chain on line {number}")
                    first = records[0]["record"]
                    if (record["original_text"] != first["original_text"]
                            or record["intent"] != first["intent"]):
                        raise ObjectiveInputError(
                            "original_text and intent are immutable; create a new objective_id for a new objective"
                        )
                item = {"record": record, "sha256": digest}
                if lineage is not None:
                    item["lineage"] = lineage
                records.append(item)
        return records

    def history(self, objective_id: str) -> List[dict]:
        path = self._path(objective_id)
        if os.path.islink(path):
            raise ObjectiveInputError("objective revision ledger path must not be a symlink")
        if not os.path.exists(path):
            return []
        lock_path = path + ".lock"
        lock_fd = _open_regular_store_file(
            lock_path, os.O_CREAT | os.O_RDWR,
            label="objective revision lock path", mode=0o600,
        )
        with os.fdopen(lock_fd, "r+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_SH)
            try:
                return self._history_unlocked(objective_id)
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def append(self, payload: Any, lineage: Any = None) -> dict:
        record = validate_objective(payload)
        checked_lineage = _validate_objective_lineage(record, lineage)
        path = self._path(record["objective_id"])
        lock_path = path + ".lock"
        lock_fd = _open_regular_store_file(
            lock_path, os.O_CREAT | os.O_RDWR,
            label="objective revision lock path", mode=0o600,
        )
        with os.fdopen(lock_fd, "r+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                history = self._history_unlocked(record["objective_id"])
                digest = _digest(record)
                revision = record["revision"]
                if revision <= len(history):
                    existing = history[revision - 1]
                    if existing["sha256"] == digest:
                        if existing.get("lineage") != checked_lineage:
                            raise ObjectiveInputError(
                                "objective revision already exists with different proposal lineage"
                            )
                        return {**existing, "replayed": True}
                    raise ObjectiveInputError(
                        f"revision {revision} already exists with different content; revisions are immutable"
                    )
                if revision != len(history) + 1:
                    raise ObjectiveInputError(
                        f"expected revision {len(history) + 1}, received revision {revision}"
                    )
                if not history:
                    if record["supersedes_sha256"] is not None:
                        raise ObjectiveInputError("first revision must use supersedes_sha256=null")
                else:
                    previous = history[-1]
                    if record["supersedes_sha256"] != previous["sha256"]:
                        raise ObjectiveInputError("supersedes_sha256 must match the immediately previous revision")
                    first = history[0]["record"]
                    if (record["original_text"] != first["original_text"]
                            or record["intent"] != first["intent"]):
                        raise ObjectiveInputError(
                            "original_text and intent are immutable; create a new objective_id for a new objective"
                        )
                wrapper = {"record": record, "sha256": digest}
                if checked_lineage is not None:
                    wrapper["lineage"] = checked_lineage
                # One append-only record per revision. Never rewrite an earlier revision.
                # The file fsync protects its contents; on first creation also
                # fsync the containing directory so the new ledger entry itself
                # survives a crash/power loss.
                created = not os.path.exists(path)
                ledger_fd = _open_regular_store_file(
                    path, os.O_WRONLY | os.O_APPEND | os.O_CREAT,
                    label="objective revision ledger path",
                )
                with os.fdopen(ledger_fd, "a", encoding="utf-8") as fh:
                    fh.write(_canonical_json(wrapper) + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
                if created:
                    directory = os.path.dirname(os.path.abspath(path)) or "."
                    dir_fd = os.open(directory, os.O_RDONLY)
                    try:
                        os.fsync(dir_fd)
                    finally:
                        os.close(dir_fd)
                return {**wrapper, "replayed": False}
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def compare_revisions(previous: dict, current: dict) -> dict:
    """Report changed top-level inputs without discarding either revision."""
    old = validate_objective(previous)
    new = validate_objective(current)
    if old["objective_id"] != new["objective_id"] or new["revision"] <= old["revision"]:
        raise ObjectiveInputError("revision comparison requires increasing revisions of the same objective")
    changed = {}
    for key in old:
        if key in _IMMUTABLE_REVISION_FIELDS:
            continue
        if old[key] != new[key]:
            changed[key] = {"previous": old[key], "current": new[key]}
    return {"objective_id": old["objective_id"], "from_revision": old["revision"],
            "to_revision": new["revision"], "changed_fields": changed}


def _repository_revision(repo_dir: str) -> str:
    """Return a clean, identifiable Git snapshot; refuse a dirty/unknown tree."""
    root = os.path.abspath(repo_dir)
    try:
        head = subprocess.run(
            ["git", "-C", root, "rev-parse", "--verify", "HEAD"],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", root, "status", "--porcelain", "--untracked-files=all"],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        raise ObjectiveInputError(f"cannot establish a repository snapshot: {exc}") from exc
    if not _GIT_SHA.fullmatch(head):
        raise ObjectiveInputError("repository HEAD is not a full commit SHA")
    if status.strip():
        raise ObjectiveInputError(
            "repository working tree is not clean; objective intake requires an identifiable snapshot"
        )
    return head


def _cycle_id(objective_id: str, revision: int, repository_revision: str) -> str:
    identity = f"{objective_id}\n{revision}\n{repository_revision}"
    token = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    return f"obj_{token}_r{revision:06d}"


def _cycle_summary(cycle, summary: Optional[dict] = None) -> dict:
    return {
        "cycle_id": cycle.id,
        "objective": cycle.objective,
        "counts": cycle.counts,
        "reused": cycle.reused,
        "signature_matches": cycle.signature_matches,
        "missing": cycle.missing,
        "anti_requirements": cycle.anti_requirements,
        "frontier": cycle.frontier,
        "work_packages": cycle.work_packages,
        "verification": cycle.verification,
        "run_summary": summary,
    }


def submit_objective(payload: Any, repo_dir: str = ".", workdir: str = "rdo/.cycles",
                     objective_lineage: Optional[Dict] = None) -> dict:
    """Persist one immutable objective revision and run the existing RDO pipeline."""
    record = validate_objective(payload)
    input_store = ObjectiveInputStore(os.path.join(workdir, "objectives"))
    stored = input_store.append(record, lineage=objective_lineage)
    stored_lineage = dict(stored.get("lineage") or {})
    repository_revision = _repository_revision(repo_dir)
    cycle_id = _cycle_id(record["objective_id"], record["revision"], repository_revision)
    cycle_store = CycleStore(workdir)
    metadata = {
        "schema_version": record["schema_version"],
        "objective_id": record["objective_id"],
        "revision": record["revision"],
        "sha256": stored["sha256"],
        "repository_revision": repository_revision,
    }

    if cycle_id in cycle_store.list_ids():
        existing = cycle_store.load(cycle_id)
        if (existing.objective_input != metadata
                or existing.objective_lineage != stored_lineage):
            raise ObjectiveInputError("cycle ID collision: stored input/snapshot/proposal lineage differs")
        return {
            "status": "reused_existing_cycle",
            "objective_id": record["objective_id"],
            "revision": record["revision"],
            "input_sha256": stored["sha256"],
            "repository_revision": repository_revision,
            "summary": _cycle_summary(existing),
            "cycle": existing.to_dict(),
        }

    from rdo.orchestrator import _active_experiments, run_cycle

    source = record["source"]
    provenance = f"seed; intake:{source['kind']}:{source['reference']}"
    seeds = [
        Obligation(
            key=item["key"], title=item["title"], kind=item["kind"],
            classification=item["classification"], rationale=item["rationale"],
            impact=item["impact"], evidence_needs=list(item["evidence_needs"]),
            assumptions=list(item["assumptions"]), provenance=provenance,
            confidence=item["confidence"],
        )
        for item in record["seed_obligations"]
    ]
    relationships = [Relationship(**edge) for edge in record["relationships"]]
    signatures = {
        key: [Signature(**signature) for signature in items]
        for key, items in record["reconciliation_signatures"].items()
    }
    memory = PatternMemory(os.path.join(workdir, "patterns.jsonl"))
    cycle_kwargs = {
        "repo_dir": repo_dir,
        "active_experiments": _active_experiments(repo_dir),
        "authorised_gates": set(),
        "memory": memory,
        "max_depth": record["max_depth"],
        "initial_relationships": relationships,
        "objective_input": metadata,
        "objective_context": {
            "intent": record["intent"],
            "owner": record["owner"],
            "source": dict(record["source"]),
            "scope": dict(record["scope"]),
            "assumptions": list(record["assumptions"]),
            "constraints": list(record["constraints"]),
            "exclusions": list(record["exclusions"]),
            "acceptance_criteria": list(record["acceptance_criteria"]),
        },
    }
    if stored_lineage:
        cycle_kwargs["objective_lineage"] = stored_lineage
    cycle, summary = run_cycle(
        cycle_id, record["original_text"], list(record["assumptions"]),
        seeds, signatures, **cycle_kwargs,
    )
    cycle_store.save(cycle)
    return {
        "status": "created",
        "objective_id": record["objective_id"],
        "revision": record["revision"],
        "input_sha256": stored["sha256"],
        "repository_revision": repository_revision,
        "summary": _cycle_summary(cycle, summary),
        "cycle": cycle.to_dict(),
        "persisted_to": cycle_store._cycle_path(cycle_id),
    }


def objective_history(workdir: str, objective_id: str) -> dict:
    history = ObjectiveInputStore(os.path.join(workdir, "objectives")).history(objective_id)
    revisions = []
    for i, item in enumerate(history):
        record = item["record"]
        diff = (compare_revisions(history[i - 1]["record"], record)
                if i else None)
        revision_summary = {
            "revision": record["revision"], "sha256": item["sha256"],
            "supersedes_sha256": record["supersedes_sha256"],
            "changed_fields": sorted((diff or {}).get("changed_fields", {}).keys()),
        }
        if item.get("lineage") is not None:
            revision_summary["proposal_lineage"] = item["lineage"]
        revisions.append(revision_summary)
    return {"objective_id": objective_id, "revisions": revisions}


def resume_objective(workdir: str, objective_id: str, revision: int) -> dict:
    """Load the exact input revision and every persisted cycle made from it."""
    history = ObjectiveInputStore(os.path.join(workdir, "objectives")).history(objective_id)
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1 or revision > len(history):
        raise ObjectiveInputError(f"objective revision {revision!r} does not exist")
    stored = history[revision - 1]
    cycle_store = CycleStore(workdir)
    cycles = []
    for cycle_id in cycle_store.list_ids():
        cycle = cycle_store.load(cycle_id)
        metadata = cycle.objective_input
        if (metadata.get("objective_id") == objective_id
                and metadata.get("revision") == revision
                and metadata.get("sha256") == stored["sha256"]):
            expected_lineage = dict(stored.get("lineage") or {})
            if cycle.objective_lineage != expected_lineage:
                raise ObjectiveInputError(
                    "CycleStore proposal lineage does not match the objective revision ledger"
                )
            cycles.append(cycle.to_dict())
    if not cycles:
        raise ObjectiveInputError("the objective revision is stored, but no completed RDO cycle was found")
    result = {
        "objective": stored["record"],
        "input_sha256": stored["sha256"],
        "cycles": cycles,
    }
    if stored.get("lineage") is not None:
        result["proposal_lineage"] = stored["lineage"]
    return result

