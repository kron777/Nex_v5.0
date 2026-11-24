"""Architecture readers + a SEPARATE runtime-architecture graph.

Two readers parse the existing source artifacts READ-ONLY and never modify them:
  * `read_mind_map`  — mind_map/MIND_MAP.yaml (the mental-factor / property aspect map)
  * `read_dag`       — sentience_dag.json (the build-dependency DAG)

`RuntimeGraph` is a THIRD, independent reconstruction of the actual runtime
producer->consumer wiring. It is NOT a modification or replacement of the DAG or
mind map.

Each edge carries THREE independent evidence dimensions, kept distinguishable
(founder constraint #5):
  * source_implemented — the code for this edge was read in source
  * test_verified      — a test asserts the behaviour
  * runtime_observed   — the edge was seen firing in a live trace (host only)
An edge's `level` is the strongest dimension it has; a cycle's status is its
WEAKEST edge (a loop is only as established as its least-established link). These
flags are curated review assertions, not dynamically derived proofs; the current
source references are group-level and do not provide a per-edge source/test trace.
NEX is in STANDBY, so nothing is `runtime_observed` yet — that stays an honest gap.
"""
from __future__ import annotations

import dataclasses
import json
from typing import Dict, List, Optional, Tuple

import yaml

from .evidence import Evidence

# level ordering, weakest -> strongest
LEVELS = ("hypothesis", "source_implemented", "test_verified", "runtime_observed")


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
    source_implemented: bool
    test_verified: bool
    runtime_observed: bool
    origin: str = "cloud"
    source_ref: str = ""
    note: Optional[str] = None

    @property
    def level(self) -> str:
        if self.runtime_observed:
            return "runtime_observed"
        if self.test_verified:
            return "test_verified"
        if self.source_implemented:
            return "source_implemented"
        return "hypothesis"


class RuntimeGraph:
    """A separate reconstruction of NEX's runtime wiring. Never writes to the DAG
    or mind map."""

    def __init__(self) -> None:
        self.nodes: set[str] = set()
        self.edges: List[Edge] = []

    def add(self, edge: Edge) -> None:
        self.nodes.add(edge.src)
        self.nodes.add(edge.dst)
        self.edges.append(edge)

    def _level_index(self, lvl: str) -> int:
        return LEVELS.index(lvl)

    def find_cycles(self) -> List[dict]:
        """All simple directed cycles (DFS). Each is labeled with its WEAKEST
        edge level, and the per-dimension flags are preserved."""
        adj: Dict[str, List[Edge]] = {}
        for e in self.edges:
            adj.setdefault(e.src, []).append(e)
        out: List[dict] = []
        seen: set = set()

        def dfs(start, node, path_nodes, path_edges, onstack):
            for e in adj.get(node, []):
                if e.dst == start and path_edges:
                    cyc = path_nodes + [start]
                    key = frozenset(cyc)
                    if key not in seen:
                        seen.add(key)
                        edges = path_edges + [e]
                        weakest = min((x.level for x in edges), key=self._level_index)
                        out.append({
                            "cycle": cyc,
                            "status": weakest,
                            "source_implemented": all(x.source_implemented for x in edges),
                            "test_verified": all(x.test_verified for x in edges),
                            "runtime_observed": all(x.runtime_observed for x in edges),
                        })
                elif e.dst not in onstack:
                    dfs(start, e.dst, path_nodes + [e.dst], path_edges + [e], onstack | {e.dst})

        for n in list(self.nodes):
            dfs(n, n, [n], [], {n})
        return out

    def to_dict(self) -> dict:
        return {"nodes": sorted(self.nodes),
                "edges": [{**dataclasses.asdict(e), "level": e.level} for e in self.edges]}


def build_runtime_graph() -> RuntimeGraph:
    """Seed the runtime graph from Phase-1 source reads. Edges carry the three
    evidence dimensions explicitly. Nothing is `runtime_observed` yet (STANDBY)."""
    g = RuntimeGraph()
    src = "Phase-1 source read (expectations.py, global_workspace, commitments.py, episodic.py)"
    # (src, dst, label): all are source_implemented AND test_verified (Build B/D + r77
    # have tests), NOT runtime_observed (NEX is off).
    tv: List[Tuple[str, str, str]] = [
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
    for s, d, lbl in tv:
        g.add(Edge(s, d, lbl, source_implemented=True, test_verified=True,
                   runtime_observed=False, origin="cloud", source_ref=src))

    # Candidate mood loop: HYPOTHESIS ONLY. source_implemented=False -> level 'hypothesis'.
    g.add(Edge("affect_state", "chat_assembly",
               "mood/affect stances feed generation (stage_affect.*.stance_for, gui/server)",
               source_implemented=False, test_verified=False, runtime_observed=False,
               origin="cloud", source_ref="Phase-1 source read (gui/server.py imports)",
               note="HYPOTHESIS: candidate mood loop mood->generation->beliefs->expectations->"
                    "valence->mood. NOT verified; needs a live runtime trace (host)."))
    g.add(Edge("chat_assembly", "beliefs.confidence",
               "generated content can crystallise to beliefs (fountain)",
               source_implemented=False, test_verified=False, runtime_observed=False,
               origin="cloud", source_ref="Phase-1 source read",
               note="HYPOTHESIS edge for the candidate mood loop; unverified."))
    return g


def runtime_graph_evidence(g: RuntimeGraph) -> Evidence:
    cycles = g.find_cycles()
    return Evidence(
        "runtime_graph",
        {"nodes": sorted(g.nodes), "edge_count": len(g.edges), "feedback_cycles": cycles,
         "level_legend": "weakest->strongest: " + " < ".join(LEVELS)},
        "cloud", "implemented",
        "watcher.architecture.build_runtime_graph",
        interpretation="SEPARATE reconstruction (not the DAG or mind map). Each edge keeps "
                       "source_implemented / test_verified / runtime_observed distinct. The live "
                       "learning<->beliefs loop is test_verified (not yet runtime_observed, STANDBY); "
                       "mood-loop cycles are hypothesis.")


def collect(mind_map_path: str, dag_path: str) -> List[Evidence]:
    out: List[Evidence] = []
    try:
        out.append(read_mind_map(mind_map_path))
    except Exception as e:
        out.append(Evidence("mind_map", None, "cloud", "unknown", mind_map_path,
                            modifier="unverified", interpretation=f"unreadable: {e}"))
    try:
        out.append(read_dag(dag_path))
    except Exception as e:
        out.append(Evidence("sentience_dag", None, "cloud", "unknown", dag_path,
                            modifier="unverified", interpretation=f"unreadable: {e}"))
    out.append(runtime_graph_evidence(build_runtime_graph()))
    return out
