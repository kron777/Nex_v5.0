"""Feed 3 — AI lab blogs.

Anthropic, OpenAI, DeepMind, Meta AI RSS feeds. One adapter, four
sources. Each source is polled; events carry the source URL as
provenance. Poll interval: 1800s.
"""
from __future__ import annotations

from typing import Optional

from substrate import Writer
from theory_x.stage1_sense.base import Adapter, RequestFn, SenseEvent
from ._helpers import parse_rss

THEORY_X_STAGE = 1

_FEEDS = [
    ("anthropic", "https://www.anthropic.com/rss.xml"),
    ("openai",    "https://openai.com/news/rss.xml"),
    ("deepmind",  "https://deepmind.google/blog/rss.xml"),
    ("meta_ai",   "https://ai.meta.com/blog/rss/"),
]


class LabBlogs(Adapter):
    id = "lab_blogs"
    stream = "ai_research.lab_blogs"
    poll_interval_seconds = 1800
    provenance = ";".join(url for _, url in _FEEDS)

    def __init__(self, writer: Writer, *, request_fn: Optional[RequestFn] = None) -> None:
        super().__init__(writer, request_fn=request_fn)

    def poll(self) -> list[SenseEvent]:
        events: list[SenseEvent] = []
        for _name, url in _FEEDS:
            try:
                raw = self._fetch(url)
                events.extend(parse_rss(raw, self.stream, url, max_entries=5))
            except Exception:
                pass  # individual source failure is not fatal
        return events
