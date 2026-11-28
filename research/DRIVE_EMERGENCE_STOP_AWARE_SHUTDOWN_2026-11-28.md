# DriveEmergence stop-aware clustering tick — 28 November 2026

**Base:** main at 55fd635bd535d15ece3e3878bf1e71621f56fa7c.  
**Scope:** cooperative stop checkpoints around the always-started DriveEmergence clustering and persistence stages. No cluster threshold, candidate limit, scoring weights, decay rate, topic synthesis, feature flag, cadence or schema changed.

## 1. Source evidence

- run.py constructs DriveEmergence, starts its 600-second loop and registers it with AppState.
- The loop performs an immediate first background tick, then waits on its stop Event.
- A tick reads the existing drive row, pulls up to 200 beliefs, optionally computes own-voice document frequency over up to 2,000 beliefs, embeds every candidate, clusters them, scores clusters and writes a drive-emergence observability row. It may then replace/reinforce the drive row or persist decay.
- Before this change, the Event was used only for the interval wait and was not passed into the active tick. A stop during the embedding/clustering sequence could therefore be followed by later observability and drive-state writes.
- The AppState producer join allowance is at most five seconds.

## 2. Bounded correction

- Pass the existing stop Event into the immediate/periodic worker tick and background tick.
- Pass it into the optional own-voice DF calculation and check between documents.
- Check after existing-drive and candidate reads, before/after each candidate embedding, after clustering, between scored clusters, before the observability write and before drive-state persistence.
- If stop arrives during an embedding, discard the partial embedding map and do not start clustering or later writes.
- If stop arrives during the optional own-voice DF pass, stop before candidate embeddings.
- If stop arrives after the observability row has started/completed, skip the subsequent drive-state write.
- Pass the Event into the decay persistence helper so a decay write does not start after stop has been observed.
- Add deterministic tests for stop during embedding, during own-voice DF, after observability persistence and already-stopped entry.

## 3. Boundaries and residuals

- Individual Reader calls, embedding calls and the pure clustering operation are synchronous and not cancelled. The current operation must return before the Event can be observed.
- A delete/update/insert Writer operation already started before stop may complete.
- The observability log and drive-state row are separate writes; this increment explicitly permits the already-started observability row to complete and skips the later drive-state write if stop is observed afterwards.
- The diagnostic file append is skipped when stop is observed after the database stage.
- This does not establish host-level shutdown safety or prove all producers quiescent.

## 4. Validation

Exact-head full-suite CI and baseline verification are required before merge. Tests use mocked Readers/Writers and deterministic Events; no live embedding model or database is required.

No cluster threshold, candidate limit, weight, decay rate, topic synthesis, feature flag, cadence, schema, frozen S-01–S-25/M1.8 specification, Master Roadmap, Gate 0 or Phase 1 authority changed.
