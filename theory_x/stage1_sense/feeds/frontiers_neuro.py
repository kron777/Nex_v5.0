"""Feed 10 — Frontiers in Neuroscience RSS. Poll interval: 3600s."""
from __future__ import annotations

from typing import Optional

from substrate import Writer
from theory_x.stage1_sense.base import Adapter, RequestFn, SenseEvent
from ._helpers import parse_rss

THEORY_X_STAGE = 1

_URL = "https://www.frontiersin.org/journals/neuroscience/rss"


class FrontiersNeuro(Adapter):
    id = "frontiers_neuro"
    stream = "cognition.frontiers"
    poll_interval_seconds = 3600
    provenance = _URL

    def __init__(self, writer: Writer, *, request_fn: Optional[RequestFn] = None) -> None:
        super().__init__(writer, request_fn=request_fn)

    def poll(self) -> list[SenseEvent]:
        raw = self._fetch(_URL)
        return parse_rss(raw, self.stream, self.provenance)
