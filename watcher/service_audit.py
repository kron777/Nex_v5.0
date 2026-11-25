"""Read-only diagnostics for the fixed NEX user-service set.

This module never starts, stops, enables, disables, reloads, or edits services.
It asks systemd for selected properties and checks referenced filesystem paths.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
from typing import Any

SERVICES = (
    "nex-vitals.service",
    "nex5-db-reaper.service",
    "nex5-keepalive.service",
    "nex5-power-switch.service",
)
PROPERTIES = (
    "LoadState", "ActiveState", "SubState", "Result",
    "ExecMainCode", "ExecMainStatus", "MainPID", "NRestarts",
    "FragmentPath", "DropInPaths", "WorkingDirectory",
    "ExecStart", "Restart", "RestartUSec",
    "RestartPreventExitStatus", "KillMode",
)


def parse_properties(output: str) -> dict[str, str]:
    """Parse systemctl's key=value properties without retaining unrequested fields."""
    parsed: dict[str, str] = {}
    for line in output.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            parsed[key] = value
    return parsed


def _decode_systemd_path(value: str) -> str:
    """Decode systemd's \\xHH path escaping for filesystem checks."""
    return re.sub(
        r"\\x([0-9a-fA-F]{2})",
        lambda match: chr(int(match.group(1), 16)),
        value,
    )


def _exec_paths(value: str) -> tuple[str | None, list[str]]:
    """Return executable and absolute path arguments, never the raw argv."""
    executable_match = re.search(r"(?:^|[ {])path=([^;}]+)", value)
    executable = _decode_systemd_path(executable_match.group(1).strip()) if executable_match else None

    argv_match = re.search(
        r"argv\[\]=(.*?)(?:\s*;\s*(?:ignore_errors|start_time|stop_time|pid|code|status)=|\s*})",
        value,
    )
    path_arguments: list[str] = []
    if argv_match:
        try:
            tokens = shlex.split(_decode_systemd_path(argv_match.group(1)))
        except ValueError:
            tokens = []
        for token in tokens[1:]:
            if token.startswith("/") and token not in path_arguments:
                path_arguments.append(token)
    return executable, path_arguments


def _path_state(raw_path: str | None, *, executable: bool = False) -> dict[str, Any] | None:
    if not raw_path or raw_path == "-":
        return None
    path = Path(raw_path).expanduser()
    exists = path.exists()
    result: dict[str, Any] = {"path": str(path), "exists": exists}
    if exists and path.is_file():
        result["executable"] = os.access(path, os.X_OK) if executable else None
    return result


def build_service_record(unit: str, properties: dict[str, str]) -> dict[str, Any]:
    """Create a redacted record: paths and selected state, never full ExecStart argv."""
    executable, path_arguments = _exec_paths(properties.get("ExecStart", ""))
    fragment = _path_state(properties.get("FragmentPath"))
    working = properties.get("WorkingDirectory", "")
    if working.startswith("-"):
        working = working[1:]
    working_state = _path_state(working) if working and working != "-" else None

    exec_state = _path_state(executable, executable=True)
    argument_states = [
        state for state in (_path_state(path) for path in path_arguments)
        if state is not None
    ]
    drop_ins = [
        state for state in (_path_state(path) for path in properties.get("DropInPaths", "").split())
        if state is not None
    ]

    missing = []
    for state in [fragment, working_state, exec_state, *argument_states, *drop_ins]:
        if state is not None and not state["exists"] and state["path"] not in missing:
            missing.append(state["path"])

    selected = {
        key: properties[key]
        for key in (
            "LoadState", "ActiveState", "SubState", "Result",
            "ExecMainCode", "ExecMainStatus", "MainPID", "NRestarts",
            "Restart", "RestartUSec", "RestartPreventExitStatus", "KillMode",
        )
        if key in properties
    }
    return {
        "unit": unit,
        "properties": selected,
        "fragment": fragment,
        "drop_ins": drop_ins,
        "working_directory": working_state,
        "exec_executable": exec_state,
        "exec_path_arguments": argument_states,
        "missing_paths": missing,
        "exec_start_arguments_redacted": True,
    }


def collect_service_audit(*, timeout: int = 15) -> dict[str, Any]:
    """Collect selected systemd state for four known units; no service actions."""
    systemctl = shutil.which("systemctl")
    if systemctl is None:
        return {
            "status": "SYSTEMCTL_UNAVAILABLE",
            "services": [],
            "note": "No systemctl executable was found; service state is unknown.",
        }

    try:
        manager = subprocess.run(
            [systemctl, "--user", "show-environment"],
            capture_output=True, text=True, timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "status": "USER_MANAGER_UNAVAILABLE",
            "error_type": type(exc).__name__,
            "services": [],
            "note": "The user service manager could not be queried; unit state is unknown.",
        }

    if manager.returncode != 0:
        return {
            "status": "USER_MANAGER_UNAVAILABLE",
            "return_code": manager.returncode,
            "services": [],
            "note": "The user service manager could not be queried; unit state is unknown.",
        }

    records = []
    for unit in SERVICES:
        try:
            completed = subprocess.run(
                [systemctl, "--user", "show", unit,
                 *[f"--property={name}" for name in PROPERTIES], "--no-pager"],
                capture_output=True, text=True, timeout=timeout, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            records.append({
                "unit": unit,
                "status": "QUERY_FAILED",
                "error_type": type(exc).__name__,
                "state": "UNKNOWN",
            })
            continue

        if completed.returncode != 0:
            records.append({
                "unit": unit,
                "status": "QUERY_FAILED",
                "return_code": completed.returncode,
                "state": "UNKNOWN",
            })
            continue

        properties = parse_properties(completed.stdout)
        record = build_service_record(unit, properties)
        record["status"] = "COLLECTED"
        if not properties:
            record["state"] = "UNKNOWN_EMPTY_PROPERTIES"
        records.append(record)

    return {
        "status": "COLLECTED",
        "services": records,
        "scope": list(SERVICES),
        "properties_requested": list(PROPERTIES),
        "read_only": True,
        "note": (
            "Only selected systemd properties and path-existence checks were collected. "
            "No unit file contents, environment values, or raw ExecStart arguments are emitted. "
            "No service lifecycle or configuration action was performed."
        ),
    }


def main() -> int:
    print(json.dumps(collect_service_audit(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
