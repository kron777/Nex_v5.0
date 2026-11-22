"""Tests for the offline ripple reader (watcher/ripple.py).

Covers both offline-tier views (source-dependents, test-delta), the honest
runtime placeholder, Evidence validity, and the package independence invariant
(no theory_x / substrate imports anywhere in watcher/).
"""
import ast
import glob
import os

import pytest

from watcher import ripple
from watcher.evidence import EVIDENCE_CLASSES, ORIGINS


# ------------------------------------------------- (a) source-dependents
def _write(p, text):
    p.write_text(text, encoding="utf-8")


def test_source_dependents_finds_importers_and_tests(tmp_path):
    _write(tmp_path / "a.py", "def foo():\n    return 1\n")
    _write(tmp_path / "b.py", "import a\n\ndef use():\n    return a.foo()\n")
    _write(tmp_path / "c.py", "x = 1  # does not import a\n")
    (tmp_path / "tests").mkdir()
    _write(tmp_path / "tests" / "test_a.py", "from a import foo\n\ndef test_foo():\n    assert foo() == 1\n")

    ev = ripple.source_dependents(str(tmp_path), [str(tmp_path / "a.py")])
    assert ev.origin == "cloud" and ev.evidence_class == "static"
    dep = ev.data["dependents"]["a"]
    assert "b" in dep["direct_importers"]
    assert "c" not in dep["direct_importers"]
    assert "tests.test_a" in dep["downstream_tests"]
    assert "foo" in dep["symbols"]


def test_source_dependents_resolves_relative_imports(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    _write(pkg / "__init__.py", "")
    _write(pkg / "mod.py", "VALUE = 7\n")
    _write(pkg / "user.py", "from .mod import VALUE\n\ndef g():\n    return VALUE\n")

    ev = ripple.source_dependents(str(tmp_path), [str(pkg / "mod.py")])
    assert "pkg.user" in ev.data["dependents"]["pkg.mod"]["direct_importers"]


def test_non_python_change_is_listed_for_manual_review(tmp_path):
    _write(tmp_path / "a.py", "x=1\n")
    ev = ripple.source_dependents(str(tmp_path), [str(tmp_path / "schema.sql")])
    assert "schema.sql" in ev.data["changed_non_python"]


# ------------------------------------------------- (b) test-delta
def test_test_delta_classifies_newly_failing_and_appeared():
    before = {"outcomes": {"t::a": "passed", "t::b": "passed"}}
    after = {"outcomes": {"t::a": "failed", "t::b": "passed", "t::c": "passed"}}
    findings = ripple.test_delta(before, after)
    kinds = {f["subject"]: (f["kind"], f["severity"]) for f in findings}
    assert kinds["t::a"] == ("newly_failing", "critical")
    assert kinds["t::c"] == ("test_appeared", "info")
    assert "t::b" not in kinds  # unchanged pass is not a finding


def test_test_delta_newly_passing_and_removed():
    before = {"outcomes": {"t::a": "failed", "t::b": "passed"}}
    after = {"outcomes": {"t::a": "passed"}}
    findings = ripple.test_delta(before, after)
    kinds = {f["subject"]: f["kind"] for f in findings}
    assert kinds["t::a"] == "newly_passing"
    assert kinds["t::b"] == "test_removed"
    summary = ripple.summarize_delta(findings)
    assert summary["info"] >= 1 and summary["warning"] >= 1


def test_test_outcomes_runs_pytest_and_parses(tmp_path):
    (tmp_path / "test_tiny.py").write_text(
        "def test_pass():\n    assert True\n\ndef test_fail():\n    assert False\n",
        encoding="utf-8")
    result = ripple.test_outcomes(str(tmp_path), target="test_tiny.py", timeout=120)
    outs = result["outcomes"]
    assert any(k.endswith("test_pass") and v == "passed" for k, v in outs.items())
    assert any(k.endswith("test_fail") and v == "failed" for k, v in outs.items())
    assert result["summary"]["passed"] >= 1 and result["summary"]["failed"] >= 1


def test_test_delta_evidence_is_cloud_implemented():
    before = {"target": "x", "summary": {}, "outcomes": {"t::a": "passed"}}
    after = {"target": "x", "summary": {}, "outcomes": {"t::a": "failed"}}
    ev = ripple.test_delta_evidence(before, after)
    assert ev.origin == "cloud" and ev.evidence_class == "implemented"
    assert "live-confirm pending" in (ev.interpretation or "").lower() or \
           "live-confirm" in (ev.interpretation or "").lower()


# ------------------------------------------------- runtime placeholder + assembly
def test_runtime_placeholder_is_honest_host_unknown():
    ev = ripple.runtime_ripple_placeholder()
    assert ev.origin == "host" and ev.evidence_class == "unknown"
    assert ev.modifier == "unverified" and ev.data is None


def test_collect_offline_ripple_shape(tmp_path):
    _write(tmp_path / "a.py", "def f():\n    return 1\n")
    changed = [str(tmp_path / "a.py")]
    # without test snapshots: source-dependents + runtime placeholder
    recs = ripple.collect_offline_ripple(str(tmp_path), changed)
    subjects = [r.subject for r in recs]
    assert subjects == ["ripple.source_dependents", "ripple.runtime"]
    # with test snapshots: + test-delta, in the middle
    recs2 = ripple.collect_offline_ripple(
        str(tmp_path), changed,
        before={"outcomes": {"t::a": "passed"}},
        after={"outcomes": {"t::a": "failed"}})
    assert [r.subject for r in recs2] == \
        ["ripple.source_dependents", "ripple.test_delta", "ripple.runtime"]
    for r in recs2:
        assert r.origin in ORIGINS and r.evidence_class in EVIDENCE_CLASSES


# ------------------------------------------------- independence invariant
def test_watcher_package_imports_no_theory_x_or_substrate():
    """Every watcher/*.py (ripple.py included) stays independent of NEX's runtime."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(ripple.__file__)))
    watcher_dir = os.path.join(root, "watcher")
    offenders = []
    for path in glob.glob(os.path.join(watcher_dir, "**", "*.py"), recursive=True):
        with open(path, "r", encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=path)
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                mods = [node.module or ""]
            for m in mods:
                if m.split(".")[0] in ("theory_x", "substrate"):
                    offenders.append((os.path.relpath(path, root), m))
    assert not offenders, f"watcher must not import NEX runtime: {offenders}"
