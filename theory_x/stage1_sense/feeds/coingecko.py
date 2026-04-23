"""Feed 14 — CoinGecko market data.

Top 20 coins by market cap via the free public CoinGecko API.
Returns one SenseEvent containing the full snapshot.
Poll interval: 60s.
"""
from __future__ import annotations

import json
import time
from typing import Optional

from substrate import Writer
from theory_x.stage1_sense.base import Adapter, RequestFn, SenseEvent

THEORY_X_STAGE = 1

_URL = "https://api.coingecko.com/api/v3/coins/markets"
_PARAMS = {
    "vs_currency": "usd",
    "order": "market_cap_desc",
    "per_page": 20,
    "page": 1,
    "sparkline": "false",
}


class CoinGecko(Adapter):
    id = "coingecko"
    stream = "crypto.coingecko"
    poll_interval_seconds = 60
    provenance = _URL

    def __init__(self, writer: Writer, *, request_fn: Optional[RequestFn] = None) -> None:
        super().__init__(writer, request_fn=request_fn)

    def poll(self) -> list[SenseEvent]:
        raw = self._fetch(_URL, params=_PARAMS)
        coins = json.loads(raw)
        now = int(time.time())
        snapshot = [
            {
                "id": c.get("id", ""),
                "symbol": c.get("symbol", ""),
                "name": c.get("name", ""),
                "current_price": c.get("current_price"),
                "market_cap": c.get("market_cap"),
                "price_change_24h": c.get("price_change_percentage_24h"),
                "volume_24h": c.get("total_volume"),
                "rank": c.get("market_cap_rank"),
            }
            for c in (coins if isinstance(coins, list) else [])
        ]
        return [
            SenseEvent(
                stream=self.stream,
                payload=json.dumps({"coins": snapshot, "fetched_at": now}, ensure_ascii=False),
                provenance=self.provenance,
                timestamp=now,
            )
        ]
