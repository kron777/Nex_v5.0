"""Experiment-registry ingestion from the existing rNN records.

The project already runs a pre-registration-based experiment program in
`observation_reports/` (rNN final reports, rNN_PREREGISTRATION.md, rNN_baselines/,
and *_tripwire_log.jsonl). The Watcher INGESTS these read-only as the canonical
registry — it never modifies a record. An experiment with a preregistration but
no final report is an ACTIVE/PENDING window that must not be contaminated.
"""
from __future__ import annotations

import os
import re
from typing import Dict, List

from .evidence import Evidence

_RN = re.compile(r"(r\d+)")


def ingest_registry(obs_dir: str) -> Evidence:
    """Read observation_reports/ into a per-experiment registry (read-only)."""
    reg: Dict[str, dict] = {}

    def slot(name: str) -> dict:
        m = _RN.match(name)
        key = m.group(1) if m else name.split("_")[0]
        return reg.setdefault(key, {"report": False, "preregistration": False,
                                    "baselines": False, "tripwire_logs": [], "other": []})

    try:
        entries = sorted(os.listdir(obs_dir))
    except FileNotFoundError:
        return Evidence("experiment_registry", None, "cloud", "unknown", obs_dir,
                        modifier="unverified", interpretation="observation_reports not found")

    for name in entries:
        full = os.path.join(obs_dir, name)
        s = slot(name)
        low = name.lower()
        if re.fullmatch(r"r\d+\.md", name):
            s["report"] = True
        elif "preregistration" in low:
            s["preregistration"] = True
        elif os.path.isdir(full) and "baseline" in low:
            s["baselines"] = True
        elif "tripwire" in low and low.endswith((".jsonl", ".json", ".log")):
            s["tripwire_logs"].append(name)
        else:
            s["other"].append(name)

    active = sorted(k for k, v in reg.items()
                    if v["preregistration"] and not v["report"])
    reported = sorted(k for k, v in reg.items() if v["report"])
    data = {"experiments": reg,
            "reported": reported,
            "active_or_pending": active,
            "counts": {"total": len(reg), "reported": len(reported), "active": len(active)}}
    return Evidence(
        "experiment_registry", data, "cloud", "measured", obs_dir,
        interpretation="Canonical rNN registry, ingested read-only. 'active_or_pending' "
                       "experiments (preregistration, no final report) must NOT be contaminated.")


def collect(obs_dir: str) -> List[Evidence]:
    return [ingest_registry(obs_dir)]
