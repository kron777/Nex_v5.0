# CompetingDrives stop-aware measurements and Fountain preflight — 28 November 2026

**Base:** main at 55fd635bd535d15ece3e3878bf1e71621f56fa7c.  
**Scope:** cooperative stop checkpoints through the periodic CompetingDrives measurement tick and the synchronous Fountain preflight call. No drive weights, tension thresholds, formulas, cadence or schema changed.

## 1. Source evidence

- CompetingDrives owns a 60-second background loop registered with AppState.
- Each tick reads a set of substrate metrics (belief source ratios, groove severity, signals, contradictions, active arcs, branch instability, open problems, probes, sense freshness, branch entropy, content complexity and affect variance), computes weights/tensions, then writes the current drives_competing row and an audit log row.
- Fountain also calls compute_now() synchronously before prompt assembly. That path recomputes the same metrics, updates the current drive row and inserts a per-fire drive_activations row.
- Before this change, the stop Event interrupted only the periodic wait. The active metric pass did not receive it, and compute_now() had no cancellation checkpoint.

## 2. Bounded correction

- Pass the Event into the periodic tick and check between the synchronous metric readers.
- Return without persistence if stop is observed during metric collection or tension calculation.
- After the current drives_competing row write, update the in-memory view; skip the optional audit row and file log if stop is then observed.
- Add an optional keyword-only stop Event to compute_now() and preserve direct-call compatibility.
- If stop arrives during metric collection, do not mutate in-memory state or start writes.
- If stop arrives during the current drives_competing row write, allow it to complete and skip the subsequent per-fire activation insert.
- Once the per-fire activation insert begins, complete its follow-up ID read so callers receive a consistent reference.
- Fountain passes its own stop Event into compute_now(), preventing a stop during preflight metric collection from starting later drive writes.
- Add deterministic tests for stop between readers, during compute_now() preparation, after the current-state write and during the periodic tick.

## 3. Boundaries and residuals

- Individual Reader/SQLite calls are synchronous and not cancelled; the current call must return before the Event is observed.
- The periodic current-state row, audit log and diagnostic file are separate effects. An already-started write may complete; later optional writes are skipped.
- The per-fire activation insert and its ID read are a logical pair, not a database transaction.
- This does not change the descriptive role of drive faculties or give them authority to gate, score, block, veto or authorize actions.

## 4. Validation

Exact-head full-suite CI and baseline verification are required before merge. Tests use mocked Readers/Writers and deterministic Events.
