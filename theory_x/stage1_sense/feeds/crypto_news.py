"""Feed 16 — Crypto news RSS.

The Block, CoinDesk, Decrypt. One adapter, three sources.
Poll interval: 900s.
"""
from __future__ import annotations

from typing import Optional

from substrate import Writer
from theory_x.stage1_sense.base import Adapter, RequestFn, SenseEvent
from ._helpers import parse_rss

THEORY_X_STAGE = 1

_FEEDS = [
    ("the_block",  "https://www.theblock.co/rss.xml"),
    ("coindesk",   "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("decrypt",    "https://decrypt.co/feed"),
]


class CryptoNews(Adapter):
    id = "crypto_news"
    stream = "crypto.news"
    poll_interval_seconds = 900
    provenance = ";".join(url for _, url in _FEEDS)

    def __init__(self, writer: Writer, *, request_fn: Optional[RequestFn] = None) -> None:
        super().__init__(writer, request_fn=request_fn)

    def poll(self) -> list[SenseEvent]:
        events: list[SenseEvent] = []
        for _name, url in _FEEDS:
            try:
                raw = self._fetch(url)
                events.extend(parse_rss(raw, self.stream, url, max_entries=8))
            except Exception:
                pass
        return events
