"""Feed 4 — ML conference proceedings.

NeurIPS, ICML, ICLR RSS feeds. Poll interval: 86400s (daily).
"""
from __future__ import annotations

from typing import Optional

from substrate import Writer
from theory_x.stage1_sense.base import Adapter, RequestFn, SenseEvent
from ._helpers import parse_rss

THEORY_X_STAGE = 1

_FEEDS = [
    ("neurips", "https://papers.nips.cc/static/feed.xml"),
    ("icml",    "https://icml.cc/static/core/img/ICML_icon.png"),  # placeholder — ICML has no public RSS
    ("iclr",    "https://openreview.net/rss"),
]

# Filter to just feeds that have real RSS. ICML has no consistent RSS;
# keep the slot so Phase 3 can point it at proceedings once released.
_ACTIVE_FEEDS = [
    ("neurips", "https://papers.nips.cc/static/feed.xml"),
    ("iclr",    "https://openreview.net/rss"),
]


class MLConferences(Adapter):
    id = "ml_conferences"
    stream = "ai_research.conferences"
    poll_interval_seconds = 86400
    provenance = ";".join(url for _, url in _ACTIVE_FEEDS)

    def __init__(self, writer: Writer, *, request_fn: Optional[RequestFn] = None) -> None:
        super().__init__(writer, request_fn=request_fn)

    def poll(self) -> list[SenseEvent]:
        events: list[SenseEvent] = []
        for _name, url in _ACTIVE_FEEDS:
            try:
                raw = self._fetch(url)
                events.extend(parse_rss(raw, self.stream, url, max_entries=10))
            except Exception:
                pass
        return events
