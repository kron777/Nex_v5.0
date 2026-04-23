"""Feed 21 — Temporal.

Time-texture signals: unix epoch, hour-of-day, day-of-week,
day-of-year, ISO datetime string. NEX has a sense of when she is.

Always enabled. Poll interval: 60s.
"""
from __future__ import annotations

import datetime
from typing import Optional

from substrate import Writer
from theory_x.stage1_sense.base import Adapter, RequestFn, SenseEvent

THEORY_X_STAGE = 1


class Temporal(Adapter):
    id = "temporal"
    stream = "internal.temporal"
    poll_interval_seconds = 60
    provenance = "substrate://clock"
    is_internal = True

    def __init__(self, writer: Writer, *, request_fn: Optional[RequestFn] = None) -> None:
        super().__init__(writer, request_fn=request_fn)

    def poll(self) -> list[SenseEvent]:
        now = datetime.datetime.now()
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        ts = int(now.timestamp())
        payload = self.pack(
            unix_timestamp=ts,
            iso_local=now.isoformat(timespec="seconds"),
            iso_utc=utc_now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            hour_of_day=now.hour,
            minute_of_hour=now.minute,
            day_of_week=now.weekday(),       # 0=Monday
            day_of_week_name=now.strftime("%A"),
            day_of_year=now.timetuple().tm_yday,
            week_of_year=int(now.strftime("%W")),
            month=now.month,
            year=now.year,
        )
        return [SenseEvent(
            stream=self.stream,
            payload=payload,
            provenance=self.provenance,
            timestamp=ts,
        )]
