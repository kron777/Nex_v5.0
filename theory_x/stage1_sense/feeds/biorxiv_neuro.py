"""Feed 9 — bioRxiv neuroscience RSS. Poll interval: 3600s."""
from __future__ import annotations

from typing import Optional

from substrate import Writer
from theory_x.stage1_sense.base import Adapter, RequestFn, SenseEvent
from ._helpers import parse_rss

THEORY_X_STAGE = 1

_URL = "https://connect.biorxiv.org/biorxiv_xml.php?subject=neuroscience"


class BiorxivNeuro(Adapter):
    id = "biorxiv_neuro"
    stream = "cognition.biorxiv"
    poll_interval_seconds = 3600
    provenance = _URL

    def __init__(self, writer: Writer, *, request_fn: Optional[RequestFn] = None) -> None:
        super().__init__(writer, request_fn=request_fn)

    def poll(self) -> list[SenseEvent]:
        raw = self._fetch(_URL)
        return parse_rss(raw, self.stream, self.provenance)
