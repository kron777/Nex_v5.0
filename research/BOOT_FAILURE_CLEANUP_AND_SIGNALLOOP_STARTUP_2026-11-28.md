# Boot-time ownership and internal-start rollback study

**Date:** 28 November 2026  
**Source baseline:** `main` at `dd0f2c32bb5669d85a9b01bdf4cdc5636cc3f96f`  
**Candidate status:** implementation assembled on `fix/boot-time-appstate-ownership-2026-11-28`; exact-head CI pending.

## Question

What owns producer threads, Writers and shutdown when NEX boot fails before the application reaches its normal `AppState` construction and graceful-shutdown setup?

## Source observations

1. `run.py` constructs database Writers before application state. Writer construction starts the Writer's own worker thread.
2. Before this candidate, the application `AppState` was constructed only after the Sense Scheduler, Dynamic, Resolver, World Model, Membrane, optional cognitive producers, Fountain, Speech Queue Consumer, SignalLoop, DiversityLoop and Edge Generator startup paths had already been reached.
3. `atexit.register(state.close)` and the normal SIGTERM/SIGINT graceful handler were also installed late. An exception or termination earlier in boot therefore did not have the same application-level owner and cleanup path as a fully-started process.
4. The direct `run.py` start sites correspond to fields already understood by `AppState`; the main defect was late ownership publication, not a need for a second process-wide supervisor.
5. Several builders start workers internally. Their partial-start rollback must be guaranteed inside the builder because the caller cannot own a returned object before the builder returns. The Sense Scheduler, Dynamic, World Model, Membrane and Fountain builders now have individually tested rollback increments. SignalLoop was the remaining internal-start boundary in this audit.

## Candidate design

- Construct `AppState` immediately after Writers and Readers exist; register its `close()` with `atexit` before the first producer builder or explicit start.
- Give `AppState` a boot-shutdown request Event and optional absolute shutdown deadline. A boot-time signal handler latches the request; it does not close Writers underneath a builder that may still be starting.
- Check the request after each builder publishes its returned owner and after explicit worker starts. A requested boot abort unwinds through the current builder/helper, then `atexit` closes the already-published services using the original deadline.
- Use `_own_and_start` for explicit `run.py` starts: publish the worker field first, invoke start second, and on failure request stop and perform a bounded join before re-raising. The AppState retains the reference for final cleanup if the first rollback cannot finish.
- Make SignalLoop's own `start()` transactional with a start gate. If `Thread.start()` raises after the OS thread exists, set stop before releasing the gate, preventing the detector loop body from running, then join the worker.
- Install the normal clean-shutdown handler only after `create_app()` has returned. A boot abort does not write the clean-shutdown marker.
- Preserve one absolute deadline from the original boot-time signal through AppState cleanup. Partial Writer construction has a bounded cleanup callback until AppState takes ownership.

## Regression evidence added

- AST test verifies the single AppState construction and `atexit` registration precede all producer builder/start paths, and that normal clean-shutdown semantics are not installed before application construction.
- Failure injection starts a worker thread and then raises from its start method; the helper must stop and join it without losing ownership.
- A boot-shutdown request injected during a start call must unwind through the helper and quiesce the thread.
- AppState close must use the absolute deadline latched at the boot signal.
- SignalLoop failure injection starts the wrapper thread, waits briefly, then raises; the start gate must keep the loop body from running and the failed worker must be joined.

## Boundaries and residual unknowns

- This is a source- and test-level change, not evidence from a live robot or host shutdown rehearsal. Real SIGTERM delivery, service-manager timeouts, filesystem/SQLite contention and hardware-specific startup behavior remain unobserved.
- A signal received during a synchronous builder is latched and acted upon at the next safe checkpoint; shutdown response therefore waits for that builder to return. The builder startup paths are expected to be bounded, but host timing is not established here.
- Partial Writer cleanup covers Writers whose constructors returned and were published in the local registry. A failure inside a Writer constructor after an OS thread has been created but before the constructor returns is not separately fault-injected in this candidate.
- Python cleanup cannot handle SIGKILL, power loss or process abort.
- No process-wide thread census, new runtime flag, database, cognitive mechanism, Mind Aspect action authority or frozen-spec change is introduced.
- Capability ownership remains distinct from approval authority, execution and post-execution verification.
