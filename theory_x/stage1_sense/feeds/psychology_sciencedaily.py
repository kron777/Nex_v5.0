"""Feed — ScienceDaily Mind & Brain (psychology, behaviour, cognition).

Fills a genuine gap: no psychology.* stream previously existed, so the
psychology BONSAI branch was starved (0.00). Adds human-behaviour / emotion /
social-psychology content the graph otherwise lacks — breadth to protect
synthesis from re-narrowing.

Poll interval: 1800s (30 min).
"""
from __future__ import annotations

from typing import Optional

from substrate import Writer
from theory_x.stage1_sense.base import Adapter, RequestFn, SenseEvent
from ._helpers import parse_rss

THEORY_X_STAGE = 1

_URL = "https://www.sciencedaily.com/rss/mind_brain/psychology.xml"


class PsychologyScienceDaily(Adapter):
    id = "psychology_sciencedaily"
    stream = "psychology.sciencedaily"
    poll_interval_seconds = 1800
    provenance = _URL

    def __init__(self, writer: Writer, *, request_fn: Optional[RequestFn] = None) -> None:
        super().__init__(writer, request_fn=request_fn)

    def poll(self) -> list[SenseEvent]:
        raw = self._fetch(_URL)
        return parse_rss(raw, self.stream, self.provenance, max_entries=10)
