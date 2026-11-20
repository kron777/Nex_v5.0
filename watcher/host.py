"""The host-side evidence collection — DESCRIBED here, executed only by Claude
Code on the machine. Cloud-side never runs these; it never pretends to have
observed the live machine.

`host_requests()` returns the read-only collection spec (the same shape dispatched
to Claude Code on the handoffs branch). `ingest_host_results()` turns the results
Claude Code returns into Evidence tagged origin='host', so cloud and host findings
stay distinguishable when combined.
"""
from __future__ import annotations

import dataclasses
from typing import Any, Dict, List

from .evidence import Evidence, utc_now


@dataclasses.dataclass(frozen=True)
class HostRequest:
    id: str
    title: str
    collects: str
    read_only_commands: List[str]


def host_requests() -> List[HostRequest]:
    """Read-only host-side collection. No exec of unknown tools, no writes, no
    restart, no config change, no cleanup."""
    return [
        HostRequest(
            "checkouts_drift", "Checkouts + deployment drift",
            "path, drive, SHA, dirty-state and drift-vs-GitHub for EVERY nex5 checkout",
            ["git -C <checkout> rev-parse HEAD",
             "git -C <checkout> status -s",
             "git -C <checkout> remote -v",
             "git -C <checkout> rev-list --left-right --count origin/main...HEAD"]),
        HostRequest(
            "runtime_identity", "Runtime state + process identity (if running)",
            "pid, checkout the live process runs from, NEX5_* flags; else confirm STANDBY",
            ["pgrep -af 'run.py|power_switch'",
             "tr '\\0' '\\n' < /proc/<pid>/environ | grep '^NEX5_'  # only if running"]),
        HostRequest(
            "classify_unknown_tools", "Classify the 5 unknown decryption tools (SOURCE ONLY)",
            "passive/isolated/active/unknown per tool, with cited side-effect lines",
            ["# read-only source inspection; DO NOT run them",
             "grep -nE 'INSERT|UPDATE|DELETE|\\.commit|subprocess|connect\\(' "
             "decryption/{atlas_builder,classifier,differential_analyzer,spark_detector,"
             "nex_cognition_simulator}.py"]),
        HostRequest(
            "live_db_metadata", "Live DB read-only metadata (mode=ro only)",
            "beliefs/dynamic/conversations DB paths, drive, row counts, WAL sizes",
            ["sqlite3 'file:<db>?mode=ro' 'SELECT COUNT(*) FROM <table>'  # mode=ro ONLY"]),
        HostRequest(
            "registry_state", "Experiment registry state",
            "observation_reports r78-r84 status + any open tripwire flag files (read-only)",
            ["ls observation_reports/ | grep -E 'r7[8-9]|r8[0-4]'"]),
    ]


def host_requests_as_data() -> List[dict]:
    return [dataclasses.asdict(h) for h in host_requests()]


def ingest_host_results(results: Dict[str, Any]) -> List[Evidence]:
    """Turn Claude Code's returned host findings into Evidence (origin='host').

    `results` maps a HostRequest.id -> {data, evidence_class, source_ref, note}.
    Anything not returned is recorded as an unverified host placeholder, so the
    gap is explicit rather than silently filled.
    """
    ids = {h.id for h in host_requests()}
    out: List[Evidence] = []
    for rid in sorted(ids):
        r = results.get(rid)
        if r is None:
            out.append(Evidence(f"host:{rid}", None, "host", "unknown",
                                "host (not yet returned)", modifier="unverified",
                                interpretation="awaiting Claude Code's host-side run"))
            continue
        out.append(Evidence(
            f"host:{rid}", r.get("data"), "host",
            r.get("evidence_class", "measured"),
            r.get("source_ref", f"host run {utc_now()}"),
            interpretation=r.get("note")))
    return out
