"""Feed 15 — Exchange prices.

Binance, Coinbase, Kraken public ticker APIs for BTC, ETH, SOL, BNB.
One SenseEvent per exchange per poll. Poll interval: 60s.
"""
from __future__ import annotations

import json
import time
from typing import Optional

from substrate import Writer
from theory_x.stage1_sense.base import Adapter, RequestFn, SenseEvent

THEORY_X_STAGE = 1

_BINANCE_URL = "https://api.binance.com/api/v3/ticker/price"
_COINBASE_URL = "https://api.coinbase.com/v2/prices/{pair}/spot"
_KRAKEN_URL   = "https://api.kraken.com/0/public/Ticker"

_BINANCE_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
_COINBASE_PAIRS  = ["BTC-USD", "ETH-USD", "SOL-USD"]
_KRAKEN_PAIRS    = "XBTUSD,ETHUSD,SOLUSD"


class ExchangePrices(Adapter):
    id = "exchange_prices"
    stream = "crypto.exchanges"
    poll_interval_seconds = 60
    provenance = f"{_BINANCE_URL};{_COINBASE_URL};{_KRAKEN_URL}"

    def __init__(self, writer: Writer, *, request_fn: Optional[RequestFn] = None) -> None:
        super().__init__(writer, request_fn=request_fn)

    def poll(self) -> list[SenseEvent]:
        now = int(time.time())
        events: list[SenseEvent] = []

        # Binance
        try:
            prices = {}
            for sym in _BINANCE_SYMBOLS:
                raw = self._fetch(_BINANCE_URL, params={"symbol": sym})
                d = json.loads(raw)
                prices[d["symbol"]] = float(d["price"])
            events.append(SenseEvent(
                stream=self.stream,
                payload=json.dumps({"exchange": "binance", "prices": prices, "fetched_at": now}),
                provenance=_BINANCE_URL,
                timestamp=now,
            ))
        except Exception:
            pass

        # Coinbase
        try:
            prices = {}
            for pair in _COINBASE_PAIRS:
                raw = self._fetch(_COINBASE_URL.format(pair=pair))
                d = json.loads(raw)
                prices[pair] = float(d.get("data", {}).get("amount", 0))
            events.append(SenseEvent(
                stream=self.stream,
                payload=json.dumps({"exchange": "coinbase", "prices": prices, "fetched_at": now}),
                provenance=_COINBASE_URL,
                timestamp=now,
            ))
        except Exception:
            pass

        # Kraken
        try:
            raw = self._fetch(_KRAKEN_URL, params={"pair": _KRAKEN_PAIRS})
            d = json.loads(raw)
            result = d.get("result", {})
            prices = {pair: float(info["c"][0]) for pair, info in result.items() if "c" in info}
            events.append(SenseEvent(
                stream=self.stream,
                payload=json.dumps({"exchange": "kraken", "prices": prices, "fetched_at": now}),
                provenance=_KRAKEN_URL,
                timestamp=now,
            ))
        except Exception:
            pass

        return events
