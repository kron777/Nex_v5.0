"""Fail-closed assertions for the disposable CI test container.

This probe runs before pytest. It verifies the properties the workflow asks
Docker to enforce; it does not claim to be a general-purpose sandbox auditor.
"""
from __future__ import annotations

import os
import socket
import subprocess
import tempfile
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"TEST SANDBOX PROBE FAILED: {message}")


require(os.name == "posix", "expected a POSIX container")
require(os.geteuid() != 0, "test process must not run as root")

status = Path("/proc/self/status").read_text(encoding="utf-8")
cap_eff = next((line.split(":", 1)[1].strip() for line in status.splitlines()
                if line.startswith("CapEff:")), None)
require(cap_eff is not None and int(cap_eff, 16) == 0,
        "effective Linux capabilities must be empty")

for name in os.environ:
    upper = name.upper()
    if any(marker in upper for marker in ("TOKEN", "API_KEY", "SECRET", "PASSWORD", "CREDENTIAL")):
        raise SystemExit(f"TEST SANDBOX PROBE FAILED: credential-like environment variable present: {name}")

workspace = Path("/workspace")
require(workspace.is_dir(), "workspace is missing")
git_config = workspace / ".git" / "config"
require(git_config.is_file(), "credential-free checkout metadata is required for repository provenance tests")
git_config_text = git_config.read_text(encoding="utf-8").lower()
require("extraheader" not in git_config_text and "credential" not in git_config_text,
        "checkout Git configuration must not contain persisted credentials")
require((workspace / ".git").stat().st_uid == os.geteuid(),
        "checkout metadata must be owned by the unprivileged test UID")
git_status = subprocess.run(
    ["git", "-C", str(workspace), "status", "--porcelain", "--untracked-files=all"],
    capture_output=True, text=True, check=False,
)
require(git_status.returncode == 0, f"Git provenance command failed: {git_status.stderr.strip()}")
print(f"Sandbox checkout status: {git_status.stdout!r}")
require(not git_status.stdout.strip(), "checkout must be clean before tests start")
try:
    with (workspace / ".sandbox-write-probe").open("x", encoding="utf-8"):
        pass
except OSError:
    pass
else:
    (workspace / ".sandbox-write-probe").unlink(missing_ok=True)
    raise SystemExit("TEST SANDBOX PROBE FAILED: repository workspace is writable")

require(not (workspace / "data").exists(),
        "live-data directory must not be copied into the test image")
data_dir = Path(os.environ.get("NEX5_DATA_DIR", "")).resolve()
require(data_dir == Path("/tmp/nex5-data"),
        "NEX5_DATA_DIR must point to the disposable tmpfs location")

with tempfile.NamedTemporaryFile(dir="/tmp", prefix="sandbox-probe-", delete=True):
    pass

# --network none must leave the container without a default IPv4 route.
routes = Path("/proc/net/route").read_text(encoding="utf-8").splitlines()[1:]
has_default_route = any(line.split()[1] == "00000000" for line in routes if len(line.split()) > 2)
require(not has_default_route, "container has a default IPv4 route")

try:
    socket.create_connection(("1.1.1.1", 443), timeout=2)
except OSError:
    pass
else:
    raise SystemExit("TEST SANDBOX PROBE FAILED: outbound network connection succeeded")

print("TEST SANDBOX PROBE OK: unprivileged, no capabilities, no credentials, "
      "read-only source, disposable data/tmpfs, no default route, no outbound network")
