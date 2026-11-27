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


# --------------------------- before/after neighbour impact review -------------------

def test_neighbour_impact_delta_reviews_adjacent_edges_without_claiming_causality():
    before = [
        {"src": "capability-A", "dst": "service-B", "kind": "influences",
         "authority": "bounded", "note": "old"},
        {"src": "service-C", "dst": "capability-A", "kind": "depends_on"},
        {"src": "unrelated-X", "dst": "unrelated-Y", "kind": "depends_on",
         "note": "before"},
    ]
    after = [
        {"src": "capability-A", "dst": "service-B", "kind": "influences",
         "authority": "strong", "note": "old"},
        {"src": "service-C", "dst": "capability-A", "kind": "depends_on"},
        {"src": "capability-A", "dst": "service-D", "kind": "produces_for"},
        {"src": "unrelated-X", "dst": "unrelated-Y", "kind": "depends_on",
         "note": "after"},
    ]
    result = graph.relationship_impact_delta(before, after, ["capability-A"])
    assert result["status"] == "reviewed"
    assert result["summary"] == {
        "adjacent_relationships_reviewed": 3,
        "adjacent_relationships_changed": 2,
        "unrelated_changes": 1,
    }
    assert {tuple(item["identity"]) for item in result["changed_adjacent_relationships"]} == {
        ("capability-A", "service-B", "influences"),
        ("capability-A", "service-D", "produces_for"),
    }
    assert "not_established" in result["causal_attribution"]


def test_neighbour_impact_delta_includes_assessment_changes_on_unchanged_edges():
    edge = {"src": "changed", "dst": "neighbour", "kind": "influences",
            "authority": "bounded"}
    subject = "changed -influences-> neighbour"
    before = [{"level": "relationship", "subject": subject, "verdict": "unknown"}]
    after = [{"level": "relationship", "subject": subject, "verdict": "overdeveloped"}]
    result = graph.relationship_impact_delta(
        [edge], [dict(edge)], ["changed"], before_assessments=before,
        after_assessments=after,
    )
    item = result["reviewed_adjacent_relationships"][0]
    assert item["change"] == "unchanged"
    assert item["assessment_changed"] is True
    assert item["assessment_before"]["verdict"] == "unknown"
    assert item["assessment_after"]["verdict"] == "overdeveloped"


def test_neighbour_impact_delta_fails_closed_on_duplicate_relationship_identity():
    edges = [
        {"src": "A", "dst": "B", "kind": "depends_on"},
        {"src": "A", "dst": "B", "kind": "depends_on", "note": "duplicate"},
    ]
    with pytest.raises(ValueError, match="duplicate identity"):
        graph.relationship_impact_delta(edges, [], ["A"])


def test_neighbour_impact_delta_requires_explicit_changed_node_keys():
    with pytest.raises(ValueError, match="changed_nodes"):
        graph.relationship_impact_delta([], [], "capability-A")


def test_neighbour_impact_delta_detects_added_or_removed_assessment():
    edge = {"src": "changed", "dst": "neighbour", "kind": "depends_on"}
    subject = "changed -depends_on-> neighbour"
    assessment = [{"level": "relationship", "subject": subject, "verdict": "unknown"}]
    appeared = graph.relationship_impact_delta(
        [edge], [dict(edge)], ["changed"], after_assessments=assessment,
    )
    disappeared = graph.relationship_impact_delta(
        [edge], [dict(edge)], ["changed"], before_assessments=assessment,
    )
    assert appeared["changed_adjacent_relationships"][0]["assessment_changed"] is True
    assert disappeared["changed_adjacent_relationships"][0]["assessment_changed"] is True


def test_neighbour_impact_delta_detects_missing_vs_null_relationship_fields():
    before = [{"src": "changed", "dst": "neighbour", "kind": "depends_on", "note": None}]
    after = [{"src": "changed", "dst": "neighbour", "kind": "depends_on"}]
    result = graph.relationship_impact_delta(before, after, ["changed"])
    assert result["changed_adjacent_relationships"][0]["changed_fields"] == ["note"]


def test_neighbour_impact_delta_rejects_duplicate_assessment_subjects():
    edge = {"src": "changed", "dst": "neighbour", "kind": "depends_on"}
    subject = "changed -depends_on-> neighbour"
    assessments = [
        {"level": "relationship", "subject": subject, "verdict": "unknown"},
        {"level": "relationship", "subject": subject, "verdict": "sufficient"},
    ]
    with pytest.raises(ValueError, match="duplicate subject"):
        graph.relationship_impact_delta(
            [edge], [edge], ["changed"], before_assessments=assessments,
        )
