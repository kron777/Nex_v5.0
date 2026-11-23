"""Stage 7 (RDO v1.3 §16) — execution integration verified through the Watcher.

Closes the loop: an RDO work package is handed to an execution agent (e.g. Claude Code), the
execution produces artifacts + tests, and the **Watcher independently verifies** the outcome along
THREE SEPARATE evidence dimensions (source-implemented, test-verified, runtime-observed). A success
is NEVER inferred from a completion claim, a commit, or a file's mere existence: the verdict is
derived from the Watcher's independent evidence. Runtime observation stays host-only and UNKNOWN.

Reuse (no second Watcher, no general execution framework): `watcher.ledger.ConnectionLedger` for the
three-dimension lifecycle, `watcher.evidence` (Evidence / host_placeholder) for provenance + honest
unknowns, and the RDO's read-only grep for source evidence. The verified outcome feeds the Stage-6
learning loop with provenance preserved.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

from watcher.evidence import Evidence, host_placeholder, utc_now
from watcher.ledger import ConnectionLedger

from .belief_audit import _grep   # read-only, .sql-aware evidence grep


def create_execution_record(execution_id: str, cycle_id: str, objective: str,
                            work_package: dict, evidence_requirements: Dict[str, dict]) -> dict:
    """Durable record linking a work package to its ORIGINATING objective + obligations, with the
    independent evidence required to verify each obligation (a source signature + an optional test)."""
    return {
        "execution_id": execution_id,
        "cycle_id": cycle_id,
        "objective": objective,
        "work_package": work_package.get("key"),
        "obligation_keys": list(work_package.get("obligation_keys", [])),
        "acceptance_criteria": "each required obligation must be INDEPENDENTLY confirmed by the Watcher "
                               "(source + test); runtime remains a separate host-only dimension",
        "evidence_requirements": evidence_requirements,   # {obligation: {source_signature, source_path, test_file?}}
        "handoff": {
            "agent": "claude_code",
            "instruction": f"Implement work package {work_package.get('key')} for objective: {objective}. "
                           "Satisfy each obligation's source signature and make its test pass. Report "
                           "changed artifacts, tests and any failures. A completion claim is not "
                           "acceptance — the Watcher verifies independently.",
            "evidence_required": sorted(evidence_requirements),
        },
        "status": "declared",
        "claim": None,
        "verification": None,
        "verdict": None,
        "created_at": utc_now(),
    }


def record_claim(record: dict, *, completion_claim: bool, changed_artifacts: List[str],
                 tests: List[str], failures: List[str]) -> dict:
    """Attach the execution agent's self-reported claim. This is recorded, NOT trusted: verification
    is independent."""
    record["claim"] = {
        "completion_claim": bool(completion_claim),
        "changed_artifacts": list(changed_artifacts),
        "tests": list(tests),
        "failures": list(failures),
        "claimed_at": utc_now(),
    }
    record["status"] = "claimed_complete" if completion_claim else "in_progress"
    return record


def _approved_test_path(test_file: str, repo_dir: str,
                         approved_test_files: Optional[List[str]]) -> Optional[str]:
    """Resolve one exact, caller-approved repo-relative test path.

    Absolute paths, traversal, missing files and symlinks escaping repo_dir are refused.
    A path in evidence_requirements is a requirement, NOT permission to execute it.
    """
    if not test_file or not approved_test_files:
        return None
    try:
        requested = Path(test_file)
        if requested.is_absolute() or ".." in requested.parts:
            return None
        root = Path(repo_dir).resolve()
        resolved = (root / requested).resolve(strict=True)
        relative = resolved.relative_to(root).as_posix()
        if not resolved.is_file():
            return None
        allowed = set()
        for item in approved_test_files:
            candidate = Path(item)
            if candidate.is_absolute() or ".." in candidate.parts:
                continue
            allowed.add(candidate.as_posix())
        return relative if relative in allowed else None
    except (OSError, RuntimeError, ValueError):
        return None


def _run_test(test_file: str, repo_dir: str,
              approved_test_files: Optional[List[str]] = None) -> tuple[str, Optional[bool]]:
    """Run only an explicitly approved, repo-contained test.

    Returns (status, result). No allowlist / unsafe path -> ('not_authorized', None).
    """
    relative = _approved_test_path(test_file, repo_dir, approved_test_files)
    if relative is None:
        return "not_authorized", None
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", relative, "-q"],
                           cwd=repo_dir, capture_output=True, text=True, timeout=120)
        return ("passed" if r.returncode == 0 else "failed"), (r.returncode == 0)
    except (OSError, subprocess.SubprocessError):
        return "error", None


def _obligation_verdict(source_ok: bool, test_ok: Optional[bool]) -> str:
    if test_ok is False:
        return "failed"
    if not source_ok:
        return "claim_unverified"          # no independent source evidence -> a claim is not enough
    if test_ok is None:
        return "partial"                   # source present, but no test evidence
    return "verified"                      # source confirmed AND test passed


def _overall_verdict(per: Dict[str, str]) -> str:
    vals = set(per.values())
    if "failed" in vals:
        return "failed"
    if "claim_unverified" in vals:
        return "claim_unverified"
    if "partial" in vals:
        return "partial"
    return "verified" if vals == {"verified"} else "partial"


def verify(record: dict, repo_dir: str, ledger_path: str,
           *, approved_test_files: Optional[List[str]] = None) -> dict:
    """INDEPENDENT Watcher verification along three SEPARATE dimensions.

    Test execution requires an explicit exact-path allowlist supplied by the caller. The
    test_file recorded as an evidence requirement is not, by itself, execution permission.
    The path must also resolve inside repo_dir. Lifecycle is recorded in the Watcher's
    append-only ConnectionLedger; runtime stays an honest host-only UNKNOWN.
    """
    ledger = ConnectionLedger(ledger_path)
    dims: Dict[str, dict] = {}
    per: Dict[str, str] = {}
    for ob, req in record["evidence_requirements"].items():
        cid = f"{record['execution_id']}:{ob}"
        if ledger.current_state(cid) is None:
            ledger.record(cid, "DECLARED", note=ob)
        # SOURCE dimension (cloud, read-only grep of the after-state)
        hits = _grep(req["source_signature"], repo_dir, req.get("source_path"))
        source_ok = bool(hits)
        if source_ok and ledger.current_state(cid) == "DECLARED":
            ledger.record(cid, "SOURCE_CONFIRMED", evidence_refs=hits[:1])
        # TEST dimension (cloud, independent run). A declared test path is not permission:
        # the caller must explicitly allowlist the exact repo-relative path.
        if req.get("test_file"):
            test_status, test_ok = _run_test(req["test_file"], repo_dir, approved_test_files)
        else:
            test_status, test_ok = "not_requested", None
        if source_ok and test_ok is not None and ledger.current_state(cid) == "SOURCE_CONFIRMED":
            ledger.record(cid, "TEST_WRITTEN")
            ledger.record(cid, "TEST_PASSED" if test_ok else "TEST_FAILED")
        # RUNTIME dimension (host-only) — kept separate and UNKNOWN
        runtime = host_placeholder(f"runtime:{ob}", "host: a live trace",
                                   "runtime observation is host-only (NEX in standby) — UNKNOWN")
        source_ev = Evidence(f"source:{ob}", {"hits": hits}, "cloud",
                             "static" if source_ok else "unknown",
                             req.get("source_path") or repo_dir,
                             modifier=None if source_ok else "unverified")
        dims[ob] = {
            "source_implemented": source_ev.to_dict(),
            "test_verified": {"status": test_status,
                              "test_file": req.get("test_file"),
                              "execution_authorized": test_status not in ("not_authorized", "not_requested")},
            "runtime_observed": runtime.to_dict(),
            "ledger_state": ledger.current_state(cid),
        }
        per[ob] = _obligation_verdict(source_ok, test_ok)

    verdict = _overall_verdict(per)
    record["verification"] = {
        "dimensions": dims, "per_obligation_verdict": per, "ledger_path": ledger_path,
        "note": "source + test are INDEPENDENT cloud evidence; runtime is a SEPARATE host-only "
                "UNKNOWN; the verdict ignores the completion claim",
    }
    record["verdict"] = verdict
    record["status"] = verdict
    return record


def feedback_to_learning(record: dict) -> dict:
    """Translate the WATCHER-VERIFIED outcome (not the claim) into a learning `actual` for the
    Stage-6 loop, provenance preserved. Obligations that fail verification are reopened."""
    per = (record.get("verification") or {}).get("per_obligation_verdict", {})
    reopened = sorted(ob for ob, v in per.items() if v in ("failed", "claim_unverified"))
    return {
        "review_kind": "watcher_verified_execution",   # independent; NOT planning review, NOT a bare claim
        "reviewer": "watcher (independent evidence)",
        "verdict": record.get("verdict"),
        "verified_obligations": sorted(ob for ob, v in per.items() if v == "verified"),
        "reopened": reopened,
        "regressions": reopened,                        # failed verification feeds the loop as regressions
        "notes": "independently verified via the Watcher ledger; runtime is host-only UNKNOWN",
    }


def save_record(record: dict, path: str) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, default=str)
    return path


def load_record(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
