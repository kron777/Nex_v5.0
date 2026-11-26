"""Repository / checkout provenance and deployment-drift detection.

Cloud-side this reads the Git state of the checkout the Watcher runs in (the
GitHub clone) with read-only `git` commands. It can only see THIS checkout; the
*deployed* and any *home-drive* checkouts live on the machine, so for those it
emits honest host placeholders (origin=host, class=unknown) rather than guessing.
Drift is a first-class finding on this project: the deployed copy has diverged
from GitHub before, and a checkout was lost in a disk-full.
"""
from __future__ import annotations

import subprocess
from typing import List

from .evidence import Evidence, host_placeholder


def _git(repo_dir: str, *args: str) -> str | None:
    """Return stdout (including a valid empty string), or None when Git failed."""
    try:
        out = subprocess.run(
            ["git", "-C", repo_dir, *args],
            capture_output=True, text=True, timeout=20, check=False,
        )
        if out.returncode != 0:
            return None
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def collect_repo_provenance(repo_dir: str = ".") -> List[Evidence]:
    """Provenance of the checkout the Watcher is running in (cloud/static)."""
    src = f"git -C {repo_dir}"
    head = _git(repo_dir, "rev-parse", "HEAD")
    branch = _git(repo_dir, "rev-parse", "--abbrev-ref", "HEAD")
    status = _git(repo_dir, "status", "--porcelain")
    remotes = _git(repo_dir, "remote", "-v")
    last = _git(repo_dir, "log", "--oneline", "-1")
    def ev(subject, value, interpretation=None, *, empty_is_valid=False):
        available = value is not None and (bool(value) or empty_is_valid)
        return Evidence(subject, (bool(value) if subject == "checkout.dirty" and available else
                                  value if available else None),
                        "cloud", "measured" if available else "unknown", src,
                        modifier=None if available else "unverified",
                        interpretation=interpretation or ("Git command failed or returned an invalid empty value."
                                                          if not available else None))

    return [
        ev("checkout.HEAD", head, "SHA of the checkout the Watcher runs in (the GitHub clone)."),
        ev("checkout.branch", branch),
        ev("checkout.dirty", status, "True if the working tree has uncommitted changes.", empty_is_valid=True),
        ev("checkout.remotes", remotes, empty_is_valid=True),
        ev("checkout.last_commit", last),
    ]


def detect_drift(repo_dir: str = ".", baseline: str = "origin/main") -> List[Evidence]:
    """Ahead/behind of this checkout vs a baseline ref (cloud/static)."""
    src = f"git -C {repo_dir} rev-list --left-right --count {baseline}...HEAD"
    counts = _git(repo_dir, "rev-list", "--left-right", "--count", f"{baseline}...HEAD")
    behind = ahead = None
    if counts is not None and len(counts.split()) == 2:
        try:
            behind, ahead = (int(x) for x in counts.split())
        except ValueError:
            behind = ahead = None
    rel = ("equal" if ahead == 0 and behind == 0
           else "ahead" if behind == 0 and (ahead or 0) > 0
           else "behind" if ahead == 0 and (behind or 0) > 0
           else "diverged" if ahead and behind else "unknown")
    return [
        Evidence("drift.vs_baseline",
                 {"baseline": baseline, "ahead": ahead, "behind": behind, "relation": rel},
                 "cloud", "measured" if counts is not None and ahead is not None else "unknown", src,
                 modifier=None if counts is not None and ahead is not None else "unverified",
                 interpretation=(f"This checkout is {rel} relative to {baseline}." if counts is not None and ahead is not None
                                 else f"Git could not establish drift relative to {baseline}.")),
        # The deployed + home-drive checkouts can only be read on the machine.
        host_placeholder(
            "drift.deployed_and_local_checkouts",
            "host: git in /mnt/games/... and any home-drive checkout",
            "Deployed/home-drive checkout SHAs and their drift vs GitHub are HOST-only — "
            "see the dispatched host-side request. Do not assume GitHub is authoritative."),
    ]


def collect(repo_dir: str = ".", baseline: str = "origin/main") -> List[Evidence]:
    return collect_repo_provenance(repo_dir) + detect_drift(repo_dir, baseline)
