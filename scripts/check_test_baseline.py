#!/usr/bin/env python3
"""Run the test suite and gate on a known-failure allowlist.

The suite carries a small set of intentional, un-masked failures (the one-pen
compliance ratchet). Tracking the baseline count by hand in commit prose is
error-prone, so this gates on the *delta* instead:

  * exits non-zero if any test NOT in tests/known_failures.txt fails
    (a new regression — CI red);
  * reports any allowlisted test that now PASSES ("newly fixed" — trim the list),
    which does not fail the build.

Runs pytest itself so it works the same locally and in CI:

    PYTHONPATH=. python3 scripts/check_test_baseline.py

Honours the same env the suite expects (conftest.py redirects NEX5_DATA_DIR to a
temp dir; HF_HUB_OFFLINE keeps embeddings from reaching the network — tests mock
embed(), so no model is needed).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWLIST = ROOT / "tests" / "known_failures.txt"

# Matches a pytest short-summary line: "FAILED path.py::Case::test - reason".
# Requires "::" so captured-log "ERROR substrate.writer:..." noise is excluded.
_SUMMARY_RE = re.compile(r"^(?:FAILED|ERROR)\s+(\S+::\S+?)(?:\s+-\s+.*)?$")


def _load_allowlist() -> set[str]:
    if not ALLOWLIST.exists():
        return set()
    out = set()
    for line in ALLOWLIST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.add(line)
    return out


def _run_pytest() -> tuple[int, str]:
    env = dict(os.environ)
    env.setdefault("PYTHONPATH", str(ROOT))
    env.setdefault("HF_HUB_OFFLINE", "1")
    env.setdefault("TRANSFORMERS_OFFLINE", "1")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-rfE", "--tb=no",
         "-p", "no:cacheprovider", "-o", "addopts="],
        cwd=str(ROOT), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    return proc.returncode, proc.stdout


def _parse_failures(output: str) -> set[str]:
    # Only parse the short-summary section to avoid matching failures echoed
    # inside tracebacks / captured logs.
    marker = "short test summary info"
    tail = output.split(marker, 1)[1] if marker in output else output
    failures = set()
    for line in tail.splitlines():
        m = _SUMMARY_RE.match(line.strip())
        if m:
            failures.add(m.group(1))
    return failures


def main() -> int:
    allowlist = _load_allowlist()
    rc, output = _run_pytest()
    print(output)

    # The suite's own last line ("N passed, M failed, ...") is the human summary;
    # the gate below is what decides the exit code.
    failures = _parse_failures(output)
    if not failures and rc != 0:
        # pytest failed but we parsed no FAILED/ERROR node ids — a collection or
        # environment error (e.g. a missing dependency). Fail loudly.
        print("\n[baseline] pytest exited non-zero with no parseable failures "
              "— treat as a build/env error.", file=sys.stderr)
        return rc or 1

    new_failures = sorted(failures - allowlist)
    newly_fixed = sorted(allowlist - failures)

    print("\n" + "=" * 68)
    print(f"[baseline] total failing: {len(failures)}  "
          f"allowlisted: {len(allowlist)}  "
          f"new: {len(new_failures)}  newly-fixed: {len(newly_fixed)}")

    if newly_fixed:
        print("\n[baseline] these allowlisted tests now PASS — remove them from "
              "tests/known_failures.txt:")
        for t in newly_fixed:
            print(f"    - {t}")

    if new_failures:
        print("\n[baseline] NEW failures (not in the allowlist) — CI red:")
        for t in new_failures:
            print(f"    FAILED {t}")
        return 1

    print("\n[baseline] OK — only known/intentional failures remain.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
