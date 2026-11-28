"""Shutdown regression: a poll finishing after stop must not write to Writers."""
from __future__ import annotations

import threading

from theory_x.stage1_sense.base import Adapter, SenseEvent
from theory_x.stage1_sense.scheduler import SenseScheduler


class _BlockingPollAdapter(Adapter):
    id = "shutdown.blocking"
    stream = "test.shutdown"
    poll_interval_seconds = 3600
    provenance = "unit-test"
    is_internal = False

    def __init__(self):
        super().__init__(object())
        self.poll_started = threading.Event()
        self.release_poll = threading.Event()
        self.submitted = 0

    def poll(self):
        self.poll_started.set()
        self.release_poll.wait(timeout=5.0)
        return [
            SenseEvent(
                stream=self.stream,
                payload='{"value":"late"}',
                provenance=self.provenance,
                timestamp=1,
            )
        ]

    def submit(self, events):
        self.submitted += len(events)
        return len(events)


def test_scheduler_discards_poll_result_when_stop_arrives_during_poll():
    adapter = _BlockingPollAdapter()
    scheduler = SenseScheduler([adapter])
    try:
        assert adapter.poll_started.wait(timeout=2.0)

        # The worker is now blocked in poll(). Shutdown signals stop before
        # the network-like poll is released.
        scheduler.shutdown()
        adapter.release_poll.set()

        alive = scheduler.join(timeout=2.0)
        assert alive == []
        assert adapter.submitted == 0
    finally:
        scheduler.shutdown()
        adapter.release_poll.set()
        scheduler.join(timeout=2.0)
