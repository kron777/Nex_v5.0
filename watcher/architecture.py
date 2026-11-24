"""Architecture readers + a SEPARATE static/design relationship graph.

Two readers parse the existing source artifacts READ-ONLY and never modify them:
  * `read_mind_map`  — mind_map/MIND_MAP.yaml (the mental-factor / property aspect map)
  * `read_dag`       — sentience_dag.json (the build-dependency DAG)

`RuntimeGraph` is a THIRD, independent static/design view of source-present
producer->consumer relationships. It is NOT a modification or replacement of the
build DAG or mind map, and it does not establish that a relationship is live.

Each edge carries THREE independent evidence dimensions, kept distinguishable
(founder constraint #5):
  * source_implemented — the relationship is present in inspected source
  * test_verified      — a cited test exercises/asserts the scoped relationship
  * runtime_observed   — the edge was seen firing in a live trace (host only)
An edge's `level` is the strongest dimension it has; a cycle's status is its
WEAKEST edge (a loop is only as established as its least-established link). These
flags are curated review assertions, not dynamically derived proofs. Each
source-backed edge carries a scoped claim, source reference, test reference when
verified, and caveat. Synthetic tests are not live traces. NEX is in STANDBY, so
nothing is `runtime_observed` yet — that stays an honest gap.
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
    test_ref: str = ""
    claim: str = ""
    scope: str = ""
    caveat: Optional[str] = None
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
    """A separate static/design view of source-present relationships. Never writes
    to the build DAG or mind map, and never implies live execution."""

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
    """Seed the static relationship graph from Phase-1 source reads. Edges carry
    independent evidence dimensions; nothing is `runtime_observed` in STANDBY."""
    g = RuntimeGraph()
    src = "Phase-1 source read (expectations.py, global_workspace, commitments.py, episodic.py)"
    # Per-edge records are curated source/test claims, not runtime observations.
    # References identify the implementation and synthetic test path; caveats narrow
    # claims where coverage is indirect, conditional, or family-specific.
    edge_records = [
        dict(src="producers", dst="expectations",
             label="owned-belief/surprise producer rows -> expectation headers",
             source_ref="theory_x/stage_world/expectations.py:105-115,221-260,345-368",
             test_ref="tests/test_expectations.py::test_surprise_empty_window_is_unresolved_never_violated; tests/test_expectations.py::test_one_live_cell_three_exact_zeros",
             claim="Producer rows are linked to expectation headers during ingestion/reconciliation.",
             scope="Owned-belief and surprise paths represented by the cited tests.",
             caveat="Self/world producer-family assertions are weaker or indirect; commitments are outside this narrowed label."),
        dict(src="expectations", dst="reconciler",
             label="ingest() ledger rows -> reconcile() dispatch",
             source_ref="theory_x/stage_world/expectations.py:221-260,345-380",
             test_ref="tests/test_expectations.py::test_one_live_cell_three_exact_zeros",
             claim="The reconciler ingests, selects due expectation rows, and dispatches them.",
             scope="Representative synthetic integration paths.",
             caveat="Does not claim exhaustive coverage of every dispatch branch."),
        dict(src="reconciler", dst="event_valence",
             label="resolved reconcile branches write event_valence",
             source_ref="theory_x/stage_world/expectations.py:345-431",
             test_ref="tests/test_expectations.py::test_one_live_cell_three_exact_zeros",
             claim="Resolved, valence-admissible branches can write linked event_valence rows.",
             scope="Representative resolved synthetic path.",
             caveat="Not every resolution writes a row; unresolved branches can skip insertion."),
        dict(src="reconciler", dst="affect_nudges",
             label="nonzero reconciled valence writes affect_nudges",
             source_ref="theory_x/stage_world/expectations.py:412-428",
             test_ref="tests/test_expectations.py::test_three_cells",
             claim="A nonzero reconciled valence can produce an affect_nudges row.",
             scope="Synthetic two-channel reconciliation path.",
             caveat="Test observes downstream mood_nudge indirectly rather than asserting the inserted row directly."),
        dict(src="reconciler", dst="expectation_learning_log",
             label="eligible, feature-gated reconcile calls _learn()",
             source_ref="theory_x/stage_world/expectations.py:429-430,520-573",
             test_ref="tests/test_expectations.py::test_external_basis_learning_on_authored_beliefs_is_attributed",
             claim="A qualifying reconciliation can call _learn(), which records learning-log rows.",
             scope="Conditional synthetic path with learning enabled and eligibility satisfied.",
             caveat="Integration assertion is indirect through a consumer result; helper-only tests are not edge proof."),
        dict(src="source_kind", dst="ownership",
             label="basis source_kind contributes to ownership share",
             source_ref="theory_x/stage_world/expectations.py:142-147,243-255",
             test_ref="tests/test_expectations.py::test_ownership_share",
             claim="Ownership is calculated from basis source_kind values and applied during ingestion.",
             scope="Function-boundary ownership calculation.",
             caveat="The cited test does not prove the full persisted-row-to-ingest pipeline."),
        dict(src="ownership", dst="valence_gate",
             label="ownership threshold gates valence admission",
             source_ref="theory_x/stage_world/expectations.py:173-189,412-422",
             test_ref="",
             claim="Valence admission rejects ownership below 0.5.",
             scope="Implementation exists; relationship-specific threshold test absent.",
             caveat="test_verified=false until a focused threshold test isolates ownership with other admission inputs fixed.",
             test_verified=False),
        dict(src="reconciler", dst="beliefs.confidence",
             label="eligible, feature-gated _learn() updates basis-belief confidence",
             source_ref="theory_x/stage_world/expectations.py:429-430,520-575",
             test_ref="tests/test_expectations.py::test_three_cells",
             claim="A qualifying reconciliation can update basis-belief confidence through _learn().",
             scope="Synthetic path with learning enabled and eligible basis beliefs.",
             caveat="Conditional on NEX5_EXPECT_LEARN and learning eligibility; not unconditional."),
        dict(src="beliefs.confidence", dst="producers",
             label="belief confidence -> owned-belief producer path",
             source_ref="theory_x/stage_world/owned_belief.py:119-141",
             test_ref="tests/test_owned_belief.py::test_row_is_open_owned_band_four_with_its_own_confidence",
             claim="The owned-belief producer copies originating belief confidence into the expectation/basis record.",
             scope="Owned-belief producer path only.",
             caveat="Internal-surprise confidence transfer is not asserted by the cited test and is not included in this edge."),
        dict(src="affect_nudges", dst="affect_state",
             label="affect_state consumes nudges behind mood and eligibility gates",
             source_ref="theory_x/stage_affect/affect_state.py:208-223; theory_x/stage_world/expectations.py:661-670",
             test_ref="tests/test_expectations.py::test_both_signs_open_the_gate; tests/test_expectations.py::test_one_sided_organic_valence_keeps_mood_at_zero",
             claim="The affect-state consumer applies stored nudges only when its gates pass.",
             scope="Synthetic consumer-side coupling tests.",
             caveat="These tests verify the table-to-state consumer edge, not the upstream reconciler writer."),
        dict(src="held_tensions", dst="episodic",
             label="opt-in episodic reader records held-tension episodes",
             source_ref="theory_x/memory/episodic.py:142-165,180-205; schema/dynamic.sql:182-193",
             test_ref="tests/test_episodic.py::test_held_tension_recorded_with_belief_content; tests/test_episodic.py::test_held_tension_episode_reads_as_event_not_as_a_belief",
             claim="The callable episodic reader can retrieve held tensions and record episodes.",
             scope="Explicitly invoked synthetic callable path.",
             caveat="No automatic live-loop invocation is established; opt-in behavior only."),
        dict(src="global_workspace", dst="chat_assembly",
             label="flagged chat assembly calls workspace selector",
             source_ref="gui/server.py:239-264; theory_x/stage_tom/global_workspace.py:144-168",
             test_ref="tests/test_chat_arbiter.py::test_on_trims_low_salience_keeps_exempt",
             claim="Chat assembly invokes the workspace selector when its feature flag is enabled.",
             scope="Conditional synthetic assembly integration test.",
             caveat="Selector-only tests do not establish assembly wiring; NEX5_CHAT_WORKSPACE=1 is required."),
    ]
    for record in edge_records:
        verified = record.pop("test_verified", True)
        g.add(Edge(record.pop("src"), record.pop("dst"), record.pop("label"),
                   source_implemented=True, test_verified=verified,
                   runtime_observed=False, origin="cloud", **record))

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
    graph_data = g.to_dict()
    return Evidence(
        "runtime_graph",
        {"nodes": sorted(g.nodes), "edge_count": len(g.edges), "edges": graph_data["edges"],
         "feedback_cycles": cycles,
         "level_legend": "weakest->strongest: " + " < ".join(LEVELS)},
        "cloud", "implemented",
        "watcher.architecture.build_runtime_graph",
        interpretation="SEPARATE static/design reconstruction (not the DAG or mind map). Per-edge "
                       "claims, scope, source refs, test refs, and caveats are curated. Synthetic "
                       "test evidence is not live observation; runtime_observed remains false in "
                       "STANDBY. Candidate mood-loop cycles remain hypotheses.")


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
