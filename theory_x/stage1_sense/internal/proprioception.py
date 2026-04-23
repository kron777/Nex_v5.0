"""Feed 20 — Proprioception.

System-level body sense: CPU usage, memory usage, thermal readings,
load average. NEX knows how hot and busy she is.

Always enabled. Poll interval: 10s.
"""
from __future__ import annotations

import time
from typing import Optional

import psutil

import errors as error_channel
from substrate import Writer
from theory_x.stage1_sense.base import Adapter, RequestFn, SenseEvent

THEORY_X_STAGE = 1


class Proprioception(Adapter):
    id = "proprioception"
    stream = "internal.proprioception"
    poll_interval_seconds = 10
    provenance = "substrate://system"
    is_internal = True

    def __init__(self, writer: Writer, *, request_fn: Optional[RequestFn] = None) -> None:
        super().__init__(writer, request_fn=request_fn)

    def poll(self) -> list[SenseEvent]:
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            load = psutil.getloadavg() if hasattr(psutil, "getloadavg") else (0.0, 0.0, 0.0)

            thermal: dict = {}
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        if entries:
                            thermal[name] = round(entries[0].current, 1)
            except (AttributeError, Exception):
                pass

            payload = self.pack(
                cpu_percent=round(cpu, 1),
                mem_percent=round(mem.percent, 1),
                mem_available_mb=round(mem.available / 1024 / 1024, 1),
                load_1m=round(load[0], 2),
                load_5m=round(load[1], 2),
                load_15m=round(load[2], 2),
                thermal=thermal,
            )
            return [SenseEvent(
                stream=self.stream,
                payload=payload,
                provenance=self.provenance,
                timestamp=self.now(),
            )]
        except Exception as e:
            error_channel.record(
                f"proprioception.poll error: {e}",
                source="adapter[proprioception]",
                exc=e,
            )
            return []
