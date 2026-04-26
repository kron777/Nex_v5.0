"""Feed 29 — arXiv q-bio.NC (quantitative biology — neurons & cognition).

Neuroscience preprints covering neural computation, cognitive modelling,
and consciousness research. Complements cs.AI with a biological angle.
Poll interval: 1800s.
"""
from __future__ import annotations

from typing import Optional

from substrate import Writer
from theory_x.stage1_sense.base import Adapter, RequestFn, SenseEvent
from ._helpers import parse_rss

THEORY_X_STAGE = 1

_URL = "http://export.arxiv.org/rss/q-bio.NC"


class ArxivQbioNC(Adapter):
    id = "arxiv_qbio_nc"
    stream = "neuroscience.arxiv_qbio"
    poll_interval_seconds = 1800
    provenance = _URL

    def __init__(self, writer: Writer, *, request_fn: Optional[RequestFn] = None) -> None:
        super().__init__(writer, request_fn=request_fn)

    def poll(self) -> list[SenseEvent]:
        raw = self._fetch(_URL)
        return parse_rss(raw, self.stream, self.provenance, max_entries=15)
