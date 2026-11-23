"""RDO behaviour + required adversarial tests (RDO spec v1.4 §28, Part X).

Isolated fixtures / temp repos throughout. One test per required case: incomplete
information, duplicate discovery, false dependency, feedback cycle, over-expansion,
under-expansion, inappropriate reuse — plus pattern-memory non-promotion, the
learning loop, and the independence guarantee. A final smoke test runs the whole
cycle against the real repository.
"""
import os

import pytest

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


def test_pattern_memory_confidence_can_decrease_on_disconfirmation(tmp_path):
    # the deficiency fix (item 4): confidence was monotonic; it can now DROP when a
    # later cycle disagrees, and the disconfirming evidence is retained.
    from rdo.memory import PatternMemory
    mem = PatternMemory(str(tmp_path / "p.jsonl"))
    mem.add(Pattern("k", "stmt", "cycle:1", confidence=0.5, exceptions=["seed exception"]))
    mem.add(Pattern("k", "stmt", "cycle:2"))                 # corroborate -> 0.6
    assert mem.patterns()[0].confidence == 0.6
    mem.refute("k", "cycle:3 disagreed")                     # disconfirm -> 0.5
    p = mem.patterns()[0]
    assert p.confidence == 0.5 and p.disconfirmed_count == 1
    assert any("disconfirmed" in e for e in p.exceptions)    # evidence retained
    assert "seed exception" in p.exceptions                   # earlier exceptions kept
    assert mem.refute("unknown", "x") is None                 # no-op on unknown key
    # persists across reopen
    assert PatternMemory(str(tmp_path / "p.jsonl")).patterns()[0].disconfirmed_count == 1


# ---- refute() dependability: the six properties verified (item 2) ----

def test_corroboration_dedup_and_ceiling(tmp_path):
    from rdo.memory import PatternMemory
    mem = PatternMemory(str(tmp_path / "p.jsonl"))
    mem.add(Pattern("k", "s", "src0", confidence=0.3))
    for _ in range(5):                       # same provenance -> deduped, no inflation
        mem.add(Pattern("k", "s", "src0"))
    p = mem.patterns()[0]
    assert p.observed_count == 1 and p.confidence == 0.3
    for i in range(1, 20):                   # 20 DISTINCT sources -> ceiling at 0.9
        mem.add(Pattern("k", "s", f"src{i}"))
    p = mem.patterns()[0]
    assert p.observed_count == 20 and p.confidence == 0.9


def test_disconfirmation_dedup_floor_and_evidence_preserved(tmp_path):
    from rdo.memory import PatternMemory
    mem = PatternMemory(str(tmp_path / "p.jsonl"))
    mem.add(Pattern("k", "s", "src0", confidence=0.3, exceptions=["orig"]))
    mem.refute("k", "E1")
    mem.refute("k", "E1")                    # (c) duplicate disconfirmation -> deduped
    p = mem.patterns()[0]
    assert p.disconfirmed_count == 1
    assert "orig" in p.exceptions and any("disconfirmed: E1" in e for e in p.exceptions)  # (a)
    for i in range(10):                      # (e) floor at 0, never negative
        mem.refute("k", f"D{i}")
    assert mem.patterns()[0].confidence == 0.0


def test_confidence_is_pure_and_order_independent(tmp_path):
    from rdo.memory import PatternMemory, _confidence
    # (b) pure function of (base, observed, disconfirmed) with a single clamp
    assert _confidence(0.3, 3, 1) == 0.4
    assert _confidence(0.9, 5, 1) == 0.9     # ceiling
    assert _confidence(0.1, 1, 5) == 0.0     # floor
    # order independence: corroborate-then-refute == refute-then-corroborate
    a = PatternMemory(str(tmp_path / "a.jsonl"))
    a.add(Pattern("k", "s", "s0", confidence=0.5)); a.add(Pattern("k", "s", "s1")); a.refute("k", "E")
    b = PatternMemory(str(tmp_path / "b.jsonl"))
    b.add(Pattern("k", "s", "s0", confidence=0.5)); b.refute("k", "E"); b.add(Pattern("k", "s", "s1"))
    assert a.patterns()[0].confidence == b.patterns()[0].confidence == 0.5
    # reconstructible from the persisted event history (reopen recomputes identically)
    assert PatternMemory(str(tmp_path / "a.jsonl")).patterns()[0].confidence == 0.5


def test_corroboration_and_refutation_counts_are_independent(tmp_path):
    from rdo.memory import PatternMemory
    mem = PatternMemory(str(tmp_path / "p.jsonl"))
    mem.add(Pattern("k", "s", "s0")); mem.add(Pattern("k", "s", "s1")); mem.refute("k", "E")
    p = mem.patterns()[0]                     # (d) separate, non-contradictory counts
    assert p.observed_count == 2 and p.disconfirmed_count == 1
    assert len(p.confirmations) == 2 and len(p.disconfirmations) == 1


def test_zero_confidence_retained_but_not_applicable(tmp_path):
    from rdo.memory import PatternMemory
    mem = PatternMemory(str(tmp_path / "p.jsonl"))
    mem.add(Pattern("k", "s", "s0", confidence=0.3, applicability="widget"))
    for i in range(5):
        mem.refute("k", f"D{i}")             # decay to zero + net negative
    p = mem.patterns()[0]
    assert p.confidence == 0.0 and p in mem.patterns()          # (f) retained for inspection
    assert p.to_dict()["reliable"] is False
    assert mem.applicable("build a widget") == []              # but NOT offered as guidance


# ---- persistence lifecycle + reconstruction (item 2) ----

def test_persistence_lifecycle_reconstruction_and_append_only(tmp_path):
    from rdo.memory import PatternMemory
    path = str(tmp_path / "p.jsonl")
    mem = PatternMemory(path)
    mem.add(Pattern("k", "rule", "cycle:1", confidence=0.3, exceptions=["seed"]))
    mem.add(Pattern("k", "rule", "cycle:2"))        # corroborate
    mem.add(Pattern("k", "rule", "cycle:2"))        # DUPLICATE corroboration -> no state/log change
    mem.refute("k", "E")                            # disconfirm
    mem.refute("k", "E")                            # DUPLICATE refutation -> no state/log change
    before = mem.patterns()[0]
    assert (before.confidence, before.observed_count, before.disconfirmed_count) == (0.3, 2, 1)
    # append-only log: exactly the three state-changing events, duplicates wrote nothing
    lines = [ln for ln in open(path, encoding="utf-8").read().splitlines() if ln.strip()]
    assert len(lines) == 3
    # reload -> confidence/counts reconstructed deterministically from the persisted history
    after = PatternMemory(path).patterns()[0]
    assert (after.confidence, after.observed_count, after.disconfirmed_count) == (0.3, 2, 1)
    assert after.confirmations == ["cycle:1", "cycle:2"] and after.disconfirmations == ["E"]


def test_tolerant_reload_skips_a_truncated_line(tmp_path):
    from rdo.memory import PatternMemory
    path = str(tmp_path / "p.jsonl")
    mem = PatternMemory(path)
    mem.add(Pattern("k", "rule", "cycle:1", confidence=0.4))
    with open(path, "a", encoding="utf-8") as fh:   # simulate a crash mid-append
        fh.write('{"key": "k", "statement": "trunc')
    reloaded = PatternMemory(path)                  # must not brick on the truncated line
    assert reloaded.patterns()[0].confidence == 0.4


def test_record_executed_raises_on_persistence_failure_without_partial_lessons(tmp_path):
    from rdo.orchestrator import _record_executed
    from rdo.memory import PatternMemory
    mem = PatternMemory(str(tmp_path / "p.jsonl"))

    class _FailingStore:
        def save(self, cycle):
            raise OSError("disk full")

    with pytest.raises(OSError):
        _record_executed(_FailingStore(), mem, cycle_id="x", objective="o",
                         predicted={"effort": 1}, reused=["r"], verification={},
                         actual={"effort_actual": 1, "missed": []})
    # persistence failed BEFORE any lesson was added -> no partial "success"
    assert mem.patterns() == []


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


def test_orchestrator_is_domain_free():
    """The generic cycle DRIVER must name no domain specifics in its CODE. Genius/
    migration/config knowledge lives in knowledge.py; the demonstration + reporting
    live in report.py. This guards the responsibility split so the driver cannot
    silently re-absorb domain logic (the leak that motivated extracting report.py and
    genius_authority_audit). Docstrings/comments are stripped first, so the check is
    on identifiers and in-code string literals (e.g. `== "genius"`), not prose."""
    import ast
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "orchestrator.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    # drop module/function/class docstrings; ast.unparse already omits comments
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            body = node.body
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                node.body = body[1:] or [ast.Pass()]
    code = ast.unparse(tree).lower()
    forbidden = ["genius", "migration", "config_invariant", "affinity",
                 "assess_signal_authority", "quality_synthesis", "tagger"]
    present = [tok for tok in forbidden if tok in code]
    assert present == [], f"orchestrator.py code must stay domain-free; found: {present}"


# ---- full cycle against the real repository (integration smoke) ----

def test_demo_cycle_against_real_repo(tmp_path):
    from rdo.report import demo_genius_tagger
    res = demo_genius_tagger(repo_dir=".", workdir=str(tmp_path / "cycles"))
    for k in ("1_discovered", "2_correctly_reused", "3_rejected_or_deferred",
              "4_recommended_work", "5_verification", "6_learned"):
        assert k in res
    assert res["5_verification"]["all_reuse_backed"] is True
    assert res["2_correctly_reused"], "should reconcile some already-built mechanisms"
    assert all(w["eligibility"] == "blocked" for w in res["4_recommended_work"])
    audit = res["optimal_functional_tension"]["signal_authority_audit"]
    assert audit["consumer_count"] >= 4
    # authority is assessed by relationship, not count: behavioural < total, and the
    # audit names material/self-reinforcement concerns rather than flagging the count
    assert audit["behavioural_count"] < audit["consumer_count"]
    assert audit["self_reinforcement_candidates"]
    assert audit["evidence_grounded"] is True


# ---- generalisation: a second cycle of a DIFFERENT pattern (defect remediation) ----

def test_defect_pattern_generalises_and_metrics(tmp_path):
    from rdo.report import run_catalogue
    res = run_catalogue(repo_dir=".", workdir=str(tmp_path / "cycles"))
    cycles = res["cycles"]
    assert len(cycles) == 4  # genius + migration_defect + affinity_drift + config_invariant
    defect = cycles["migration_defect (defect-remediation pattern)"]
    # the defect cycle reconciles applied fixes as reuse...
    assert any("fix" in r for r in defect["2_correctly_reused"])
    # ...and still produces at least one ELIGIBLE net-new package (adding a test is safe,
    # unlike the all-gated genius consumers) — the prioritiser distinguishes the two
    assert any(w["eligibility"] == "eligible" for w in defect["4_recommended_work"])
    # FOUR executed+verified cycles recorded (3 test-guards + 1 refactor-type consolidation)
    assert len(res["executed_cycles"]) == 4
    m = res["learning_metrics"]
    assert len(m["per_cycle"]) == 9 and len(m["measures"]) == 8
    # the HONEST comparable pool is the 2 MIGRATION guards (engineering_pattern), not 3 test_guards
    assert set(m["comparability"]["efficiency_comparison_pool"]) == {
        "arc_closers_regtest_2026-11", "affinity_regtest_2026-11"}
    assert m["completed_executed_cycles"] == 4 and m["largest_comparable_group"] == 2
    cp = m["comparability"]["genuinely_comparable_by_engineering_pattern"]
    assert set(cp.get("migration_guard", [])) == {"arc_closers_regtest_2026-11", "affinity_regtest_2026-11"}
    assert "invariant_guard" in cp and "refactor" in cp
    assert res["comparability_assessment"]["largest_genuinely_comparable_group"] == 2
    assert "watcher_2026-11" in m["comparability"]["excluded_from_efficiency"]["imported_retrospective"]
    # cross-cycle transfer recorded as an OBSERVATION, not proof
    tr = res["cross_cycle_transfer"]
    assert len(tr["executed_cycles"]) == 4 and "not proof" in tr["observation"].lower()
    matched = {r["cycle"]: r["prediction_matched"] for r in tr["executed_cycles"]}
    assert matched["arc_closers_regtest_2026-11"] is False     # cycle 1 missed an obligation
    assert matched["affinity_regtest_2026-11"] is True         # lesson applied
    assert matched["config_invariant_2026-11"] is True         # transferred beyond migration
    # four-way change categorisation present (terminology clarity, item 5)
    assert set(res["change_categories"]) >= {"general_engine_logic", "pattern_taxonomy",
                                             "domain_knowledge", "recorded_experience"}


def test_defect_kind_expands_to_fix_and_regression_test():
    obs, _, _ = expand([Obligation("bug", "a bug", "defect")],
                       reconcile_fn=lambda o: MISSING, max_depth=4)
    for child in ("bug.fix", "bug.regression_test", "bug.root_cause", "bug.verification"):
        assert child in obs


def test_cycle_metrics_pending_vs_recorded():
    from rdo.memory import cycle_metrics
    pending = CycleRecord(id="p", objective="o",
                          obligations=[{"key": "a", "recon_status": "missing", "provenance": "seed"}],
                          verification={"all_reuse_backed": True})
    mp = cycle_metrics(pending)
    assert mp["outcome_status"] == "pending" and mp["missed_obligation_count"] is None
    recorded = CycleRecord(id="r", objective="o", predicted={"effort": 2})
    record_actual(recorded, {"missed": ["x"], "effort_actual": 3})
    mr = cycle_metrics(recorded)
    assert mr["outcome_status"] == "recorded" and mr["prediction_error_effort"] == 1


# ---- generalisation: obligation scope taxonomy + engine non-contamination ----

def test_obligation_scope_taxonomy():
    from rdo.extrapolator import classify_scope, scope_summary
    assert classify_scope({"classification": "anti_requirement", "provenance": "seed",
                           "kind": "x"}) == "anti_requirement"
    assert classify_scope({"classification": "conditional", "provenance": "expansion_rule:a->b",
                           "kind": "migration"}) == "context_dependent"
    assert classify_scope({"classification": "necessary", "provenance": "seed",
                           "kind": "persistence"}) == "domain_specific"
    assert classify_scope({"classification": "necessary",
                           "provenance": "expansion_rule:persistence->schema",
                           "kind": "schema"}) == "general"
    assert classify_scope({"classification": "necessary", "provenance": "expansion_rule:x->y",
                           "kind": "an_unknown_kind"}) == "novel"
    s = scope_summary([{"classification": "necessary", "provenance": "seed",
                        "kind": "persistence", "key": "k"}])
    assert s["domain_specific"] == ["k"]


def test_engine_has_no_domain_tokens():
    # the common reasoning engine must stay uncontaminated by any domain
    import rdo.extrapolator as ex
    src = open(ex.__file__, encoding="utf-8").read()
    for token in ("genius", "arc_closers", "quality_synthesis", "beliefs_content"):
        assert token not in src, f"engine contaminated with domain token: {token}"


def test_genius_feedback_is_hypothesis():
    from rdo.knowledge import genius_feedback_hypothesis
    h = genius_feedback_hypothesis()
    assert h["classification"] == "HYPOTHESIS"
    assert h["path"] and h["gain_variables"] and h["existing_safeguards"]
    assert h["runtime_observations_needed"] and "do NOT" in h["do_not"]


def test_executed_cycle_efficiency_eligibility(tmp_path):
    from rdo.report import record_arc_closers_execution
    from rdo.memory import CycleStore, PatternMemory, metrics_series, record_actual
    from rdo.model import CycleRecord, IMPORTED_RETROSPECTIVE
    store = CycleStore(str(tmp_path))
    mem = PatternMemory(str(tmp_path / "p.jsonl"))
    c = record_arc_closers_execution(store, mem)
    assert c.kind == "executed_verified" and c.actual is not None
    imp = CycleRecord(id="i", objective="o", kind=IMPORTED_RETROSPECTIVE)
    record_actual(imp, {"effort_actual": 1})          # imported, has actuals, still NOT comparable
    m = metrics_series([c, imp])
    assert m["completed_executed_cycles"] == 1
    assert m["comparability"]["efficiency_comparison_pool"] == [c.id]


# ---- recorder-consolidation equivalence: each recorder's record is unchanged ----

def _run_recorder(fn, tmp_path):
    from rdo.memory import CycleStore, PatternMemory
    store = CycleStore(str(tmp_path))
    mem = PatternMemory(str(tmp_path / "p.jsonl"))
    return fn(store, mem), mem


def test_arc_closers_recorder_record_equivalent(tmp_path):
    from rdo.report import record_arc_closers_execution
    c, mem = _run_recorder(record_arc_closers_execution, tmp_path)
    assert c.kind == "executed_verified"
    assert c.predicted["effort"] == 1 and c.actual["effort_actual"] == 2
    assert c.actual["missed"] == ["arc_closers_migration.legacy_upgrade_path"]
    assert c.verification["tests"] == 6 and c.verification["legacy_upgrade_path_verified"] is True
    keys = {p.key for p in mem.patterns()}
    assert {"migration_dual_path", "migration_guard_needs_legacy_path",
            "under_expansion", "effort_estimate_bias"} <= keys
    # lessons derived EXACTLY once (not double-counted)
    eeb = next(p for p in mem.patterns() if p.key == "effort_estimate_bias")
    assert eeb.observed_count == 1


def test_affinity_recorder_record_equivalent(tmp_path):
    from rdo.report import record_affinity_execution
    c, mem = _run_recorder(record_affinity_execution, tmp_path)
    assert c.kind == "executed_verified"
    assert c.predicted["effort"] == 1 and c.actual["effort_actual"] == 1
    assert c.actual["missed"] == [] and c.verification["tests"] == 2
    # no effort/under-expansion lessons when prediction matched
    assert not any(p.key in ("under_expansion", "effort_estimate_bias") for p in mem.patterns())


def test_config_recorder_record_equivalent(tmp_path):
    from rdo.report import record_config_invariant_execution
    c, mem = _run_recorder(record_config_invariant_execution, tmp_path)
    assert c.kind == "executed_verified"
    assert c.predicted["effort"] == 1 and c.actual["effort_actual"] == 1
    assert c.actual["missed"] == [] and c.verification["non_vacuous"] is True
    assert c.verification["no_production_change"] is True


# ---- the RDO subjected to its own Optimal Functional Tension ----

def test_rdo_self_assessment_lean_and_independent():
    from rdo.report import self_assess
    r = self_assess()
    assert r["independence_no_nex_import"] is True
    assert r["reuses_watcher_infrastructure"] is True
    # 13 cohesive modules: the 10 engine/demo modules + graph (Stage 3), belief_audit (Stage 4)
    # and pathway (Stage 5). Each is one authorised roadmap capability, not proliferation; the
    # bound is kept at exactly the current count so a further module still trips this review.
    assert r["module_count"] <= 13
    assert not any(f["verdict"] == "VIOLATION" for f in r["findings"])
