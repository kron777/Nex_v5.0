"""Feed 2 — Papers With Code trending papers.

JSON API. Poll interval: 3600s.
"""
from __future__ import annotations

import json
import time
from typing import Optional

from substrate import Writer
from theory_x.stage1_sense.base import Adapter, RequestFn, SenseEvent

THEORY_X_STAGE = 1

_PWC_URL = "https://paperswithcode.com/api/v1/papers/"


class PapersWithCode(Adapter):
    id = "papers_with_code"
    stream = "ai_research.pwc"
    poll_interval_seconds = 3600
    provenance = _PWC_URL

    def __init__(self, writer: Writer, *, request_fn: Optional[RequestFn] = None) -> None:
        super().__init__(writer, request_fn=request_fn)

    def poll(self) -> list[SenseEvent]:
        raw = self._fetch(_PWC_URL, params={"ordering": "-published", "items_per_page": 20})
        data = json.loads(raw)
        results = data.get("results", data) if isinstance(data, dict) else data
        now = int(time.time())
        events: list[SenseEvent] = []
        for paper in results[:20]:
            payload = json.dumps(
                {
                    "title": paper.get("title", ""),
                    "arxiv_id": paper.get("arxiv_id", ""),
                    "url_pdf": paper.get("url_pdf", ""),
                    "url_abs": paper.get("url_abs", ""),
                    "published": paper.get("published", ""),
                    "authors": paper.get("authors", [])[:5],
                    "stars": paper.get("github_link", {}).get("stars", 0) if isinstance(paper.get("github_link"), dict) else 0,
                },
                ensure_ascii=False,
            )
            events.append(SenseEvent(stream=self.stream, payload=payload, provenance=self.provenance, timestamp=now))
        return events
