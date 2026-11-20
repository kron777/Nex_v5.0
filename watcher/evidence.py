"""Evidence schema — the one record type every observation becomes.

Reuses NEX's own evidence vocabulary (from `mind_map/MIND_MAP.yaml`
`meta.evidence_classes` / `meta.modifiers`) so the Watcher speaks the same
language as the system it observes, rather than inventing a competing one.

Each record pins down four things the project cares about:
  * origin         — WHERE it was observed: 'cloud' (static/GitHub) or 'host'
                     (the live machine, via Claude Code). Cloud evidence must
                     never claim to have seen the live machine.
  * collected_at   — WHEN, in UTC.
  * evidence_class — HOW strong: measured | implemented | static | inferred | unknown.
  * source_ref     — WHAT backs it: a file path, git ref, tool name or command.

`data` is the raw observation. `interpretation` is a reading of it, kept
explicitly separate so interpretation is never presented as fact.
"""
from __future__ import annotations

import dataclasses
import datetime
import json
from typing import Any, Optional

# NEX's vocabulary (mind_map meta). Do not extend without a reason.
EVIDENCE_CLASSES = ("measured", "implemented", "static", "inferred", "unknown")
MODIFIERS = ("dark", "blocked", "unverified")
ORIGINS = ("cloud", "host")


def utc_now() -> str:
    """UTC timestamp, seconds precision, ISO-8601."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


@dataclasses.dataclass(frozen=True)
class Evidence:
    subject: str
    data: Any
    origin: str
    evidence_class: str
    source_ref: str
    collected_at: str = dataclasses.field(default_factory=utc_now)
    modifier: Optional[str] = None
    interpretation: Optional[str] = None

    def __post_init__(self) -> None:
        if self.origin not in ORIGINS:
            raise ValueError(f"origin must be one of {ORIGINS}, got {self.origin!r}")
        if self.evidence_class not in EVIDENCE_CLASSES:
            raise ValueError(
                f"evidence_class must be one of {EVIDENCE_CLASSES}, got {self.evidence_class!r}"
            )
        if self.modifier is not None and self.modifier not in MODIFIERS:
            raise ValueError(f"modifier must be one of {MODIFIERS} or None, got {self.modifier!r}")

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


def host_placeholder(subject: str, source_ref: str, note: str) -> "Evidence":
    """An honest stand-in for something only the host can observe.

    Cloud-side code uses this to RECORD that a fact is unavailable rather than
    guessing it. evidence_class is 'unknown' and origin is 'host' with the
    'unverified' modifier, so it can never be mistaken for a real observation.
    """
    return Evidence(
        subject=subject,
        data=None,
        origin="host",
        evidence_class="unknown",
        source_ref=source_ref,
        modifier="unverified",
        interpretation=note,
    )


def dumps(records) -> str:
    """Serialise a list of Evidence to pretty JSON."""
    return json.dumps([r.to_dict() for r in records], indent=2, default=str)
