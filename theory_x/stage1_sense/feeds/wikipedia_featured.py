"""Feed 24 — Wikipedia Featured Article (daily rotating Atom feed).

Poll interval: 1800s (30 min).
"""
from __future__ import annotations

from typing import Optional

from substrate import Writer
from theory_x.stage1_sense.base import Adapter, RequestFn, SenseEvent
from ._helpers import parse_rss

THEORY_X_STAGE = 1

_URL = (
    "https://en.wikipedia.org/w/api.php"
    "?action=featuredfeed&feed=featured&feedformat=atom"
)


class WikipediaFeatured(Adapter):
    id = "wikipedia_featured"
    stream = "history.wikipedia_featured"
    poll_interval_seconds = 1800
    provenance = _URL

    def __init__(self, writer: Writer, *, request_fn: Optional[RequestFn] = None) -> None:
        super().__init__(writer, request_fn=request_fn)

    def poll(self) -> list[SenseEvent]:
        raw = self._fetch(_URL)
        return parse_rss(raw, self.stream, self.provenance, max_entries=5)
