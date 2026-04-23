"""Feed 11 — PhilPapers philosophy of mind RSS. Poll interval: 7200s."""
from __future__ import annotations

from typing import Optional

from substrate import Writer
from theory_x.stage1_sense.base import Adapter, RequestFn, SenseEvent
from ._helpers import parse_rss

THEORY_X_STAGE = 1

_URL = "https://philpapers.org/rss/min_areas.pl?area=phi"


class PhilPapers(Adapter):
    id = "philpapers"
    stream = "cognition.philpapers"
    poll_interval_seconds = 7200
    provenance = _URL

    def __init__(self, writer: Writer, *, request_fn: Optional[RequestFn] = None) -> None:
        super().__init__(writer, request_fn=request_fn)

    def poll(self) -> list[SenseEvent]:
        raw = self._fetch(_URL)
        return parse_rss(raw, self.stream, self.provenance)
