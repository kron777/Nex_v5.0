"""Feed 12 — arXiv computing.

Categories: cs.AR (computer architecture), cs.DC (distributed computing).
Poll interval: 3600s.
"""
from __future__ import annotations

from typing import Optional

from substrate import Writer
from theory_x.stage1_sense.base import Adapter, RequestFn, SenseEvent
from ._helpers import parse_rss

THEORY_X_STAGE = 1

_ARXIV_URL = "https://export.arxiv.org/api/query"
_CATEGORIES = "cat:cs.AR OR cat:cs.DC"


class ArxivComputing(Adapter):
    id = "arxiv_computing"
    stream = "computing.arxiv"
    poll_interval_seconds = 3600
    provenance = _ARXIV_URL

    def __init__(self, writer: Writer, *, request_fn: Optional[RequestFn] = None) -> None:
        super().__init__(writer, request_fn=request_fn)

    def poll(self) -> list[SenseEvent]:
        raw = self._fetch(
            _ARXIV_URL,
            params={
                "search_query": _CATEGORIES,
                "max_results": 15,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            },
        )
        return parse_rss(raw, self.stream, self.provenance)
