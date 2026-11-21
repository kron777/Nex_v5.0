"""Stage 2 (RDO v1.3 §16) — Extrapolator MVP vertical slice.

A real belief-DEVELOPMENT objective (staleness-based confidence decay) is run end to
end through the EXISTING extrapolator, reconciler and CycleStore — no duplicate
persistence/graph/reconciliation mechanism is introduced. This is NOT the Stage-4
belief audit: existing belief mechanisms are only inspected read-only to ground the
reconciliation signatures.

Each test maps to a documented Extrapolator capability or RDO acceptance rule:
  accept/structure objective · recursive obligation discovery · parent/rationale/
  class/confidence/impact/evidence per obligation · bounded repository reconciliation ·
  existing-mechanism + duplication identification · traceable acyclic dependency graph ·
  stable canonical IDs · no silent merge of duplicates · no verification without
  acceptance evidence · hard prerequisites not bypassed · unresolved/deferred branches
  survive persistence · persist + resume in a new process.
"""
import json
import os
import subprocess
import sys

import pytest

from rdo.knowledge import belief_decay_idea
from rdo.memory import CycleStore
from rdo.orchestrator import run_cycle

CID = "belief_decay_mvp"

# A DETERMINISTIC TEST-FIXTURE review — a test construct, NOT an authorised production reviewer.
# It exercises the calibration pipeline in isolated temp stores; it never represents a genuine
# reviewed outcome, and the default runner path writes no pattern at all.
FIXTURE_REVIEW = {
    "reviewer": "test-fixture (deterministic; not an authorised reviewer)",
    "missed": ["belief_decay_rollback"],
    "notes": "deterministic fixture planning review, for pipeline testing only",
}


@pytest.fixture(scope="module")
def sl(tmp_path_factory):
    objective, assumptions, seeds, signatures = belief_decay_idea()
    cycle, summary = run_cycle(CID, objective, assumptions, seeds, signatures, repo_dir=".")
    d = str(tmp_path_factory.mktemp("cycles"))
    CycleStore(d).save(cycle)
    return {"objective": objective, "seeds": seeds, "cycle": cycle,
            "summary": summary, "dir": d, "store": CycleStore(d)}


def test_accepts_and_structures_objective(sl):
    c = sl["cycle"]
    assert c.id == CID and c.objective == sl["objective"]
    assert c.assumptions, "a structured objective carries its assumptions"


def test_recursively_discovers_obligations(sl):
    c = sl["cycle"]
    assert len(c.obligations) > len(sl["seeds"]), "expansion must discover more than the seeds"
    assert max(o["depth"] for o in c.obligations) >= 1, "children must be discovered below the seeds"


def test_records_each_obligation_attribute(sl):
    c = sl["cycle"]
    obls = {o["key"]: o for o in c.obligations}
    for o in c.obligations:
        # parent, rationale, class, confidence, impact, evidence-need are all present
        for field in ("classification", "confidence", "impact", "recon_status", "rationale"):
            assert field in o
        if o["depth"] > 0:
            assert o["parent_key"] in obls, "a child must trace to a real parent"
            assert o["rationale"], "expansion rationale must be recorded"
    # impact is recorded on every authored seed
    for s in sl["seeds"]:
        assert obls[s.key]["impact"], f"impact missing on seed {s.key}"


def test_reconciles_against_repository_evidence(sl):
    c = sl["cycle"]
    # REUSE: the real belief_activation recency table is found, with file evidence
    assert "belief_staleness_input" in c.reused
    ev = {o["key"]: o["recon_evidence"] for o in c.obligations}
    assert any("belief_activation" in e for e in ev["belief_staleness_input"])
    # MISSING: the decay policy and applier are genuinely absent (net-new work)
    assert "belief_decay_policy" in c.missing
    assert "belief_decay_daemon" in c.missing


def test_identifies_duplication_as_anti_requirements(sl):
    c = sl["cycle"]
    assert "anti_second_confidence_store" in c.anti_requirements
    assert "anti_delete_stale_beliefs" in c.anti_requirements


def test_no_verification_without_acceptance_evidence(sl):
    # every reuse claim must be backed by real file evidence
    c = sl["cycle"]
    assert c.verification["all_reuse_backed"] is True
    assert c.verification["unbacked_reuse_claims"] == []


def test_stable_canonical_ids_and_no_silent_merge(sl):
    c = sl["cycle"]
    keys = [o["key"] for o in c.obligations]
    assert len(keys) == len(set(keys)), "distinct obligations must not be merged under one key"
    for o in c.obligations:
        assert o["id"] == o["key"], "id mirrors the stable canonical key"


def test_traceable_acyclic_dependency_graph(sl):
    c = sl["cycle"]
    obls = {o["key"]: o for o in c.obligations}

    # every obligation traces up to a seed root via parent_key, with no node its own ancestor
    def trace_to_root(key, seen):
        assert key not in seen, f"cycle in parent chain at {key}"
        parent = obls[key]["parent_key"]
        return key if parent is None else trace_to_root(parent, seen | {key})

    roots = {trace_to_root(k, set()) for k in obls}
    seed_keys = {s.key for s in sl["seeds"]}
    assert roots <= seed_keys, "every obligation must trace to an authored seed"

    # depends_on edges run parent(shallower) -> child(deeper): a DAG, never a self-loop
    for r in c.relationships:
        if r["kind"] == "depends_on" and r["src"] in obls and r["dst"] in obls:
            assert r["src"] != r["dst"]
            assert obls[r["dst"]]["depth"] >= obls[r["src"]]["depth"]


def test_dependency_cycles_are_detected(sl):
    """'cycles must be detected' is an ACTIVE capability (tension._find_cycles, wired into
    assess_system and run every cycle), not merely by-construction absence. The belief-decay
    slice is acyclic; a deliberate cycle must be flagged."""
    from rdo import tension
    from rdo.model import Obligation, Relationship
    # (a) the real slice surfaces no feedback-cycle system tension
    c = sl["cycle"]
    assert [t for t in c.tension if t.get("subject") == "feedback_cycles"] == []
    # (b) a deliberate A->B->C->A dependency cycle IS detected and surfaced
    obls = {k: Obligation(k, k, "consumer") for k in ("A", "B", "C")}
    rels = [Relationship("A", "B", "depends_on"), Relationship("B", "C", "depends_on"),
            Relationship("C", "A", "depends_on")]
    assert tension._find_cycles(rels) == [["A", "B", "C", "A"]]
    sys_t = [t.to_dict() for t in tension.assess_system(obls, rels)]
    assert any(t["subject"] == "feedback_cycles" for t in sys_t)


def test_hard_prerequisites_not_bypassed(sl):
    # the eligibility gate blocks work with unmet prerequisites, and names them
    c = sl["cycle"]
    blocked = [p for p in c.work_packages if p["eligibility"] == "blocked"]
    assert blocked, "the runtime-verification / consumer-safety work should be gated"
    assert all(p["blockers"] for p in blocked), "a blocked package must name its blockers"


def test_unresolved_branches_survive_persistence(sl):
    # obligations with no reconciliation signature are honest UNKNOWNs (deferred branches);
    # they must survive a save + reload unchanged.
    c, store = sl["cycle"], sl["store"]
    unresolved = sorted(o["key"] for o in c.obligations if o["recon_status"] == "unknown")
    assert unresolved, "the slice should carry unresolved/deferred branches"
    reloaded = store.load(CID)
    reloaded_unresolved = sorted(o["key"] for o in reloaded.obligations
                                 if o["recon_status"] == "unknown")
    assert reloaded_unresolved == unresolved


def test_persist_and_resume_identity(sl):
    reloaded = sl["store"].load(CID)
    assert reloaded.to_dict() == sl["cycle"].to_dict(), "reload must be byte-for-byte identical"


def test_resume_in_a_new_process(sl):
    # the strongest restart evidence: reload the persisted cycle in a FRESH interpreter
    code = (
        "import json; from rdo.memory import CycleStore; "
        f"c = CycleStore({sl['dir']!r}).load({CID!r}); "
        "print(json.dumps({'id': c.id, 'n': len(c.obligations), "
        "'reused': c.reused, 'missing': c.missing}))"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                       cwd=os.getcwd())
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["id"] == CID
    assert out["n"] == len(sl["cycle"].obligations)
    assert out["reused"] == sl["cycle"].reused
    assert out["missing"] == sl["cycle"].missing


# ----------------------- §15 acceptance-gap regression tests ------------------------

def test_convergence_shared_prerequisite(sl):
    """#1 A genuine shared prerequisite appears in the REAL expansion output: the two
    consumers of the decayed-confidence signal converge on ONE runtime-verification node
    (in-degree > 1), via the existing `_merge` mechanism — not a hand-built graph."""
    c = sl["cycle"]
    from collections import Counter
    indeg = Counter(r["dst"] for r in c.relationships if r["kind"] == "depends_on")
    converging = {k: v for k, v in indeg.items() if v > 1}
    assert converging, "the slice must contain at least one converging prerequisite"
    node = "shared_runtime_effect.runtime_verification"
    assert indeg[node] >= 2
    parents = sorted(r["src"] for r in c.relationships
                     if r["kind"] == "depends_on" and r["dst"] == node)
    assert parents == ["belief_decay_consumer_generation", "belief_decay_consumer_safety"]


def test_complete_counts_persisted_and_consistent(sl):
    """#4 All six counts are reported, internally consistent, and survive persistence."""
    c = sl["cycle"]
    for k in ("discovered", "unique", "reuse", "net_new", "deferred", "unresolved"):
        assert k in c.counts
    # unique == discovered proves no silent key collision (stable canonical IDs)
    assert c.counts["unique"] == c.counts["discovered"] == len(c.obligations)
    # category counts are bounded by discovery and match the lists they summarise
    assert c.counts["reuse"] == len(c.reused)
    assert c.counts["net_new"] == len(c.missing)
    assert c.counts["unresolved"] == sum(1 for o in c.obligations if o["recon_status"] == "unknown")
    # #2 deferred is GENUINELY-deferred only (budget / no-rule) — never the whole frontier, and
    # anti-requirement / already-satisfied stops are NOT double-counted here (they live under
    # anti_requirements / reuse respectively).
    from rdo.extrapolator import frontier_breakdown
    fb = frontier_breakdown(c.frontier)
    assert c.counts["deferred"] == fb["deferred"]
    assert c.counts["frontier_total"] == len(c.frontier)
    assert (fb["deferred"] + fb["anti_requirement"] + fb["already_satisfied"] + fb["other"]
            == len(c.frontier))
    # for this slice nothing hits the budget: the frontier is intentional stops only
    assert c.counts["deferred"] == 0
    assert c.counts["frontier_already_satisfied"] >= 1 and c.counts["frontier_anti_requirement"] >= 1
    assert sl["store"].load(CID).counts == c.counts


def test_frontier_preserved_under_expansion_budget(tmp_path):
    """#3 A tight expansion budget defers obligations WITH their reasons, through the public
    run_cycle pipeline, and they survive persistence + resume."""
    from rdo.orchestrator import run_cycle
    objective, assumptions, seeds, signatures = belief_decay_idea()
    c, _ = run_cycle("bd_budget", objective, assumptions, seeds, signatures,
                     repo_dir=".", max_depth=1)
    budget_items = [f for f in c.frontier if "max_depth" in f["reason"]]
    assert budget_items, "a max_depth budget must leave deferred items on the frontier"
    d = str(tmp_path / "cyc"); CycleStore(d).save(c)
    reloaded = CycleStore(d).load("bd_budget")
    assert reloaded.frontier == c.frontier               # reasons preserved across persistence
    assert any("max_depth" in f["reason"] for f in reloaded.frontier)


def test_work_packages_priority_ordered_not_alphabetical(sl):
    """#5 Inter-package order is meaningful: eligible (buildable) first, then priority desc,
    then canonical key — deterministic, and NOT merely alphabetical."""
    c = sl["cycle"]
    wps = c.work_packages

    def score(p):
        return max((d["_provisional_sort_score_uncalibrated"]
                    for d in p["priority_dimensions"].values()), default=0.0)

    keys = [(0 if p["eligibility"] == "eligible" else 1, -score(p), p["key"]) for p in wps]
    assert keys == sorted(keys), "packages must be ordered eligible-first, priority desc, key"
    # eligible come before blocked (hard prerequisites respected)
    elig_idx = [i for i, p in enumerate(wps) if p["eligibility"] == "eligible"]
    blk_idx = [i for i, p in enumerate(wps) if p["eligibility"] == "blocked"]
    assert (not elig_idx or not blk_idx) or max(elig_idx) < min(blk_idx)
    # not the old alphabetical order
    assert [p["key"] for p in wps] != sorted(p["key"] for p in wps)


def test_cycle_detection_and_classification(sl):
    """#6 Cycles are detected, CLASSIFIED by edge evidence, and reported — UNKNOWN retained
    where evidence is insufficient to call a loop essential/problematic."""
    from rdo import tension
    from rdo.model import Obligation, Relationship
    # the real slice is acyclic
    assert [t for t in sl["cycle"].tension if t.get("subject") == "feedback_cycles"] == []
    obls = {k: Obligation(k, k, "consumer") for k in ("A", "B")}
    # a pure depends_on cycle -> prerequisite_cycle (unsatisfiable build order) -> underdeveloped
    dep = [Relationship("A", "B", "depends_on"), Relationship("B", "A", "depends_on")]
    td = [t.to_dict() for t in tension.assess_system(obls, dep) if t.subject == "feedback_cycles"][0]
    assert td["verdict"] == "underdeveloped"
    assert td["dimensions"]["classified_cycles"][0]["classification"] == "prerequisite_cycle"
    # a cycle through an influences edge -> feedback_loop, verdict stays UNKNOWN (not forced)
    fl = [Relationship("A", "B", "depends_on"), Relationship("B", "A", "influences")]
    tf = [t.to_dict() for t in tension.assess_system(obls, fl) if t.subject == "feedback_cycles"][0]
    assert tf["verdict"] == "unknown"
    assert tf["dimensions"]["classified_cycles"][0]["classification"] == "feedback_loop"


def test_planning_review_and_calibration_are_durable(tmp_path):
    """#2 Prediction -> reviewed PLANNING outcome -> calibration is exercised and persisted,
    and a reviewed plan is never recorded as a completed implementation outcome."""
    from rdo.report import run_stage2_belief_decay
    from rdo.memory import PatternMemory
    d = str(tmp_path / "s2")
    res = run_stage2_belief_decay(repo_dir=".", workdir=d, review=FIXTURE_REVIEW)
    pr = res["prediction_vs_review"]
    assert "planning_review" in pr["kind"] and "not an execution" in pr["kind"]
    assert pr["predicted"]["net_new_count"] == 2
    assert pr["comparison"]["under_expansion_missed"] == ["belief_decay_rollback"]
    assert "under_expansion" in pr["calibration_patterns"]
    # durable: the reviewed actual and the calibration pattern are persisted, the pattern carrying
    # explicit reviewer provenance and clearly marked as a planning review (not execution)
    reloaded = CycleStore(d).load("belief_decay_mvp")
    assert reloaded.kind == "native_planning"                     # NOT executed_verified
    assert reloaded.actual["review_kind"] == "planning_review"
    under = [p for p in PatternMemory(d + "/patterns.jsonl").patterns() if p.key == "under_expansion"]
    assert under and "planning_review" in under[0].provenance and "reviewer=" in under[0].provenance


def test_stage2_end_to_end(tmp_path):
    """End-to-end Stage 2: one runner call yields convergence, complete counts, deferred
    frontier, ordered packages and a durable reviewed-planning calibration."""
    from rdo.report import run_stage2_belief_decay
    d = str(tmp_path / "e2e")
    res = run_stage2_belief_decay(repo_dir=".", workdir=d, review=FIXTURE_REVIEW)
    assert res["converging_prerequisites"] == ["shared_runtime_effect.runtime_verification"]
    assert {"discovered", "unique", "reuse", "net_new", "deferred", "unresolved"} <= set(res["counts"])
    assert res["deferred_frontier"] and res["frontier_breakdown"]["deferred"] == 0
    assert res["work_packages_ordered"][0][1] == "eligible"       # a buildable package leads
    assert res["prediction_vs_review"]["calibration_patterns"] == ["under_expansion"]
    # the persisted artefact resumes in a fresh process with all of it intact
    import json as _json, subprocess as _sp, sys as _sys
    code = (f"import json; from rdo.memory import CycleStore; c=CycleStore({d!r}).load('belief_decay_mvp'); "
            "print(json.dumps({'counts':c.counts,'frontier':len(c.frontier),'kind':c.kind}))")
    r = _sp.run([_sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = _json.loads(r.stdout)
    assert out["counts"]["discovered"] == 41 and out["frontier"] == 4 and out["kind"] == "native_planning"


# --------------------- integrity pass: four correctness points ----------------------

def test_calibration_requires_an_authorised_review(tmp_path):
    """#1 A predetermined demonstration never becomes a learned production pattern. With no
    review the default runner writes NO pattern; a review without a named reviewer is refused;
    only a reviewer-attributed review calibrates."""
    import pytest
    from rdo.report import run_stage2_belief_decay
    from rdo.memory import PatternMemory
    # default path: no review -> no calibration pattern written
    d0 = str(tmp_path / "none")
    res0 = run_stage2_belief_decay(repo_dir=".", workdir=d0)
    assert "no review" in res0["prediction_vs_review"]
    assert PatternMemory(d0 + "/patterns.jsonl").patterns() == []
    # a review with no reviewer provenance is refused
    d1 = str(tmp_path / "anon")
    with pytest.raises(ValueError):
        run_stage2_belief_decay(repo_dir=".", workdir=d1, review={"missed": ["x"]})


def test_safe_convergence_merge(sl):
    """#3 The shared prerequisite merges only compatible obligations: both parent relationships
    and both provenance paths survive, the merged node is coherent, and incompatible collisions
    are surfaced rather than silently merged."""
    from rdo.extrapolator import expand, MergeConflict
    from rdo.model import Obligation, ANTI_REQUIREMENT
    c = sl["cycle"]
    node = "shared_runtime_effect.runtime_verification"
    merged = [o for o in c.obligations if o["key"] == node][0]
    parents = sorted(r["src"] for r in c.relationships
                     if r["kind"] == "depends_on" and r["dst"] == node)
    assert parents == ["belief_decay_consumer_generation", "belief_decay_consumer_safety"]  # both rels
    assert "consumer->runtime_verification" in merged["provenance"]                          # path kept
    assert merged["kind"] == "runtime_verification" and merged["classification"] == "necessary"
    # incompatible kind under one key -> surfaced
    import pytest
    with pytest.raises(MergeConflict):
        expand([Obligation("k", "a", "daemon"), Obligation("k", "b", "score")])
    # build vs anti-requirement under one key -> surfaced
    with pytest.raises(MergeConflict):
        expand([Obligation("k", "a", "consumer"),
                Obligation("k", "b", "consumer", classification=ANTI_REQUIREMENT)])


def test_work_package_ordering_limitation_is_honest(sl):
    """#4 The ordering guarantee is exactly: eligible-first, then priority, then key — NOT a full
    prerequisite topological sort. Blocked packages keep their blockers; the limitation is real."""
    c = sl["cycle"]
    wps = c.work_packages
    # guaranteed: every eligible package precedes every blocked one
    tiers = [0 if p["eligibility"] == "eligible" else 1 for p in wps]
    assert tiers == sorted(tiers)
    # blocked packages still carry their hard blockers (unresolved prerequisites stay visible)
    assert all(p["blockers"] for p in wps if p["eligibility"] == "blocked")
    # NOT claimed: a full topological order. Blocked packages are ranked by score, so the blocked
    # tier is a priority order, not a dependency order — assert we don't accidentally provide one.
    blocked = [p for p in wps if p["eligibility"] == "blocked"]
    def score(p):
        return max((dd["_provisional_sort_score_uncalibrated"]
                    for dd in p["priority_dimensions"].values()), default=0.0)
    assert [p["key"] for p in blocked] == [p["key"] for p in
            sorted(blocked, key=lambda p: (-score(p), p["key"]))]
