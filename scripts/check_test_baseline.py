#!/usr/bin/env python3
"""Run the test suite with the known-intentional failures deselected.

The suite carries a small set of intentional failures (the one-pen compliance
ratchet) that this gate should ignore while still turning red on any *new*
failure. Those compliance tests grep the live filesystem and are not
deterministic across environments, so they are *deselected* here rather than
diffed — the gate runs everything else and fails if anything fails.

    PYTHONPATH=. python3 scripts/check_test_baseline.py

The allowlist lives in tests/known_failures.txt (one pytest node id per line;
blank lines and # comments ignored). Removing an entry re-arms that test in CI.

Env: conftest.py redirects NEX5_DATA_DIR to a temp dir. Embeddings reach the
network only to load the model on first use; CI pre-downloads + caches it, so
set HF_HUB_OFFLINE=1 for the run once it is cached (tests then load from cache).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWLIST = ROOT / "tests" / "known_failures.txt"


def _load_allowlist() -> list[str]:
    if not ALLOWLIST.exists():
        return []
    out = []
    for line in ALLOWLIST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def main() -> int:
    deselect = _load_allowlist()
    cmd = [sys.executable, "-m", "pytest", "-q", "--tb=short",
           "-p", "no:cacheprovider", "-o", "addopts="]
    for node in deselect:
        cmd += ["--deselect", node]

    env = dict(os.environ)
    env.setdefault("PYTHONPATH", str(ROOT))

    print(f"[baseline] deselecting {len(deselect)} known-intentional test(s); "
          "any other failure fails the run.\n", flush=True)
    rc = subprocess.run(cmd, cwd=str(ROOT), env=env).returncode

    if rc == 0:
        print("\n[baseline] OK — no failures outside the known-intentional set.")
    else:
        print(f"\n[baseline] FAIL — pytest exited {rc}; a non-allowlisted test "
              "failed (or a collection/env error occurred). See output above.",
              file=sys.stderr)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
