"""Prepare an explicitly reviewed seed proposal for RDO objective intake.

This is a read-only preparation bridge. It validates and maps an approved
selection into objective.v1, computes graph diagnostics, and returns a
cross-reference envelope. It does not append the intake ledger, run a cycle,
expand obligations, create a handoff, or execute anything.
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from rdo.graph import tarjan_sccs
from rdo.model import Obligation, Relationship
from rdo.tension import _classify_cycle, _find_cycles, assess_system
from rdo_adapters.objective_intake import ObjectiveInputStore, submit_objective, validate_objective
from rdo_adapters.seed_proposals import SeedProposalStore

SCHEMA_VERSION = "rdo.reviewed_seed_bridge.v2"
CYCLE_KINDS = ("depends_on", "influences")
MAX_CYCLE_SCC_NODES = 7
MAX_CYCLE_SCC_EDGES = 18


class ReviewedSeedBridgeError(ValueError):
    """An approved selection cannot be safely prepared for objective intake."""


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _merge_unique(*groups: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for value in group:
            if value not in seen:
                seen.add(value)
                result.append(value)
    return result


def _graph_diagnostics(seeds: list[dict], edges: list[dict]) -> dict:
    """Reuse RDO's iterative SCC and tension machinery with a cycle-enumeration cap.

    Simple-cycle enumeration can grow exponentially inside a dense SCC. Tarjan's
    SCC pass is linear; detailed cycle enumeration and system assessment run only
    when every cyclic component is within the configured safety bounds. If any
    component is larger, all cycle classifications remain UNKNOWN.
    """
    keys = sorted(seed["key"] for seed in seeds)
    adjacency = {key: set() for key in keys}
    cycle_edges = [edge for edge in edges if edge["kind"] in CYCLE_KINDS]
    for edge in cycle_edges:
        adjacency[edge["src"]].add(edge["dst"])
    ordered_adjacency = {
        key: sorted(targets) for key, targets in adjacency.items()
    }
    raw_components = tarjan_sccs(keys, ordered_adjacency)
    cyclic_components = []
    bounded = False

    for members in raw_components:
        member_set = set(members)
        internal = [
            edge for edge in cycle_edges
            if edge["src"] in member_set and edge["dst"] in member_set
        ]
        self_loop = any(edge["src"] == edge["dst"] for edge in internal)
        if len(members) == 1 and not self_loop:
            continue
        too_large = (
            len(members) > MAX_CYCLE_SCC_NODES
            or len(internal) > MAX_CYCLE_SCC_EDGES
        )
        bounded = bounded or too_large
        cyclic_components.append({
            "members": members,
            "size": len(members),
            "internal_cycle_edge_count": len(internal),
            "enumeration": "skipped_unknown" if too_large else "eligible",
        })

    if bounded:
        return {
            "status": "bounded_unknown",
            "scc_components": cyclic_components,
            "classified_cycles": [],
            "system_assessments": [],
            "limits": {
                "max_scc_nodes": MAX_CYCLE_SCC_NODES,
                "max_internal_cycle_edges": MAX_CYCLE_SCC_EDGES,
            },
            "note": (
                "At least one cyclic SCC exceeds the safe simple-cycle "
                "enumeration bound. Its cycle type and system assessment remain "
                "UNKNOWN; no cycle was removed or rewritten."
            ),
        }

    obligations = [
        Obligation(
            key=seed["key"],
            title=seed["title"],
            kind=seed["kind"],
            classification=seed["classification"],
            rationale=seed["rationale"],
            impact=seed["impact"],
            evidence_needs=list(seed["evidence_needs"]),
            assumptions=list(seed["assumptions"]),
            confidence=seed["confidence"],
            provenance="reviewed_seed_proposal",
        )
        for seed in seeds
    ]
    relationships = [Relationship(**edge) for edge in edges]
    cycles = _find_cycles(relationships)
    classified = [
        {
            "cycle": cycle,
            "classification": _classify_cycle(cycle, relationships),
        }
        for cycle in cycles
    ]
    assessments = [
        item.to_dict()
        for item in assess_system(
            {item.key: item for item in obligations}, relationships
        )
    ]
    return {
        "status": "complete",
        "scc_components": cyclic_components,
        "classified_cycles": classified,
        "system_assessments": assessments,
        "limits": {
            "max_scc_nodes": MAX_CYCLE_SCC_NODES,
            "max_internal_cycle_edges": MAX_CYCLE_SCC_EDGES,
        },
        "note": (
            "Structural analysis only. Prerequisite cycles are reported as "
            "build-order blockers; influence cycles are feedback candidates, "
            "not automatic defects. No planning or execution was started."
        ),
    }


def prepare_reviewed_selection(
    proposal_store: SeedProposalStore,
    proposal_id: str,
    objective_store: ObjectiveInputStore,
) -> dict:
    """Return a validated objective.v1 candidate plus its independent lineage.

    Only an explicitly approved proposal is accepted. The function reads both
    ledgers but writes neither. The caller must make any later append decision
    separately; this function never calls submit_objective().
    """
    selection = proposal_store.approved_selection(proposal_id)
    stored = proposal_store.get(proposal_id)
    proposal = stored["proposal"]
    if stored["status"] != "approved":
        raise ReviewedSeedBridgeError("proposal is not explicitly approved")
    if proposal.get("proposal_id") != proposal_id:
        raise ReviewedSeedBridgeError("proposal identity mismatch")
    if selection.get("proposal_id") != proposal_id:
        raise ReviewedSeedBridgeError("approved selection identity mismatch")

    raw = selection["raw_objective"]
    raw_digest = _canonical_digest(raw)
    if raw_digest != selection.get("raw_objective_sha256"):
        raise ReviewedSeedBridgeError("raw-objective digest does not match approved selection")

    alternative = selection["alternative"]
    alternative_id = selection["selected_alternative_id"]
    if alternative.get("alternative_id") != alternative_id:
        raise ReviewedSeedBridgeError("selected alternative identity mismatch")

    approval = selection["approval"]
    approval_events = [
        event for event in proposal_store.events()
        if event.get("event_kind") == "review_decision"
        and event.get("proposal_id") == proposal_id
        and event.get("record") == approval
    ]
    if len(approval_events) != 1:
        raise ReviewedSeedBridgeError(
            "the exact approval event could not be uniquely recovered"
        )
    approval_event = approval_events[0]

    history = objective_store.history(raw["objective_id"])
    existing_matches = [
        item for item in history
        if item.get("lineage", {}).get("proposal_id") == proposal_id
    ]
    if existing_matches:
        existing = existing_matches[-1]
        existing_lineage = existing["lineage"]
        if (existing_lineage.get("raw_objective_sha256") != raw_digest
                or existing_lineage.get("raw_objective_revision") != raw["revision"]
                or existing_lineage.get("raw_objective_supersedes_sha256") != raw["supersedes_sha256"]
                or existing_lineage.get("selected_alternative_id") != alternative_id):
            raise ReviewedSeedBridgeError(
                "this proposal already has an intake revision with conflicting lineage"
            )
        objective = validate_objective(existing["record"])
        objective_digest = _canonical_digest(objective)
        graph = _graph_diagnostics(
            objective["seed_obligations"], objective["relationships"]
        )
        return {
            "status": "already_persisted_for_intake",
            "objective": objective,
            "objective_input_sha256": objective_digest,
            "lineage": existing_lineage,
            "graph_analysis": graph,
            "persisted": True,
            "planning_started": False,
            "stage7_handoff_created": False,
            "note": (
                "The exact approved proposal lineage is already present in the "
                "objective revision ledger; no new revision was created."
            ),
        }
    if history:
        first = history[0]["record"]
        if (
            raw["original_text"] != first["original_text"]
            or raw["intent"] != first["intent"]
        ):
            raise ReviewedSeedBridgeError(
                "raw objective original_text/intent do not match the existing intake chain"
            )
        intake_revision = len(history) + 1
        intake_supersedes = history[-1]["sha256"]
    else:
        intake_revision = 1
        intake_supersedes = None

    # Raw and alternative-level constraints are both retained. Raw-level
    # reconciliation signatures remain in the raw proposal snapshot; only the
    # selected alternative's seed-keyed signatures fit objective.v1.
    payload = {
        "schema_version": "rdo.objective.v1",
        "objective_id": raw["objective_id"],
        "revision": intake_revision,
        "supersedes_sha256": intake_supersedes,
        "original_text": raw["original_text"],
        "intent": raw["intent"],
        "owner": raw["owner"],
        "source": dict(raw["source"]),
        "scope": dict(raw["scope"]),
        "constraints": _merge_unique(raw["constraints"], alternative["constraints"]),
        "exclusions": _merge_unique(raw["exclusions"], alternative["exclusions"]),
        "assumptions": _merge_unique(raw["assumptions"], alternative["assumptions"]),
        "acceptance_criteria": list(raw["acceptance_criteria"]),
        "seed_obligations": list(alternative["seed_obligations"]),
        "relationships": list(alternative["relationships"]),
        "reconciliation_signatures": dict(alternative["reconciliation_signatures"]),
        "max_depth": raw["max_depth"],
    }
    try:
        objective = validate_objective(payload)
    except Exception as exc:
        raise ReviewedSeedBridgeError(
            f"selected proposal does not satisfy objective.v1: {exc}"
        ) from exc

    objective_digest = _canonical_digest(objective)
    graph = _graph_diagnostics(
        objective["seed_obligations"], objective["relationships"]
    )
    lineage = {
        "schema_version": SCHEMA_VERSION,
        "proposal_id": proposal_id,
        "selected_alternative_id": alternative_id,
        "proposer_kind": proposal["proposer_kind"],
        "proposer_reference": proposal["proposer_reference"],
        "proposal_source_reference": proposal["source_reference"],
        "raw_objective_id": raw["objective_id"],
        "raw_objective_revision": raw["revision"],
        "raw_objective_sha256": raw_digest,
        "raw_objective_supersedes_sha256": raw["supersedes_sha256"],
        "raw_reconciliation_signatures": dict(raw["reconciliation_signatures"]),
        "acceptance_criterion_coverage": list(
            alternative["acceptance_criterion_coverage"]
        ),
        "approval": {
            "sequence": approval_event["sequence"],
            "event_sha256": approval_event["event_sha256"],
            "record": approval,
            "event": approval_event,
        },
        "objective_id": objective["objective_id"],
        "objective_revision": objective["revision"],
        "objective_supersedes_sha256": objective["supersedes_sha256"],
        "objective_input_sha256": objective_digest,
    }
    return {
        "status": "prepared_for_intake_review",
        "objective": objective,
        "objective_input_sha256": objective_digest,
        "lineage": lineage,
        "graph_analysis": graph,
        "persisted": False,
        "planning_started": False,
        "stage7_handoff_created": False,
        "note": (
            "Read-only preparation. The objective.v1 payload and lineage envelope "
            "are returned for review; neither ledger is appended and no RDO cycle runs."
        ),
    }


def submit_reviewed_selection(
    proposal_store: SeedProposalStore,
    proposal_id: str,
    objective_store: ObjectiveInputStore,
    repo_dir: str = ".",
    workdir: str = "rdo/.cycles",
) -> dict:
    """Persist an approved objective and lineage together, then run advisory RDO planning.

    The objective revision wrapper is the single durable append containing both
    the validated objective.v1 record and its proposal lineage. The proposal ledger
    is read-only here. A retry reuses the same objective revision and CycleStore
    identity; it does not create another revision for the same approved proposal.
    """
    expected_objective_dir = os.path.abspath(os.path.join(workdir, "objectives"))
    if os.path.abspath(objective_store.directory) != expected_objective_dir:
        raise ReviewedSeedBridgeError(
            "objective_store must point to the objectives directory inside workdir"
        )
    prepared = prepare_reviewed_selection(proposal_store, proposal_id, objective_store)
    intake = submit_objective(
        prepared["objective"],
        repo_dir=repo_dir,
        workdir=workdir,
        objective_lineage=prepared["lineage"],
    )
    return {
        "status": intake["status"],
        "proposal_id": proposal_id,
        "selected_alternative_id": prepared["lineage"]["selected_alternative_id"],
        "lineage": prepared["lineage"],
        "graph_analysis": prepared["graph_analysis"],
        "intake": intake,
        "note": (
            "The approved proposal was persisted with its lineage in one objective-ledger "
            "append. RDO planning is advisory; no Stage-7 handoff or execution was created."
        ),
    }
