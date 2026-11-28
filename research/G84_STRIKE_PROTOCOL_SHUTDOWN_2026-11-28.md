# G-84 follow-on — StrikeProtocol delayed catalogue writers (2026-11-28)

## Observed source path

`strikes/protocols.py::StrikeProtocol.fire()` records a strike synchronously, then started an untracked daemon thread for `_delayed_belief_check(record_id)`. That worker slept for 60 seconds and then called `StrikeCatalogue.update_beliefs_after()`, which writes directly to the strikes SQLite catalogue rather than through a Writer wrapper.

`AppState` already held the `strike_protocol` reference, but the G-84 producer registry did not stop it or collect its background threads. Consequently, a delayed catalogue write could outlive the AppState shutdown drain and race with the clean-shutdown marker. The existing strike tests also left these 60-second daemon workers running after their temporary catalogues were cleaned up.

## Bounded implementation

- Add a protocol stop Event, a lock-protected owned-thread registry, and an idempotent `stop()` operation.
- Replace the fixed 60-second sleep with `Event.wait(60)`: normal timing is unchanged, while shutdown can cancel pending checks immediately.
- Register delayed workers before starting them and remove them from the registry in `finally`.
- Track the synchronous `fire()` caller thread for the duration of its catalogue write, so AppState can detect and join an in-flight request rather than declaring a clean drain while it is still writing.
- Reject new `fire()` calls after stop begins. A fire already in progress may finish its synchronous work, but it cannot schedule a new delayed check after stop.
- Register `strike_protocol` with AppState and make the shared quiesce routine take a snapshot of each managed service's `_threads` collection, in addition to its single `_thread` handle.
- Keep the 60-second post-fire delay and all strike scoring, dispatch, record content and belief-count semantics unchanged.

If an in-flight catalogue operation exceeds the shared shutdown deadline, it remains in the report's alive set. The existing G-84 shutdown path therefore withholds the clean marker and exits non-zero. The catalogue opens/closes its SQLite connection within each update; joining the worker prevents a delayed write from continuing after a successful AppState drain.

## Evidence and tests

- `tests/test_strike_protocol_shutdown.py` proves multiple delayed catalogue workers are stopped/joined, future fires are rejected, normal delayed updates still occur when the wait expires, and an in-flight fire exceeding the budget is reported.
- `tests/test_strikes.py` now stops and joins protocol workers during test cleanup, avoiding delayed writes into removed temporary directories.
- AppState's managed-producer path collects multi-thread services from a stable snapshot, avoiding list-mutation skips while workers remove themselves.

## Remaining boundary

This closes the known delayed `StrikeProtocol` catalogue-writer gap. It does not prove that every WSGI request thread or every direct database writer in the repository is registered. The host/server shutdown contract and a repository-wide direct-DB/thread census remain separate work. No strike policy, runtime decision semantics, database schema, frozen specification, Master Roadmap, Gate 0 or Phase 1 authority is changed.
