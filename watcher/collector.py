"""Cloud-side evidence collection + a simple baseline/treatment comparator.

Orchestrates the passive cloud collectors into one list of Evidence (all
origin='cloud'). Host-side evidence is ingested separately (see watcher.host) and
carries origin='host'; the two are never conflated.
"""
from __future__ import annotations

import os
from typing import Dict, List

from . import adapters, architecture, provenance, registry
from .evidence import Evidence
from .host import ingest_host_results


def collect_cloud(repo_dir: str = ".",
                  mind_map_path: str = "mind_map/MIND_MAP.yaml",
                  dag_path: str = "sentience_dag.json",
                  obs_dir: str = "observation_reports") -> List[Evidence]:
    """Run every passive cloud collector. Read-only."""
    records: List[Evidence] = []
    records += provenance.collect(repo_dir)
    records += architecture.collect(os.path.join(repo_dir, mind_map_path),
                                    os.path.join(repo_dir, dag_path))
    records += registry.collect(os.path.join(repo_dir, obs_dir))
    records += adapters.collect(repo_dir)
    return records


def collect_combined(repo_dir: str = ".",
                     host_results: Dict | None = None,
                     **cloud_kwargs) -> List[Evidence]:
    """Cloud evidence PLUS host evidence, with origins preserved.

    Cloud records (origin='cloud') come from `collect_cloud`. Host records
    (origin='host') come from `watcher.host.ingest_host_results`: real findings
    when Claude Code has returned them, honest `unknown` placeholders where it has
    not. The two sets are concatenated, never merged into a single claim — every
    record keeps its own origin, so a combined report can never pass a cloud/static
    reading off as a live-machine observation."""
    records = collect_cloud(repo_dir, **cloud_kwargs)
    records += ingest_host_results(host_results or {})
    return records


def compare(baseline: List[Evidence], treatment: List[Evidence]) -> Dict[str, list]:
    """Compare two evidence sets by subject. Reports changed / added / missing —
    the skeleton of the Watcher's comparator; magnitude/scoring is deliberately
    out of scope for this first version (observe, don't optimise)."""
    b = {e.subject: e for e in baseline}
    t = {e.subject: e for e in treatment}
    changed, added, missing, same = [], [], [], []
    for subj in sorted(set(b) | set(t)):
        if subj in b and subj in t:
            (changed if b[subj].data != t[subj].data else same).append(subj)
        elif subj in t:
            added.append(subj)
        else:
            missing.append(subj)
    return {"changed": changed, "added": added, "missing": missing, "unchanged": same}
