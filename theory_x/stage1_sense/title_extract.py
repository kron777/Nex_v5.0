"""Sense title extractor — shared utility for stage1 and stage6.

extract_sense_title() is the canonical title-extraction function for
sense event payloads. It was originally _extract_sense_summary() on
FountainGenerator; moved here so stage2_dynamic can import it without
a stage2→stage6 cross-stage dependency.

Per §0: no content-meaning filtering. Only format transformation —
JSON → readable text. Relevance decisions stay in the substrate.
"""
from __future__ import annotations

import json

THEORY_X_STAGE = 1


def extract_sense_title(
    stream: str, payload: str, max_items: int = 3
) -> "str | None":
    """Return a human-readable string from a sense payload, or None.

    JSON objects/arrays: extracts title/headline/name/subject fields
    (up to max_items, joined with ·).  Plain text: returned as-is,
    truncated at 200 chars.  Malformed JSON, empty payload: None.
    """
    if not payload or not payload.strip():
        return None

    stripped = payload.lstrip()
    if not (stripped.startswith("{") or stripped.startswith("[")):
        return payload[:200] if len(payload) > 200 else payload

    try:
        data = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return None

    titles: list[str] = []

    def _collect(obj: object) -> None:
        if len(titles) >= max_items:
            return
        if isinstance(obj, dict):
            for key in ("title", "headline", "name", "subject"):
                val = obj.get(key)
                if isinstance(val, str) and val.strip():
                    titles.append(val.strip())
                    if len(titles) >= max_items:
                        return
                    break
            for key in ("items", "results", "entries", "coins", "data"):
                if key in obj and isinstance(obj[key], list):
                    _collect(obj[key])
                    if len(titles) >= max_items:
                        return
        elif isinstance(obj, list):
            for item in obj:
                _collect(item)
                if len(titles) >= max_items:
                    return

    _collect(data)

    if not titles:
        return None
    return " · ".join(titles)
