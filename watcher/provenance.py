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


def _git(repo_dir: str, *args: str) -> str:
    """Run a read-only git command; return stdout stripped, or '' on failure."""
    try:
        out = subprocess.run(
            ["git", "-C", repo_dir, *args],
            capture_output=True, text=True, timeout=20, check=False,
        )
        return out.stdout.strip()
    except Exception:
        return ""


def collect_repo_provenance(repo_dir: str = ".") -> List[Evidence]:
    """Provenance of the checkout the Watcher is running in (cloud/static)."""
    src = f"git -C {repo_dir}"
    head = _git(repo_dir, "rev-parse", "HEAD")
    branch = _git(repo_dir, "rev-parse", "--abbrev-ref", "HEAD")
    status = _git(repo_dir, "status", "--porcelain")
    remotes = _git(repo_dir, "remote", "-v")
    last = _git(repo_dir, "log", "--oneline", "-1")
    return [
        Evidence("checkout.HEAD", head, "cloud", "measured", src,
                 interpretation="SHA of the checkout the Watcher runs in (the GitHub clone)."),
        Evidence("checkout.branch", branch, "cloud", "measured", src),
        Evidence("checkout.dirty", bool(status), "cloud", "measured", src,
                 interpretation="True if the working tree has uncommitted changes."),
        Evidence("checkout.remotes", remotes, "cloud", "measured", src),
        Evidence("checkout.last_commit", last, "cloud", "measured", src),
    ]


def detect_drift(repo_dir: str = ".", baseline: str = "origin/main") -> List[Evidence]:
    """Ahead/behind of this checkout vs a baseline ref (cloud/static)."""
    src = f"git -C {repo_dir} rev-list --left-right --count {baseline}...HEAD"
    counts = _git(repo_dir, "rev-list", "--left-right", "--count", f"{baseline}...HEAD")
    behind = ahead = None
    if counts and len(counts.split()) == 2:
        behind, ahead = (int(x) for x in counts.split())
    rel = ("equal" if ahead == 0 and behind == 0
           else "ahead" if behind == 0 and (ahead or 0) > 0
           else "behind" if ahead == 0 and (behind or 0) > 0
           else "diverged" if ahead and behind else "unknown")
    return [
        Evidence("drift.vs_baseline",
                 {"baseline": baseline, "ahead": ahead, "behind": behind, "relation": rel},
                 "cloud", "measured", src,
                 interpretation=f"This checkout is {rel} relative to {baseline}."),
        # The deployed + home-drive checkouts can only be read on the machine.
        host_placeholder(
            "drift.deployed_and_local_checkouts",
            "host: git in /mnt/games/... and any home-drive checkout",
            "Deployed/home-drive checkout SHAs and their drift vs GitHub are HOST-only — "
            "see the dispatched host-side request. Do not assume GitHub is authoritative."),
    ]


def collect(repo_dir: str = ".", baseline: str = "origin/main") -> List[Evidence]:
    return collect_repo_provenance(repo_dir) + detect_drift(repo_dir, baseline)
