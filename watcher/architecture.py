"""Architecture readers + a SEPARATE runtime-architecture graph.

Two readers parse the existing source artifacts READ-ONLY and never modify them:
  * `read_mind_map`  — mind_map/MIND_MAP.yaml (the mental-factor / property aspect map)
  * `read_dag`       — sentience_dag.json (the build-dependency DAG)

`RuntimeGraph` is a THIRD, independent reconstruction of the actual runtime
producer->consumer wiring. It is NOT a modification or replacement of the DAG or
mind map; it is built in memory from verified source edges (plus honest
lower-confidence ones) and emitted as its own artifact. Cycle detection runs on
it to surface feedback loops — the real ones live in the data flow, not the
acyclic build DAG.
"""
from __future__ import annotations

import dataclasses
import json
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .evidence import Evidence


# ----------------------------------------------------------------- readers ----

def read_mind_map(path: str) -> Evidence:
    with open(path, "r", encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    nodes = [n for n in (doc.get("nodes") or []) if isinstance(n, dict) and "id" in n]
    classes: Dict[str, int] = {}
    for n in nodes:
        classes[n.get("evidence", "unknown")] = classes.get(n.get("evidence", "unknown"), 0) + 1
    data = {"node_count": len(nodes), "by_evidence_class": classes,
            "nodes": {n["id"]: {"layer": n.get("layer"), "evidence": n.get("evidence"),
                                "last_verified": n.get("last_verified")} for n in nodes}}
    return Evidence("mind_map", data, "cloud", "static", path,
                    interpretation="MIND_MAP.yaml parsed read-only; node evidence classes counted.")


def read_dag(path: str) -> Evidence:
    with open(path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    nodes = doc.get("nodes", {})
    status: Dict[str, int] = {}
    for _, n in nodes.items():
        status[n.get("status", "?")] = status.get(n.get("status", "?"), 0) + 1
    data = {"node_count": len(nodes), "by_status": status,
            "nodes": {k: {"layer": v.get("layer"), "status": v.get("status"),
                          "prereqs": v.get("prereqs", [])} for k, v in nodes.items()}}
    return Evidence("sentience_dag", data, "cloud", "static", path,
                    interpretation="sentience_dag.json parsed read-only; build-order DAG.")


# -------------------------------------------------- the runtime graph ----------

@dataclasses.dataclass
class Edge:
    src: str
    dst: str
    label: str
    evidence_class: str          # implemented | inferred | unknown | measured
    origin: str = "cloud"
    source_ref: str = ""
    note: Optional[str] = None   # kept separate from the fact of the edge


class RuntimeGraph:
    """A separate reconstruction of NEX's runtime wiring. Never writes to the
    DAG or mind map."""

    def __init__(self) -> None:
        self.nodes: set[str] = set()
        self.edges: List[Edge] = []

    def add(self, edge: Edge) -> None:
        self.nodes.add(edge.src)
        self.nodes.add(edge.dst)
        self.edges.append(edge)

    def find_cycles(self) -> List[List[str]]:
        """All simple directed cycles (DFS). Feedback loops."""
        adj: Dict[str, List[str]] = {}
        for e in self.edges:
            adj.setdefault(e.src, []).append(e.dst)
        cycles: List[List[str]] = []
        seen_keys: set = set()

        def dfs(start: str, node: str, stack: List[str], onstack: set) -> None:
            for nxt in adj.get(node, []):
                if nxt == start and len(stack) >= 1:
                    cyc = stack + [start]
                    key = frozenset(cyc)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        cycles.append(cyc)
                elif nxt not in onstack:
                    dfs(start, nxt, stack + [nxt], onstack | {nxt})

        for n in list(self.nodes):
            dfs(n, n, [n], {n})
        return cycles

    def to_dict(self) -> dict:
        return {"nodes": sorted(self.nodes),
                "edges": [dataclasses.asdict(e) for e in self.edges]}


def build_runtime_graph() -> RuntimeGraph:
    """Seed the runtime graph from the edges verified against source in Phase 1.

    Evidence classes are honest: 'implemented' = producer->consumer read in code
    this session; the candidate mood loop is 'inferred' and tagged HYPOTHESIS per
    the founder constraint (not promoted to fact without a live runtime trace).
    """
    g = RuntimeGraph()
    V = "implemented"  # code+tests exist; read in source Phase 1
    src = "Phase-1 source read (expectations.py, global_workspace, commitments.py, episodic.py)"
    verified: List[Tuple[str, str, str]] = [
        ("producers", "expectations", "ingest(): self/world/surprise/owned-belief -> expectations header"),
        ("expectations", "reconciler", "single reconcile() adjudicates; DB-guarded single writer"),
        ("reconciler", "event_valence", "writes event_valence per resolution"),
        ("reconciler", "affect_nudges", "writes affect_nudges when valence != 0"),
        ("reconciler", "expectation_learning_log", "learning deltas (provenance-logged)"),
        ("source_kind", "ownership", "provenance (Build D) -> ownership share"),
        ("ownership", "valence_gate", "ownership>=0.5 gates valence admission"),
        ("reconciler", "beliefs.confidence", "_learn step (flag-gated): mutates basis-belief confidence"),
        ("beliefs.confidence", "producers", "beliefs feed surprise/owned-belief expectations"),
        ("affect_nudges", "affect_state", "mood_nudge: one-way, rate-limited"),
        ("held_tensions", "episodic", "episodic retrieves held_tensions (one-way)"),
        ("global_workspace", "chat_assembly", "r77 chat arbiter: budget-gated selection"),
    ]
    for s, d, lbl in verified:
        g.add(Edge(s, d, lbl, V, "cloud", src))

    # The learning<->beliefs feedback loop is REAL and live (two implemented edges
    # above already close it: learning->beliefs.confidence->producers->...->learning).

    # Candidate mood loop: HYPOTHESIS ONLY until a runtime trace closes it.
    g.add(Edge("affect_state", "chat_assembly",
               "mood/affect stances feed generation (stage_affect.*.stance_for, gui/server)",
               "inferred", "cloud", "Phase-1 source read (gui/server.py imports)",
               note="HYPOTHESIS: part of a candidate mood feedback loop "
                    "mood->generation->beliefs->expectations->valence->mood. "
                    "NOT a verified cycle; needs a live runtime trace (host)."))
    g.add(Edge("chat_assembly", "beliefs.confidence",
               "generated content can crystallise to beliefs (fountain)",
               "inferred", "cloud", "Phase-1 source read",
               note="HYPOTHESIS edge for the candidate mood loop; unverified."))
    return g


def runtime_graph_evidence(g: RuntimeGraph) -> Evidence:
    cycles = g.find_cycles()
    # Separate verified cycles from hypothesis cycles by the edges they use.
    hyp_nodes = {"affect_state"}
    labelled = []
    for c in cycles:
        is_hyp = any(n in hyp_nodes for n in c)
        labelled.append({"cycle": c, "status": "HYPOTHESIS" if is_hyp else "implemented"})
    return Evidence(
        "runtime_graph",
        {"nodes": sorted(g.nodes), "edge_count": len(g.edges),
         "feedback_cycles": labelled},
        "cloud", "implemented",
        "watcher.architecture.build_runtime_graph",
        interpretation="SEPARATE reconstruction (not the DAG or mind map). The live "
                       "learning<->beliefs cycle is implemented; mood-loop cycles are HYPOTHESIS.")


def collect(mind_map_path: str, dag_path: str) -> List[Evidence]:
    out: List[Evidence] = []
    try:
        out.append(read_mind_map(mind_map_path))
    except Exception as e:  # record the gap, don't guess
        out.append(Evidence("mind_map", None, "cloud", "unknown", mind_map_path,
                            modifier="unverified", interpretation=f"unreadable: {e}"))
    try:
        out.append(read_dag(dag_path))
    except Exception as e:
        out.append(Evidence("sentience_dag", None, "cloud", "unknown", dag_path,
                            modifier="unverified", interpretation=f"unreadable: {e}"))
    out.append(runtime_graph_evidence(build_runtime_graph()))
    return out
