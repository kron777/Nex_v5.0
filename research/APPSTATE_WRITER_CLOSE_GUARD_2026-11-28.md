# AppState Writer-close guard when producers fail to quiesce — 28 November 2026

**Base:** main at 55fd635bd535d15ece3e3878bf1e71621f56fa7c.  
**Scope:** prevent shared Writer closure when AppState cannot prove that all registered producers have stopped. No timeout, producer order, Writer queue semantics or database schema changed.

## 1. Source evidence

- AppState.close() signals registered producers and joins them against the shared producer-stop deadline.
- It records producer threads that remain alive and errors raised by producer stop methods.
- Before this correction, AppState proceeded to call close() on every shared Writer even when a producer remained alive or a stop method failed.
- A late producer could therefore submit to a Writer after its close sentinel/queue drain had begun, creating a race with a closed Writer or a blocked submitter.

## 2. Bounded correction

- If any producer thread remains alive or any producer stop operation reports an error, skip closure of **all** shared Writers.
- Report the skipped Writer names in a new `writer_close_skipped` field and still report any Writer threads that remain alive.
- Mark shutdown unsuccessful. The existing signal/keepalive path can then refuse the clean marker and enforce the hard process deadline.
- Only close Writers after producer quiescence is established without producer-stop errors.
- Add a deterministic regression where a producer outlives a short join deadline and completes its in-flight database write while the Writer remains open.
- Extend the stop-error regression to assert that Writer closure is skipped conservatively.

## 3. Safety boundary

This intentionally prefers an unclean, supervisor-terminated process over closing shared Writers underneath an active producer. It does not forcibly cancel the producer, extend its join deadline, or guarantee that the producer will finish before the supervisor's hard kill. If a producer never returns, the process is expected to exit non-zero and be terminated by the keepalive/service manager.

A stop-method error causes conservative Writer-close skipping even if the associated thread is no longer alive; the coordinator does not assume the failed stop left the producer harmless.

## 4. Validation

Exact-head full-suite CI and baseline verification are required before merge. The regression uses an isolated temporary database, a deterministic held producer and a short patched producer join timeout.
