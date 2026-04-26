"""Feed 28 — arXiv cs.AI RSS (dedicated AGI/AI-safety preprints).

Uses the category RSS endpoint (not the API query used by arxiv_ai.py),
giving a different cut of cs.AI submissions with richer metadata.
Poll interval: 1800s.
"""
from __future__ import annotations

from typing import Optional

from substrate import Writer
from theory_x.stage1_sense.base import Adapter, RequestFn, SenseEvent
from ._helpers import parse_rss

THEORY_X_STAGE = 1

_URL = "http://export.arxiv.org/rss/cs.AI"


class ArxivCsAI(Adapter):
    id = "arxiv_cs_ai"
    stream = "agi.arxiv_cs_ai"
    poll_interval_seconds = 1800
    provenance = _URL

    def __init__(self, writer: Writer, *, request_fn: Optional[RequestFn] = None) -> None:
        super().__init__(writer, request_fn=request_fn)

    def poll(self) -> list[SenseEvent]:
        raw = self._fetch(_URL)
        return parse_rss(raw, self.stream, self.provenance, max_entries=15)
