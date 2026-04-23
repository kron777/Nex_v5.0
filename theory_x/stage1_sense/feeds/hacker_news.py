"""Feed 5 — Hacker News.

Front page + new stories via the Algolia HN API (JSON).
Poll interval: 300s.
"""
from __future__ import annotations

import json
import time
from typing import Optional

from substrate import Writer
from theory_x.stage1_sense.base import Adapter, RequestFn, SenseEvent

THEORY_X_STAGE = 1

_HN_URL = "https://hn.algolia.com/api/v1/search_by_date"


class HackerNews(Adapter):
    id = "hacker_news"
    stream = "emerging_tech.hn"
    poll_interval_seconds = 300
    provenance = _HN_URL

    def __init__(self, writer: Writer, *, request_fn: Optional[RequestFn] = None) -> None:
        super().__init__(writer, request_fn=request_fn)

    def poll(self) -> list[SenseEvent]:
        raw = self._fetch(_HN_URL, params={"tags": "front_page", "hitsPerPage": 30})
        data = json.loads(raw)
        hits = data.get("hits", [])
        now = int(time.time())
        events: list[SenseEvent] = []
        for hit in hits:
            payload = json.dumps(
                {
                    "title": hit.get("title", ""),
                    "url": hit.get("url", ""),
                    "author": hit.get("author", ""),
                    "points": hit.get("points", 0),
                    "num_comments": hit.get("num_comments", 0),
                    "created_at": hit.get("created_at", ""),
                    "story_id": hit.get("story_id") or hit.get("objectID", ""),
                },
                ensure_ascii=False,
            )
            events.append(SenseEvent(stream=self.stream, payload=payload, provenance=self.provenance, timestamp=now))
        return events
