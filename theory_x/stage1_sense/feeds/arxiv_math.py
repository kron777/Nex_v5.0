"""Feed 20 — arXiv Mathematics (math.GM general + math.HO history/overview).

Poll interval: 1800s (30 min).
"""
from __future__ import annotations

from typing import Optional

from substrate import Writer
from theory_x.stage1_sense.base import Adapter, RequestFn, SenseEvent
from ._helpers import parse_rss

THEORY_X_STAGE = 1

_URL_GM = "http://export.arxiv.org/rss/math.GM"
_URL_HO = "http://export.arxiv.org/rss/math.HO"


class ArxivMath(Adapter):
    id = "arxiv_math"
    stream = "mathematics.arxiv"
    poll_interval_seconds = 1800
    provenance = _URL_GM

    def __init__(self, writer: Writer, *, request_fn: Optional[RequestFn] = None) -> None:
        super().__init__(writer, request_fn=request_fn)

    def poll(self) -> list[SenseEvent]:
        events: list[SenseEvent] = []
        for url in (_URL_GM, _URL_HO):
            try:
                raw = self._fetch(url)
                events.extend(parse_rss(raw, self.stream, url, max_entries=10))
            except Exception:
                pass
        return events
