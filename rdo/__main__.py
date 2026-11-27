"""RDO CLI — `python -m rdo ...`.

Planning and handoff commands write RDO-owned cycle/evidence artifacts but do not
write NEX runtime state. The legacy `stage7` command runs its fixed test in a
temporary fixture; `handoff-verify` is source/path-only and never runs tests.

  python -m rdo run-demo [--repo .] [--out rdo/.cycles]
        run the full cycle on the real genius-tagger objective; print the six
        demonstration outputs as JSON.

  python -m rdo influence [--repo .] [--signal genius] [--subtree theory_x]
        audit how many subsystems consume a signal (capability != authority).

  python -m rdo failure-propagation --cycle-id <id> --failed-key <key> [--dir rdo/.cycles]
        trace potential dependents via depends_on edges; no runtime propagation is inferred.

  python -m rdo impact --before-cycle-id <id> --after-cycle-id <id> --changed-capability <key> [--dir rdo/.cycles]
        compare adjacent relationship and tension snapshots; differences are not causal attribution.

  python -m rdo patterns [--dir rdo/.cycles]
        print the accumulated Development Pattern Memory.

  python -m rdo handoff-verify --handoff-id <handoff-id> [--repo .] [--out rdo/.cycles]
        invoke independent Watcher source/path verification; no tests or runtime actions.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .knowledge import genius_authority_audit
from .memory import CycleStore, PatternMemory
from .graph import compare_adjacent_relationship_impacts, failure_propagation_candidates
from rdo_adapters.objective_intake import (ObjectiveInputError, load_objective_file,
                                           objective_history, resume_objective,
                                           submit_objective)
from rdo_adapters.handoff import (HandoffError, create_handoff, handoff_history,
                                  record_human_acceptance, record_scope_review,
                                  record_context_mapping, record_acceptance_verification,
                                  verify_with_watcher)
from .report import (demo_genius_tagger, run_catalogue, run_stage2_belief_decay,
                     run_stage3_graph_intelligence, run_stage4_belief_audit,
                     run_stage5_belief_pathway, run_stage6_learning_loop,
                     run_stage7_execution_integration, self_assess)


def _run_demo(args) -> int:
    print(json.dumps(demo_genius_tagger(args.repo, args.out), indent=2, default=str))
    return 0


def _run_all(args) -> int:
    print(json.dumps(run_catalogue(args.repo, args.out), indent=2, default=str))
    return 0


def _influence(args) -> int:
    print(json.dumps(genius_authority_audit(args.repo, args.signal), indent=2, default=str))
    return 0


def _stage2(args) -> int:
    print(json.dumps(run_stage2_belief_decay(args.repo, args.out), indent=2, default=str))
    return 0


def _stage3(args) -> int:
    print(json.dumps(run_stage3_graph_intelligence(args.repo, args.out), indent=2, default=str))
    return 0


def _stage4(args) -> int:
    print(json.dumps(run_stage4_belief_audit(args.repo, args.out), indent=2, default=str))
    return 0


def _stage5(args) -> int:
    print(json.dumps(run_stage5_belief_pathway(args.repo, args.out), indent=2, default=str))
    return 0


def _stage6(args) -> int:
    print(json.dumps(run_stage6_learning_loop(args.repo, args.out), indent=2, default=str))
    return 0


def _stage7(args) -> int:
    print(json.dumps(run_stage7_execution_integration(args.repo, args.out), indent=2, default=str))
    return 0


def _selfcheck(args) -> int:
    print(json.dumps(self_assess(), indent=2, default=str))
    return 0


def _failure_propagation(args) -> int:
    """Read one persisted cycle and report structural dependent candidates."""
    try:
        if not os.path.isdir(args.dir):
            raise FileNotFoundError(f"cycle store directory does not exist: {args.dir}")
        cycle = CycleStore(args.dir).load(args.cycle_id)
        result = failure_propagation_candidates(
            cycle.obligations, cycle.relationships, args.failed_key
        )
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, default=str))
    return 1 if result.get("status") in ("partial", "invalid_input") else 0


def _impact(args) -> int:
    """Compare persisted before/after cycle snapshots around changed capabilities."""
    try:
        if not os.path.isdir(args.dir):
            raise FileNotFoundError(f"cycle store directory does not exist: {args.dir}")
        store = CycleStore(args.dir)
        before = store.load(args.before_cycle_id)
        after = store.load(args.after_cycle_id)
        result = compare_adjacent_relationship_impacts(
            before.to_dict(), after.to_dict(), args.changed_capability
        )
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, default=str))
    return 1 if result.get("status") in ("partial", "invalid_input") else 0


def _patterns(args) -> int:
    mem = PatternMemory(os.path.join(args.dir, "patterns.jsonl"))
    print(json.dumps([p.to_dict() for p in mem.patterns()], indent=2, default=str))
    return 0


def _intake(args) -> int:
    try:
        record = load_objective_file(args.input)
        result = submit_objective(record, repo_dir=args.repo, workdir=args.out)
    except (ObjectiveInputError, OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, default=str))
    return 0


def _history(args) -> int:
    try:
        result = objective_history(args.out, args.objective_id)
    except (ObjectiveInputError, OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, default=str))
    return 0


def _resume(args) -> int:
    try:
        result = resume_objective(args.out, args.objective_id, args.revision)
    except (ObjectiveInputError, OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, default=str))
    return 0

def _handoff_create(args) -> int:
    try:
        result = create_handoff(args.out, args.repo, args.objective_id, args.revision,
                                args.cycle_id, args.work_package)
    except (HandoffError, ObjectiveInputError, OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, default=str))
    return 0


def _handoff_history(args) -> int:
    try:
        result = handoff_history(args.out, args.handoff_id)
    except (HandoffError, OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, default=str))
    return 0


def _handoff_verify(args) -> int:
    try:
        result = verify_with_watcher(args.out, args.repo, args.handoff_id,
                                     timeout_seconds=args.timeout)
    except (HandoffError, OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, default=str))
    return 1 if result.get("exit_status") == "scope_violation" else 0


def _handoff_review(args) -> int:
    try:
        event = record_scope_review(
            args.out, args.handoff_id, args.decision, args.reviewer,
            args.source_reference, permitted_actions=args.permitted_action,
            note=args.note,
        )
    except (HandoffError, OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(event, indent=2, default=str))
    return 0


def _handoff_context_map(args) -> int:
    try:
        event = record_context_mapping(
            args.out, args.handoff_id, args.item_id,
            args.mapped_obligation, args.evidence_reference,
            args.reviewer, args.source_reference, note=args.note,
        )
    except (HandoffError, OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(event, indent=2, default=str))
    return 0


def _handoff_acceptance_verify(args) -> int:
    try:
        event = record_acceptance_verification(
            args.out, args.handoff_id, args.criterion_id, args.status,
            args.verifier, args.source_reference,
            mapped_obligation_keys=args.mapped_obligation,
            verification_method=args.verification_method,
            evidence_references=args.evidence_reference,
            confidence=args.confidence, verified_at=args.verified_at,
            note=args.note,
        )
    except (HandoffError, OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(event, indent=2, default=str))
    return 0


def _handoff_acceptance(args) -> int:
    try:
        with open(args.evidence_references, "r", encoding="utf-8") as fh:
            evidence = json.load(fh)
        event = record_human_acceptance(
            args.out, args.handoff_id, args.decision, args.reviewer,
            args.source_reference, args.delivery_reference, evidence,
            note=args.note,
        )
    except (HandoffError, OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(event, indent=2, default=str))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="rdo",
                                description="NEX Recursive Development Orchestrator (planning/evidence tools; no NEX runtime writes)")
    p.add_argument("--version", action="version", version=f"rdo {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("run-demo", help="run the full cycle on the genius-tagger objective")
    d.add_argument("--repo", default=".")
    d.add_argument("--out", default="rdo/.cycles")
    d.set_defaults(fn=_run_demo)

    ra = sub.add_parser("run-all", help="run two cycles (feature-deploy + defect) + cross-cycle metrics")
    ra.add_argument("--repo", default=".")
    ra.add_argument("--out", default="rdo/.cycles")
    ra.set_defaults(fn=_run_all)

    i = sub.add_parser("influence", help="audit a signal's influence authority (capability != authority)")
    i.add_argument("--repo", default=".")
    i.add_argument("--signal", default="genius")
    i.set_defaults(fn=_influence)

    s2 = sub.add_parser("stage2", help="RDO v1.3 §16 Stage-2 Extrapolator MVP (belief-decay objective)")
    s2.add_argument("--repo", default=".")
    s2.add_argument("--out", default="rdo/.cycles")
    s2.set_defaults(fn=_stage2)

    s3 = sub.add_parser("stage3", help="RDO v1.3 §16 Stage-3 graph intelligence (SCC / dedup / sequence)")
    s3.add_argument("--repo", default=".")
    s3.add_argument("--out", default="rdo/.cycles")
    s3.set_defaults(fn=_stage3)

    s4 = sub.add_parser("stage4", help="RDO v1.3 §16 Stage-4 read-only belief audit (lifecycle + gap map)")
    s4.add_argument("--repo", default=".")
    s4.add_argument("--out", default="rdo/.cycles")
    s4.set_defaults(fn=_stage4)

    s5 = sub.add_parser("stage5", help="RDO v1.3 §16 Stage-5 first belief-to-mechanism pathway (spec)")
    s5.add_argument("--repo", default=".")
    s5.add_argument("--out", default="rdo/.cycles")
    s5.set_defaults(fn=_stage5)

    s6 = sub.add_parser("stage6", help="RDO v1.3 §16 Stage-6 learning loop (calibration over real evidence)")
    s6.add_argument("--repo", default=".")
    s6.add_argument("--out", default="rdo/.cycles")
    s6.set_defaults(fn=_stage6)

    s7 = sub.add_parser("stage7", help="legacy Stage-7 execution-loop demo on a temporary fixture (runs its fixed fixture test)")
    s7.add_argument("--repo", default=".")
    s7.add_argument("--out", default="rdo/.cycles")
    s7.set_defaults(fn=_stage7)

    sub.add_parser("selfcheck",
                   help="assess the RDO against its own Optimal Functional Tension").set_defaults(fn=_selfcheck)

    fp = sub.add_parser(
        "failure-propagation",
        help="trace structural dependents of explicitly supplied failed obligations",
    )
    fp.add_argument("--cycle-id", required=True)
    fp.add_argument("--failed-key", action="append", required=True,
                    help="failed obligation key; repeat for multiple roots")
    fp.add_argument("--dir", default="rdo/.cycles")
    fp.set_defaults(fn=_failure_propagation)

    impact = sub.add_parser(
        "impact",
        help="compare before/after relationship assessments around changed capabilities",
    )
    impact.add_argument("--before-cycle-id", required=True)
    impact.add_argument("--after-cycle-id", required=True)
    impact.add_argument("--changed-capability", action="append", required=True,
                        help="changed obligation key; repeat for multiple capabilities")
    impact.add_argument("--dir", default="rdo/.cycles")
    impact.set_defaults(fn=_impact)

    pt = sub.add_parser("patterns", help="print accumulated development patterns")
    pt.add_argument("--dir", default="rdo/.cycles")
    pt.set_defaults(fn=_patterns)

    intake = sub.add_parser("intake", help="validate and run a versioned external objective")
    intake.add_argument("--input", required=True, help="path to objective.v1 JSON")
    intake.add_argument("--repo", default=".", help="clean Git repository snapshot to reconcile")
    intake.add_argument("--out", default="rdo/.cycles", help="RDO objective/cycle store")
    intake.set_defaults(fn=_intake)

    history = sub.add_parser("history", help="show immutable objective input revisions")
    history.add_argument("--objective-id", required=True)
    history.add_argument("--out", default="rdo/.cycles")
    history.set_defaults(fn=_history)

    resume = sub.add_parser("resume", help="reload an objective revision and its persisted cycles")
    resume.add_argument("--objective-id", required=True)
    resume.add_argument("--revision", required=True, type=int)
    resume.add_argument("--out", default="rdo/.cycles")
    resume.set_defaults(fn=_resume)

    hc = sub.add_parser("handoff-create", help="create a non-executing Stage-7 handoff manifest")
    hc.add_argument("--objective-id", required=True)
    hc.add_argument("--revision", required=True, type=int)
    hc.add_argument("--cycle-id", required=True)
    hc.add_argument("--work-package", required=True)
    hc.add_argument("--repo", default=".")
    hc.add_argument("--out", default="rdo/.cycles")
    hc.set_defaults(fn=_handoff_create)

    hh = sub.add_parser("handoff-history", help="show an immutable handoff and its human decision ledger")
    hh.add_argument("--handoff-id", required=True)
    hh.add_argument("--out", default="rdo/.cycles")
    hh.set_defaults(fn=_handoff_history)

    hv = sub.add_parser("handoff-verify", help="invoke independent Watcher source/path verification")
    hv.add_argument("--handoff-id", required=True)
    hv.add_argument("--repo", default=".")
    hv.add_argument("--out", default="rdo/.cycles")
    hv.add_argument("--timeout", type=int, default=120)
    hv.set_defaults(fn=_handoff_verify)

    hr = sub.add_parser("handoff-review", help="record a human-attributed non-executing scope decision")
    hr.add_argument("--handoff-id", required=True)
    hr.add_argument("--decision", required=True, choices=("approved", "rejected", "changes_requested"))
    hr.add_argument("--reviewer", required=True)
    hr.add_argument("--source-reference", required=True)
    hr.add_argument("--permitted-action", action="append", default=[])
    hr.add_argument("--note", default="")
    hr.add_argument("--out", default="rdo/.cycles")
    hr.set_defaults(fn=_handoff_review)

    hm = sub.add_parser("handoff-context-map", help="record a reviewed mapping from objective context to graph obligations")
    hm.add_argument("--handoff-id", required=True)
    hm.add_argument("--item-id", required=True)
    hm.add_argument("--mapped-obligation", action="append", required=True)
    hm.add_argument("--evidence-reference", action="append", required=True)
    hm.add_argument("--reviewer", required=True)
    hm.add_argument("--source-reference", required=True)
    hm.add_argument("--note", default="")
    hm.add_argument("--out", default="rdo/.cycles")
    hm.set_defaults(fn=_handoff_context_map)

    hvf = sub.add_parser("handoff-acceptance-verify", help="record verification of one acceptance criterion")
    hvf.add_argument("--handoff-id", required=True)
    hvf.add_argument("--criterion-id", required=True)
    hvf.add_argument("--status", required=True, choices=("pending", "passed", "failed", "not_applicable"))
    hvf.add_argument("--mapped-obligation", action="append", default=[])
    hvf.add_argument("--verification-method")
    hvf.add_argument("--evidence-reference", action="append", default=[])
    hvf.add_argument("--verifier", required=True)
    hvf.add_argument("--source-reference", required=True)
    hvf.add_argument("--confidence")
    hvf.add_argument("--verified-at")
    hvf.add_argument("--note", default="")
    hvf.add_argument("--out", default="rdo/.cycles")
    hvf.set_defaults(fn=_handoff_acceptance_verify)

    ha = sub.add_parser("handoff-acceptance", help="record a separate human acceptance decision")
    ha.add_argument("--handoff-id", required=True)
    ha.add_argument("--decision", required=True, choices=("accepted", "rejected", "changes_requested"))
    ha.add_argument("--reviewer", required=True)
    ha.add_argument("--source-reference", required=True)
    ha.add_argument("--delivery-reference", required=True)
    ha.add_argument("--evidence-references", required=True,
                    help="JSON object with source_implemented, test_verified and runtime_observed arrays")
    ha.add_argument("--note", default="")
    ha.add_argument("--out", default="rdo/.cycles")
    ha.set_defaults(fn=_handoff_acceptance)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
