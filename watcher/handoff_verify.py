"""Independent Watcher-process verification of an RDO handoff.

This command verifies only source/path scope. It does not execute tests, project
scripts, agents, services or NEX runtime operations. The caller-attributed review
ledger is integrity-checked, not identity-authenticated.
"""
from __future__ import annotations

import fcntl
import datetime
import hashlib
import json
import os
import re
import stat
import subprocess
import shutil
from typing import Any, Dict, List, Optional, Tuple

from .evidence import Evidence, host_placeholder, utc_now
from .ledger import ConnectionLedger

REQUEST_SCHEMA = "watcher.handoff_verify_request.v1"
REPORT_SCHEMA = "watcher.handoff_verification.v1"
MANIFEST_SCHEMA = "rdo.handoff.v1"
EVENT_SCHEMA = "rdo.handoff_event.v1"
MAX_REQUEST_BYTES = 65536
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_EVENT_BYTES = 4 * 1024 * 1024
MAX_CHANGED_PATHS = 500
MAX_SOURCE_FILE_BYTES = 10 * 1024 * 1024
_HANDOFF_ID = re.compile(r"handoff_[0-9a-f]{24}\Z")
_GIT_SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_ALLOWED_SCOPE_ACTIONS = {
    "prepare_scoped_patch",
    "edit_documentation_within_scope",
    "edit_rdo_tooling_within_scope",
}
_ALLOWED_ALL_ACTIONS = _ALLOWED_SCOPE_ACTIONS | {"create_review_branch"}


class HandoffVerificationError(ValueError):
    """Invalid request, manifest, ledger or repository snapshot."""


def _canonical(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise HandoffVerificationError(f"record is not canonical JSON: {exc}") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _reject_duplicate_keys(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise HandoffVerificationError(f"duplicate JSON property: {key}")
        out[key] = value
    return out


def _load_json(path: str, maximum: int, label: str) -> dict:
    try:
        size = os.path.getsize(path)
        if size > maximum:
            raise HandoffVerificationError(f"{label} exceeds {maximum} bytes")
        with open(path, "r", encoding="utf-8") as fh:
            value = json.load(fh, object_pairs_hook=_reject_duplicate_keys)
    except HandoffVerificationError:
        raise
    except (OSError, json.JSONDecodeError, UnicodeError) as exc:
        raise HandoffVerificationError(f"cannot read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise HandoffVerificationError(f"{label} must be a JSON object")
    return value


def _safe_relative(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise HandoffVerificationError(f"{label} must be a non-empty repository-relative path")
    if (value.startswith("/") or "\\" in value or ":" in value or
            any(ord(ch) < 32 for ch in value) or
            any(part in ("", ".", "..") for part in value.split("/")) or
            any(ch in value for ch in "*?[]")):
        raise HandoffVerificationError(f"{label} must be an exact, clean repository-relative path")
    return value


def _inside_root(root: str, relative: str, label: str, *,
                 require_file: bool = False, allow_missing: bool = False) -> Tuple[str, str]:
    relative = _safe_relative(relative, label)
    candidate = os.path.join(root, *relative.split("/"))
    resolved = os.path.realpath(candidate)
    try:
        if os.path.commonpath((root, resolved)) != root:
            raise HandoffVerificationError(f"{label} resolves outside the repository")
    except ValueError as exc:
        raise HandoffVerificationError(f"{label} cannot be resolved inside the repository") from exc

    exists = os.path.exists(candidate) or os.path.islink(candidate)
    if not exists and not allow_missing:
        raise HandoffVerificationError(f"{label} does not exist: {relative}")
    if exists:
        if os.path.isdir(candidate):
            raise HandoffVerificationError(f"{label} must identify a file, not a directory: {relative}")
        if require_file and not os.path.isfile(candidate):
            raise HandoffVerificationError(f"{label} is not a regular file: {relative}")
    resolved_relative = os.path.relpath(resolved, root).replace(os.sep, "/")
    return candidate, resolved_relative


def _git_executable() -> str:
    executable = shutil.which("git", path=os.defpath)
    if not executable:
        raise HandoffVerificationError("Git executable was not found on the trusted system path")
    return executable


def _git_environment() -> dict:
    env = {key: os.environ[key] for key in
           ("HOME", "TMPDIR", "TEMP", "TMP", "SYSTEMROOT", "WINDIR", "PATHEXT")
           if key in os.environ}
    env["PATH"] = os.defpath
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_SYSTEM"] = os.devnull
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env["GIT_NO_REPLACE_OBJECTS"] = "1"
    return env


def _run_git(root: str, args: List[str], *, timeout: int = 15) -> bytes:
    try:
        result = subprocess.run(
            [_git_executable(), "-C", root, *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_git_environment(),
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise HandoffVerificationError(f"git inspection failed: {type(exc).__name__}: {exc}") from exc
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise HandoffVerificationError(f"git {' '.join(args)} failed ({result.returncode}): {message}")
    return result.stdout


def _git_lines(root: str, args: List[str]) -> List[str]:
    raw = _run_git(root, args)
    values = [os.fsdecode(x) for x in raw.split(b"\0") if x]
    if len(values) > MAX_CHANGED_PATHS:
        raise HandoffVerificationError(f"repository change set exceeds {MAX_CHANGED_PATHS} paths")
    return values


def _read_manifest(path: str) -> dict:
    manifest = _load_json(path, MAX_MANIFEST_BYTES, "handoff manifest")
    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise HandoffVerificationError("unsupported RDO handoff schema")
    handoff_id = manifest.get("handoff_id")
    if not isinstance(handoff_id, str) or not _HANDOFF_ID.fullmatch(handoff_id):
        raise HandoffVerificationError("invalid handoff_id")
    claimed = manifest.get("manifest_sha256")
    body = dict(manifest)
    body.pop("manifest_sha256", None)
    if not isinstance(claimed, str) or not re.fullmatch(r"[0-9a-f]{64}", claimed):
        raise HandoffVerificationError("manifest digest is missing or malformed")
    actual = _digest(body)
    if actual != claimed:
        raise HandoffVerificationError("handoff manifest digest mismatch")
    authority = manifest.get("authority")
    dimensions = manifest.get("evidence_dimensions")
    if not isinstance(authority, dict) or not isinstance(dimensions, dict):
        raise HandoffVerificationError("manifest authority/evidence dimensions must be objects")
    if authority.get("execution_authority") != "none":
        raise HandoffVerificationError("manifest grants execution authority; refusing verification")
    if authority.get("tests_execution_authorized") is not False:
        raise HandoffVerificationError("manifest must not authorize test execution")
    if authority.get("runtime_operations_authorized") is not False:
        raise HandoffVerificationError("manifest must not authorize runtime operations")
    if authority.get("handoff_status") != "pending_human_review":
        raise HandoffVerificationError("manifest was not created as pending human review")
    if dimensions.get("test_verified") != "not_authorized":
        raise HandoffVerificationError("test evidence must remain not_authorized")
    if dimensions.get("runtime_observed") != "unknown_host_only":
        raise HandoffVerificationError("runtime evidence must remain host-only UNKNOWN")
    if dimensions.get("human_acceptance") != "not_recorded":
        raise HandoffVerificationError("human acceptance must not be inferred into the manifest")

    cycle = manifest.get("cycle")
    if not isinstance(cycle, dict) or not _GIT_SHA.fullmatch(str(cycle.get("repository_revision", ""))):
        raise HandoffVerificationError("manifest has no valid repository planning SHA")
    scope = manifest.get("scope")
    if not isinstance(scope, dict):
        raise HandoffVerificationError("manifest scope must be an object")
    allowed = scope.get("allowed_paths")
    resolved = scope.get("resolved_paths")
    if (not isinstance(allowed, list) or not allowed or len(allowed) > MAX_CHANGED_PATHS
            or any(not isinstance(rel, str) for rel in allowed)):
        raise HandoffVerificationError("manifest must contain a bounded non-empty string exact-file allowlist")
    if len(allowed) != len(set(allowed)):
        raise HandoffVerificationError("manifest contains duplicate allowed paths")
    normalized = [_safe_relative(x, "scope.allowed_paths") for x in allowed]
    if normalized != allowed:
        raise HandoffVerificationError("manifest allowed paths are not canonical")
    if not isinstance(resolved, dict) or set(resolved) != set(allowed):
        raise HandoffVerificationError("manifest resolved_paths do not match allowed_paths")
    for key, value in resolved.items():
        _safe_relative(value, f"scope.resolved_paths[{key}]")
    return manifest


def _read_event_chain(path: str, manifest: dict) -> List[dict]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_SH)
            try:
                size = os.fstat(fh.fileno()).st_size
                if size > MAX_EVENT_BYTES:
                    raise HandoffVerificationError("handoff event ledger exceeds size limit")
                raw_lines = fh.readlines()
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    except HandoffVerificationError:
        raise
    except OSError as exc:
        raise HandoffVerificationError(f"cannot read handoff decision ledger: {exc}") from exc

    events = []
    previous = None
    for number, line in enumerate(raw_lines, 1):
        if not line.strip():
            raise HandoffVerificationError(f"blank decision-ledger line {number}")
        try:
            event = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
        except (json.JSONDecodeError, UnicodeError) as exc:
            raise HandoffVerificationError(f"invalid decision-ledger JSON on line {number}") from exc
        if not isinstance(event, dict):
            raise HandoffVerificationError(f"decision-ledger line {number} must be an object")
        if event.get("schema_version") != EVENT_SCHEMA:
            raise HandoffVerificationError(f"unsupported decision event on line {number}")
        if (event.get("handoff_id") != manifest["handoff_id"] or
                event.get("manifest_sha256") != manifest["manifest_sha256"]):
            raise HandoffVerificationError(f"decision event on line {number} is bound to another manifest")
        if event.get("sequence") != number or event.get("previous_event_sha256") != previous:
            raise HandoffVerificationError(f"decision-ledger sequence/chain mismatch on line {number}")
        body = dict(event)
        claimed = body.pop("event_sha256", None)
        if not isinstance(claimed, str) or claimed != _digest(body):
            raise HandoffVerificationError(f"decision-ledger digest mismatch on line {number}")
        if event.get("reviewer_identity_status") != "caller_attributed_not_authenticated":
            raise HandoffVerificationError(f"reviewer identity status is invalid on line {number}")
        for field, maximum in (("recorded_at", 128), ("reviewer", 256), ("source_reference", 1000)):
            value = event.get(field)
            if not isinstance(value, str) or not value.strip() or len(value) > maximum:
                raise HandoffVerificationError(f"decision event {field} is missing or invalid on line {number}")
        note = event.get("note", "")
        if not isinstance(note, str) or len(note) > 2000:
            raise HandoffVerificationError(f"decision event note is invalid on line {number}")
        kind = event.get("event_kind")
        if kind == "scope_review":
            decision = event.get("decision")
            if decision not in ("approved", "rejected", "changes_requested"):
                raise HandoffVerificationError(f"invalid scope decision on line {number}")
            actions = event.get("permitted_actions")
            if (not isinstance(actions, list)
                    or any(not isinstance(action, str) for action in actions)
                    or len(actions) != len(set(actions))):
                raise HandoffVerificationError(f"invalid permitted action list on line {number}")
            if set(actions) - _ALLOWED_ALL_ACTIONS:
                raise HandoffVerificationError(f"unsupported/operational action on line {number}")
            if event.get("execution_authorized") is not False:
                raise HandoffVerificationError(f"scope review grants execution on line {number}")
            if decision == "approved" and not set(actions) & _ALLOWED_SCOPE_ACTIONS:
                raise HandoffVerificationError(f"scope approval has no proposal-preparation action on line {number}")
        elif kind == "context_mapping":
            item_id = event.get("context_item_id")
            assessment = manifest.get("objective_context_assessment")
            items = assessment.get("items", []) if isinstance(assessment, dict) else []
            matches = [item for item in items
                       if isinstance(item, dict) and item.get("item_id") == item_id]
            if not isinstance(item_id, str) or not item_id.strip() or len(matches) != 1:
                raise HandoffVerificationError(f"context mapping references an unknown/ambiguous item on line {number}")
            if event.get("decision") != "mapped":
                raise HandoffVerificationError(f"invalid context mapping decision on line {number}")
            mapping = event.get("mapping_record")
            keys = event.get("mapped_obligation_keys")
            references = event.get("evidence_references")
            known_keys = {
                item.get("key") for item in manifest.get("obligations", [])
                if isinstance(item, dict) and isinstance(item.get("key"), str)
            }
            if (not isinstance(keys, list) or not keys or len(keys) > 200
                    or any(not isinstance(value, str) or not value.strip() for value in keys)
                    or len(keys) != len(set(keys)) or set(keys) - known_keys):
                raise HandoffVerificationError(f"context mapping obligation keys are invalid on line {number}")
            if (not isinstance(references, list) or not references or len(references) > 200
                    or any(not isinstance(value, str) or not value.strip() or len(value) > 1000
                           for value in references)
                    or len(references) != len(set(references))):
                raise HandoffVerificationError(f"context mapping evidence references are invalid on line {number}")
            source_item = matches[0]
            if (not isinstance(mapping, dict)
                    or mapping.get("item_id") != item_id
                    or mapping.get("kind") != source_item.get("kind")
                    or mapping.get("text") != source_item.get("text")
                    or mapping.get("source_field") != source_item.get("source_field")
                    or mapping.get("source_index") != source_item.get("source_index")
                    or mapping.get("source_ref") != source_item.get("source_ref")
                    or mapping.get("classification") != source_item.get("classification")
                    or mapping.get("status") != "mapped"
                    or mapping.get("mapped_obligation_keys") != keys
                    or mapping.get("evidence") != references
                    or mapping.get("review_required") is not False):
                raise HandoffVerificationError(f"context mapping record is inconsistent on line {number}")
        elif kind == "acceptance_verification":
            criterion_id = event.get("criterion_id")
            assessment = manifest.get("objective_context_assessment")
            criteria = assessment.get("acceptance_verification", []) if isinstance(assessment, dict) else []
            matches = [item for item in criteria
                       if isinstance(item, dict) and item.get("criterion_id") == criterion_id]
            record = event.get("verification_record")
            if not isinstance(criterion_id, str) or not criterion_id.strip() or len(matches) != 1:
                raise HandoffVerificationError(f"acceptance verification references an unknown/ambiguous criterion on line {number}")
            if not isinstance(record, dict):
                raise HandoffVerificationError(f"acceptance verification record is invalid on line {number}")
            criterion = matches[0]
            status = record.get("status")
            if (record.get("criterion_id") != criterion_id
                    or record.get("source_ref") != criterion.get("source_ref")
                    or record.get("criterion") != criterion.get("criterion")
                    or status not in ("pending", "passed", "failed", "not_applicable")):
                raise HandoffVerificationError(f"acceptance verification identity/status is invalid on line {number}")
            keys = record.get("mapped_obligation_keys")
            references = record.get("evidence_refs")
            known_keys = {
                item.get("key") for item in manifest.get("obligations", [])
                if isinstance(item, dict) and isinstance(item.get("key"), str)
            }
            if (not isinstance(keys, list) or len(keys) > 200
                    or any(not isinstance(value, str) or not value.strip() for value in keys)
                    or len(keys) != len(set(keys)) or set(keys) - known_keys):
                raise HandoffVerificationError(f"acceptance verification obligation keys are invalid on line {number}")
            if (not isinstance(references, list) or len(references) > 200
                    or any(not isinstance(value, str) or not value.strip() or len(value) > 1000
                           for value in references)
                    or len(references) != len(set(references))):
                raise HandoffVerificationError(f"acceptance verification evidence references are invalid on line {number}")
            if status in ("pending", "passed", "failed"):
                prior_mapping = next(
                    (e for e in reversed(events)
                     if e.get("event_kind") == "context_mapping"
                     and e.get("context_item_id") == criterion_id),
                    None,
                )
                if prior_mapping is None or prior_mapping.get("mapped_obligation_keys") != keys:
                    raise HandoffVerificationError(f"acceptance verification lacks its matching prior context mapping on line {number}")
                method = record.get("verification_method")
                if not isinstance(method, str) or not method.strip():
                    raise HandoffVerificationError(f"acceptance verification method is missing on line {number}")
            if status in ("passed", "failed", "not_applicable"):
                if not references:
                    raise HandoffVerificationError(f"completed acceptance verification has no evidence on line {number}")
                if (not isinstance(record.get("verifier"), str) or not record["verifier"].strip()
                        or record.get("verifier") != event.get("reviewer")
                        or not isinstance(record.get("confidence"), str) or not record["confidence"].strip()):
                    raise HandoffVerificationError(f"completed acceptance verification attribution is invalid on line {number}")
                timestamp = record.get("verified_at")
                try:
                    parsed = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                except (AttributeError, TypeError, ValueError) as exc:
                    raise HandoffVerificationError(f"acceptance verification timestamp is invalid on line {number}") from exc
                if parsed.tzinfo is None or parsed.utcoffset() is None:
                    raise HandoffVerificationError(f"acceptance verification timestamp lacks a timezone on line {number}")
            if record.get("verifier") != event.get("reviewer"):
                raise HandoffVerificationError(f"acceptance verification reviewer/verifier mismatch on line {number}")
            if record.get("note", "") != event.get("note", ""):
                raise HandoffVerificationError(f"acceptance verification note mismatch on line {number}")
            if record.get("review_required") is not (status == "pending"):
                raise HandoffVerificationError(f"acceptance verification review_required flag is inconsistent on line {number}")
            if not isinstance(record.get("note", ""), str):
                raise HandoffVerificationError(f"acceptance verification note is invalid on line {number}")
        elif kind == "human_acceptance":
            if event.get("decision") not in ("accepted", "rejected", "changes_requested"):
                raise HandoffVerificationError(f"invalid human acceptance on line {number}")
            if not isinstance(event.get("delivery_reference"), str) or not event["delivery_reference"].strip():
                raise HandoffVerificationError(f"acceptance has no delivery reference on line {number}")
            if event.get("acceptance_authority") != "human_judgement_only; does_not_rewrite_source_test_runtime_evidence":
                raise HandoffVerificationError(f"acceptance authority is invalid on line {number}")
            references = event.get("evidence_references")
            required_dimensions = {"source_implemented", "test_verified", "runtime_observed"}
            if not isinstance(references, dict) or set(references) != required_dimensions:
                raise HandoffVerificationError(f"acceptance evidence dimensions are incomplete on line {number}")
            for dimension, values in references.items():
                if (not isinstance(values, list) or len(values) > 200
                        or any(not isinstance(value, str) or not value.strip() or len(value) > 1000
                               for value in values)):
                    raise HandoffVerificationError(
                        f"acceptance evidence references are invalid for {dimension} on line {number}"
                    )
            if event["decision"] == "accepted" and not any(references.values()):
                raise HandoffVerificationError(f"accepted delivery has no evidence references on line {number}")
        else:
            raise HandoffVerificationError(f"unsupported decision event kind on line {number}")
        previous = claimed
        events.append(event)
        if len(events) > 1000:
            raise HandoffVerificationError("handoff event ledger exceeds 1000 records")
    return events


def _current_review(events: List[dict]) -> Optional[dict]:
    return next((e for e in reversed(events) if e.get("event_kind") == "scope_review"), None)


def _latest_acceptance(events: List[dict]) -> Optional[dict]:
    return next((e for e in reversed(events) if e.get("event_kind") == "human_acceptance"), None)


def _open_resolved_regular_file(root: str, relative: str) -> int:
    """Open a resolved in-repository file without following a raced symlink.

    _inside_root resolves approved internal aliases first. This helper then
    traverses that resolved path with directory file descriptors and O_NOFOLLOW
    on every component, so a concurrent replacement cannot redirect the final
    source read outside the inspected tree.
    """
    relative = _safe_relative(relative, "resolved source path")
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    if not nofollow or not directory or not hasattr(os, "supports_dir_fd") or os.open not in os.supports_dir_fd:
        raise HandoffVerificationError("platform lacks safe descriptor-relative no-follow file opening")
    directory_fd = os.open(root, os.O_RDONLY | directory)
    try:
        parts = relative.split("/")
        for part in parts[:-1]:
            next_fd = os.open(part, os.O_RDONLY | directory | nofollow, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
        file_fd = os.open(parts[-1], os.O_RDONLY | nofollow, dir_fd=directory_fd)
        if not stat.S_ISREG(os.fstat(file_fd).st_mode):
            os.close(file_fd)
            raise HandoffVerificationError(f"changed path is not a regular file: {relative}")
        return file_fd
    finally:
        os.close(directory_fd)


def _current_file_evidence(root: str, relative: str, base_sha: str, head_sha: str,
                           changed_kinds: List[str]) -> Tuple[dict, Optional[Evidence]]:
    target, resolved = _inside_root(root, relative, "changed path", allow_missing=True)
    exists = os.path.exists(target) or os.path.islink(target)
    if not exists:
        return {
            "path": relative,
            "resolved_path": resolved,
            "change_kinds": changed_kinds,
            "status": "deleted_or_missing",
            "sha256": None,
            "size_bytes": None,
        }, None
    try:
        fd = _open_resolved_regular_file(root, resolved)
    except FileNotFoundError:
        return {
            "path": relative,
            "resolved_path": resolved,
            "change_kinds": changed_kinds,
            "status": "deleted_or_missing",
            "sha256": None,
            "size_bytes": None,
        }, None
    expected_target = os.path.join(root, *resolved.split("/"))
    if os.path.realpath(target) != expected_target:
        os.close(fd)
        raise HandoffVerificationError(
            f"changed path resolution changed during source verification: {relative}"
        )
    with os.fdopen(fd, "rb") as fh:
        size = os.fstat(fh.fileno()).st_size
        if size > MAX_SOURCE_FILE_BYTES:
            return {
                "path": relative, "resolved_path": resolved,
                "change_kinds": changed_kinds, "status": "size_limit_exceeded",
                "sha256": None, "size_bytes": size,
            }, None
        digest = hashlib.sha256()
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    sha = digest.hexdigest()
    evidence = Evidence(
        subject=f"handoff:{relative}",
        data={
            "path": relative,
            "resolved_path": resolved,
            "sha256": sha,
            "size_bytes": size,
            "change_kinds": changed_kinds,
            "planning_base_sha": base_sha,
            "observed_head_sha": head_sha,
        },
        origin="cloud",
        evidence_class="implemented",
        source_ref=f"watcher-handoff-file:{base_sha}:{head_sha}:{relative}:{sha}",
        interpretation=(
            "A changed regular file exists within the approved path scope. "
            "This is file-level source evidence only; it does not prove semantic satisfaction or acceptance."
        ),
    )
    return {
        "path": relative,
        "resolved_path": resolved,
        "change_kinds": changed_kinds,
        "status": "present_and_hashed",
        "sha256": sha,
        "size_bytes": size,
    }, evidence


def _append_watcher_ledger(ledger_path: str, observations: List[dict]) -> List[dict]:
    os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
    recorded = []
    # ConnectionLedger loads before writing; hold a process-wide file lock across
    # construction, transition checks and all appends so no process uses stale state.
    with open(ledger_path, "a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            ledger = ConnectionLedger(ledger_path)
            for observation in observations:
                connection_id = observation["connection_id"]
                wanted = observation["to_state"]
                current = ledger.current_state(connection_id)
                if current is None:
                    first = "DECLARED" if wanted == "SOURCE_CONFIRMED" else "BLOCKED"
                    recorded.append(ledger.record(
                        connection_id, first, origin="cloud",
                        evidence_refs=observation["evidence_refs"],
                        note="Watcher handoff source-scope inspection",
                    ))
                    current = ledger.current_state(connection_id)
                if current in ("DECLARED", "BLOCKED", "REGRESSED") and wanted == "SOURCE_CONFIRMED":
                    recorded.append(ledger.record(
                        connection_id, "SOURCE_CONFIRMED", origin="cloud",
                        evidence_refs=observation["evidence_refs"],
                        note=observation["note"],
                    ))
                elif wanted == "BLOCKED" and current != "BLOCKED":
                    recorded.append(ledger.record(
                        connection_id, "BLOCKED", origin="cloud",
                        evidence_refs=observation["evidence_refs"],
                        note=observation["note"],
                    ))
                elif current == "SOURCE_CONFIRMED" and wanted == "SOURCE_CONFIRMED":
                    # Idempotent source confirmation; never advances test/runtime state.
                    recorded.append(ledger.record(
                        connection_id, "SOURCE_CONFIRMED", origin="cloud",
                        evidence_refs=observation["evidence_refs"],
                        note=observation["note"],
                    ))
            with open(ledger_path, "rb") as persisted:
                os.fsync(persisted.fileno())
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    return recorded


def verify_handoff_request(request_path: str) -> dict:
    request = _load_json(os.path.abspath(request_path), MAX_REQUEST_BYTES, "verification request")
    required = {"schema_version", "repo_root", "manifest_path", "events_path", "ledger_path"}
    if set(request) != required:
        raise HandoffVerificationError("verification request has missing or unsupported fields")
    if request["schema_version"] != REQUEST_SCHEMA:
        raise HandoffVerificationError("unsupported handoff verification request schema")
    repo_root_value = request["repo_root"]
    if not isinstance(repo_root_value, str) or not os.path.isabs(repo_root_value):
        raise HandoffVerificationError("repo_root must be an absolute path")
    root = os.path.realpath(repo_root_value)
    top = os.path.realpath(os.fsdecode(_run_git(root, ["rev-parse", "--show-toplevel"]).strip()))
    if root != top:
        raise HandoffVerificationError("repo_root must be the exact Git worktree root")

    manifest_rel = _safe_relative(request["manifest_path"], "manifest_path")
    events_rel = _safe_relative(request["events_path"], "events_path")
    ledger_rel = _safe_relative(request["ledger_path"], "ledger_path")
    manifest_dir = os.path.dirname(manifest_rel)
    events_dir = os.path.dirname(events_rel)
    if (not manifest_dir.startswith("rdo/.cycles/")
            or os.path.basename(manifest_dir) != "handoffs"):
        raise HandoffVerificationError("manifest must be in a handoffs directory under the RDO cycle store")
    if events_dir != manifest_dir:
        raise HandoffVerificationError("manifest and decision ledger must share the same handoffs directory")
    if not ledger_rel.startswith("rdo/.cycles/"):
        raise HandoffVerificationError("Watcher ledger must be under the ignored RDO cycle store")
    manifest_path, _ = _inside_root(root, manifest_rel, "manifest_path", require_file=True)
    events_path, _ = _inside_root(root, events_rel, "events_path", require_file=True)
    ledger_path, _ = _inside_root(root, ledger_rel, "ledger_path", allow_missing=True)
    manifest = _read_manifest(manifest_path)
    if os.path.basename(manifest_rel) != f"{manifest['handoff_id']}.json":
        raise HandoffVerificationError("manifest filename does not match handoff_id")
    if os.path.basename(events_rel) != f"{manifest['handoff_id']}.events.jsonl":
        raise HandoffVerificationError("decision-ledger filename does not match handoff_id")

    events = _read_event_chain(events_path, manifest)
    review = _current_review(events)
    if not review or review.get("decision") != "approved":
        raise HandoffVerificationError("current scope review is not approved")
    if not set(review.get("permitted_actions", [])) & _ALLOWED_SCOPE_ACTIONS:
        raise HandoffVerificationError("scope review does not authorize preparation within scope")

    base_sha = manifest["cycle"]["repository_revision"]
    if not _GIT_SHA.fullmatch(base_sha):
        raise HandoffVerificationError("invalid planning commit SHA")
    head_sha = os.fsdecode(_run_git(root, ["rev-parse", "--verify", "HEAD"]).strip())
    if not _GIT_SHA.fullmatch(head_sha):
        raise HandoffVerificationError("invalid current repository HEAD SHA")
    ancestor = subprocess.run(
        [_git_executable(), "-C", root, "merge-base", "--is-ancestor", base_sha, head_sha],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=_git_environment(),
        timeout=15, check=False,
    )
    if ancestor.returncode != 0:
        raise HandoffVerificationError("planning commit is not an ancestor of current HEAD")

    changed: Dict[str, set] = {}
    committed = _git_lines(root, ["diff", "--name-only", "-z", "--no-renames", f"{base_sha}...{head_sha}"])
    unstaged = _git_lines(root, ["diff", "--name-only", "-z", "--no-renames"])
    staged = _git_lines(root, ["diff", "--cached", "--name-only", "-z", "--no-renames"])
    untracked = _git_lines(root, ["ls-files", "--others", "--exclude-standard", "-z"])
    for p in committed:
        changed.setdefault(_safe_relative(p, "committed changed path"), set()).add("committed")
    for p in unstaged:
        changed.setdefault(_safe_relative(p, "unstaged changed path"), set()).add("unstaged")
    for p in staged:
        changed.setdefault(_safe_relative(p, "staged changed path"), set()).add("staged")
    for p in untracked:
        changed.setdefault(_safe_relative(p, "untracked changed path"), set()).add("untracked")

    allowed = set(manifest["scope"]["allowed_paths"])
    path_resolution = {}
    path_resolution_errors = []
    for rel in sorted(allowed):
        try:
            _, resolved = _inside_root(root, rel, f"allowed path {rel}", allow_missing=True)
            recorded = manifest["scope"]["resolved_paths"].get(rel)
            if recorded != resolved:
                path_resolution_errors.append({"path": rel, "reason": "resolved target changed since handoff",
                                               "recorded": recorded, "current": resolved})
            path_resolution[rel] = resolved
        except HandoffVerificationError as exc:
            path_resolution_errors.append({"path": rel, "reason": str(exc)})

    if len(changed) > MAX_CHANGED_PATHS:
        raise HandoffVerificationError(
            f"combined repository change set exceeds {MAX_CHANGED_PATHS} paths"
        )
    changed_paths = sorted(changed)
    out_of_scope = sorted(set(changed_paths) - allowed)
    path_resolution_error_paths = {item["path"] for item in path_resolution_errors}
    path_results = []
    evidence_records = []
    observations = []
    for rel in changed_paths:
        if rel in out_of_scope or rel in path_resolution_error_paths:
            path_results.append({
                "path": rel,
                "change_kinds": sorted(changed[rel]),
                "status": "out_of_scope",
            })
            observations.append({
                "connection_id": f"handoff:{manifest['handoff_id']}:source:{rel}",
                "to_state": "BLOCKED",
                "evidence_refs": [f"git-path:{rel}"],
                "note": "Changed path is outside the exact handoff allowlist or a path boundary failed.",
            })
            continue
        result, evidence = _current_file_evidence(
            root, rel, base_sha, head_sha, sorted(changed[rel])
        )
        path_results.append(result)
        if evidence is not None:
            evidence_records.append(evidence)
            observations.append({
                "connection_id": f"handoff:{manifest['handoff_id']}:source:{rel}",
                "to_state": "SOURCE_CONFIRMED",
                "evidence_refs": [evidence.source_ref],
                "note": evidence.interpretation or "Source file changed within approved scope.",
            })
        else:
            observations.append({
                "connection_id": f"handoff:{manifest['handoff_id']}:source:{rel}",
                "to_state": "BLOCKED",
                "evidence_refs": [f"git-path:{rel}"],
                "note": "Changed path is missing, deleted, a non-file, or beyond the source hash limit.",
            })

    if path_resolution_errors:
        out_of_scope = sorted(set(out_of_scope) | {x["path"] for x in path_resolution_errors})
    scope_compliant = not out_of_scope and not path_resolution_errors
    ledger_entries = _append_watcher_ledger(ledger_path, observations) if observations else []

    latest_acceptance = _latest_acceptance(events)
    human_acceptance = {
        "status": latest_acceptance.get("decision") if latest_acceptance else "not_recorded",
        "reviewer_identity_status": "caller_attributed_not_authenticated" if latest_acceptance else "not_recorded",
        "delivery_reference": latest_acceptance.get("delivery_reference") if latest_acceptance else None,
    }
    report = {
        "schema_version": REPORT_SCHEMA,
        "verified_at": utc_now(),
        "verification_process": "independent_watcher_cli_process",
        "handoff": {
            "handoff_id": manifest["handoff_id"],
            "manifest_sha256": manifest["manifest_sha256"],
            "scope_review_decision": review["decision"],
            "reviewer_identity_status": review["reviewer_identity_status"],
        },
        "repository": {
            "planning_base_sha": base_sha,
            "observed_head_sha": head_sha,
            "planning_base_is_ancestor": True,
        },
        "scope": {
            "allowed_paths": sorted(allowed),
            "changed_paths": changed_paths,
            "out_of_scope_paths": out_of_scope,
            "path_resolution_errors": path_resolution_errors,
            "scope_compliant": scope_compliant,
        },
        "changed_file_evidence": path_results,
        "source_evidence": [record.to_dict() for record in evidence_records],
        "evidence_dimensions": {
            "source_implemented": "source_confirmed" if evidence_records and scope_compliant else
                                  ("scope_violation" if not scope_compliant else "not_found"),
            "test_verified": "not_authorized",
            "runtime_observed": "unknown_host_only",
            "human_acceptance": human_acceptance["status"],
        },
        "human_acceptance": human_acceptance,
        "watcher_ledger": {
            "path": ledger_rel,
            "entries_recorded": ledger_entries,
        },
        "limitations": [
            "Source evidence proves file-level presence/change only, not semantic acceptance criteria.",
            "The caller-attributed scope approval is integrity-checked but not identity-authenticated.",
            "No tests, arbitrary commands, project scripts, agents, services or runtime operations were executed.",
            "test_verified remains not_authorized; runtime_observed remains host-only UNKNOWN.",
            "Human acceptance is a separate caller-attributed decision and is not inferred from source evidence.",
        ],
        "exit_status": "scope_compliant" if scope_compliant else "scope_violation",
    }
    return report


def verify_request_file(request_path: str) -> int:
    try:
        report = verify_handoff_request(request_path)
    except HandoffVerificationError as exc:
        print(json.dumps({
            "schema_version": REPORT_SCHEMA,
            "status": "blocked",
            "error": str(exc),
            "test_verified": "not_authorized",
            "runtime_observed": "unknown_host_only",
        }, indent=2))
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["exit_status"] == "scope_compliant" else 1
