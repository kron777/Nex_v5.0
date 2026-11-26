"""Local executor for the Watcher's explicitly defined, read-only host requests.

This runs only the command strings authored in watcher.host.host_requests().
It does not accept arbitrary shell commands from the user or from the results file.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from .host import host_requests


def _collector_environment() -> dict[str, str]:
    """Use a controlled command environment; retain only the user bus needed by systemctl."""
    env = {
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "HOME": str(Path.home()),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "SYSTEMD_COLORS": "0",
        "SYSTEMD_PAGER": "cat",
        "PAGER": "cat",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_PAGER": "cat",
        "NEX_WATCHER_COLLECTOR_PID": str(os.getpid()),
    }
    # systemctl --user needs the existing session bus; do not inherit the rest
    # of the caller's environment (notably BASH_ENV, PYTHONPATH or loader hooks).
    for key in ("XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS"):
        value = os.environ.get(key)
        if value:
            env[key] = value
    return env


def collect_host_evidence(
    *,
    timeout: int = 600,
    include_artifact_hashes: bool = True,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Execute the fixed host request specification and return provenance-rich results."""
    if timeout < 1:
        raise ValueError("timeout must be at least one second")

    root = (repo_root or Path(__file__).resolve().parents[1]).resolve()
    results: dict[str, Any] = {}
    collected_at = dt.datetime.now(dt.timezone.utc).isoformat()

    for request in host_requests():
        if request.id == "runtime_artifact_hashes" and not include_artifact_hashes:
            results[request.id] = {
                "data": {
                    "status": "SKIPPED_BY_OPERATOR",
                    "reason": "Full-file SHA-256 fingerprinting was explicitly skipped.",
                    "commands": [],
                },
                "evidence_class": "unknown",
                "source_ref": f"local Watcher host collection {collected_at}: operator skip",
                "note": "Not collected; do not interpret as an empty artifact inventory.",
            }
            continue

        command_results = []
        for index, command in enumerate(request.read_only_commands, start=1):
            if request.id == "runtime_artifact_hashes" and index == 2:
                print(
                    "NOTICE: hashing selected database and snapshot files reads each "
                    "complete file and may cause substantial disk I/O.",
                    file=sys.stderr,
                    flush=True,
                )
            started = dt.datetime.now(dt.timezone.utc).isoformat()
            try:
                completed = subprocess.run(
                    ["bash", "--noprofile", "--norc", "-c", command],
                    cwd=str(root),
                    capture_output=True,
                    text=True,
                    errors="replace",
                    timeout=timeout,
                    check=False,
                    env=_collector_environment(),
                )
                command_results.append({
                    "index": index,
                    "exit_code": completed.returncode,
                    "timed_out": False,
                    "started_at": started,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                })
            except subprocess.TimeoutExpired as exc:
                stdout = exc.stdout or ""
                stderr = exc.stderr or ""
                if isinstance(stdout, bytes):
                    stdout = stdout.decode(errors="replace")
                if isinstance(stderr, bytes):
                    stderr = stderr.decode(errors="replace")
                command_results.append({
                    "index": index,
                    "exit_code": None,
                    "timed_out": True,
                    "started_at": started,
                    "stdout": stdout,
                    "stderr": stderr,
                    "timeout_seconds": timeout,
                })
            except OSError as exc:
                command_results.append({
                    "index": index,
                    "exit_code": None,
                    "timed_out": False,
                    "started_at": started,
                    "stdout": "",
                    "stderr": f"{type(exc).__name__}: {exc}",
                })

        failures = [
            item for item in command_results
            if item["exit_code"] not in (0, None) or item["timed_out"]
        ]
        results[request.id] = {
            "data": {
                "status": "COLLECTED_WITH_ERRORS" if failures else "COLLECTED",
                "working_directory": str(root),
                "command_count": len(command_results),
                "failed_command_count": len(failures),
                "commands": command_results,
            },
            "evidence_class": "static" if request.id == "classify_unknown_tools" else "measured",
            "source_ref": (
                f"local Watcher host collector {collected_at}; "
                f"request={request.id}; commands={len(command_results)}"
            ),
            "note": (
                "Exit codes and stderr are retained. A non-zero command does not "
                "establish absence; interpret its output and collection status."
            ),
        }

    return {
        "_meta": {
            "collector": "watcher.host_runner",
            "collected_at": collected_at,
            "working_directory": str(root),
            "read_only_intent": True,
            "artifact_hashing_included": include_artifact_hashes,
            "timeout_seconds_per_command": timeout,
            "warning": (
                "Read-only does not mean zero I/O. Artifact SHA-256 collection reads "
                "selected files in full. Review command outputs and provenance."
            ),
        },
        **results,
    }


def write_results(results: dict[str, Any], output: Path, *, force: bool = False) -> Path:
    """Write results atomically; never overwrite an existing report without --force."""
    output = output.expanduser()
    if output.exists() and not force:
        raise FileExistsError(f"{output} already exists; choose another path or pass --force")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    payload = json.dumps(results, indent=2, ensure_ascii=False) + "\n"
    temporary.write_text(payload, encoding="utf-8")
    os.replace(temporary, output)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="watcher host-collect",
        description="Run the Watcher's fixed, read-only host evidence requests locally.",
    )
    parser.add_argument("--out", default="host_results.json", help="results JSON path")
    parser.add_argument(
        "--repo-root", type=Path, default=None,
        help="NEX checkout root to inspect (default: the collector's own checkout)",
    )
    parser.add_argument("--timeout", type=int, default=600,
                        help="timeout per command in seconds (default: 600)")
    parser.add_argument("--skip-artifact-hashes", action="store_true",
                        help="skip full-file DB/snapshot fingerprinting")
    parser.add_argument("--force", action="store_true",
                        help="replace an existing output file")
    args = parser.parse_args(argv)

    if not args.skip_artifact_hashes:
        print(
            "Host collection will fingerprint selected DB/snapshot files using SHA-256. "
            "This reads each selected file in full and may cause substantial disk I/O. "
            "Use --skip-artifact-hashes to omit that portion.",
            file=sys.stderr,
            flush=True,
        )

    try:
        results = collect_host_evidence(
            timeout=args.timeout,
            include_artifact_hashes=not args.skip_artifact_hashes,
            repo_root=args.repo_root,
        )
        path = write_results(results, Path(args.out), force=args.force)
    except (OSError, ValueError) as exc:
        print(f"host collection failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    failed = sum(
        row.get("data", {}).get("failed_command_count", 0)
        for key, row in results.items() if not key.startswith("_")
    )
    skipped = sum(
        row.get("data", {}).get("status") == "SKIPPED_BY_OPERATOR"
        for key, row in results.items() if not key.startswith("_")
    )
    print(f"wrote {path}; requests={len(results) - 1}; command_failures={failed}; skipped_requests={skipped}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
