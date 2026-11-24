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
                       REUSE_EXISTING, SIGNATURE_MATCHED, CycleRecord, Obligation, Pattern, Relationship)
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
                     recon_evidence=["substrate/init_db.py:1"], confidence="measured",
                     recon_semantic_verified=True)
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
    def reviewed_reuse(ob):
        ob.recon_evidence = ["store.py:1"]
        ob.confidence = "measured"
        ob.recon_semantic_verified = True
        return REUSE_EXISTING
    obs, _, frontier = expand(seeds, reconcile_fn=reviewed_reuse, max_depth=4)
    assert set(obs) == {"store"}                                 # not expanded
    assert any("semantic satisfaction independently reviewed" in f["reason"] for f in frontier)


def test_signature_match_without_semantic_review_does_not_stop_expansion():
    obs, _, frontier = expand(
        [Obligation("store", "store", "persistence")],
        reconcile_fn=lambda o: SIGNATURE_MATCHED, max_depth=1)
    assert "store.schema" in obs
    assert any("semantic satisfaction unreviewed" in f["reason"] for f in frontier)


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
                     [Signature("def real_thing", None, "fn")]) == "signature_matched"
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
                             recon_evidence=["init_db.py:1"], confidence="measured",
                             recon_semantic_verified=True),
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
    for i in range(2, 22):
        mem.add(Pattern("k", "stmt", f"cycle:{i}"))
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
    assert series["completed_cycles"] == 0 and series["series"][0]["status"] == "partial"
    assert "no acceleration" in series["trend_claim"]


def test_recognize_sufficiency_restrains_development():
    obs = {"built": Obligation("built", "b", "persistence", recon_status=REUSE_EXISTING,
                               recon_evidence=["src.py:1"], confidence="measured",
                               recon_semantic_verified=True),
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
    for k in ("1_discovered", "2_signature_matches_located", "3_rejected_or_deferred",
              "4_recommended_work", "5_source_evidence_coverage", "6_learned"):
        assert k in res
    assert res["5_source_evidence_coverage"]["all_signature_matches_have_file_evidence"] is True
    assert res["2_signature_matches_located"], "should locate configured source signatures"
    blockers = [b for w in res["4_recommended_work"] for b in w["blockers"]]
    assert any("preregistered" in b for b in blockers)
    assert any("host-only" in b for b in blockers)
    audit = res["optimal_functional_tension"]["signal_authority_audit"]
    assert audit["consumer_count"] >= 4
    # authority is assessed by relationship, not count: behavioural < total, and the
    # audit names material/self-reinforcement concerns rather than flagging the count
    assert audit["behavioural_count"] < audit["consumer_count"]
    assert audit["self_reinforcement_candidates"]
    assert audit["evidence_grounded"] is True


# ---- generalisation: a second cycle of a DIFFERENT pattern (defect remediation) ----

def test_defect_pattern_generalises_and_metrics(tmp_path):
    from rdo.orchestrator import run_catalogue
    res = run_catalogue(repo_dir=".", workdir=str(tmp_path / "cycles"))
    cycles = res["cycles"]
    assert len(cycles) == 3  # genius + migration_defect + affinity_drift
    defect = cycles["migration_defect (defect-remediation pattern)"]
    # the defect cycle locates source signatures for applied fixes; semantic
    # satisfaction remains unreviewed, so these are surfaced for review.
    assert any("fix" in r for r in defect["2_signature_matches_located"])
    # Regression-test obligations must be accounted for exactly once, and a
    # reuse claim must expose the specific test declaration that supports it.
    regression_keys = [key for key in defect["1_discovered"]["obligations"]
                       if "regression_test" in key]
    assert regression_keys
    packages = defect["4_recommended_work"]
    signature_matches = set(defect["2_signature_matches_located"])
    packaged = {key for w in packages for key in w["obligations"]}
    evidence = {item["key"]: item for item in defect["reconciliation_evidence"]}
    expected_test_paths = {
        "beliefs_content_uniq.regression_test": "tests/test_beliefs_content_dedup.py",
        "arc_closers_migration.regression_test": "tests/test_arc_closers_migration.py",
    }
    for key in regression_keys:
        # The exact test declaration is source-located AND surfaced for separate
        # semantic review; the source hit is not treated as completed reuse.
        assert key in signature_matches
        assert key in packaged
        item = evidence[key]
        assert item["status"] == "signature_matched"
        expected_path = expected_test_paths[key]
        assert any(expected_path in ref for ref in item["evidence"]), (
            f"{key} source anchor is not in {expected_path}")
    # Any remaining package is blocked where necessary prerequisites remain
    # unresolved; unknown obligations remain investigable, not relabelled missing.
    assert any(w["eligibility"] == "blocked" and
               any("unknown" in blocker or "partial" in blocker for blocker in w["blockers"])
               for w in packages)
    # two executed+verified cycles recorded
    assert len(res["executed_cycles"]) == 2
    # comparable cross-cycle metrics, with no premature acceleration claim
    m = res["learning_metrics"]
    assert len(m["per_cycle"]) == 6 and "acceleration" in m["trend_claim"]
    assert len(m["measures"]) == 8
    # ONLY the two executed+verified cycles are efficiency-comparable (imported + planning excluded)
    assert set(m["comparability"]["efficiency_comparison_pool"]) == {
        "arc_closers_regtest_2026-11", "affinity_regtest_2026-11"}
    assert m["efficiency_eligible_cycles"] == 2  # still < 3 -> no acceleration claim
    assert "watcher_2026-11" in m["comparability"]["excluded_from_efficiency"]["imported_retrospective"]


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
    assert mp["signature_evidence_coverage_complete"] is None
    recorded = CycleRecord(id="r", objective="o", predicted={"effort": 2})
    record_actual(recorded, {"missed": ["x"], "effort_actual": 3})
    mr = cycle_metrics(recorded)
    assert mr["outcome_status"] == "partial"
    assert mr["missed_obligation_count"] == 1 and mr["rework"] is None
    assert mr["prediction_error_effort"] == 1
    empty = CycleRecord(id="empty", objective="o")
    record_actual(empty, {})
    me = cycle_metrics(empty)
    assert me["missed_obligation_count"] is None and me["rework"] is None
    assert me["outcome_status"] == "partial"


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
    from rdo.orchestrator import record_arc_closers_execution
    from rdo.memory import CycleStore, PatternMemory, metrics_series, record_actual
    from rdo.model import CycleRecord, IMPORTED_RETROSPECTIVE
    store = CycleStore(str(tmp_path))
    mem = PatternMemory(str(tmp_path / "p.jsonl"))
    c = record_arc_closers_execution(store, mem)
    assert c.kind == "executed_verified" and c.actual is not None
    imp = CycleRecord(id="i", objective="o", kind=IMPORTED_RETROSPECTIVE)
    record_actual(imp, {"effort_actual": 1})          # imported, has actuals, still NOT comparable
    m = metrics_series([c, imp])
    assert m["efficiency_eligible_cycles"] == 1
    assert m["comparability"]["efficiency_comparison_pool"] == [c.id]


# ---- the RDO subjected to its own Optimal Functional Tension ----

def test_rdo_self_assessment_lean_and_independent():
    from rdo.orchestrator import self_assess
    r = self_assess()
    assert r["independence_no_nex_import"] is True
    assert r["reuses_watcher_infrastructure"] is True
    assert r["module_count"] <= 12
    assert not any(f["verdict"] == "VIOLATION" for f in r["findings"])

# ---- correction regressions: evidence availability and downstream interpretation ----

def test_reconciliation_distinguishes_empty_scan_from_unavailable(tmp_path, monkeypatch):
    import subprocess
    from types import SimpleNamespace
    import rdo.reconcile as recon

    ob = Obligation("empty", "empty", "daemon")
    monkeypatch.setattr(recon.subprocess, "run",
                        lambda *a, **k: SimpleNamespace(returncode=1, stdout="", stderr=""))
    assert recon.reconcile(ob, str(tmp_path),
                           [Signature("not_present", None, "empty")]) == MISSING

    # SQL is text-readable and must be searched, not treated as an excluded format.
    sql = tmp_path / "schema.sql"
    sql.write_text("CREATE TABLE evidence_marker (id INTEGER);", encoding="utf-8")
    monkeypatch.undo()
    sql_ob = Obligation("sql", "SQL evidence", "schema")
    assert recon.reconcile(sql_ob, str(tmp_path),
                           [Signature("CREATE TABLE evidence_marker", "schema.sql")]) == "signature_matched"

    stale_review = Obligation("stale", "stale review", "schema",
                              recon_status=REUSE_EXISTING,
                              recon_evidence=["old.py:1"], confidence="measured",
                              recon_semantic_verified=True)
    assert recon.reconcile(stale_review, str(tmp_path),
                           [Signature("not_present_now")]) == MISSING
    assert stale_review.recon_semantic_verified is False
    assert stale_review.recon_evidence == []

    ob = Obligation("partial-scan", "partial scan", "daemon")
    monkeypatch.setattr(recon.subprocess, "run",
                        lambda *a, **k: SimpleNamespace(returncode=2, stdout="x.py:1:match\n", stderr="read error"))
    assert recon.reconcile(ob, str(tmp_path),
                           [Signature("match", None, "scan")]) == RECON_UNKNOWN
    assert ob.confidence == "inferred"

    ob = Obligation("missing-path", "missing path", "daemon")
    assert recon.reconcile(ob, str(tmp_path), [Signature("x", "absent.py")]) == RECON_UNKNOWN

    def timeout(*a, **k):
        raise subprocess.TimeoutExpired("grep", 30)
    monkeypatch.setattr(recon.subprocess, "run", timeout)
    ob = Obligation("timeout", "timeout", "daemon")
    assert recon.reconcile(ob, str(tmp_path), [Signature("x")]) == RECON_UNKNOWN


def test_system_readiness_does_not_promote_partial_or_unknown():
    from rdo.model import TENSION_UNKNOWN, UNDERDEVELOPED, SUFFICIENT, SIGNATURE_MATCHED
    for status, expected in ((MISSING, UNDERDEVELOPED), (PARTIAL, UNDERDEVELOPED),
                             (RECON_UNKNOWN, TENSION_UNKNOWN),
                             (SIGNATURE_MATCHED, TENSION_UNKNOWN),
                             (REUSE_EXISTING, TENSION_UNKNOWN)):
        obs = {"required": Obligation("required", "required", "test",
                                      recon_status=status)}
        readiness = next(t for t in assess_system(obs, []) if t.subject == "integration_readiness")
        assert readiness.verdict == expected
    mixed = {"partial": Obligation("partial", "p", "test", recon_status=PARTIAL),
             "unknown": Obligation("unknown", "u", "test", recon_status=RECON_UNKNOWN)}
    readiness = next(t for t in assess_system(mixed, []) if t.subject == "integration_readiness")
    assert readiness.verdict == UNDERDEVELOPED

    all_reused = {"a": Obligation("a", "a", "test", recon_status=REUSE_EXISTING),
                  "b": Obligation("b", "b", "test", recon_status=REUSE_EXISTING)}
    readiness = next(t for t in assess_system(all_reused, []) if t.subject == "integration_readiness")
    assert readiness.verdict == TENSION_UNKNOWN
    reviewed = Obligation("reviewed", "reviewed", "test", recon_status=REUSE_EXISTING,
                          recon_evidence=["src.py:12"], confidence="measured",
                          recon_semantic_verified=True)
    readiness = next(t for t in assess_system({"reviewed": reviewed}, [])
                     if t.subject == "integration_readiness")
    assert readiness.verdict == SUFFICIENT

    no_necessary = {"optional": Obligation("optional", "optional", "test",
                                           classification="optional",
                                           recon_status=REUSE_EXISTING)}
    readiness = next(t for t in assess_system(no_necessary, []) if t.subject == "integration_readiness")
    assert readiness.verdict == TENSION_UNKNOWN


def test_unresolved_dependency_blocks_dependent_but_remains_investigable():
    from rdo.model import RECON_UNKNOWN
    for status in (MISSING, PARTIAL, RECON_UNKNOWN):
        target = Obligation("target", "target", "test", recon_status=status)
        work = Obligation("feature", "feature", "test", recon_status=MISSING)
        obs = {"target": target, "feature": work}
        rels = [Relationship("feature", "target", "depends_on")]
        assert eligibility(work, obs, rels)["eligibility"] == "blocked"
        assert eligibility(target, obs, rels)["eligibility"] == "eligible"
        packages = {p.key: p for p in build_work_packages(obs, rels)}
        assert packages["wp:feature"].eligibility == "blocked"
        assert "target" in packages["wp:target"].obligation_keys
    dangling = Obligation("feature", "feature", "test", recon_status=MISSING)
    assert eligibility(dangling, {"feature": dangling},
                       [Relationship("feature", "absent", "depends_on")])["eligibility"] == "blocked"


def test_pattern_memory_provenance_replay_is_idempotent_and_merges_origins(tmp_path):
    mem = PatternMemory(str(tmp_path / "patterns.jsonl"))
    first = Pattern("lesson", "statement", "cycle:one", confidence=0.3)
    mem.add(first)
    initial = mem.patterns()[0]
    mem.add(Pattern("lesson", "statement", "cycle:one", confidence=0.3))
    assert initial.observed_count == 1 and initial.confidence == 0.3
    mem.add(Pattern("lesson", "statement", "cycle:two", confidence=0.3))
    assert initial.observed_count == 2
    assert initial.provenance == "cycle:one; cycle:two"
    reopened = PatternMemory(str(tmp_path / "patterns.jsonl")).patterns()[0]
    assert reopened.observed_count == 2 and reopened.provenance == initial.provenance
    multi = Pattern("multi", "multiple origins in one call", "origin:a; origin:b")
    mem.add(multi)
    assert multi.observed_count == 1 and multi.provenance == "origin:a; origin:b"


def test_arc_closers_execution_derives_lessons_once(tmp_path, monkeypatch):
    import rdo.orchestrator as orch
    calls = []
    monkeypatch.setattr(orch, "derive_lessons", lambda c, d: calls.append(c.id) or [])
    orch.record_arc_closers_execution(CycleStore(str(tmp_path / "cycles")),
                                      PatternMemory(str(tmp_path / "patterns.jsonl")))
    assert calls == ["arc_closers_regtest_2026-11"]


def test_catalogue_replay_does_not_inflate_learning_counts(tmp_path):
    from rdo.orchestrator import run_catalogue
    workdir = str(tmp_path / "catalogue")
    run_catalogue(repo_dir=".", workdir=workdir)
    first = {p.key: (p.observed_count, p.confidence, p.provenance)
             for p in PatternMemory(str(tmp_path / "catalogue" / "patterns.jsonl")).patterns()}
    run_catalogue(repo_dir=".", workdir=workdir)
    second = {p.key: (p.observed_count, p.confidence, p.provenance)
              for p in PatternMemory(str(tmp_path / "catalogue" / "patterns.jsonl")).patterns()}
    assert second == first


def test_merged_seed_provenance_remains_domain_specific():
    from rdo.extrapolator import classify_scope
    assert classify_scope({"classification": NECESSARY,
                           "provenance": "seed; expansion_rule:persistence->schema",
                           "kind": "schema"}) == "domain_specific"


def test_metrics_keep_predicted_and_actual_effort_separate():
    from rdo.memory import cycle_metrics, metrics_series
    pending = CycleRecord(id="pending", objective="o", predicted={"effort": 7})
    empty_actual = CycleRecord(id="empty", objective="o", predicted={"effort": 8}, actual={})
    recorded = CycleRecord(id="recorded", objective="o", predicted={"effort": 9},
                           actual={"effort_actual": 4})
    assert cycle_metrics(pending)["engineering_effort"] is None
    assert cycle_metrics(pending)["predicted_effort"] == 7
    assert cycle_metrics(empty_actual)["engineering_effort"] is None
    assert cycle_metrics(empty_actual)["predicted_effort"] == 8
    assert cycle_metrics(recorded)["engineering_effort"] == 4
    series = metrics_series([pending, empty_actual, recorded])
    assert set(series["measure_keys"]) == set(series["denominators"])
    assert len(series["measure_keys"]) == 8


def test_active_experiment_registry_empty_is_distinct_from_unavailable(tmp_path):
    from rdo.orchestrator import _active_experiments
    empty = tmp_path / "observation_reports"
    empty.mkdir()
    assert _active_experiments(str(tmp_path)) == []
    empty.rmdir()
    import pytest
    with pytest.raises(RuntimeError, match="registry unavailable"):
        _active_experiments(str(tmp_path))


def test_grep_oserror_and_invalid_exit_remain_unknown(tmp_path, monkeypatch):
    import rdo.reconcile as recon
    ob = Obligation("scan-error", "scan error", "test")
    def fail(*args, **kwargs):
        raise OSError("grep unavailable")
    monkeypatch.setattr(recon.subprocess, "run", fail)
    assert recon.reconcile(ob, str(tmp_path), [Signature("x")]) == RECON_UNKNOWN

    from types import SimpleNamespace
    monkeypatch.setattr(recon.subprocess, "run",
                        lambda *a, **k: SimpleNamespace(returncode=3, stdout="", stderr="bad regex"))
    ob = Obligation("invalid-grep", "invalid grep", "test")
    assert recon.reconcile(ob, str(tmp_path), [Signature("[")]) == RECON_UNKNOWN

def test_active_experiment_registry_unreadable_or_invalid_fails_closed(tmp_path, monkeypatch):
    import pytest
    import watcher.registry as registry
    from watcher.evidence import Evidence
    from rdo.orchestrator import _active_experiments

    def unavailable(_path):
        return Evidence("experiment_registry", None, "cloud", "unknown", "fixture",
                        modifier="unverified")
    monkeypatch.setattr(registry, "ingest_registry", unavailable)
    with pytest.raises(RuntimeError, match="registry unavailable"):
        _active_experiments(str(tmp_path))

    def unreadable(_path):
        raise PermissionError("registry unreadable")
    monkeypatch.setattr(registry, "ingest_registry", unreadable)
    with pytest.raises(PermissionError):
        _active_experiments(str(tmp_path))

def test_cycle_store_preserves_evidence_refs_without_promoting_kind(tmp_path):
    from rdo.model import NATIVE_PLANNING
    from rdo.memory import metrics_series

    cycle = CycleRecord(
        id="evidence-metadata", objective="record evidence references",
        kind=NATIVE_PLANNING,
        verification={
            "source_ref": "tests/test_example.py",
            "artifact_ref": "ci-artifact:run-123",
            "tested_commit": "abc123",
            "observed_result": {"tests": 2, "passed": 2},
        },
    )
    store = CycleStore(str(tmp_path / "cycles"))
    store.save(cycle)
    loaded = store.load(cycle.id)
    assert loaded.verification["source_ref"] == "tests/test_example.py"
    assert loaded.verification["artifact_ref"] == "ci-artifact:run-123"
    assert loaded.verification["tested_commit"] == "abc123"
    assert loaded.verification["observed_result"] == {"tests": 2, "passed": 2}
    metrics = metrics_series([loaded])
    assert metrics["efficiency_eligible_cycles"] == 0
    assert metrics["comparability"]["efficiency_comparison_pool"] == []

