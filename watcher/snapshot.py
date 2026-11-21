"""Before/after snapshots of the evidence set.

A snapshot is a timestamped, serialised capture of a list of `Evidence`. Two
snapshots can be diffed by subject to see what an integration step changed — the
foundation for regression detection (`watcher.regression`) and longitudinal
series (`watcher.longitudinal`).

Snapshots are plain JSON: portable, diffable, and safe to keep under
`watcher/reports/` (git-ignored) or hand to Claude Code. Writing a snapshot never
touches NEX — it only serialises observations already collected.
"""
from __future__ import annotations

import json
import os
import re
from typing import Dict, List

from .evidence import Evidence, utc_now

SCHEMA = "nex-watcher/snapshot/v1"


def snapshot_dict(records: List[Evidence], label: str, stage: str | None = None) -> dict:
    """Build the in-memory snapshot structure (no I/O)."""
    return {
        "schema": SCHEMA,
        "label": label,
        "stage": stage,                      # optional integration-stage tag
        "taken_at": utc_now(),
        "count": len(records),
        "records": [r.to_dict() for r in records],
    }


def _safe(label: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", label).strip("-") or "snapshot"


def take_snapshot(records: List[Evidence], label: str, out_dir: str,
                  stage: str | None = None) -> str:
    """Serialise `records` to `out_dir/snapshot_<label>_<ts>.json`; return the path."""
    os.makedirs(out_dir, exist_ok=True)
    snap = snapshot_dict(records, label, stage)
    ts = snap["taken_at"].replace(":", "").replace("-", "")
    path = os.path.join(out_dir, f"snapshot_{_safe(label)}_{ts}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(snap, fh, indent=2, default=str)
    return path


def load_snapshot(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        snap = json.load(fh)
    if snap.get("schema") != SCHEMA:
        raise ValueError(f"not a {SCHEMA} snapshot: {path}")
    return snap


def records_from_snapshot(snap: dict) -> List[Evidence]:
    """Reconstruct Evidence objects from a loaded snapshot."""
    out: List[Evidence] = []
    for d in snap.get("records", []):
        out.append(Evidence(
            subject=d["subject"], data=d.get("data"), origin=d["origin"],
            evidence_class=d["evidence_class"], source_ref=d.get("source_ref", ""),
            collected_at=d.get("collected_at", utc_now()),
            modifier=d.get("modifier"), interpretation=d.get("interpretation")))
    return out


def _by_subject(snap: dict) -> Dict[str, dict]:
    # last record wins if a subject appears twice
    return {d["subject"]: d for d in snap.get("records", [])}


def diff_snapshots(before: dict, after: dict) -> dict:
    """Diff two snapshots by subject.

    Returns added / removed subjects and, for subjects in both, a per-field change
    list covering data, evidence_class and modifier. `unchanged` lists subjects
    whose data, class and modifier all match.
    """
    b, a = _by_subject(before), _by_subject(after)
    added = sorted(set(a) - set(b))
    removed = sorted(set(b) - set(a))
    changed: List[dict] = []
    unchanged: List[str] = []
    for subj in sorted(set(a) & set(b)):
        fields = {}
        for f in ("data", "evidence_class", "modifier"):
            if b[subj].get(f) != a[subj].get(f):
                fields[f] = {"before": b[subj].get(f), "after": a[subj].get(f)}
        (changed.append({"subject": subj, "fields": fields}) if fields
         else unchanged.append(subj))
    return {
        "before_label": before.get("label"), "after_label": after.get("label"),
        "before_stage": before.get("stage"), "after_stage": after.get("stage"),
        "added": added, "removed": removed, "changed": changed, "unchanged": unchanged,
    }
