"""Immutable, non-executing Stage-7 handoff manifests and human decision records.

This adapter turns a persisted native RDO planning cycle into a bounded,
reviewable handoff artifact. It does not launch an agent, run tests, execute
commands, or grant operational authority. Human decisions are caller-attributed
and explicitly NOT identity-authenticated by this local ledger.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import subprocess
from typing import Any, Dict, List, Optional

from watcher.evidence import utc_now

from rdo.memory import CycleStore
from rdo.model import NATIVE_PLANNING
from .objective_intake import ObjectiveInputStore, _repository_revision

HANDOFF_SCHEMA = "rdo.handoff.v1"
EVENT_SCHEMA = "rdo.handoff_event.v1"
_HANDOFF_ID = re.compile(r"handoff_[0-9a-f]{24}\Z")
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_ALLOWED_ACTIONS = {
    "prepare_scoped_patch",
    "edit_documentation_within_scope",
    "edit_rdo_tooling_within_scope",
    "create_review_branch",
}
_FORBIDDEN_ACTIONS = {
    "run_tests", "execute_code", "run_commands", "deploy",
    "modify_live_nex", "write_live_database", "change_runtime_flags",
    "alter_experiments", "restart_services",
}


class HandoffError(ValueError):
    """Invalid, mismatched, tampered or out-of-bound handoff operation."""


def _canonical(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise HandoffError(f"handoff record is not canonical JSON: {exc}") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(value: Any, name: str, maximum: int = 4000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise HandoffError(f"{name} must be non-empty text of at most {maximum} characters")
    return value


def _safe_id(value: Any) -> str:
    if not isinstance(value, str) or not _HANDOFF_ID.fullmatch(value):
        raise HandoffError("invalid handoff_id")
    return value


def _handoff_root(workdir: str) -> str:
    path = os.path.join(workdir, "handoffs")
    os.makedirs(path, exist_ok=True)
    return path


def _manifest_path(workdir: str, handoff_id: str) -> str:
    return os.path.join(_handoff_root(workdir), f"{_safe_id(handoff_id)}.json")


def _event_path(workdir: str, handoff_id: str) -> str:
    return os.path.join(_handoff_root(workdir), f"{_safe_id(handoff_id)}.events.jsonl")


def _manifest_body(manifest: dict) -> dict:
    body = dict(manifest)
    body.pop("manifest_sha256", None)
    return body


def _validate_manifest(manifest: Any) -> dict:
    if not isinstance(manifest, dict):
        raise HandoffError("handoff manifest must be an object")
    required = {
        "schema_version", "handoff_id", "created_at", "objective", "cycle",
        "work_package", "scope", "obligations", "relationships", "dependencies",
        "deliverables", "acceptance_criteria", "constraints", "exclusions",
        "assumptions", "anti_requirements", "blockers", "evidence_requirements",
        "evidence_dimensions", "agent_handoff", "authority", "manifest_sha256",
    }
    missing = required - set(manifest)
    if missing:
        raise HandoffError(f"manifest missing fields: {', '.join(sorted(missing))}")
    if manifest["schema_version"] != HANDOFF_SCHEMA:
        raise HandoffError("unsupported handoff schema version")
    _safe_id(manifest["handoff_id"])
    digest = manifest["manifest_sha256"]
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise HandoffError("manifest digest is invalid")
    if _digest(_manifest_body(manifest)) != digest:
        raise HandoffError("manifest digest mismatch; immutable handoff record was changed")
    if manifest["authority"].get("execution_authority") != "none":
        raise HandoffError("handoff cannot contain execution authority")
    if manifest["evidence_dimensions"].get("test_verified") != "not_authorized":
        raise HandoffError("handoff must not authorize test execution")
    if manifest["evidence_dimensions"].get("runtime_observed") != "unknown_host_only":
        raise HandoffError("runtime must remain host-only UNKNOWN")
    if manifest["evidence_dimensions"].get("human_acceptance") != "not_recorded":
        raise HandoffError("human acceptance cannot be inferred during handoff creation")
    return manifest


def load_handoff(workdir: str, handoff_id: str) -> dict:
    path = _manifest_path(workdir, handoff_id)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"cannot load handoff {handoff_id}: {exc}") from exc
    return _validate_manifest(manifest)


def _write_manifest_exclusive(path: str, manifest: dict) -> bool:
    """Write once. Return False when an identical immutable manifest already exists."""
    payload = _canonical(manifest) + "\n"
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
    except Exception:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise
    return True


def _read_objective(workdir: str, objective_id: str, revision: int,
                    expected_digest: str) -> dict:
    records = ObjectiveInputStore(os.path.join(workdir, "objectives")).history(objective_id)
    if revision < 1 or revision > len(records):
        raise HandoffError("referenced objective input revision does not exist")
    saved = records[revision - 1]
    if saved["record"]["revision"] != revision or saved["sha256"] != expected_digest:
        raise HandoffError("cycle objective input reference does not match the immutable input ledger")
    return saved["record"]


def create_handoff(workdir: str, repo_dir: str, objective_id: str, revision: int,
                   cycle_id: str, work_package_key: str) -> dict:
    """Create a digest-bound, non-executing handoff from a persisted native cycle.

    It requires the selected repository to still be at the exact clean snapshot
    used by the cycle. Imported retrospective cycles and mismatched revisions are
    refused. Ineligible work packages can be represented as blocked manifests,
    but can never receive an approval event.
    """
    if not isinstance(cycle_id, str) or not _TOKEN.fullmatch(cycle_id):
        raise HandoffError("invalid cycle_id")
    if not isinstance(objective_id, str) or not _TOKEN.fullmatch(objective_id):
        raise HandoffError("invalid objective_id")
    if not isinstance(work_package_key, str) or not _TOKEN.fullmatch(work_package_key):
        raise HandoffError("invalid work_package_key")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise HandoffError("revision must be a positive integer")

    cycle = CycleStore(workdir).load(cycle_id)
    if cycle.kind != NATIVE_PLANNING:
        raise HandoffError("handoffs require an RDO-native planning cycle, not imported history")
    metadata = cycle.objective_input
    if (metadata.get("objective_id") != objective_id
            or metadata.get("revision") != revision):
        raise HandoffError("cycle does not belong to the requested objective revision")
    input_digest = metadata.get("sha256")
    if not isinstance(input_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", input_digest):
        raise HandoffError("cycle has no valid immutable objective-input digest")
    objective = _read_objective(workdir, objective_id, revision, input_digest)

    repository_revision = _repository_revision(repo_dir)
    if repository_revision != metadata.get("repository_revision"):
        raise HandoffError(
            "repository HEAD differs from the cycle snapshot; re-plan against the exact clean snapshot"
        )

    package = next((w for w in cycle.work_packages if w.get("key") == work_package_key), None)
    if package is None:
        raise HandoffError("work package is not present in the persisted RDO cycle")

    obligation_map = {o.get("key"): o for o in cycle.obligations if isinstance(o, dict)}
    keys = package.get("obligation_keys")
    if not isinstance(keys, list) or not keys:
        raise HandoffError("work package has no traceable obligation keys")
    missing = [key for key in keys if key not in obligation_map]
    if missing:
        raise HandoffError(f"work package references missing obligations: {missing}")
    obligations = [obligation_map[key] for key in keys]
    keyset = set(keys)
    relationships = [
        r for r in cycle.relationships
        if r.get("src") in keyset or r.get("dst") in keyset
    ]
    scope = objective["scope"]
    allowed_paths = list(scope["affected_paths"])
    eligibility = package.get("eligibility")
    blockers = list(package.get("blockers") or [])
    if eligibility != "eligible":
        blockers = blockers or ["work package is not currently eligible"]
    if not allowed_paths:
        blockers.append("objective has no explicit affected_paths; handoff scope cannot be bounded")
    status = "pending_human_review" if not blockers else "blocked"

    identity = {
        "objective_id": objective_id,
        "revision": revision,
        "input_sha256": input_digest,
        "cycle_id": cycle_id,
        "repository_revision": repository_revision,
        "work_package_key": work_package_key,
    }
    handoff_id = "handoff_" + hashlib.sha256(_canonical(identity).encode("utf-8")).hexdigest()[:24]

    evidence_requirements = {}
    for ob in obligations:
        evidence_requirements[ob["key"]] = {
            "reconciliation_status": ob.get("recon_status", "unknown"),
            "evidence_needs": list(ob.get("evidence_needs") or []),
            "source_evidence": "not_collected",
            "test_evidence": "not_authorized",
            "runtime_evidence": "unknown_host_only",
        }

    manifest = {
        "schema_version": HANDOFF_SCHEMA,
        "handoff_id": handoff_id,
        "created_at": utc_now(),
        "objective": {
            "objective_id": objective_id,
            "revision": revision,
            "input_sha256": input_digest,
            "original_text": objective["original_text"],
            "intent": objective["intent"],
            "owner_attribution": objective["owner"],
            "source_attribution": objective["source"],
        },
        "cycle": {
            "cycle_id": cycle_id,
            "cycle_kind": cycle.kind,
            "repository_revision": repository_revision,
            "created_at": cycle.created_at,
        },
        "work_package": {
            "key": work_package_key,
            "title": package.get("title"),
            "eligibility": eligibility,
            "priority_dimensions": package.get("priority_dimensions") or {},
            "anti_requirements": list(package.get("anti_requirements") or []),
            "note": package.get("note", ""),
        },
        "scope": {
            "in_scope": list(scope["in_scope"]),
            "allowed_paths": allowed_paths,
            "path_semantics": "exact repository-relative paths only; no glob expansion",
        },
        "obligations": obligations,
        "relationships": relationships,
        "dependencies": [
            r for r in relationships if r.get("kind") == "depends_on"
        ],
        "deliverables": list(objective["acceptance_criteria"]),
        "acceptance_criteria": list(objective["acceptance_criteria"]),
        "constraints": list(objective["constraints"]),
        "exclusions": list(objective["exclusions"]),
        "assumptions": list(objective["assumptions"]),
        "anti_requirements": list(cycle.anti_requirements),
        "blockers": sorted(set(blockers)),
        "evidence_requirements": evidence_requirements,
        "evidence_dimensions": {
            "source_implemented": "not_collected",
            "test_verified": "not_authorized",
            "runtime_observed": "unknown_host_only",
            "human_acceptance": "not_recorded",
        },
        "agent_handoff": {
            "target": "external_human_or_coding_agent",
            "instruction": (
                f"Prepare a proposed change for {work_package_key} only. "
                "Do not execute tests, arbitrary commands, services, deployments or runtime operations. "
                "Do not modify live NEX data, feature flags or experiments. "
                "Stay within the exact allowed_paths and exclusions. "
                "Return a proposed diff, changed-file list, rationale, unresolved questions and "
                "evidence references for human review. A completion claim is not acceptance."
            ),
            "required_return": [
                "proposed_diff_or_patch",
                "changed_files",
                "rationale",
                "acceptance_criteria_mapping",
                "evidence_references",
                "unresolved_questions",
            ],
            "launch_authorized": False,
        },
        "authority": {
            "handoff_status": status,
            "execution_authority": "none",
            "human_scope_review_required": True,
            "human_acceptance_required": True,
            "tests_execution_authorized": False,
            "runtime_operations_authorized": False,
            "live_database_writes_authorized": False,
            "experiment_changes_authorized": False,
            "deployment_authorized": False,
            "available_scope_review_actions": sorted(_ALLOWED_ACTIONS),
            "reviewer_identity": "caller_attributed_not_authenticated",
        },
    }
    manifest["manifest_sha256"] = _digest(manifest)
    path = _manifest_path(workdir, handoff_id)
    created = _write_manifest_exclusive(path, manifest)
    if not created:
        existing = load_handoff(workdir, handoff_id)
        # created_at is expected to differ on replay. Every other field must
        # match exactly; a changed cycle/package under the same identity is a conflict.
        existing_body = _manifest_body(existing)
        expected_body = _manifest_body(manifest)
        existing_body.pop("created_at", None)
        expected_body.pop("created_at", None)
        if existing_body != expected_body:
            raise HandoffError("handoff ID already exists with different immutable content")
        return existing
    return manifest


def _event_body(event: dict) -> dict:
    body = dict(event)
    body.pop("event_sha256", None)
    return body


def _read_events_unlocked(workdir: str, handoff_id: str, manifest_sha256: str) -> List[dict]:
    path = _event_path(workdir, handoff_id)
    if not os.path.exists(path):
        return []
    events = []
    previous = None
    with open(path, "r", encoding="utf-8") as fh:
        for number, line in enumerate(fh, 1):
            if not line.strip():
                raise HandoffError(f"blank decision-ledger line {number}")
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise HandoffError(f"invalid decision-ledger JSON on line {number}") from exc
            if not isinstance(event, dict):
                raise HandoffError(f"decision-ledger line {number} must be an object")
            if event.get("schema_version") != EVENT_SCHEMA:
                raise HandoffError(f"unsupported decision event on line {number}")
            if event.get("handoff_id") != handoff_id or event.get("manifest_sha256") != manifest_sha256:
                raise HandoffError(f"decision event on line {number} is bound to another manifest")
            if event.get("sequence") != number or event.get("previous_event_sha256") != previous:
                raise HandoffError(f"decision-ledger sequence/chain mismatch on line {number}")
            expected = _digest(_event_body(event))
            if event.get("event_sha256") != expected:
                raise HandoffError(f"decision-ledger digest mismatch on line {number}")
            previous = expected
            events.append(event)
    return events


def handoff_history(workdir: str, handoff_id: str) -> dict:
    manifest = load_handoff(workdir, handoff_id)
    path = _event_path(workdir, handoff_id)
    # Use a shared lock so readers never observe a partially appended decision.
    with open(path, "a+", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_SH)
        try:
            fh.seek(0)
            events = _read_events_unlocked(workdir, handoff_id, manifest["manifest_sha256"])
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    last_scope = next((e for e in reversed(events) if e["event_kind"] == "scope_review"), None)
    last_acceptance = next((e for e in reversed(events) if e["event_kind"] == "human_acceptance"), None)
    return {
        "manifest": manifest,
        "events": events,
        "latest_scope_review": last_scope,
        "latest_human_acceptance": last_acceptance,
    }


def _append_event(workdir: str, manifest: dict, event_fields: dict) -> dict:
    handoff_id = manifest["handoff_id"]
    path = _event_path(workdir, handoff_id)
    with open(path, "a+", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            fh.seek(0)
            events = _read_events_unlocked(workdir, handoff_id, manifest["manifest_sha256"])
            previous = events[-1]["event_sha256"] if events else None
            event = {
                "schema_version": EVENT_SCHEMA,
                "sequence": len(events) + 1,
                "handoff_id": handoff_id,
                "manifest_sha256": manifest["manifest_sha256"],
                "previous_event_sha256": previous,
                "recorded_at": utc_now(),
                "reviewer_identity_status": "caller_attributed_not_authenticated",
                **event_fields,
            }
            event["event_sha256"] = _digest(event)
            fh.seek(0, os.SEEK_END)
            fh.write(_canonical(event) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
            return event
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def record_scope_review(workdir: str, handoff_id: str, decision: str, reviewer: str,
                        source_reference: str, permitted_actions: Optional[List[str]] = None,
                        note: str = "") -> dict:
    """Record a caller-attributed human scope decision. This does not launch work."""
    manifest = load_handoff(workdir, handoff_id)
    reviewer = _text(reviewer, "reviewer", 256)
    source_reference = _text(source_reference, "source_reference", 1000)
    if not isinstance(decision, str) or decision not in ("approved", "rejected", "changes_requested"):
        raise HandoffError("scope decision must be approved, rejected or changes_requested")
    if permitted_actions is not None and (
            not isinstance(permitted_actions, list)
            or any(not isinstance(a, str) for a in permitted_actions)):
        raise HandoffError("permitted_actions must be a list of action names")
    actions = list(permitted_actions or [])
    if len(actions) != len(set(actions)):
        raise HandoffError("permitted_actions contains duplicates")
    forbidden = sorted(set(actions) & _FORBIDDEN_ACTIONS)
    unknown = sorted(set(actions) - _ALLOWED_ACTIONS)
    if forbidden or unknown:
        raise HandoffError(
            f"permitted_actions exceed this handoff's non-executing boundary; "
            f"forbidden={forbidden}, unsupported={unknown}"
        )
    if decision == "approved":
        if manifest["authority"]["handoff_status"] != "pending_human_review":
            raise HandoffError("blocked handoffs cannot be approved")
        if not actions:
            raise HandoffError("approval requires an explicit non-executing permitted_actions list")
    elif actions:
        raise HandoffError("rejected/changes_requested decisions cannot carry permitted actions")
    return _append_event(workdir, manifest, {
        "event_kind": "scope_review",
        "decision": decision,
        "reviewer": reviewer,
        "source_reference": source_reference,
        "permitted_actions": sorted(actions),
        "note": note if isinstance(note, str) else "",
        "execution_authorized": False,
    })


def record_human_acceptance(workdir: str, handoff_id: str, decision: str, reviewer: str,
                            source_reference: str, delivery_reference: str,
                            evidence_references: Dict[str, List[str]],
                            note: str = "") -> dict:
    """Record a separate human acceptance decision after a scope approval.

    Acceptance is a human judgement and is not computed from source/test/runtime
    evidence. The references are preserved by dimension; no evidence class
    substitutes for another. The caller/reviewer attribution is not authenticated.
    """
    manifest = load_handoff(workdir, handoff_id)
    history = handoff_history(workdir, handoff_id)
    latest_scope = history["latest_scope_review"]
    if not latest_scope or latest_scope["decision"] != "approved":
        raise HandoffError("human acceptance requires a recorded approved scope review")
    reviewer = _text(reviewer, "reviewer", 256)
    source_reference = _text(source_reference, "source_reference", 1000)
    delivery_reference = _text(delivery_reference, "delivery_reference", 1000)
    if not isinstance(decision, str) or decision not in ("accepted", "rejected", "changes_requested"):
        raise HandoffError("human acceptance decision must be accepted, rejected or changes_requested")
    required_dimensions = {"source_implemented", "test_verified", "runtime_observed"}
    if not isinstance(evidence_references, dict) or set(evidence_references) != required_dimensions:
        raise HandoffError("evidence_references must separately name source_implemented, test_verified and runtime_observed")
    normalized = {}
    for dimension in sorted(required_dimensions):
        values = evidence_references[dimension]
        if (not isinstance(values, list) or len(values) > 200
                or any(not isinstance(v, str) or not v.strip() or len(v) > 1000 for v in values)):
            raise HandoffError(f"{dimension} evidence references must be a bounded list of non-empty strings")
        normalized[dimension] = list(values)
    return _append_event(workdir, manifest, {
        "event_kind": "human_acceptance",
        "decision": decision,
        "reviewer": reviewer,
        "source_reference": source_reference,
        "delivery_reference": delivery_reference,
        "evidence_references": normalized,
        "note": note if isinstance(note, str) else "",
        "acceptance_authority": "human_judgement_only; does_not_rewrite_source_test_runtime_evidence",
    })


def _read_cli_int(value: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise HandoffError("revision must be an integer") from exc
    if parsed < 1:
        raise HandoffError("revision must be positive")
    return parsed
