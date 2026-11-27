"""Objective-context contract tests for the external RDO planning cycle."""

from rdo.model import NECESSARY, Obligation
from rdo.orchestrator import run_cycle


def _run(tmp_path, objective_context=None):
    seed = Obligation(
        "feature",
        "bounded feature",
        "persistence",
        classification=NECESSARY,
    )
    return run_cycle(
        "context-test",
        "implement a bounded feature",
        [],
        [seed],
        {},
        repo_dir=str(tmp_path),
        active_experiments=[],
        authorised_gates=set(),
        max_depth=0,
        objective_context=objective_context,
    )


def test_objective_context_is_preserved_and_unmapped_items_block_readiness(tmp_path):
    context = {
        "intent": "Prepare an auditable RDO plan",
        "owner": "founder",
        "source": {"kind": "human", "reference": "test-fixture"},
        "scope": {
            "in_scope": ["RDO planning only"],
            "affected_paths": ["rdo/orchestrator.py"],
        },
        "assumptions": ["Repository snapshot is the current HEAD"],
        "constraints": ["Do not change NEX runtime behaviour"],
        "exclusions": ["Do not activate feature flags"],
        "acceptance_criteria": ["Every declared context item is mapped to evidence"],
    }

    cycle, summary = _run(tmp_path, context)

    assert cycle.objective_context == context
    assessment = cycle.context_assessment
    assert assessment["status"] == "unmapped"
    assert assessment["review_required"] is True
    assert assessment["execution_readiness"] == "blocked"
    assert assessment["handoff_readiness"] == "reviewable"
    assert len(assessment["items"]) == 7
    assert {item["kind"] for item in assessment["items"]} == {
        "intent", "scope", "affected_path", "assumption", "constraint",
        "exclusion", "acceptance_criterion"
    }
    assert all(item["status"] == "unmapped" and item["evidence"] == []
               for item in assessment["items"])

    assert summary["objective_context"] == assessment
    assert cycle.work_packages
    for package in cycle.work_packages:
        # Stage-1 eligibility governs whether a proposal can be prepared for
        # bounded review; objective-context readiness separately blocks execution.
        assert package["eligibility"] == "eligible"
        assert not any("objective context contains unmapped" in blocker
                       for blocker in package["blockers"])
        assert any("Do not activate feature flags" in item
                   for item in package["anti_requirements"])


def test_absent_objective_context_does_not_change_legacy_cycle_readiness(tmp_path):
    cycle, _ = _run(tmp_path)

    assert cycle.objective_context == {}
    assert cycle.context_assessment["status"] == "not_supplied"
    assert cycle.context_assessment["review_required"] is False
    assert cycle.context_assessment["execution_readiness"] == "unknown"
    assert cycle.context_assessment["handoff_readiness"] == "not_applicable"
    assert cycle.work_packages
    assert all(package["eligibility"] == "eligible"
               for package in cycle.work_packages)
