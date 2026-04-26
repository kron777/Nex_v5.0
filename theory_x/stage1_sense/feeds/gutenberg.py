"""Feed 25 — Project Gutenberg daily new additions (classic literature).

Poll interval: 1800s (30 min).
"""
from __future__ import annotations

from typing import Optional

from substrate import Writer
from theory_x.stage1_sense.base import Adapter, RequestFn, SenseEvent
from ._helpers import parse_rss

THEORY_X_STAGE = 1

_URL = "https://www.gutenberg.org/cache/epub/feeds/today.rss"


class Gutenberg(Adapter):
    id = "gutenberg"
    stream = "literature.gutenberg"
    poll_interval_seconds = 1800
    provenance = _URL

    def __init__(self, writer: Writer, *, request_fn: Optional[RequestFn] = None) -> None:
        super().__init__(writer, request_fn=request_fn)

    def poll(self) -> list[SenseEvent]:
        raw = self._fetch(_URL)
        return parse_rss(raw, self.stream, self.provenance, max_entries=10)
