"""Feed 1 — arXiv AI research.

Categories: cs.AI, cs.LG, cs.CL, cs.NE. Daily pull via arXiv Atom API.
Poll interval: 3600s.
"""
from __future__ import annotations

from typing import Optional

from substrate import Writer
from theory_x.stage1_sense.base import Adapter, RequestFn, SenseEvent
from ._helpers import parse_rss

THEORY_X_STAGE = 1

_ARXIV_URL = "https://export.arxiv.org/api/query"
_CATEGORIES = "cat:cs.AI OR cat:cs.LG OR cat:cs.CL OR cat:cs.NE"


class ArxivAI(Adapter):
    id = "arxiv_ai"
    stream = "ai_research.arxiv"
    poll_interval_seconds = 3600
    provenance = _ARXIV_URL

    def __init__(self, writer: Writer, *, request_fn: Optional[RequestFn] = None) -> None:
        super().__init__(writer, request_fn=request_fn)

    def poll(self) -> list[SenseEvent]:
        raw = self._fetch(
            _ARXIV_URL,
            params={
                "search_query": _CATEGORIES,
                "max_results": 20,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            },
        )
        return parse_rss(raw, self.stream, self.provenance)
