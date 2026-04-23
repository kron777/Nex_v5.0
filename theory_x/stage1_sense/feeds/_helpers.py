"""Shared parsing helpers for feed adapters.

Not an Adapter subclass — a utility module imported by individual
adapters. Keeps common feedparser/JSON boilerplate out of each file.
"""
from __future__ import annotations

import json
import time
from typing import Any

import feedparser

from theory_x.stage1_sense.base import SenseEvent

THEORY_X_STAGE = 1


def parse_rss(
    raw: str,
    stream: str,
    provenance: str,
    max_entries: int = 20,
) -> list[SenseEvent]:
    """Parse an RSS or Atom feed string. Works with arXiv Atom too."""
    feed = feedparser.parse(raw)
    now = int(time.time())
    events: list[SenseEvent] = []
    for entry in feed.entries[:max_entries]:
        payload = json.dumps(
            {
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "summary": (entry.get("summary") or "")[:600],
                "published": entry.get("published", ""),
                "authors": [
                    a.get("name", "") for a in entry.get("authors", [])
                ],
                "tags": [t.get("term", "") for t in entry.get("tags", [])],
            },
            ensure_ascii=False,
        )
        events.append(
            SenseEvent(stream=stream, payload=payload, provenance=provenance, timestamp=now)
        )
    return events


def parse_json(
    data: Any,
    stream: str,
    provenance: str,
    extract_fn: "Any" = None,
) -> list[SenseEvent]:
    """Wrap a JSON payload as a single SenseEvent. `extract_fn`, if given,
    transforms the data before serialisation."""
    now = int(time.time())
    content = extract_fn(data) if extract_fn else data
    return [
        SenseEvent(
            stream=stream,
            payload=json.dumps(content, ensure_ascii=False),
            provenance=provenance,
            timestamp=now,
        )
    ]
