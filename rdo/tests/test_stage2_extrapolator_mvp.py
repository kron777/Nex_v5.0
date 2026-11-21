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
