"""Feed 18 — Associated Press RSS. Poll interval: 900s.

REMOVED FROM build_scheduler() 2026-07-25: feeds.apnews.com has been
NXDOMAIN since this system's build (2026-04-23) -- zero successful polls
ever, confirmed via public DNS (8.8.8.8), not just this box's resolver.
apnews.com itself resolves fine; only the feeds. subdomain is gone -- AP
retired public RSS years before this was built. Class kept for its unit
tests (test_sense.py exercises it directly against a fixture, not via
build_scheduler()) and in case AP ever ships a replacement feed URL. Do
not re-add to build_scheduler() without first confirming
feeds.apnews.com resolves again.
"""
from __future__ import annotations

from typing import Optional

from substrate import Writer
from theory_x.stage1_sense.base import Adapter, RequestFn, SenseEvent
from ._helpers import parse_rss

THEORY_X_STAGE = 1

_URL = "https://feeds.apnews.com/rss/apf-topnews"


class APNews(Adapter):
    id = "ap_news"
    stream = "news.ap"
    poll_interval_seconds = 900
    provenance = _URL

    def __init__(self, writer: Writer, *, request_fn: Optional[RequestFn] = None) -> None:
        super().__init__(writer, request_fn=request_fn)

    def poll(self) -> list[SenseEvent]:
        raw = self._fetch(_URL)
        return parse_rss(raw, self.stream, self.provenance)
