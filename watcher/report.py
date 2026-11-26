"""Structured reports — every item carries source, timestamp and evidence class,
and keeps the raw observation (`data`) separate from any interpretation.
"""
from __future__ import annotations

import collections
import json
from typing import List

from .evidence import Evidence, dumps


def _summary(records: List[Evidence]) -> str:
    by_origin = collections.Counter(r.origin for r in records)
    by_class = collections.Counter(r.evidence_class for r in records)
    return (f"- observations: **{len(records)}**  \n"
            f"- by origin: {dict(by_origin)}  \n"
            f"- by evidence class: {dict(by_class)}")


def render_markdown(records: List[Evidence], title: str = "NEX Watcher — Evidence Report") -> str:
    lines = [f"# {title}", ""]
    if records:
        lines.append(f"_Generated {records[0].collected_at} (first observation's clock)._")
    lines += ["", "## Summary", _summary(records), "",
              "> `data` is the raw observation; `interpretation` is a reading held separate from it. "
              "`origin=cloud` is static/GitHub; `origin=host` is the live machine (via Claude Code).",
              "", "## Observations", ""]
    for r in records:
        lines.append(f"### {r.subject}")
        lines.append(f"- **origin:** `{r.origin}` · **class:** `{r.evidence_class}`"
                     + (f" · **modifier:** `{r.modifier}`" if r.modifier else ""))
        lines.append(f"- **source:** `{r.source_ref}` · **at:** {r.collected_at}")
        data_str = json.dumps(r.data, indent=2, default=str)
        if len(data_str) > 1500:
            data_str = data_str[:1500] + "\n… (truncated)"
        lines.append(f"- **data:**\n\n```json\n{data_str}\n```")
        if r.interpretation:
            lines.append(f"- **interpretation:** {r.interpretation}")
        lines.append("")
    return "\n".join(lines)


def render_json(records: List[Evidence]) -> str:
    return dumps(records)
