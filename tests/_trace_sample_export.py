"""Opt-in exporter for the isolated Phase-0 causal trace fixture artifact.

The normal test suite remains side-effect free. CI opts in by setting
NEX_CAUSAL_TRACE_SAMPLE_PATH; only metadata/digest trace rows from throwaway
fixtures are exported. This is not a live-runtime capture.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def append_trace_sample(kind: str, rows: Iterable[dict], checks: list[str]) -> None:
    destination = os.environ.get("NEX_CAUSAL_TRACE_SAMPLE_PATH")
    if not destination:
        return
    records = list(rows)
    if not records:
        raise AssertionError(f"cannot export empty {kind} trace")

    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    revision = os.environ.get("GITHUB_SHA") or "unknown"
    if path.exists():
        sample = json.loads(path.read_text(encoding="utf-8"))
        if sample.get("source_revision") != revision:
            sample = {}
    else:
        sample = {}

    if not sample:
        sample = {
            "schema_version": "1.0",
            "classification": "isolated_fixture_not_live_runtime",
            "source_revision": revision,
            "source_ref": os.environ.get("GITHUB_REF", "unknown"),
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "privacy": "metadata_and_payload_digests_only; no prompts, responses or database rows",
            "traces": {},
        }

    trace_id = records[0].get("trace_id")
    if any(row.get("trace_id") != trace_id for row in records):
        raise AssertionError(f"{kind} sample contains more than one trace_id")
    if records[0].get("event_type") != "trace_start" or records[-1].get("event_type") != "trace_end":
        raise AssertionError(f"{kind} sample is not a complete trace")
    sample["traces"][kind] = {
        "trace_id": trace_id,
        "record_count": len(records),
        "first_event": records[0].get("event_type"),
        "last_event": records[-1].get("event_type"),
        "off_on_equivalence": True,
        "checks": checks,
        "records": records,
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(sample, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
