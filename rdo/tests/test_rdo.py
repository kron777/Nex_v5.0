"""RDO behaviour + required adversarial tests (RDO spec v1.4 §28, Part X).

Isolated fixtures / temp repos throughout. One test per required case: incomplete
information, duplicate discovery, false dependency, feedback cycle, over-expansion,
under-expansion, inappropriate reuse — plus pattern-memory non-promotion, the
learning loop, and the independence guarantee. A final smoke test runs the whole
cycle against the real repository.
"""
import os

from rdo.extrapolator import expand
from rdo.memory import (CycleStore, PatternMemory, accuracy_series, compare,
                        derive_lessons, record_actual)
from rdo.model import (ANTI_REQUIREMENT, MISSING, NECESSARY, PARTIAL, RECON_UNKNOWN,
                       REUSE_EXISTING, CycleRecord, Obligation, Pattern, Relationship)
from rdo.prioritise import build_work_packages, eligibility
from rdo.reconcile import Signature, prune_false_dependencies, reconcile
from rdo.tension import assess_system, recognize_sufficiency


# ---- incomplete information: honest unknown, never fabricated ----

def test_incomplete_information_is_unknown_not_fabricated(tmp_path):
    ob = Obligation("x", "x", "persistence")
    status = reconcile(ob, str(tmp_path), signatures=None)
    assert status == RECON_UNKNOWN
    assert ob.confidence == "inferred"
    assert ob.recon_evidence == []          # nothing invented
    assert "inference" in ob.note


# ---- duplicate discovery merges (convergent branches) ----

def test_duplicate_discovery_merges():
    seeds = [Obligation("store", "store", "persistence"),
             Obligation("store.schema", "dup schema", "schema")]  # same key a child will produce
    obs, rels, _ = expand(seeds, reconcile_fn=None, max_depth=4)
    assert list(obs).count("store.schema") == 1
    prov = obs["store.schema"].provenance
    assert "seed" in prov and "expansion_rule" in prov          # both discoveries recorded
    assert any(r.dst == "store.schema" and r.src == "store" for r in rels)


# ---- false dependency pruned ----

def test_false_dependency_is_pruned():
    tgt = Obligation("db", "db", "persistence", recon_status=REUSE_EXISTING,
                     recon_evidence=["substrate/init_db.py:1"])
    src = Obligation("feature", "feature", "consumer")
    obs = {"db": tgt, "feature": src}
    rels = [Relationship("feature", "db", "depends_on")]
    pruned = prune_false_dependencies(obs, rels)
    assert pruned and rels[0].kind == "reuses"                  # reclassified, not net-new


# ---- feedback cycle detected at system level ----

def test_feedback_cycle_detected():
    obs = {"a": Obligation("a", "a", "consumer"), "b": Obligation("b", "b", "consumer")}
    rels = [Relationship("a", "b", "depends_on"), Relationship("b", "a", "depends_on")]
    sys_t = assess_system(obs, rels)
    assert any(t.subject == "feedback_cycles" for t in sys_t)


# ---- over-expansion controlled: reuse stops expansion; max_depth bounds ----

def test_over_expansion_stopped_by_reuse():
    seeds = [Obligation("store", "store", "persistence")]
    obs, _, frontier = expand(seeds, reconcile_fn=lambda o: REUSE_EXISTING, max_depth=4)
    assert set(obs) == {"store"}                                 # not expanded
    assert any("already satisfied" in f["reason"] for f in frontier)


def test_max_depth_bounds_expansion():
    obs, _, frontier = expand([Obligation("store", "s", "persistence")],
                              reconcile_fn=None, max_depth=0)
    assert set(obs) == {"store"} and any("max_depth" in f["reason"] for f in frontier)


# ---- under-expansion avoided: a MISSING necessary mechanism decomposes ----

def test_under_expansion_builds_children_when_missing():
    obs, _, _ = expand([Obligation("store", "s", "persistence")],
                       reconcile_fn=lambda o: MISSING, max_depth=4)
    for child in ("store.schema", "store.write_path", "store.provenance", "store.test"):
        assert child in obs


# ---- inappropriate reuse: reconcile needs a real match ----

def test_reconcile_requires_real_match(tmp_path):
    (tmp_path / "f.py").write_text("def real_thing():\n    return 1\n")
    ob_missing = Obligation("m", "m", "daemon")
    assert reconcile(ob_missing, str(tmp_path),
                     [Signature("class GeniusTagger", None, "daemon")]) == MISSING
    ob_reuse = Obligation("r", "r", "daemon")
    assert reconcile(ob_reuse, str(tmp_path),
                     [Signature("def real_thing", None, "fn")]) == REUSE_EXISTING
    ob_partial = Obligation("p", "p", "daemon")
    assert reconcile(ob_partial, str(tmp_path),
                     [Signature("def real_thing", None, "a"),
                      Signature("def absent", None, "b")]) == PARTIAL  # not reuse


# ---- eligibility: active changes need a gate; host-only runtime is blocked ----

def test_eligibility_blocks_ungated_and_host_only():
    obs = {}
    consumer = Obligation("c", "c", "consumer")
    e = eligibility(consumer, obs, [], active_experiments=[], authorised_gates=set())
    assert e["eligibility"] == "blocked" and any("gate" in b for b in e["blockers"])
    rt = Obligation("v", "v", "runtime_verification")
    assert eligibility(rt, obs, [])["eligibility"] == "blocked"


def test_anti_requirements_appear_and_reused_not_rebuilt():
    obs = {
        "exists": Obligation("exists", "e", "persistence", recon_status=REUSE_EXISTING,
                             recon_evidence=["init_db.py:1"]),
        "anti": Obligation("anti", "no second store", "anti_requirement",
                           classification=ANTI_REQUIREMENT, rationale="already persisted"),
        "todo": Obligation("todo", "t", "consumer", recon_status=MISSING),
    }
    pkgs = build_work_packages(obs, [], [], set())
    anti_all = sum((p.anti_requirements for p in pkgs), [])
    assert any("do NOT rebuild 'exists'" in a for a in anti_all)
    assert any("already persisted" in a for a in anti_all)
    assert all("exists" not in p.obligation_keys for p in pkgs)   # reused != work


# ---- pattern memory never becomes a universal rule ----

def test_pattern_memory_no_universal_promotion(tmp_path):
    mem = PatternMemory(str(tmp_path / "p.jsonl"))
    mem.add(Pattern("k", "stmt", "cycle:1", confidence=0.3,
                    exceptions=["observed once"]))
    for _ in range(20):
        mem.add(Pattern("k", "stmt", "cycle:n"))
    p = mem.patterns()[0]
    assert p.confidence <= 0.9 and p.confidence < 1.0            # capped, never certain
    assert p.exceptions                                          # exceptions retained
    # persistence across reopen
    assert PatternMemory(str(tmp_path / "p.jsonl")).patterns()[0].observed_count == p.observed_count


# ---- learning loop: predicted vs actual, no acceleration claim ----

def test_learning_compare_and_series(tmp_path):
    c = CycleRecord(id="1", objective="o", predicted={"effort": 3})
    record_actual(c, {"missed": ["need_x"], "effort_actual": 5})
    disc = compare(c)
    assert disc["under_expansion_missed"] == ["need_x"] and disc["effort_error"] == 2
    lessons = {p.key for p in derive_lessons(c, disc)}
    assert "under_expansion" in lessons and "effort_estimate_bias" in lessons
    series = accuracy_series([c])
    assert series["completed_cycles"] == 1 and "no acceleration" in series["trend_claim"]


def test_recognize_sufficiency_restrains_development():
    obs = {"built": Obligation("built", "b", "persistence", recon_status=REUSE_EXISTING),
           "opt": Obligation("opt", "o", "ui", classification="optional",
                             recon_status=MISSING)}
    suff = {s["key"] for s in recognize_sufficiency(obs)}
    assert "built" in suff and "opt" in suff                     # neither needs more work


# ---- independence guarantee: RDO never imports NEX's cognitive runtime ----

def test_rdo_never_imports_nex_runtime():
    import rdo
    assert rdo.ADVISORY_ONLY is True
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    import re
    bad = re.compile(r"^\s*(from|import)\s+(theory_x|substrate)\b", re.M)
    offenders = []
    for d, _, files in os.walk(root):
        if "__pycache__" in d:
            continue
        for f in files:
            if f.endswith(".py"):
                with open(os.path.join(d, f), encoding="utf-8") as fh:
                    if bad.search(fh.read()):
                        offenders.append(f)
    assert offenders == [], f"RDO must not import NEX runtime: {offenders}"


# ---- full cycle against the real repository (integration smoke) ----

def test_demo_cycle_against_real_repo(tmp_path):
    from rdo.orchestrator import demo_genius_tagger
    res = demo_genius_tagger(repo_dir=".", workdir=str(tmp_path / "cycles"))
    for k in ("1_discovered", "2_correctly_reused", "3_rejected_or_deferred",
              "4_recommended_work", "5_verification", "6_learned"):
        assert k in res
    assert res["5_verification"]["all_reuse_backed"] is True
    assert res["2_correctly_reused"], "should reconcile some already-built mechanisms"
    assert all(w["eligibility"] == "blocked" for w in res["4_recommended_work"])
    assert res["optimal_functional_tension"]["signal_influence_audit"]["consumer_count"] >= 4
