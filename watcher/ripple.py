"""Offline ripple reader — what a change touched, before NEX is live.

The one job: after a wire is connected, say what rippled, so the effects can be
smoothed before the next wire — without hand-reading the whole codebase. This is
the Watcher's OFFLINE tier (no live NEX needed), in two read-only views:

  (a) source-dependency ripple — who else imports/depends on whatever the wire
      touched (a static reverse-import map over the actual Python source), plus
      which tests sit downstream of it.
  (b) test-suite delta — whether the test suite shifted after the change: capture
      per-test outcomes before and after and diff them (newly failing / passing /
      appeared / removed).

Both stay within the Watcher's contract: external, read-only, independent of NEX's
cognitive runtime (this module imports no `theory_x` / `substrate`), and every
finding is an `Evidence` record with origin='cloud' (static/offline) so it is never
confused with a live-machine observation. The RUNTIME tier (what actually fired,
how her behaviour changed) is left as an honest host-only placeholder + a clean
ingestion hook; it is not built here and does not block the offline tier.
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional

from .evidence import Evidence, host_placeholder, utc_now

_SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache",
             ".mypy_cache", "build", "dist", ".eggs"}


# --------------------------------------------------------------------------- #
# (a) source-dependency ripple — static reverse-import map
# --------------------------------------------------------------------------- #

def _py_files(repo_dir: str) -> List[str]:
    out: List[str] = []
    for d, dirs, fs in os.walk(repo_dir):
        dirs[:] = [x for x in dirs if x not in _SKIP_DIRS]
        for f in fs:
            if f.endswith(".py"):
                out.append(os.path.join(d, f))
    return sorted(out)


def _module_name(path: str, repo_dir: str) -> str:
    """Repo-relative file path -> dotted module name (``pkg/__init__.py`` -> ``pkg``)."""
    rel = os.path.relpath(os.path.abspath(path), os.path.abspath(repo_dir))
    rel = rel[:-3] if rel.endswith(".py") else rel
    parts = rel.split(os.sep)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(p for p in parts if p and p != ".")


def _imports_of(path: str, module: str) -> set:
    """Fully-qualified module strings this file imports.

    ``import a.b`` -> {"a", "a.b"}; ``from a.b import c`` -> {"a.b", "a.b.c"};
    relative imports are resolved against this file's own package.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=path)
    except (OSError, SyntaxError):
        return set()

    pkg = module.rsplit(".", 1)[0] if "." in module else ""
    found: set = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                found.add(a.name)
                if "." in a.name:
                    found.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:  # relative: climb `level` packages from this file's package
                climb = pkg.split(".") if pkg else []
                climb = climb[: len(climb) - (node.level - 1)] if node.level > 1 else climb
                base = ".".join([p for p in climb if p] + ([base] if base else []))
            if base:
                found.add(base)
                for a in node.names:
                    if a.name != "*":
                        found.add(f"{base}.{a.name}")
    return found


def _top_level_symbols(path: str) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=path)
    except (OSError, SyntaxError):
        return []
    out = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.append(node.name)
    return out


def _is_test_module(module: str, path: str) -> bool:
    base = os.path.basename(path)
    return base.startswith("test_") or base.endswith("_test.py") or "/tests/" in path.replace(os.sep, "/")


def source_dependents(repo_dir: str, changed_paths: List[str]) -> Evidence:
    """Who imports/depends on the changed modules (direct static reverse-import map)."""
    files = _py_files(repo_dir)
    module_of = {p: _module_name(p, repo_dir) for p in files}
    imports_of = {p: _imports_of(p, module_of[p]) for p in files}

    changed_py = [p for p in changed_paths if p.endswith(".py")]
    changed_other = [p for p in changed_paths if not p.endswith(".py")]
    changed_modules = {}
    for p in changed_py:
        # resolve the changed path to a module even if it is outside the walked set
        changed_modules[p] = _module_name(p, repo_dir)

    dependents: Dict[str, dict] = {}
    for cp, cmod in changed_modules.items():
        direct, tests = [], []
        for f in files:
            if os.path.abspath(f) == os.path.abspath(cp):
                continue
            imps = imports_of[f]
            hit = any(s == cmod or s.startswith(cmod + ".") for s in imps)
            if hit:
                fmod = module_of[f]
                (tests if _is_test_module(fmod, f) else direct).append(fmod)
        dependents[cmod] = {
            "path": os.path.relpath(cp, repo_dir),
            "symbols": _top_level_symbols(cp),
            "direct_importers": sorted(set(direct)),
            "downstream_tests": sorted(set(tests)),
            "importer_count": len(set(direct)) + len(set(tests)),
        }

    total_importers = sorted({m for d in dependents.values()
                              for m in d["direct_importers"] + d["downstream_tests"]})
    note = ("Direct static reverse-import map (import-level, not a full call graph). "
            "'downstream_tests' are the tests that import the touched modules — run those "
            "first after a wire. Non-Python changes are listed for manual review.")
    return Evidence(
        subject="ripple.source_dependents",
        data={
            "changed_python": [os.path.relpath(p, repo_dir) for p in changed_py],
            "changed_non_python": [os.path.relpath(p, repo_dir) for p in changed_other],
            "dependents": dependents,
            "unique_downstream_modules": total_importers,
            "unique_downstream_count": len(total_importers),
        },
        origin="cloud",
        evidence_class="static",
        source_ref=f"ast-import-graph:{os.path.relpath(repo_dir) or '.'}",
        interpretation=note,
    )


# --------------------------------------------------------------------------- #
# (b) test-suite delta — per-test outcome snapshot + diff
# --------------------------------------------------------------------------- #

def test_outcomes(repo_dir: str, target: Optional[str] = None,
                  timeout: int = 1800) -> dict:
    """Run the repo's pytest suite (offline, isolated — never the live host) and
    return per-test outcomes via JUnit XML. Reads results only; changes nothing."""
    with tempfile.TemporaryDirectory() as td:
        xml = os.path.join(td, "junit.xml")
        cmd = [sys.executable, "-m", "pytest",
               "-p", "no:cacheprovider", "--continue-on-collection-errors",
               "-o", "addopts=", "-q", f"--junitxml={xml}"]
        if target:
            cmd.append(target)
        try:
            proc = subprocess.run(cmd, cwd=repo_dir, capture_output=True,
                                  text=True, timeout=timeout)
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            return {"ran_at": utc_now(), "target": target or "<repo>",
                    "error": f"pytest timed out after {timeout}s", "outcomes": {}}
        outcomes = _parse_junit(xml)
    summary = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
    for o in outcomes.values():
        summary[o] = summary.get(o, 0) + 1
    return {"ran_at": utc_now(), "target": target or "<repo>", "returncode": rc,
            "total": len(outcomes), "summary": summary, "outcomes": outcomes}


def _parse_junit(xml_path: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not os.path.exists(xml_path):
        return out
    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError:
        return out
    for tc in root.iter("testcase"):
        cls, name = tc.get("classname", ""), tc.get("name", "")
        nodeid = f"{cls}::{name}" if cls else name
        if tc.find("failure") is not None:
            out[nodeid] = "failed"
        elif tc.find("error") is not None:
            out[nodeid] = "error"
        elif tc.find("skipped") is not None:
            out[nodeid] = "skipped"
        else:
            out[nodeid] = "passed"
    return out


_BAD = {"failed", "error"}


def test_delta(before: dict, after: dict) -> List[dict]:
    """Diff two outcome maps (from ``test_outcomes``). Newly-failing is the signal
    that matters most after a wire."""
    bo, ao = before.get("outcomes", before), after.get("outcomes", after)
    findings: List[dict] = []

    def add(subject, kind, severity, b, a, note):
        findings.append({"subject": subject, "kind": kind, "severity": severity,
                         "before": b, "after": a, "note": note})

    for nid in sorted(set(bo) & set(ao)):
        b, a = bo[nid], ao[nid]
        if b == a:
            continue
        if b not in _BAD and a in _BAD:
            add(nid, "newly_failing", "critical", b, a, "passed/other before, failing after the change")
        elif b in _BAD and a not in _BAD:
            add(nid, "newly_passing", "info", b, a, "was failing before, resolved after the change")
        else:
            add(nid, "outcome_changed", "warning", b, a, f"outcome changed {b} -> {a}")
    for nid in sorted(set(ao) - set(bo)):
        add(nid, "test_appeared", "info", None, ao[nid], "test present only after the change")
    for nid in sorted(set(bo) - set(ao)):
        add(nid, "test_removed", "warning", bo[nid], None, "test present before the change, gone after")
    return findings


def summarize_delta(findings: List[dict]) -> Dict[str, int]:
    out = {"critical": 0, "warning": 0, "info": 0}
    for f in findings:
        out[f["severity"]] = out.get(f["severity"], 0) + 1
    return out


def test_delta_evidence(before: dict, after: dict) -> Evidence:
    findings = test_delta(before, after)
    return Evidence(
        subject="ripple.test_delta",
        data={
            "summary": summarize_delta(findings),
            "before": {"target": before.get("target"), "counts": before.get("summary")},
            "after": {"target": after.get("target"), "counts": after.get("summary")},
            "findings": findings,
        },
        origin="cloud",
        evidence_class="implemented",  # test-verified (ran offline), not live-measured
        source_ref="pytest-junit-delta",
        interpretation=("Repo-proven test-suite shift (offline). 'newly_failing' is the "
                        "ripple to smooth before the next wire. Live-confirm pending — this "
                        "is not her runtime behaviour, only the suite's."),
    )


# --------------------------------------------------------------------------- #
# runtime tier — honest placeholder + clean hook (NOT built here)
# --------------------------------------------------------------------------- #

def runtime_ripple_placeholder(changed_paths: Optional[List[str]] = None) -> Evidence:
    """The runtime tier (what actually fired / how her behaviour changed) is host-only
    and is not collected offline. Recorded as an honest UNKNOWN so the report never
    implies a live observation it did not make. When NEX is live, a host collector
    fills this via `watcher.host` ingestion (same path as other host evidence)."""
    ev = host_placeholder(
        subject="ripple.runtime",
        source_ref="watcher.host (live NEX required)",
        note=("Runtime ripple — what fired and how behaviour shifted — requires a live "
              "NEX run with before/after behaviour capture. Hook: collect host-side and "
              "ingest via `watcher combined --results <host.json>`. Offline tiers above "
              "are repo-proven; this stays UNKNOWN until live-confirmed."),
    )
    return ev


# --------------------------------------------------------------------------- #
# assembly
# --------------------------------------------------------------------------- #

def collect_offline_ripple(repo_dir: str, changed_paths: List[str],
                           before: Optional[dict] = None,
                           after: Optional[dict] = None) -> List[Evidence]:
    """The offline ripple for a change: source-dependents always; test-delta when
    before/after outcome snapshots are supplied; plus the runtime placeholder."""
    records = [source_dependents(repo_dir, changed_paths)]
    if before is not None and after is not None:
        records.append(test_delta_evidence(before, after))
    records.append(runtime_ripple_placeholder(changed_paths))
    return records
