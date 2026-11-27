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


# -------------------------------------- before/after neighbour impact review ----

def relationship_impact_delta(before_relationships: List[dict],
                              after_relationships: List[dict],
                              changed_nodes: List[str],
                              before_assessments: Optional[List[dict]] = None,
                              after_assessments: Optional[List[dict]] = None) -> dict:
    """Compare relationship evidence around explicitly declared changed capabilities.

    This is a structural before/after review aid, not causal attribution or a verdict.
    It reports every incident relationship (including unchanged ones), structural
    additions/removals/field changes, and any supplied relationship-assessment change.
    It never mutates either snapshot or infers that a coincident change was caused by
    the declared capability change.
    """
    if not isinstance(changed_nodes, (list, tuple, set)):
        raise ValueError("changed_nodes must be a list, tuple or set of non-blank keys")
    if any(not isinstance(node, str) or not node.strip() for node in changed_nodes):
        raise ValueError("changed_nodes must contain non-blank string keys")
    changed = set(changed_nodes)

    def index_relationships(items, label):
        if not isinstance(items, list):
            raise ValueError(f"{label} relationships must be a list")
        indexed = {}
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"{label} relationship entries must be dictionaries")
            identity = tuple(item.get(field) for field in ("src", "dst", "kind"))
            if any(not isinstance(value, str) or not value.strip() for value in identity):
                raise ValueError(f"{label} relationship identity must contain non-blank src, dst and kind")
            if identity in indexed:
                raise ValueError(f"{label} relationships contain duplicate identity: {identity!r}")
            indexed[identity] = dict(item)
        return indexed

    def index_assessments(items, label):
        if items is None:
            return {}
        if not isinstance(items, list):
            raise ValueError(f"{label} assessments must be a list")
        indexed = {}
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("subject"), str):
                continue
            indexed[item["subject"]] = dict(item)
        return indexed

    before = index_relationships(before_relationships, "before")
    after = index_relationships(after_relationships, "after")
    before_t = index_assessments(before_assessments, "before")
    after_t = index_assessments(after_assessments, "after")
    all_keys = sorted(set(before) | set(after))
    structural_changes = {}
    for key in all_keys:
        old, new = before.get(key), after.get(key)
        if old is None:
            change, fields = "added", sorted(k for k in new if k not in ("src", "dst", "kind"))
        elif new is None:
            change, fields = "removed", sorted(k for k in old if k not in ("src", "dst", "kind"))
        else:
            fields = sorted(k for k in set(old) | set(new)
                            if k not in ("src", "dst", "kind") and old.get(k) != new.get(k))
            change = "modified" if fields else "unchanged"
        structural_changes[key] = (change, fields)

    reviewed = []
    unrelated_changes = []
    for key in all_keys:
        src, dst, kind = key
        old, new = before.get(key), after.get(key)
        change, fields = structural_changes[key]
        subject = f"{src} -{kind}-> {dst}"
        old_assessment = before_t.get(subject)
        new_assessment = after_t.get(subject)
        assessment_changed = (
            old_assessment != new_assessment
            if old_assessment is not None and new_assessment is not None else None
        )
        entry = {
            "identity": [src, dst, kind],
            "change": change,
            "changed_fields": fields,
            "before": old,
            "after": new,
            "assessment_before": old_assessment,
            "assessment_after": new_assessment,
            "assessment_changed": assessment_changed,
        }
        if src in changed or dst in changed:
            reviewed.append(entry)
        elif change != "unchanged" or assessment_changed is True:
            unrelated_changes.append(entry)

    changed_reviewed = [item for item in reviewed
                        if item["change"] != "unchanged" or item["assessment_changed"] is True]
    return {
        "status": "reviewed",
        "declared_changed_nodes": sorted(changed),
        "reviewed_adjacent_relationships": reviewed,
        "changed_adjacent_relationships": changed_reviewed,
        "unrelated_changes": unrelated_changes,
        "summary": {
            "adjacent_relationships_reviewed": len(reviewed),
            "adjacent_relationships_changed": len(changed_reviewed),
            "unrelated_changes": len(unrelated_changes),
        },
        "causal_attribution": "not_established; this is a structural before/after comparison",
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
