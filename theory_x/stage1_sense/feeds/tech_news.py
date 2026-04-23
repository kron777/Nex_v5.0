"""Feed 13 — Tech news RSS.

The Register, Ars Technica, AnandTech. One adapter, three sources.
Poll interval: 1800s.
"""
from __future__ import annotations

from typing import Optional

from substrate import Writer
from theory_x.stage1_sense.base import Adapter, RequestFn, SenseEvent
from ._helpers import parse_rss

THEORY_X_STAGE = 1

_FEEDS = [
    ("the_register", "https://www.theregister.com/headlines.atom"),
    ("ars_technica",  "https://feeds.arstechnica.com/arstechnica/index"),
    ("anandtech",     "https://www.anandtech.com/rss/"),
]


class TechNews(Adapter):
    id = "tech_news"
    stream = "computing.tech_news"
    poll_interval_seconds = 1800
    provenance = ";".join(url for _, url in _FEEDS)

    def __init__(self, writer: Writer, *, request_fn: Optional[RequestFn] = None) -> None:
        super().__init__(writer, request_fn=request_fn)

    def poll(self) -> list[SenseEvent]:
        events: list[SenseEvent] = []
        for _name, url in _FEEDS:
            try:
                raw = self._fetch(url)
                events.extend(parse_rss(raw, self.stream, url, max_entries=8))
            except Exception:
                pass
        return events
