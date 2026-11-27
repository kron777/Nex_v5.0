"""Graph intelligence over a discovered obligation graph (RDO v1.3 §16 Stage 3).

Stage 2 produces obligations + typed relationships and persists them. Stage 3 makes the
Extrapolator *understand* that structure, reusing the existing pieces rather than rebuilding:

  * typed edges            — the `Relationship.kind` vocabulary already exists
                             (depends_on | produces_for | reuses | duplicates | influences);
                             this module reads and summarises it and ADDS `duplicates`
                             CANDIDATE edges for review (never a silent merge).
  * cycle detection        — `tension._find_cycles` / `_classify_cycle` are reused; this module
                             adds proper SCC decomposition (Tarjan) on top.
  * safe convergence       — exact-key merging + MergeConflict stay in `extrapolator`; here we
                             only SURFACE semantic-duplicate candidates, we never merge them.

Everything is read-only analysis over obligation dicts + relationship dicts (as persisted on a
CycleRecord), so it resumes from a persisted artefact in a fresh process. Canonical keys are the
identity throughout; provenance and parent_key are preserved on every candidate.
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional, Set, Tuple

# edge kinds that express a build/runtime dependency direction (src depends on / is influenced by dst)
DEP_KINDS = ("depends_on", "influences")
BUILD_KINDS = ("depends_on",)   # hard prerequisites for implementation sequencing


# --------------------------------------------------------------------- adjacency ----

def _adjacency(rels: List[dict], kinds: Tuple[str, ...]) -> Dict[str, List[str]]:
    adj: Dict[str, List[str]] = {}
    for r in rels:
        if r.get("kind") in kinds:
            adj.setdefault(r["src"], []).append(r["dst"])
            adj.setdefault(r["dst"], [])
    return adj


def failure_propagation_candidates(
    obligations: List[dict],
    rels: List[dict],
    failed_keys: List[str],
) -> dict:
    """Trace potential downstream dependents of explicitly supplied failures.

    A depends_on edge is oriented consumer -> prerequisite, so a failure of the
    prerequisite may affect the consumer. This is structural dependency analysis
    only: it does not claim runtime propagation, severity, probability or causality.
    Influence/feedback edges are deliberately excluded.
    """
    if not isinstance(obligations, list) or not isinstance(rels, list) or not isinstance(failed_keys, list):
        return {
            "status": "invalid_input",
            "roots": [],
            "unknown_roots": [],
            "invalid_roots": [],
            "invalid_obligations": 0,
            "affected": [],
            "unresolved_dependency_edges": 0,
            "cycle_encountered": False,
        }

    known = set()
    invalid_obligations = 0
    for item in obligations:
        if not isinstance(item, dict) or not isinstance(item.get("key"), str) or not item["key"].strip():
            invalid_obligations += 1
            continue
        key = item["key"]
        if key in known:
            invalid_obligations += 1
            continue
        known.add(key)
    roots = sorted({key for key in failed_keys if isinstance(key, str) and key.strip()})
    invalid_roots = [str(key) for key in failed_keys
                     if not isinstance(key, str) or not key.strip()]
    unknown_roots = [key for key in roots if key not in known]

    dependents: Dict[str, Set[str]] = {}
    unresolved_edges = 0
    for edge in rels:
        if not isinstance(edge, dict):
            unresolved_edges += 1
            continue
        src, dst, kind = edge.get("src"), edge.get("dst"), edge.get("kind")
        if kind in ("produces_for", "reuses", "duplicates", "influences"):
            continue
        if kind != "depends_on":
            unresolved_edges += 1
            continue
        if (not isinstance(src, str) or not src.strip()
                or not isinstance(dst, str) or not dst.strip()
                or src not in known or dst not in known):
            unresolved_edges += 1
            continue
        dependents.setdefault(dst, set()).add(src)

    affected = []
    cycle_encountered = False
    for root in roots:
        if root not in known:
            continue
        queue = [root]
        distance = {root: 0}
        paths = {root: [root]}
        index = 0
        while index < len(queue):
            current = queue[index]
            index += 1
            for consumer in sorted(dependents.get(current, set())):
                if consumer in paths[current]:
                    cycle_encountered = True
                    continue
                # Breadth-first traversal preserves one deterministic shortest path
                # per dependent. An alternate convergent path is not a graph cycle.
                if consumer in distance:
                    continue
                distance[consumer] = distance[current] + 1
                paths[consumer] = paths[current] + [consumer]
                queue.append(consumer)

        for key in sorted((item for item in distance if item != root),
                          key=lambda item: (distance[item], item)):
            affected.append({
                "root": root,
                "key": key,
                "distance": distance[key],
                "direct": distance[key] == 1,
                "path": paths[key],
                "relationships": [
                    f"{paths[key][index + 1]}:depends_on:{paths[key][index]}"
                    for index in range(len(paths[key]) - 1)
                ],
            })

    status = (
        "partial" if unknown_roots or invalid_roots or invalid_obligations or unresolved_edges else
        "not_supplied" if not roots else
        "candidate_only" if affected else
        "no_known_dependents"
    )
    return {
        "status": status,
        "roots": roots,
        "unknown_roots": unknown_roots,
        "invalid_roots": invalid_roots,
        "invalid_obligations": invalid_obligations,
        "affected": affected,
        "unresolved_dependency_edges": unresolved_edges,
        "cycle_encountered": cycle_encountered,
        "note": (
            "Potential structural dependents via depends_on edges only; no runtime "
            "failure propagation, severity, probability or causal effect is inferred."
        ),
    }


# ------------------------------------------------------------ SCC decomposition ----

def tarjan_sccs(nodes: List[str], adj: Dict[str, List[str]]) -> List[List[str]]:
    """Tarjan's strongly connected components. Returns SCCs; order is deterministic
    (reverse topological). A trivial SCC is a single node with no self-loop."""
    index: Dict[str, int] = {}
    low: Dict[str, int] = {}
    on_stack: Set[str] = set()
    stack: List[str] = []
    counter = [0]
    out: List[List[str]] = []

    def strongconnect(v: str) -> None:
        # iterative DFS to avoid recursion limits on deep graphs
        work: List[Tuple[str, int]] = [(v, 0)]
        while work:
            node, pi = work[-1]
            if pi == 0:
                index[node] = low[node] = counter[0]
                counter[0] += 1
                stack.append(node)
                on_stack.add(node)
            recursed = False
            neigh = adj.get(node, [])
            for i in range(pi, len(neigh)):
                w = neigh[i]
                if w not in index:
                    work[-1] = (node, i + 1)
                    work.append((w, 0))
                    recursed = True
                    break
                if w in on_stack:
                    low[node] = min(low[node], index[w])
            if recursed:
                continue
            if low[node] == index[node]:
                comp: List[str] = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    comp.append(w)
                    if w == node:
                        break
                out.append(sorted(comp))
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])

    for n in nodes:
        if n not in index:
            strongconnect(n)
    return out


def _classify_component(members: Set[str], rels: List[dict]) -> str:
    """Classify an SCC's internal edges (same rule as tension._classify_cycle):
    all depends_on -> prerequisite_cycle; any influences -> feedback_loop; else unknown."""
    kinds = {r["kind"] for r in rels
             if r["src"] in members and r["dst"] in members and r["kind"] in DEP_KINDS}
    if "influences" in kinds:
        return "feedback_loop"
    if kinds == {"depends_on"}:
        return "prerequisite_cycle"
    return "unknown"


def scc_decomposition(obligations: List[dict], rels: List[dict],
                      kinds: Tuple[str, ...] = DEP_KINDS) -> dict:
    """Decompose the graph into SCCs. Non-trivial SCCs (size>1, or a self-loop) are the
    strongly connected *components*; each reports its members, the individual cycles inside it
    (reusing tension._find_cycles), a classification, its external PREREQUISITES (edges in from
    outside) and downstream DEPENDENTS (edges out to outside). Cycles are NOT removed."""
    from .tension import _find_cycles              # reuse the Stage-2 cycle detector
    from .model import Relationship

    keys = [o["key"] for o in obligations]
    adj = _adjacency(rels, kinds)
    for k in keys:
        adj.setdefault(k, [])
    sccs = tarjan_sccs(keys, adj)

    rel_objs = [Relationship(r["src"], r["dst"], r["kind"]) for r in rels if r.get("kind") in kinds]
    components: List[dict] = []
    for comp in sccs:
        members = set(comp)
        self_loop = any(r["src"] in members and r["dst"] in members and r["src"] == r["dst"]
                        for r in rels)
        if len(comp) == 1 and not self_loop:
            continue                               # trivial SCC — not a component
        internal = [r for r in rels if r["src"] in members and r["dst"] in members
                    and r.get("kind") in kinds]
        member_cycles = [" -> ".join(c) for c in _find_cycles(rel_objs)
                         if set(c) <= members]
        # src depends_on dst => dst is a PREREQUISITE of src. External prerequisites are the
        # outside nodes the component depends on; downstream dependents are outside nodes that
        # depend on the component.
        prerequisites = sorted({r["dst"] for r in rels if r["src"] in members
                                and r["dst"] not in members and r.get("kind") in kinds})
        dependents = sorted({r["src"] for r in rels if r["dst"] in members
                             and r["src"] not in members and r.get("kind") in kinds})
        components.append({
            "members": comp,
            "size": len(comp),
            "classification": _classify_component(members, rels),
            "internal_cycles": member_cycles,
            "internal_edges": [(r["src"], r["dst"], r["kind"]) for r in internal],
            "external_prerequisites": prerequisites,
            "downstream_dependents": dependents,
        })
    return {
        "scc_count": len(sccs),
        "nontrivial_components": components,
        "has_cyclic_components": bool(components),
    }


# ------------------------------------------------- semantic duplicate candidates ----

def _tokens(*parts: str) -> Set[str]:
    out: Set[str] = set()
    for p in parts:
        out |= {t for t in (p or "").lower().replace("_", " ").split() if len(t) > 2}
    return out


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def dedup_candidates(obligations: List[dict], threshold: float = 0.6) -> List[dict]:
    """Semantic duplicate CANDIDATES beyond exact-key matching — surfaced for review, NEVER
    merged. Two obligations of the SAME kind are candidates when they either reconcile to the
    SAME existing mechanism (confirmed_equivalent) or are strongly similar in child-kind/title
    (uncertain_similar). Provenance + parent are retained for each side so a reviewer can act."""
    by_kind: Dict[str, List[dict]] = {}
    for o in obligations:
        by_kind.setdefault(o["kind"], []).append(o)

    out: List[dict] = []
    for kind, obs in by_kind.items():
        for i in range(len(obs)):
            for j in range(i + 1, len(obs)):
                a, b = obs[i], obs[j]
                a_ev = tuple(a.get("recon_evidence") or [])
                b_ev = tuple(b.get("recon_evidence") or [])
                suffix_a = a["key"].rsplit(".", 1)[-1]
                suffix_b = b["key"].rsplit(".", 1)[-1]
                sim = _jaccard(_tokens(a.get("title"), a.get("rationale")),
                               _tokens(b.get("title"), b.get("rationale")))
                if a_ev and a_ev == b_ev:
                    status, reason = "confirmed_equivalent", "reconcile to the same mechanism"
                elif suffix_a == suffix_b or sim >= threshold:
                    status, reason = "uncertain_similar", (
                        "same child-kind" if suffix_a == suffix_b else f"title similarity {sim:.2f}")
                else:
                    continue
                out.append({
                    "kind": kind, "status": status, "reason": reason, "similarity": round(sim, 2),
                    "a": {"key": a["key"], "parent": a.get("parent_key"),
                          "provenance": a.get("provenance")},
                    "b": {"key": b["key"], "parent": b.get("parent_key"),
                          "provenance": b.get("provenance")},
                })
    # confirmed first, then most-similar; deterministic
    out.sort(key=lambda c: (c["status"] != "confirmed_equivalent", -c["similarity"],
                            c["a"]["key"], c["b"]["key"]))
    return out


def duplicate_candidate_edges(candidates: List[dict]) -> List[dict]:
    """Represent duplicate candidates as typed `duplicates` edges (review artefacts, not merges),
    reusing the existing Relationship.kind vocabulary."""
    return [{"src": c["a"]["key"], "dst": c["b"]["key"], "kind": "duplicates",
             "note": f"{c['status']}: {c['reason']}"} for c in candidates]


# -------------------------------------------------------------- typed edge view ----

def typed_edge_summary(rels: List[dict]) -> Dict[str, int]:
    """Count edges by their actual type — the graph is not a bare depends_on tree."""
    out: Dict[str, int] = {}
    for r in rels:
        out[r.get("kind", "unknown")] = out.get(r.get("kind", "unknown"), 0) + 1
    return out


# producers of a signal (kinds that generate output a consumer reads); evidence = the kind itself
_PRODUCER_KINDS = {"score", "daemon", "calibration", "api"}


def derive_produces_for(obligations: List[dict]) -> List[dict]:
    """Derive `produces_for` edges from the architecture: at the objective's top level, a producer
    (score/daemon/...) supplies the signal its consumers read. This reuses the EXISTING
    `produces_for` relationship type (no new taxonomy); the obligation kinds are the evidence. It
    only runs at depth 0 (the architectural units), so it does not flood the graph with edges."""
    seeds = [o for o in obligations if o.get("depth", 0) == 0]
    producers = [o["key"] for o in seeds if o.get("kind") in _PRODUCER_KINDS]
    consumers = [o["key"] for o in seeds if o.get("kind") == "consumer"]
    return [{"src": p, "dst": c, "kind": "produces_for",
             "note": "producer supplies the signal the consumer reads"}
            for p in sorted(producers) for c in sorted(consumers)]


# -------------------------------------------------------------- completeness ----

def completeness(obligations: List[dict], frontier: List[dict]) -> dict:
    """What the graph accounts for, measured against the discovered obligations themselves (NOT an
    arbitrary node/edge target): accounted (reuse/net-new/anti), unresolved (no signature),
    deferred (budget), and where evidence is missing (net-new with no reconciliation signature)."""
    from .extrapolator import frontier_breakdown
    total = len(obligations)
    reuse = [o["key"] for o in obligations if o.get("recon_status") == "reuse_existing"]
    net_new = [o["key"] for o in obligations if o.get("recon_status") in ("missing", "partial")]
    unresolved = [o["key"] for o in obligations if o.get("recon_status") == "unknown"]
    anti = [o["key"] for o in obligations if o.get("classification") == "anti_requirement"]
    # evidence gaps: a reuse claim with no backing evidence (should be none), or net-new with no
    # reconciliation signature at all (absence asserted without a check)
    reuse_unbacked = [o["key"] for o in obligations
                      if o.get("recon_status") == "reuse_existing" and not o.get("recon_evidence")]
    fb = frontier_breakdown(frontier)
    return {
        "discovered": total,
        "accounted": {"reuse": len(reuse), "net_new": len(net_new), "anti_requirement": len(anti)},
        "unresolved": unresolved,
        "unresolved_count": len(unresolved),
        "deferred_count": fb["deferred"],
        "evidence_gaps": {"reuse_claims_without_evidence": reuse_unbacked},
        # complete w.r.t. the objective iff nothing is unresolved and every reuse claim is backed
        "complete_against_objective": len(unresolved) == 0 and not reuse_unbacked,
        "note": "completeness is measured against the discovered obligations, not a target count",
    }


# -------------------------------------------------- implementation sequence ----

def implementation_sequence(obligations: List[dict], rels: List[dict]) -> dict:
    """A defensible build sequence derived from HARD prerequisites (depends_on), NOT priority.

    SCCs of the depends_on graph are collapsed to single units (a cyclic build component cannot be
    linearised internally); the resulting condensation DAG is levelised by Kahn's algorithm so each
    level is a set of independent units that may proceed IN PARALLEL. Cyclic components are reported
    as units; nodes that cannot be ordered (should not happen after condensation) are surfaced."""
    keys = [o["key"] for o in obligations]
    build_sccs = tarjan_sccs(keys, _adjacency(rels, BUILD_KINDS))
    comp_of: Dict[str, int] = {}
    for i, comp in enumerate(build_sccs):
        for k in comp:
            comp_of[k] = i
    cyclic = {i for i, comp in enumerate(build_sccs)
              if len(comp) > 1 or any(r["src"] == r["dst"] and r["src"] in comp
                                      for r in rels if r.get("kind") == "depends_on")}

    # condensation edges (between components), dependency direction src depends_on dst
    cond_adj: Dict[int, Set[int]] = {i: set() for i in range(len(build_sccs))}
    indeg: Dict[int, int] = {i: 0 for i in range(len(build_sccs))}
    for r in rels:
        if r.get("kind") != "depends_on":
            continue
        cs, cd = comp_of.get(r["src"]), comp_of.get(r["dst"])
        if cs is None or cd is None or cs == cd:
            continue
        # src depends_on dst -> dst must be built first -> edge dst -> src in build order
        if cs not in cond_adj[cd]:
            cond_adj[cd].add(cs)
            indeg[cs] += 1

    # Kahn levelisation -> parallelisable levels
    frontier = sorted(i for i in range(len(build_sccs)) if indeg[i] == 0)
    seen: Set[int] = set()
    levels: List[List[dict]] = []
    while frontier:
        level: List[dict] = []
        nxt: Set[int] = set()
        for ci in frontier:
            seen.add(ci)
            members = build_sccs[ci]
            level.append({"unit": members if ci in cyclic else members[0],
                          "cyclic_component": ci in cyclic,
                          "members": members})
            for nb in cond_adj[ci]:
                indeg[nb] -= 1
                if indeg[nb] == 0:
                    nxt.add(nb)
        levels.append(sorted(level, key=lambda u: str(u["unit"])))
        frontier = sorted(nxt)

    unsequenced = [build_sccs[i] for i in range(len(build_sccs)) if i not in seen]  # cycle remnant
    return {
        "levels": levels,
        "parallel_width": max((len(l) for l in levels), default=0),
        "cyclic_components": [build_sccs[i] for i in sorted(cyclic)],
        "unsequenced": unsequenced,
        "note": "order is from depends_on prerequisites only; it is NOT a priority ranking",
    }


def compare_adjacent_relationship_impacts(
    before_cycle: dict,
    after_cycle: dict,
    changed_capabilities: List[str],
) -> dict:
    """Compare relationship and tension snapshots around explicitly changed nodes.

    This is a differential evidence report, not causal attribution. The caller
    supplies the capability keys being changed; this function identifies incident
    relationships and compares their stored records and relationship assessments
    before/after. It does not calculate benefit, harm, risk or sufficiency.
    """
    if (not isinstance(before_cycle, dict) or not isinstance(after_cycle, dict)
            or not isinstance(changed_capabilities, list)):
        return {
            "status": "invalid_input",
            "changed_capabilities": [],
            "invalid_capabilities": [],
            "affected_relationships": [],
            "invalid_relationship_records": 0,
            "unresolved_relationship_references": 0,
            "invalid_assessment_records": 0,
            "invalid_obligation_records": 0,
            "unknown_capabilities": [],
        }

    changed = sorted({key for key in changed_capabilities
                      if isinstance(key, str) and key.strip() and key == key.strip()})
    invalid_capabilities = [str(key) for key in changed_capabilities
                            if not isinstance(key, str) or not key.strip() or key != key.strip()]
    if not changed:
        return {
            "status": "partial" if invalid_capabilities else "not_supplied",
            "changed_capabilities": [],
            "invalid_capabilities": invalid_capabilities,
            "affected_relationships": [],
            "invalid_relationship_records": 0,
            "unresolved_relationship_references": 0,
            "invalid_assessment_records": 0,
            "invalid_obligation_records": 0,
            "unknown_capabilities": [],
        }
    changed_set = set(changed)

    def _obligation_keys(cycle):
        keys = set()
        invalid = 0
        records = cycle.get("obligations")
        if not isinstance(records, list):
            return keys, 1
        for record in records:
            if (not isinstance(record, dict)
                    or not isinstance(record.get("key"), str)
                    or not record["key"].strip()
                    or record["key"] != record["key"].strip()):
                invalid += 1
                continue
            key = record["key"]
            if key in keys:
                invalid += 1
                continue
            keys.add(key)
        return keys, invalid

    def _relationship_groups(cycle):
        groups = {}
        invalid = 0
        records = cycle.get("relationships")
        if not isinstance(records, list):
            return groups, 1
        for record in records:
            if not isinstance(record, dict):
                invalid += 1
                continue
            src, dst, kind = record.get("src"), record.get("dst"), record.get("kind")
            if not all(isinstance(item, str) and item.strip() and item == item.strip()
                       for item in (src, dst, kind)):
                invalid += 1
                continue
            identity = (src, kind, dst)
            try:
                encoded = json.dumps(record, sort_keys=True, separators=(",", ":"))
            except (TypeError, ValueError):
                invalid += 1
                continue
            groups.setdefault(identity, []).append((encoded, json.loads(encoded)))
        return {
            key: [record for _, record in sorted(items, key=lambda pair: pair[0])]
            for key, items in groups.items()
        }, invalid

    def _assessment_groups(cycle):
        groups = {}
        invalid = 0
        records = cycle.get("tension")
        if not isinstance(records, list):
            return groups, 1
        for record in records:
            if not isinstance(record, dict):
                invalid += 1
                continue
            if record.get("level") != "relationship":
                continue
            subject = record.get("subject")
            if not isinstance(subject, str) or not subject.strip() or subject != subject.strip():
                invalid += 1
                continue
            try:
                encoded = json.dumps(record, sort_keys=True, separators=(",", ":"))
            except (TypeError, ValueError):
                invalid += 1
                continue
            groups.setdefault(subject, []).append((encoded, json.loads(encoded)))
        return {
            key: [record for _, record in sorted(items, key=lambda pair: pair[0])]
            for key, items in groups.items()
        }, invalid

    before_nodes, invalid_before_obligations = _obligation_keys(before_cycle)
    after_nodes, invalid_after_obligations = _obligation_keys(after_cycle)
    before_relationships, invalid_before_relationships = _relationship_groups(before_cycle)
    after_relationships, invalid_after_relationships = _relationship_groups(after_cycle)
    before_assessments, invalid_before_assessments = _assessment_groups(before_cycle)
    after_assessments, invalid_after_assessments = _assessment_groups(after_cycle)
    invalid_assessments = invalid_before_assessments + invalid_after_assessments
    known_capabilities = before_nodes | after_nodes
    unknown_capabilities = sorted(
        key for key in changed if key not in known_capabilities
    )
    invalid_obligations = invalid_before_obligations + invalid_after_obligations
    invalid_relationship_references = sum(
        1
        for groups, nodes in (
            (before_relationships, before_nodes),
            (after_relationships, after_nodes),
        )
        for src, _kind, dst in groups
        if src not in nodes or dst not in nodes
    )
    invalid_relationships = invalid_before_relationships + invalid_after_relationships

    identities = sorted(
        identity for identity in set(before_relationships) | set(after_relationships)
        if identity[0] in changed_set or identity[2] in changed_set
    )
    affected = []
    partial = bool(invalid_capabilities or invalid_relationships or invalid_assessments
                   or invalid_obligations or invalid_relationship_references
                   or unknown_capabilities)

    for src, kind, dst in identities:
        identity = f"{src} -{kind}-> {dst}"
        before_records = before_relationships.get((src, kind, dst), [])
        after_records = after_relationships.get((src, kind, dst), [])
        if not before_records:
            relationship_status = "added"
        elif not after_records:
            relationship_status = "removed"
        elif before_records == after_records:
            relationship_status = "unchanged"
        else:
            relationship_status = "changed"

        before_matches = before_assessments.get(identity, [])
        after_matches = after_assessments.get(identity, [])
        assessment_status = "compared"
        before_assessment = before_matches[0] if len(before_matches) == 1 else None
        after_assessment = after_matches[0] if len(after_matches) == 1 else None
        changed_dimensions = []
        changed_assessment_fields = []
        assessment_changed = None
        verdict_changed = None

        if len(before_matches) > 1 or len(after_matches) > 1:
            assessment_status = "ambiguous"
            partial = True
        elif before_assessment is None and after_assessment is None:
            assessment_status = "not_recorded"
            partial = True
        elif before_assessment is None:
            assessment_status = (
                "newly_assessed" if relationship_status == "added" else
                "orphaned_after" if relationship_status == "removed" else
                "missing_before"
            )
            if relationship_status != "added":
                partial = True
        elif after_assessment is None:
            assessment_status = (
                "assessment_removed" if relationship_status == "removed" else
                "orphaned_before" if relationship_status == "added" else
                "missing_after"
            )
            if relationship_status != "removed":
                partial = True
        else:
            before_dimensions = before_assessment.get("dimensions", {})
            after_dimensions = after_assessment.get("dimensions", {})
            if isinstance(before_dimensions, dict) and isinstance(after_dimensions, dict):
                dimension_keys = set(before_dimensions) | set(after_dimensions)
                changed_dimensions = sorted(
                    key for key in dimension_keys
                    if ((key in before_dimensions) != (key in after_dimensions)
                        or before_dimensions.get(key) != after_dimensions.get(key))
                )
            else:
                changed_dimensions = ["<dimensions>"]
                partial = True
            changed_assessment_fields = sorted(
                field for field in ("verdict", "inference", "evidence", "note")
                if ((field in before_assessment) != (field in after_assessment)
                    or before_assessment.get(field) != after_assessment.get(field))
            )
            assessment_changed = bool(changed_dimensions or changed_assessment_fields)
            verdict_changed = before_assessment.get("verdict") != after_assessment.get("verdict")

        affected.append({
            "identity": identity,
            "src": src,
            "kind": kind,
            "dst": dst,
            "neighbours": sorted({endpoint for endpoint in (src, dst)
                                  if endpoint not in changed_set}),
            "relationship_status": relationship_status,
            "before_relationships": before_records,
            "after_relationships": after_records,
            "assessment_status": assessment_status,
            "before_assessment": before_assessment,
            "after_assessment": after_assessment,
            "assessment_changed": assessment_changed,
            "verdict_changed": verdict_changed,
            "changed_dimensions": changed_dimensions,
            "changed_assessment_fields": changed_assessment_fields,
        })

    status = (
        "partial" if partial else
        "no_adjacent_relationships" if not affected else
        "compared"
    )
    return {
        "status": status,
        "changed_capabilities": changed,
        "invalid_capabilities": invalid_capabilities,
        "unknown_capabilities": unknown_capabilities,
        "invalid_obligation_records": invalid_obligations,
        "affected_relationships": affected,
        "invalid_relationship_records": invalid_relationships,
        "unresolved_relationship_references": invalid_relationship_references,
        "invalid_assessment_records": invalid_assessments,
        "note": (
            "Before/after differences for relationships incident to explicitly changed capabilities. "
            "These are correlated structural and assessment changes, not proof of causality, harm or benefit."
        ),
    }


# --------------------------------------------------------------- top-level ----

def analyse(obligations: List[dict], relationships: List[dict], frontier: List[dict]) -> dict:
    """Run the full Stage-3 analysis over a (persisted) obligation graph. Read-only; canonical
    keys are the identity; nothing is merged or mutated."""
    candidates = dedup_candidates(obligations)
    produces_for = derive_produces_for(obligations)
    dup_edges = duplicate_candidate_edges(candidates)
    structural = typed_edge_summary(relationships)
    # the represented relationship model, by type: structural depends_on + derived produces_for
    # (architecture) + duplicates CANDIDATES (review). Distinct meanings kept distinct.
    typed = dict(structural)
    typed["produces_for"] = len(produces_for)
    typed["duplicates(candidate)"] = len(dup_edges)
    return {
        "typed_edges": typed,
        "structural_edges": structural,
        "derived_relationships": {"produces_for": produces_for, "duplicates": dup_edges},
        "scc": scc_decomposition(obligations, relationships),
        "duplicate_candidates": candidates,
        "duplicate_candidate_edges": dup_edges,
        "completeness": completeness(obligations, frontier),
        "implementation_sequence": implementation_sequence(obligations, relationships),
    }
