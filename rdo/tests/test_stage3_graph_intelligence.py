"""Stage 3 (RDO v1.3 §16) — Graph Intelligence.

Reuses the Stage-2 belief-development objective + its persisted artefact as the regression
baseline, and a deliberately-constructed cyclic component as a fixture. Covers SCC decomposition,
semantic duplicate candidates (surfaced, never merged), typed relationships, completeness, and a
prerequisite-derived implementation sequence — plus property tests and an end-to-end run.
"""
import json
import subprocess
import sys

import pytest

from rdo import graph
from rdo.knowledge import belief_decay_idea
from rdo.memory import CycleStore
from rdo.orchestrator import run_cycle


@pytest.fixture(scope="module")
def cyc():
    objective, assumptions, seeds, signatures = belief_decay_idea()
    c, _ = run_cycle("belief_decay_mvp", objective, assumptions, seeds, signatures, repo_dir=".")
    return c


# a deliberately-constructed cyclic component: A<->B<->C (prerequisite cycle), external
# prerequisite `ext`, downstream dependent `down`, and an independent parallel node `par`.
def _ob(k, kind="consumer", **kw):
    base = {"key": k, "kind": kind, "classification": "necessary", "recon_status": "unknown",
            "title": k, "rationale": "", "parent_key": None, "provenance": "seed",
            "recon_evidence": [], "depth": 0}
    base.update(kw)
    return base


FIX_OBS = [_ob(k) for k in ("ext", "A", "B", "C", "down", "par")]
FIX_RELS = [
    {"src": "A", "dst": "B", "kind": "depends_on"},
    {"src": "B", "dst": "C", "kind": "depends_on"},
    {"src": "C", "dst": "A", "kind": "depends_on"},     # the cycle
    {"src": "A", "dst": "ext", "kind": "depends_on"},    # ext is a prerequisite of the component
    {"src": "down", "dst": "B", "kind": "depends_on"},   # down depends on the component
]


# ------------------------------- SCC decomposition ---------------------------------

def test_scc_decomposes_cyclic_component():
    d = graph.scc_decomposition(FIX_OBS, FIX_RELS)
    assert d["has_cyclic_components"]
    comps = d["nontrivial_components"]
    assert len(comps) == 1
    comp = comps[0]
    assert comp["members"] == ["A", "B", "C"] and comp["size"] == 3
    assert comp["classification"] == "prerequisite_cycle"       # all depends_on -> must be broken
    assert comp["internal_cycles"]                              # the individual cycle is reported
    # external prerequisites and downstream dependents are correctly directed
    assert comp["external_prerequisites"] == ["ext"]
    assert comp["downstream_dependents"] == ["down"]


def test_scc_distinguishes_individual_cycle_from_component():
    # two separate 2-cycles must be two components, not one
    obs = [_ob(k) for k in ("A", "B", "C", "D")]
    rels = [{"src": "A", "dst": "B", "kind": "depends_on"}, {"src": "B", "dst": "A", "kind": "depends_on"},
            {"src": "C", "dst": "D", "kind": "depends_on"}, {"src": "D", "dst": "C", "kind": "depends_on"}]
    comps = graph.scc_decomposition(obs, rels)["nontrivial_components"]
    assert sorted(c["members"] for c in comps) == [["A", "B"], ["C", "D"]]


def test_feedback_loop_classified_but_not_removed():
    # a cycle through an influences edge is a feedback loop (may be essential), not auto-removed
    obs = [_ob("A"), _ob("B")]
    rels = [{"src": "A", "dst": "B", "kind": "depends_on"}, {"src": "B", "dst": "A", "kind": "influences"}]
    comp = graph.scc_decomposition(obs, rels)["nontrivial_components"][0]
    assert comp["classification"] == "feedback_loop"
    # decomposition never deletes edges/nodes — the members and internal edges survive
    assert set(comp["members"]) == {"A", "B"} and len(comp["internal_edges"]) == 2


def test_real_belief_graph_is_acyclic_and_convergence_preserved(cyc):
    d = graph.scc_decomposition(cyc.obligations, cyc.relationships)
    assert not d["has_cyclic_components"]
    # the genuine shared runtime-verification prerequisite is ONE node reached by both consumers
    from collections import Counter
    indeg = Counter(r["dst"] for r in cyc.relationships if r["kind"] == "depends_on")
    assert indeg["shared_runtime_effect.runtime_verification"] == 2


# ------------------------------- deduplication -------------------------------------

def test_semantic_duplicates_surfaced_not_merged(cyc):
    before = [dict(o) for o in cyc.obligations]
    cands = graph.dedup_candidates(cyc.obligations)
    # the two consumers' parallel children are surfaced as uncertain candidates
    assert cands and all(c["status"] in ("confirmed_equivalent", "uncertain_similar") for c in cands)
    pair = next(c for c in cands if c["a"]["key"].endswith(".read_path"))
    assert pair["status"] == "uncertain_similar"
    # provenance + parent are retained on both sides, for a reviewer to act
    assert pair["a"]["provenance"] and pair["b"]["provenance"]
    assert "parent" in pair["a"] and "parent" in pair["b"]
    # NEVER merged: the obligation set is unchanged by analysis
    assert cyc.obligations == before


def test_confirmed_vs_uncertain_distinguished():
    # two obligations reconciled to the SAME mechanism are confirmed; same-kind only is uncertain
    obs = [
        _ob("x.read_path", kind="read_path", recon_evidence=["[m] substrate/init_db.py:1 FOO"]),
        _ob("y.read_path", kind="read_path", recon_evidence=["[m] substrate/init_db.py:1 FOO"]),
        _ob("z.test", kind="test", title="test for a", recon_evidence=[]),
        _ob("w.test", kind="test", title="test for b", recon_evidence=[]),
    ]
    cands = graph.dedup_candidates(obs)
    by = {frozenset((c["a"]["key"], c["b"]["key"])): c["status"] for c in cands}
    assert by[frozenset(("x.read_path", "y.read_path"))] == "confirmed_equivalent"
    assert by[frozenset(("w.test", "z.test"))] == "uncertain_similar"


# ------------------------------- typed relationships -------------------------------

def test_typed_relationships_beyond_depends_on(cyc):
    res = graph.analyse(cyc.obligations, cyc.relationships, cyc.frontier)
    te = res["typed_edges"]
    assert te["depends_on"] > 0 and te["produces_for"] == 4 and te["duplicates(candidate)"] > 0
    pf = res["derived_relationships"]["produces_for"]
    # producers (policy/daemon) supply the consumers — direction producer -> consumer
    srcs = {e["src"] for e in pf}
    dsts = {e["dst"] for e in pf}
    assert srcs == {"belief_decay_policy", "belief_decay_daemon"}
    assert dsts == {"belief_decay_consumer_safety", "belief_decay_consumer_generation"}


# ------------------------------- completeness --------------------------------------

def test_completeness_measured_against_objective(cyc):
    comp = graph.completeness(cyc.obligations, cyc.frontier)
    assert comp["discovered"] == len(cyc.obligations)
    # it reports unresolved/accounted, not a target count
    assert comp["unresolved_count"] == sum(1 for o in cyc.obligations if o["recon_status"] == "unknown")
    assert comp["accounted"]["reuse"] == len(cyc.reused)
    # unresolved obligations exist here, so the graph is honestly NOT complete against the objective
    assert comp["complete_against_objective"] is False
    assert comp["evidence_gaps"]["reuse_claims_without_evidence"] == []   # every reuse is backed


# ------------------------------- implementation sequence ---------------------------

def test_sequence_respects_prerequisites_and_parallelism():
    seq = graph.implementation_sequence(FIX_OBS, FIX_RELS)
    # ext (no prereqs) first; the cyclic component as ONE unit; down (depends on component) after
    flat = [u["unit"] for lvl in seq["levels"] for u in lvl]
    assert ["A", "B", "C"] in [u if isinstance(u, list) else [u] for u in flat]
    # the cyclic component is represented as a unit, never linearised internally
    assert seq["cyclic_components"] == [["A", "B", "C"]]
    # ext precedes the component; down follows it (hard prerequisites respected)
    levels = [[u["unit"] for u in lvl] for lvl in seq["levels"]]
    ext_lvl = next(i for i, l in enumerate(levels) if "ext" in l)
    comp_lvl = next(i for i, l in enumerate(levels) if ["A", "B", "C"] in l)
    down_lvl = next(i for i, l in enumerate(levels) if "down" in l)
    assert ext_lvl < comp_lvl < down_lvl
    # `par` is independent and may proceed in parallel at the first level
    assert "par" in levels[0]


def test_sequence_is_not_priority_ranking():
    # the sequence is explicitly prerequisite order, NOT a priority ranking: it carries no
    # priority score, and the note states the distinction.
    seq = graph.implementation_sequence(FIX_OBS, FIX_RELS)
    assert "depends_on prerequisites" in seq["note"] and "NOT a priority" in seq["note"]
    assert "_provisional_sort_score_uncalibrated" not in json.dumps(seq)   # no priority score leaks in


# ------------------------------- property tests ------------------------------------

def test_property_scc_partitions_all_nodes(cyc):
    keys = [o["key"] for o in cyc.obligations]
    adj = graph._adjacency(cyc.relationships, graph.DEP_KINDS)
    for k in keys:
        adj.setdefault(k, [])
    sccs = graph.tarjan_sccs(keys, adj)
    flat = [n for comp in sccs for n in comp]
    assert sorted(flat) == sorted(keys)          # every node in exactly one SCC
    assert len(flat) == len(set(flat))


def test_property_same_scc_iff_mutually_reachable():
    # build a graph and check Tarjan agrees with reachability
    obs = [_ob(k) for k in ("A", "B", "C", "D", "E")]
    rels = [{"src": "A", "dst": "B", "kind": "depends_on"}, {"src": "B", "dst": "C", "kind": "depends_on"},
            {"src": "C", "dst": "A", "kind": "depends_on"}, {"src": "C", "dst": "D", "kind": "depends_on"},
            {"src": "D", "dst": "E", "kind": "depends_on"}]
    keys = [o["key"] for o in obs]
    adj = graph._adjacency(rels, graph.DEP_KINDS)
    for k in keys:
        adj.setdefault(k, [])
    scc_of = {}
    for i, comp in enumerate(graph.tarjan_sccs(keys, adj)):
        for n in comp:
            scc_of[n] = i

    def reach(a, b):
        seen, stack = set(), [a]
        while stack:
            x = stack.pop()
            if x == b and x != a or (x == b and a == b):
                return True
            for y in adj.get(x, []):
                if y not in seen:
                    seen.add(y); stack.append(y)
        return b in seen or a == b

    for a in keys:
        for b in keys:
            mutual = reach(a, b) and reach(b, a)
            assert (scc_of[a] == scc_of[b]) == mutual or a == b


def test_property_sequence_respects_every_prerequisite(cyc):
    seq = graph.implementation_sequence(cyc.obligations, cyc.relationships)
    level_of = {}
    for i, lvl in enumerate(seq["levels"]):
        for u in lvl:
            for m in u["members"]:
                level_of[m] = i
    # for every depends_on edge src->dst, dst (the prerequisite) is at an earlier-or-equal level
    for r in cyc.relationships:
        if r["kind"] == "depends_on" and r["src"] in level_of and r["dst"] in level_of:
            assert level_of[r["dst"]] <= level_of[r["src"]]


# ------------------------------- end-to-end + resume -------------------------------

def test_stage3_end_to_end_and_resume(tmp_path):
    from rdo.report import run_stage3_graph_intelligence
    d = str(tmp_path / "s3")
    res = run_stage3_graph_intelligence(repo_dir=".", workdir=d)
    assert res["convergence_preserved"] is True
    assert res["duplicate_candidates"] > 0 and res["scc_nontrivial_components"] == 0
    assert set(res["typed_edges"]) >= {"depends_on", "produces_for", "duplicates(candidate)"}
    assert res["completeness"]["complete_against_objective"] is False
    # durable analysis persisted; canonical identity + analysis recompute identically in a fresh process
    code = ("import json; from rdo.memory import CycleStore; from rdo.graph import analyse; "
            f"c=CycleStore({d!r}).load('belief_decay_mvp'); "
            "a=analyse(c.obligations,c.relationships,c.frontier); "
            "print(json.dumps({'dups':len(a['duplicate_candidates']),'te':a['typed_edges']}))")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["dups"] == res["duplicate_candidates"]
    assert out["te"]["produces_for"] == 4


def test_failure_propagation_candidates_trace_direct_and_transitive_dependents():
    affected = graph.failure_propagation_candidates(
        FIX_OBS, FIX_RELS, ["ext"],
    )
    assert affected["status"] == "candidate_only"
    assert affected["unknown_roots"] == []
    by_key = {item["key"]: item for item in affected["affected"]}
    assert by_key["A"]["direct"] is True
    assert by_key["A"]["path"] == ["ext", "A"]
    assert by_key["A"]["relationships"] == ["A:depends_on:ext"]
    assert by_key["C"]["path"] == ["ext", "A", "C"]
    assert by_key["B"]["path"] == ["ext", "A", "C", "B"]
    assert by_key["down"]["path"] == ["ext", "A", "C", "B", "down"]
    assert by_key["down"]["distance"] == 4
    assert by_key["down"]["relationships"] == [
        "A:depends_on:ext", "C:depends_on:A",
        "B:depends_on:C", "down:depends_on:B",
    ]
    assert affected["cycle_encountered"] is True
    assert "runtime" in affected["note"]


def test_failure_propagation_candidates_exclude_influence_feedback_edges():
    obligations = [_ob("source"), _ob("consumer")]
    rels = [{"src": "consumer", "dst": "source", "kind": "influences"}]
    result = graph.failure_propagation_candidates(obligations, rels, ["source"])
    assert result["status"] == "no_known_dependents"
    assert result["affected"] == []
    assert result["cycle_encountered"] is False


def test_failure_propagation_candidates_mark_unknown_roots_and_unresolved_edges():
    obligations = [_ob("known")]
    rels = [{"src": "missing_consumer", "dst": "known", "kind": "depends_on"}]
    result = graph.failure_propagation_candidates(
        obligations, rels, ["unknown_root", "known"],
    )
    assert result["status"] == "partial"
    assert result["unknown_roots"] == ["unknown_root"]
    assert result["unresolved_dependency_edges"] == 1
    assert result["affected"] == []


def test_failure_propagation_candidates_use_deterministic_shortest_paths():
    obligations = [_ob(key) for key in ("root", "a", "b", "join")]
    rels = [
        {"src": "a", "dst": "root", "kind": "depends_on"},
        {"src": "b", "dst": "root", "kind": "depends_on"},
        {"src": "join", "dst": "a", "kind": "depends_on"},
        {"src": "join", "dst": "b", "kind": "depends_on"},
    ]
    result = graph.failure_propagation_candidates(obligations, rels, ["root"])
    join = next(item for item in result["affected"] if item["key"] == "join")
    assert join["distance"] == 2
    assert join["path"] == ["root", "a", "join"]
    assert result["cycle_encountered"] is False


def test_failure_propagation_candidates_reject_malformed_inputs_without_throwing():
    result = graph.failure_propagation_candidates(None, [], ["root"])
    assert result["status"] == "invalid_input"
    assert result["affected"] == []


def test_failure_propagation_candidates_preserve_unknown_edge_and_obligation_shapes():
    obligations = [_ob("known"), {"title": "missing canonical key"}]
    rels = [
        {"src": "known", "dst": "known", "kind": "unrecognised_edge"},
        {"src": "known", "dst": "known"},
    ]
    result = graph.failure_propagation_candidates(obligations, rels, ["known"])
    assert result["status"] == "partial"
    assert result["invalid_obligations"] == 1
    assert result["unresolved_dependency_edges"] == 2
    assert result["affected"] == []


def test_failure_propagation_candidates_distinguish_no_failure_input_from_no_dependents():
    result = graph.failure_propagation_candidates(FIX_OBS, FIX_RELS, [])
    assert result["status"] == "not_supplied"
    assert result["roots"] == []
    assert result["affected"] == []



def test_failure_propagation_detects_cycles_across_bfs_branches():
    obligations = [_ob(key) for key in ("root", "b", "c", "d")]
    rels = [
        {"src": "b", "dst": "root", "kind": "depends_on"},
        {"src": "c", "dst": "root", "kind": "depends_on"},
        {"src": "d", "dst": "b", "kind": "depends_on"},
        {"src": "b", "dst": "c", "kind": "depends_on"},
        {"src": "c", "dst": "d", "kind": "depends_on"},
    ]

    result = graph.failure_propagation_candidates(obligations, rels, ["root"])

    assert result["status"] == "candidate_only"
    assert {item["key"] for item in result["affected"]} == {"b", "c", "d"}
    assert result["cycle_encountered"] is True
