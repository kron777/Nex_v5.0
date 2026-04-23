"""Feed 23 — Meta-awareness.

Substrate self-observation: Writer queue depths per DB, error channel
length, sense scheduler global state, adapter counts.

Receives a late-bound state dict so it can be constructed before the
scheduler exists. The dict is populated by the factory after the
scheduler is created; poll() reads from it lazily.

Always enabled. Poll interval: 10s.
"""
from __future__ import annotations

from typing import Any, Optional

import errors as error_channel
from substrate import Writer
from theory_x.stage1_sense.base import Adapter, RequestFn, SenseEvent

THEORY_X_STAGE = 1


class MetaAwareness(Adapter):
    id = "meta_awareness"
    stream = "internal.meta_awareness"
    poll_interval_seconds = 10
    provenance = "substrate://self"
    is_internal = True

    def __init__(
        self,
        writer: Writer,
        *,
        meta_state: dict[str, Any],
        request_fn: Optional[RequestFn] = None,
    ) -> None:
        super().__init__(writer, request_fn=request_fn)
        # meta_state is filled in after the scheduler is created:
        #   {"scheduler": SenseScheduler, "writers": dict[str, Writer]}
        self._state = meta_state

    def poll(self) -> list[SenseEvent]:
        try:
            writers: dict = self._state.get("writers") or {}
            queue_depths = {name: w.queue_depth() for name, w in writers.items()}

            scheduler = self._state.get("scheduler")
            if scheduler is not None:
                sched_status = scheduler.status()
                global_running = sched_status.get("global_running", False)
                adapter_count = len(sched_status.get("adapters", {}))
                internal_count = sum(
                    1 for s in sched_status["adapters"].values() if s["is_internal"]
                )
                active_count = sum(
                    1 for s in sched_status["adapters"].values()
                    if s["enabled"] and not s["is_internal"]
                )
            else:
                global_running = False
                adapter_count = 0
                internal_count = 0
                active_count = 0

            error_events = error_channel.recent(limit=500)

            payload = self.pack(
                writer_queue_depths=queue_depths,
                error_channel_length=len(error_events),
                sense_global_running=global_running,
                sense_adapter_count=adapter_count,
                sense_internal_count=internal_count,
                sense_active_external_count=active_count,
            )
            return [SenseEvent(
                stream=self.stream,
                payload=payload,
                provenance=self.provenance,
                timestamp=self.now(),
            )]
        except Exception as e:
            error_channel.record(
                f"meta_awareness.poll error: {e}",
                source="adapter[meta_awareness]",
                exc=e,
            )
            return []
