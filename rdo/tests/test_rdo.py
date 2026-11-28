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
                     recon_semantic_verified=True,
                     recon_semantic_review_evidence=["manual review: obligation scope checked"])
    src = Obligation("feature", "feature", "consumer")
    obs = {"db": tgt, "feature": src}
    rels = [Relationship("feature", "db", "depends_on")]
    pruned = prune_false_dependencies(obs, rels)
    assert pruned and rels[0].kind == "reuses"                  # reclassified, not net-new


# ---- feedback cycle detected at system level ----

def test_feedback_cycle_detected():
    obs = {"a": Obligation("a", "a", "consumer"), "b": Obligation("b", "b", "consumer")}
    rels = [Relationship("a", "b", "depends_on"), Relationship("b", "a", "influences")]
    sys_t = assess_system(obs, rels)
    assessment = next(t for t in sys_t if t.subject == "feedback_cycles")
    assert assessment.dimensions["classified_cycles"][0]["classification"] == "feedback_loop"
    loop = assessment.dimensions["feedback_loop_assessments"][0]
    assert loop["members"] == ["a", "b"]
    assert loop["relationships"] == ["a:depends_on:b", "b:influences:a"]
    assert loop["stability_state"] == "unknown"
    assert loop["assessment_status"] == "unknown"
    assert loop["gain"]["value"] is None
    assert loop["recovery"]["value"] is None


# ---- over-expansion controlled: reuse stops expansion; max_depth bounds ----

def test_over_expansion_stopped_by_reuse():
    seeds = [Obligation("store", "store", "persistence")]
    def reviewed_reuse(ob):
        ob.recon_evidence = ["store.py:1"]
        ob.confidence = "measured"
        ob.recon_semantic_verified = True
        ob.recon_semantic_review_evidence = ["manual review: persistence contract checked"]
        return REUSE_EXISTING
    obs, _, frontier = expand(seeds, reconcile_fn=reviewed_reuse, max_depth=4)
    assert set(obs) == {"store"}                                 # not expanded
    assert any("semantic satisfaction independently reviewed" in f["reason"] for f in frontier)


def test_cycle_summary_reports_semantically_reviewed_reuse(monkeypatch):
    from rdo import orchestrator as orch

    def reviewed_reuse(ob):
        ob.recon_evidence = ["store.py:1"]
        ob.confidence = "measured"
        ob.recon_semantic_verified = True
        ob.recon_semantic_review_evidence = ["manual review: storage contract checked"]
        return REUSE_EXISTING

    monkeypatch.setattr(
        orch.recon_mod, "make_reconciler",
        lambda _repo_dir, _signatures: reviewed_reuse,
    )
    cycle, summary = orch.run_cycle(
        "reviewed-reuse", "reviewed reuse summary", [],
        [Obligation("store", "store", "persistence")], signatures={},
    )

    assert cycle.reused == ["store"]
    assert summary["rejected_or_deferred"] == ["store"]

def test_prepopulated_reuse_seed_is_freshly_reconciled_before_stopping():
    stale = Obligation(
        "stale-seed", "stale reviewed seed", "persistence",
        recon_status=REUSE_EXISTING,
        recon_evidence=["old-source.py:12"],
        confidence="measured",
        recon_semantic_verified=True,
        recon_semantic_review_evidence=["old review from a previous source state"],
    )
    observed = []

    def fresh_scan(ob):
        observed.append((ob.recon_evidence[:], ob.recon_semantic_verified,
                         ob.recon_semantic_review_evidence[:]))
        return SIGNATURE_MATCHED

    obligations, _, frontier = expand([stale], reconcile_fn=fresh_scan, max_depth=1)
    assert observed and observed[0] == ([], False, [])
    assert stale.recon_status == SIGNATURE_MATCHED
    assert "stale-seed.schema" in obligations
    assert any("semantic satisfaction unreviewed" in f["reason"] for f in frontier)


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


def test_terminal_kind_records_frontier_stop_reason():
    obs, _, frontier = expand(
        [Obligation("store.schema", "storage schema", "schema")],
        reconcile_fn=lambda _ob: MISSING,
        max_depth=4,
    )
    assert set(obs) == {"store.schema"}
    assert frontier == [{
        "key": "store.schema",
        "reason": "terminal kind 'schema' (leaf; no further decomposition)",
    }]


def test_novel_kind_frontier_exposes_rule_proposal_request_without_auto_expansion():
    from rdo.extrapolator import EXPANSION_RULES, TERMINAL_KINDS, frontier_breakdown

    novel = Obligation(
        "deployment.specialized",
        "specialized deployment mechanism",
        "specialized_deployment",
        rationale="A deployment-specific mechanism is required.",
        evidence_needs=["Demonstrate the deployment environment and constraints."],
    )
    obligations, relationships, frontier = expand(
        [novel], reconcile_fn=lambda _ob: MISSING, max_depth=4
    )

    assert set(obligations) == {novel.key}
    assert relationships == []
    assert len(frontier) == 1
    item = frontier[0]
    assert item["reason"] == "no expansion rule for kind 'specialized_deployment'"
    assert item["frontier_type"] == "novel_kind_requires_rule_proposal"
    request = item["rule_proposal_request"]
    assert request["schema_version"] == 1
    assert request["target_kind"] == novel.kind
    assert request["source_obligation"] == novel.to_dict()
    assert request["known_rule_kinds"] == sorted(EXPANSION_RULES)
    assert request["terminal_kinds"] == sorted(TERMINAL_KINDS)
    assert request["activation_policy"] == "candidate_only_until_explicit_review"
    assert "disconfirming_cases" in request["proposal_requirements"]
    assert "positive_and_negative_tests" in request["proposal_requirements"]
    assert frontier_breakdown(frontier)["deferred"] == 1




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
                             recon_semantic_verified=True,
                             recon_semantic_review_evidence=["manual review: persistence contract checked"]),
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

@pytest.mark.parametrize(
    "confidence, expected",
    [(-0.25, 0.0), (0, 0.0), (0.45, 0.45), (0.9, 0.9), (1.0, 0.9), (25, 0.9)],
)
def test_pattern_memory_confidence_is_bounded_on_insert(tmp_path, confidence, expected):
    mem = PatternMemory(str(tmp_path / "patterns.jsonl"))
    pattern = mem.add(Pattern("bounded", "statement", "cycle:one",
                              confidence=confidence))
    assert pattern.confidence == expected
    assert PatternMemory(str(tmp_path / "patterns.jsonl")).patterns()[0].confidence == expected


@pytest.mark.parametrize(
    "confidence",
    [float("nan"), float("inf"), float("-inf"), "0.4", True, None],
)
def test_pattern_memory_rejects_invalid_confidence_on_insert(tmp_path, confidence):
    mem = PatternMemory(str(tmp_path / "patterns.jsonl"))
    with pytest.raises(ValueError, match="pattern confidence must be a finite number"):
        mem.add(Pattern("invalid", "statement", "cycle:one", confidence=confidence))
    assert mem.patterns() == []


def test_pattern_memory_rejects_aliased_non_finite_confidence_before_replay_mutation(tmp_path):
    path = tmp_path / "patterns.jsonl"
    mem = PatternMemory(str(path))
    mem.add(Pattern("aliased", "statement", "cycle:one", confidence=0.3))
    stored = mem.patterns()[0]
    stored.confidence = float("nan")
    before = path.read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="pattern confidence must be a finite number"):
        mem.add(Pattern("aliased", "statement", "cycle:one", confidence=0.3,
                        exceptions=["new exception"]))

    assert stored.confidence != stored.confidence  # remains the caller-injected NaN
    assert stored.exceptions == []
    assert path.read_text(encoding="utf-8") == before


def test_pattern_memory_rejects_aliased_non_finite_confidence_before_corroboration_mutation(tmp_path):
    path = tmp_path / "patterns.jsonl"
    mem = PatternMemory(str(path))
    mem.add(Pattern("aliased", "statement", "cycle:one", confidence=0.3))
    stored = mem.patterns()[0]
    stored.confidence = float("nan")
    before = (stored.provenance, stored.observed_count, list(stored.exceptions))
    persisted_before = path.read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="pattern confidence must be a finite number"):
        mem.add(Pattern("aliased", "statement", "cycle:two", confidence=0.3))

    assert (stored.provenance, stored.observed_count, stored.exceptions) == before
    assert path.read_text(encoding="utf-8") == persisted_before


def test_pattern_memory_applicable_alias_cannot_persist_non_finite_confidence(tmp_path):
    path = tmp_path / "patterns.jsonl"
    mem = PatternMemory(str(path))
    mem.add(Pattern("aliased", "statement", "cycle:one",
                    applicability="robotics", confidence=0.3))
    mem.applicable("robotics")[0].confidence = float("nan")

    with pytest.raises(ValueError, match="pattern confidence must be a finite number"):
        mem.add(Pattern("aliased", "statement", "cycle:one", confidence=0.3,
                        exceptions=["new exception"]))

    assert len(path.read_text(encoding="utf-8").splitlines()) == 1


def test_pattern_memory_clamps_finite_out_of_range_alias_before_replay_persistence(tmp_path):
    path = tmp_path / "patterns.jsonl"
    mem = PatternMemory(str(path))
    mem.add(Pattern("aliased", "statement", "cycle:one", confidence=0.3))
    mem.applicable("robotics")  # getter is also covered by the alias-boundary tests
    mem.patterns()[0].confidence = 4.2

    replayed = mem.add(Pattern("aliased", "statement", "cycle:one", confidence=0.3,
                               exceptions=["new exception"]))

    assert replayed.confidence == 0.9
    reopened = PatternMemory(str(path)).patterns()[0]
    assert reopened.confidence == 0.9
    assert reopened.exceptions == ["new exception"]


def test_pattern_memory_persists_alias_normalization_on_idempotent_replay(tmp_path):
    path = tmp_path / "patterns.jsonl"
    mem = PatternMemory(str(path))
    mem.add(Pattern("aliased", "statement", "cycle:one", confidence=0.3))
    stored = mem.patterns()[0]
    stored.confidence = 4.2

    replayed = mem.add(Pattern("aliased", "statement", "cycle:one", confidence=0.3))

    assert replayed.confidence == 0.9
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    reopened = PatternMemory(str(path)).patterns()[0]
    assert reopened.confidence == 0.9
    assert reopened.provenance == "cycle:one"
    assert reopened.observed_count == 1
    assert reopened.exceptions == []


def test_pattern_memory_append_rejects_aliased_non_finite_confidence(tmp_path):
    mem = PatternMemory(str(tmp_path / "patterns.jsonl"))
    invalid = Pattern("invalid", "statement", "cycle:one", confidence=float("nan"))
    with pytest.raises(ValueError, match="pattern confidence must be a finite number"):
        mem._append(invalid)
    assert not (tmp_path / "patterns.jsonl").exists()


def test_pattern_memory_normalizes_finite_legacy_confidence_on_load(tmp_path):
    path = tmp_path / "patterns.jsonl"
    path.write_text(
        '{"key":"low","statement":"s","provenance":"cycle:1","confidence":-0.2}\n'
        '{"key":"high","statement":"s","provenance":"cycle:2","confidence":1.2}\n',
        encoding="utf-8",
    )
    patterns = {p.key: p for p in PatternMemory(str(path)).patterns()}
    assert patterns["low"].confidence == 0.0
    assert patterns["high"].confidence == 0.9


def test_pattern_memory_rejects_non_finite_legacy_confidence_on_load(tmp_path):
    path = tmp_path / "patterns.jsonl"
    path.write_text(
        '{"key":"bad","statement":"s","provenance":"cycle:1","confidence":NaN}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="pattern confidence must be a finite number"):
        PatternMemory(str(path))




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


def test_cycle_metrics_reject_malformed_effort_and_zero_obligation_denominator():
    from rdo.memory import cycle_metrics, metrics_series

    empty = CycleRecord("empty", "empty objective", obligations=[])
    metrics = cycle_metrics(empty)
    assert metrics["obligations_discovered"] == 0
    assert metrics["duplicate_discovery_rate"] is None
    assert metrics["reconciliation_status_coverage"] is None

    with pytest.raises(ValueError):
        CycleRecord("bad-kind", "bad", kind="executed-ish")
    with pytest.raises(ValueError):
        record_actual(empty, {"missed": [], "unnecessary": [],
                              "reuse_wrong": [], "regressions": [],
                              "effort_actual": True})
    with pytest.raises(ValueError):
        record_actual(empty, {"missed": "none"})

    malformed = CycleRecord(
        "malformed-effort", "test", kind="executed_verified",
        actual={"missed": [], "unnecessary": [], "reuse_wrong": [],
                "regressions": [], "effort_actual": "seven"},
    )
    assert compare(malformed)["effort_error"] is None
    series = metrics_series([malformed])
    assert series["efficiency_eligible_cycles"] == 0
    assert series["comparability"]["efficiency_comparison_pool"] == []

    bad_counts = CycleRecord(
        "bad-counts", "test", obligations=[],
        verification={"signature_matches": True,
                      "signature_matches_backed_by_file_evidence": 1},
    )
    assert cycle_metrics(bad_counts)["signature_matches"] is None


def test_recognize_sufficiency_restrains_development():
    # The prioritiser must also fail closed when called directly, outside expand().
    unsupported = Obligation("unsupported", "unsupported reuse", "persistence",
                              recon_status=REUSE_EXISTING)
    direct_packages = build_work_packages({"unsupported": unsupported}, [])
    assert direct_packages and "unsupported" in direct_packages[0].obligation_keys

    obs = {"built": Obligation("built", "b", "persistence", recon_status=REUSE_EXISTING,
                               recon_evidence=["src.py:1"], confidence="measured",
                               recon_semantic_verified=True,
                               recon_semantic_review_evidence=["manual review: source and test reviewed"]),
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
    from rdo.report import demo_genius_tagger
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
    from rdo.report import run_catalogue
    res = run_catalogue(repo_dir=".", workdir=str(tmp_path / "cycles"))
    cycles = res["cycles"]
    assert len(cycles) == 4  # genius + defect + affinity + config invariant
    defect = cycles["migration_defect (defect-remediation pattern)"]
    # Source signatures are source anchors, not semantic reuse approval.
    assert any("fix" in r for r in defect["2_signature_matches_located"])
    regression_keys = [key for key in defect["1_discovered"]["obligations"]
                       if "regression_test" in key]
    assert regression_keys
    packages = defect["4_recommended_work"]
    signature_matches = set(defect["2_signature_matches_located"])
    packaged = {key for package in packages for key in package["obligations"]}
    evidence = {item["key"]: item for item in defect["reconciliation_evidence"]}
    expected_test_paths = {
        "beliefs_content_uniq.regression_test": "tests/test_beliefs_content_dedup.py",
        "arc_closers_migration.regression_test": "tests/test_arc_closers_migration.py",
    }
    for key in regression_keys:
        assert key in signature_matches
        assert key in packaged  # review work remains visible, not silently treated as done
        item = evidence[key]
        assert item["status"] == "signature_matched"
        assert any(expected_test_paths[key] in ref for ref in item["evidence"])
    assert any(package["eligibility"] == "blocked" and package["blockers"]
               for package in packages)

    # Four executed records are present, but only like-for-like migration guards
    # belong in the genuinely comparable efficiency group.
    assert len(res["executed_cycles"]) == 4
    metrics = res["learning_metrics"]
    assert len(metrics["per_cycle"]) == 9 and len(metrics["measures"]) == 8
    assert metrics["completed_executed_cycles"] == 4
    assert metrics["largest_comparable_group"] == 2
    assert set(metrics["comparability"]["efficiency_comparison_pool"]) == {
        "arc_closers_regtest_2026-11", "affinity_regtest_2026-11"}
    groups = metrics["comparability"]["genuinely_comparable_by_engineering_pattern"]
    assert set(groups.get("migration_guard", [])) == {
        "arc_closers_regtest_2026-11", "affinity_regtest_2026-11"}
    assert "invariant_guard" in groups and "refactor" in groups
    assert res["comparability_assessment"]["largest_genuinely_comparable_group"] == 2
    assert "watcher_2026-11" in metrics["comparability"]["excluded_from_efficiency"]["imported_retrospective"]

    transfer = res["cross_cycle_transfer"]
    assert len(transfer["executed_cycles"]) == 4
    assert "not proof" in transfer["observation"].lower()
    matched = {row["cycle"]: row["prediction_matched"] for row in transfer["executed_cycles"]}
    assert matched["arc_closers_regtest_2026-11"] is False
    assert matched["affinity_regtest_2026-11"] is True
    assert matched["config_invariant_2026-11"] is True
    assert set(res["change_categories"]) >= {
        "general_engine_logic", "pattern_taxonomy", "domain_knowledge", "recorded_experience"
    }


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



def test_orchestrator_is_domain_free():
    """The generic cycle driver contains no domain-specific code."""
    import ast
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "orchestrator.py"), encoding="utf-8") as handle:
        tree = ast.parse(handle.read())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                node.body = body[1:] or [ast.Pass()]
    code = ast.unparse(tree).lower()
    forbidden = ["genius", "migration", "config_invariant", "affinity",
                 "assess_signal_authority", "quality_synthesis", "tagger"]
    assert [token for token in forbidden if token in code] == []

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


def test_historical_execution_records_carry_exact_ci_provenance(tmp_path):
    from rdo.report import record_arc_closers_execution, record_affinity_execution
    from rdo.memory import CycleStore, PatternMemory

    store = CycleStore(str(tmp_path / "cycles"))
    memory = PatternMemory(str(tmp_path / "patterns.jsonl"))
    expected = {
        "source_commit": "c352f6a83bec2136d5eff518deb210fc3cd4b3a2",
        "workflow": "tests",
        "workflow_run_id": 44855260626,
        "workflow_run_number": 182,
        "job_id": 136695850460,
        "conclusion": "success",
        "suite_result": {
            "passed": 2219,
            "skipped": 7,
            "subtests_passed": 40,
        },
    }

    cycles = [
        record_arc_closers_execution(store, memory),
        record_affinity_execution(store, memory),
    ]
    assert {cycle.id for cycle in cycles} == {
        "arc_closers_regtest_2026-11",
        "affinity_regtest_2026-11",
    }
    for cycle in cycles:
        assert cycle.verification["ci_evidence"] == expected
        assert store.load(cycle.id).verification["ci_evidence"] == expected


# ---- the RDO subjected to its own Optimal Functional Tension ----

def test_rdo_self_assessment_lean_and_independent():
    from rdo.report import self_assess
    r = self_assess()
    assert r["independence_no_nex_import"] is True
    assert r["reuses_watcher_infrastructure"] is True
    assert r["module_count"] <= 14  # core reasoning modules
    assert r["evidence_model_count"] == 3
    assert "operating_envelope.py" in r["evidence_models"]
    assert "feedback_loop.py" in r["evidence_models"]
    assert "failure_evidence.py" in r["evidence_models"]
    assert r["boundary_adapter_count"] == 2
    assert r["total_module_count"] == (
        r["module_count"] + r["evidence_model_count"] + r["boundary_adapter_count"]
    )
    assert "objective_intake.py" in r["boundary_adapters"]
    assert "handoff.py" in r["boundary_adapters"]
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
                              recon_semantic_verified=True,
                              recon_semantic_review_evidence=["old manual review"])
    assert recon.reconcile(stale_review, str(tmp_path),
                           [Signature("not_present_now")]) == MISSING
    assert stale_review.recon_semantic_verified is False
    assert stale_review.recon_semantic_review_evidence == []
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
                          recon_semantic_verified=True,
                          recon_semantic_review_evidence=["manual review: full obligation verified"])
    readiness = next(t for t in assess_system({"reviewed": reviewed}, [])
                     if t.subject == "integration_readiness")
    assert readiness.verdict == SUFFICIENT
    flag_only = Obligation("flag_only", "flag only", "test", recon_status=REUSE_EXISTING,
                           recon_evidence=["src.py:12"], confidence="measured",
                           recon_semantic_verified=True)
    readiness = next(t for t in assess_system({"flag_only": flag_only}, [])
                     if t.subject == "integration_readiness")
    assert readiness.verdict == TENSION_UNKNOWN

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
        assert eligibility(target, obs, rels, active_experiments=[])["eligibility"] == "eligible"
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
    import rdo.orchestrator as driver
    from rdo.report import record_arc_closers_execution
    calls = []
    monkeypatch.setattr(driver, "derive_lessons", lambda c, d: calls.append(c.id) or [])
    record_arc_closers_execution(CycleStore(str(tmp_path / "cycles")),
                                 PatternMemory(str(tmp_path / "patterns.jsonl")))
    assert calls == ["arc_closers_regtest_2026-11"]


def test_catalogue_replay_does_not_inflate_learning_counts(tmp_path):
    from rdo.report import run_catalogue
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
    # Historical reuse claims are not a substitute for explicit signature counts.
    legacy = CycleRecord(id="legacy", objective="o", reused=["old_reuse_claim"],
                         verification={"all_reuse_backed": True})
    legacy_metrics = cycle_metrics(legacy)
    assert legacy_metrics["signature_matches"] is None
    assert legacy_metrics["signature_evidence_coverage"] is None
    assert legacy_metrics["signature_evidence_coverage_complete"] is None
    assert cycle_metrics(empty_actual)["engineering_effort"] is None
    assert cycle_metrics(empty_actual)["predicted_effort"] == 8
    assert cycle_metrics(recorded)["engineering_effort"] == 4
    series = metrics_series([pending, empty_actual, recorded])
    assert set(series["measure_keys"]) == set(series["denominators"])
    assert len(series["measure_keys"]) == 8


def test_metrics_fail_closed_on_malformed_legacy_signature_match_containers():
    from rdo.memory import cycle_metrics

    malformed = ("signature", 3, {"match": "x"}, ["valid", 3], [None], ["  "])
    for value in malformed:
        cycle = CycleRecord(id="malformed", objective="o", signature_matches=value)
        metrics = cycle_metrics(cycle)
        assert metrics["signature_matches"] is None
        assert metrics["signature_evidence_coverage"] is None
        assert metrics["signature_evidence_coverage_complete"] is None

    valid = CycleRecord(id="valid-legacy", objective="o",
                        signature_matches=["src/a.py:1", "src/b.py:2"])
    assert cycle_metrics(valid)["signature_matches"] == 2


def test_reconciliation_coverage_excludes_unreviewed_reuse_consistently():
    from rdo.memory import cycle_metrics
    from rdo.reconcile import summarize

    invalid = Obligation("unreviewed", "unreviewed reuse", "test",
                         recon_status=REUSE_EXISTING)
    invalid_summary = summarize({invalid.key: invalid})
    invalid_cycle = CycleRecord(
        id="invalid-reuse-coverage", objective="o",
        obligations=[invalid.to_dict()],
    )
    invalid_metrics = cycle_metrics(invalid_cycle)
    assert invalid_summary[RECON_UNKNOWN] == ["unreviewed"]
    assert invalid_metrics["reconciliation_status_coverage"] == 0.0

    reviewed = Obligation(
        "reviewed", "reviewed reuse", "test", recon_status=REUSE_EXISTING,
        recon_evidence=["src/reuse.py:12"], confidence="measured",
        recon_semantic_verified=True,
        recon_semantic_review_evidence=["manual review: obligation satisfied"],
    )
    reviewed_summary = summarize({reviewed.key: reviewed})
    reviewed_cycle = CycleRecord(
        id="reviewed-reuse-coverage", objective="o",
        obligations=[reviewed.to_dict()],
    )
    reviewed_metrics = cycle_metrics(reviewed_cycle)
    assert reviewed_summary[REUSE_EXISTING] == ["reviewed"]
    assert reviewed_metrics["reconciliation_status_coverage"] == 1.0


def test_reuse_review_requires_nonblank_text_evidence_across_consumers():
    from rdo.memory import cycle_metrics
    from rdo.model import has_valid_reuse_review
    from rdo.prioritise import priority_dimensions
    from rdo.reconcile import summarize
    from rdo.tension import (TENSION_UNKNOWN, assess_node, assess_relationship,
                             assess_system, recognize_sufficiency)

    def reviewed_obligation(key="reuse"):
        return Obligation(
            key, key, "persistence", recon_status=REUSE_EXISTING,
            recon_evidence=["src/mechanism.py:12"], confidence="measured",
            recon_semantic_verified=True,
            recon_semantic_review_evidence=["manual review: obligation satisfied"],
        )

    valid = reviewed_obligation()
    assert has_valid_reuse_review(valid)
    assert has_valid_reuse_review(valid.to_dict())

    malformed_fields = (
        ("recon_evidence", []),
        ("recon_evidence", [""]),
        ("recon_evidence", ["   "]),
        ("recon_evidence", [None]),
        ("recon_evidence", [7]),
        ("recon_evidence", [object()]),
        ("recon_evidence", ["src/mechanism.py:12", None]),
        ("recon_semantic_review_evidence", []),
        ("recon_semantic_review_evidence", [""]),
        ("recon_semantic_review_evidence", ["   "]),
        ("recon_semantic_review_evidence", [None]),
        ("recon_semantic_review_evidence", ["manual review", ""]),
        ("recon_semantic_review_evidence", ["manual review", None]),
        ("recon_semantic_verified", 1),
        ("recon_semantic_verified", "true"),
    )
    for field, malformed in malformed_fields:
        candidate = reviewed_obligation(field)
        setattr(candidate, field, malformed)
        assert not has_valid_reuse_review(candidate), (field, malformed)
        assert not has_valid_reuse_review(candidate.to_dict()), (field, malformed)

    # Every consumer must treat malformed review data as unreviewed.
    invalid = reviewed_obligation("invalid")
    invalid.recon_semantic_review_evidence = ["   "]
    assert summarize({invalid.key: invalid})[RECON_UNKNOWN] == ["invalid"]

    cycle = CycleRecord(id="malformed-reuse", objective="o",
                        obligations=[invalid.to_dict()])
    assert cycle_metrics(cycle)["reconciliation_status_coverage"] == 0.0
    assert priority_dimensions(invalid, {})["readiness_to_build"] > 0.0
    assert assess_node(invalid).verdict == TENSION_UNKNOWN
    assert recognize_sufficiency({invalid.key: invalid}) == []

    rel = Relationship("consumer", invalid.key, "depends_on")
    assert assess_relationship(rel, {invalid.key: invalid}).verdict == TENSION_UNKNOWN
    readiness = next(item for item in assess_system({invalid.key: invalid}, [])
                     if item.subject == "integration_readiness")
    assert readiness.verdict == TENSION_UNKNOWN

    unpruned = Relationship("consumer", invalid.key, "depends_on")
    assert prune_false_dependencies({invalid.key: invalid}, [unpruned]) == []
    assert unpruned.kind == "depends_on"

    def malformed_review_callback(ob):
        ob.recon_evidence = ["src/mechanism.py:12"]
        ob.confidence = "measured"
        ob.recon_semantic_verified = True
        ob.recon_semantic_review_evidence = ["   "]
        return REUSE_EXISTING

    expanded, _, frontier = expand(
        [Obligation("root", "root", "persistence")],
        reconcile_fn=malformed_review_callback,
        max_depth=1,
    )
    assert "root.schema" in expanded
    assert any(item["reason"] == "reuse status lacks semantic-review evidence; "
               "expanded conservatively" for item in frontier)


def test_signature_evidence_coverage_rejects_inconsistent_counts():
    from rdo.memory import cycle_metrics

    over_counted = CycleRecord(
        id="over-counted", objective="o",
        verification={
            "signature_matches": 2,
            "signature_matches_backed_by_file_evidence": 3,
            "all_signature_matches_have_file_evidence": True,
        },
    )
    metrics = cycle_metrics(over_counted)
    assert metrics["signature_matches"] == 2
    assert metrics["signature_evidence_coverage"] is None
    assert metrics["signature_evidence_coverage_complete"] is None

    consistent = CycleRecord(
        id="consistent", objective="o",
        verification={
            "signature_matches": 2,
            "signature_matches_backed_by_file_evidence": 2,
            "all_signature_matches_have_file_evidence": True,
        },
    )
    assert cycle_metrics(consistent)["signature_evidence_coverage"] == 1.0
    assert cycle_metrics(consistent)["signature_evidence_coverage_complete"] is True


def test_extreme_integer_effort_is_rejected_without_crashing_metrics():
    import pytest
    from rdo.memory import compare, cycle_metrics, record_actual

    huge = 10 ** 10000
    cycle = CycleRecord(
        id="huge-effort", objective="o", predicted={"effort": huge},
        actual={
            "effort_actual": huge,
            "missed": [],
            "unnecessary": [],
            "reuse_wrong": [],
            "regressions": [],
        },
    )
    assert compare(cycle)["effort_predicted"] is None
    assert compare(cycle)["effort_actual"] is None
    metrics = cycle_metrics(cycle)
    assert metrics["engineering_effort"] is None
    assert metrics["predicted_effort"] is None
    assert metrics["prediction_error_effort"] is None

    with pytest.raises(ValueError, match="finite, non-negative"):
        record_actual(CycleRecord(id="record", objective="o"),
                      {"effort_actual": huge})


def test_active_experiment_registry_empty_is_distinct_from_unavailable(tmp_path):
    from rdo.orchestrator import _active_experiments
    empty = tmp_path / "observation_reports"
    empty.mkdir()
    assert _active_experiments(str(tmp_path)) == []
    empty.rmdir()
    assert _active_experiments(str(tmp_path)) is None



def test_unverified_experiment_registry_blocks_direct_eligibility():
    ob = Obligation("docs", "documentation-only change", "documentation")
    unknown = eligibility(ob, {}, [], active_experiments=None)
    verified_empty = eligibility(ob, {}, [], active_experiments=[])
    assert unknown["eligibility"] == "blocked"
    assert any("registry unavailable or unverified" in item for item in unknown["blockers"])
    assert verified_empty == {"eligibility": "eligible", "blockers": []}


def test_active_experiment_registry_rejects_malformed_payload(tmp_path, monkeypatch):
    import watcher.registry as registry
    from watcher.evidence import Evidence
    from rdo.orchestrator import _active_experiments

    malformed = [
        {"active_or_pending": "r77"},
        {"active_or_pending": ["r77", 7]},
        {"active_or_pending": ["   "]},
        {"reported": []},
    ]
    for data in malformed:
        monkeypatch.setattr(
            registry,
            "ingest_registry",
            lambda _path, data=data: Evidence(
                "experiment_registry", data, "cloud", "measured", "fixture"
            ),
        )
        assert _active_experiments(str(tmp_path)) is None

def test_reconciliation_ignores_its_own_cycle_artifacts(tmp_path):
    import rdo.reconcile as recon

    cycle_dir = tmp_path / "rdo" / ".cycles"
    cycle_dir.mkdir(parents=True)
    (cycle_dir / "prior-cycle.json").write_text(
        '{"source_signature": "def required_mechanism"}', encoding="utf-8"
    )

    # RDO cycle JSON is generated evidence, not source implementation. It must
    # never satisfy an unscoped source signature on a later planning cycle.
    assert recon._grep(r"def required_mechanism", str(tmp_path), None) == []


def test_grep_handles_non_utf8_text_without_crashing(tmp_path):
    import rdo.reconcile as recon

    source = tmp_path / "legacy.txt"
    source.write_bytes(b"signature\xff-anchor\n")
    result = recon._grep("signature", str(tmp_path), None)
    assert result is not None
    assert len(result) == 1
    assert result[0].startswith("legacy.txt:1:signature")
    assert "\ufffd" in result[0]

    # The byte-oriented locale must not disable -I's binary-file exclusion.
    binary_dir = tmp_path / "binary-only"
    binary_dir.mkdir()
    (binary_dir / "payload.bin").write_bytes(b"signature\x00-anchor\n")
    assert recon._grep("signature", str(binary_dir), None) == []


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
    assert _active_experiments(str(tmp_path)) is None

    def unreadable(_path):
        raise PermissionError("registry unreadable")
    monkeypatch.setattr(registry, "ingest_registry", unreadable)
    assert _active_experiments(str(tmp_path)) is None

def test_cycle_store_rejects_unsafe_cycle_ids_before_file_access(tmp_path):
    store = CycleStore(str(tmp_path / "cycles"))
    unsafe_ids = [
        "",
        ".",
        "..",
        "../escape",
        "../../../../tmp/escape",
        "/absolute/path",
        r"..\\escape",
        "bad\x00id",
        "x" * 129,
    ]

    for cycle_id in unsafe_ids:
        with pytest.raises(ValueError, match="cycle id"):
            store.save(CycleRecord(id=cycle_id, objective="unsafe id"))
        with pytest.raises(ValueError, match="cycle id"):
            store.load(cycle_id)

    assert not (tmp_path / "escape.json").exists()


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



def test_pattern_memory_new_add_does_not_publish_when_append_fails(tmp_path, monkeypatch):
    path = tmp_path / "patterns.jsonl"
    memory = PatternMemory(str(path))

    def fail_append(_pattern):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(memory, "_append", fail_append)
    with pytest.raises(OSError, match="simulated disk failure"):
        memory.add(Pattern("new", "statement", "cycle:new"))

    assert memory.patterns() == []
    assert not path.exists()


def test_pattern_memory_corroboration_does_not_mutate_existing_alias_when_append_fails(tmp_path, monkeypatch):
    path = tmp_path / "patterns.jsonl"
    memory = PatternMemory(str(path))
    stored = memory.add(Pattern("existing", "statement", "cycle:one"))
    before = stored.to_dict()
    persisted_before = path.read_text(encoding="utf-8")

    def fail_append(_pattern):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(memory, "_append", fail_append)
    with pytest.raises(OSError, match="simulated disk failure"):
        memory.add(Pattern("existing", "statement", "cycle:two"))

    assert stored.to_dict() == before
    assert memory.patterns()[0] is stored
    assert path.read_text(encoding="utf-8") == persisted_before


def test_pattern_memory_refutation_does_not_mutate_existing_alias_when_append_fails(tmp_path, monkeypatch):
    path = tmp_path / "patterns.jsonl"
    memory = PatternMemory(str(path))
    stored = memory.add(Pattern("existing", "statement", "cycle:one"))
    before = stored.to_dict()
    persisted_before = path.read_text(encoding="utf-8")

    def fail_append(_pattern):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(memory, "_append", fail_append)
    with pytest.raises(OSError, match="simulated disk failure"):
        memory.refute("existing", "counterexample:1")

    assert stored.to_dict() == before
    assert memory.patterns()[0] is stored
    assert path.read_text(encoding="utf-8") == persisted_before


def test_cycle_store_atomic_replace_preserves_previous_cycle_on_failure(tmp_path, monkeypatch):
    store_dir = tmp_path / "cycles"
    store = CycleStore(str(store_dir))
    original = CycleRecord(id="atomic-cycle", objective="original objective")
    path = store.save(original)
    with open(path, "rb") as fh:
        original_bytes = fh.read()

    def fail_replace(_source, _destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    replacement = CycleRecord(id="atomic-cycle", objective="replacement objective")
    with pytest.raises(OSError, match="simulated replace failure"):
        store.save(replacement)

    with open(path, "rb") as fh:
        assert fh.read() == original_bytes
    assert store.load("atomic-cycle").objective == "original objective"
    assert list(store_dir.glob(".cycle_atomic-cycle.*.tmp")) == []
