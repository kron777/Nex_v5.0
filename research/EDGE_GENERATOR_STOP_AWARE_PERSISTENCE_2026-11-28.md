# EdgeGeneratorLoop stop-aware proposal and persistence — 28 November 2026

**Base:** main at 55fd635bd535d15ece3e3878bf1e71621f56fa7c.  
**Scope:** cooperative stop checkpoints in the periodic edge-proposal and edge-persistence worker. No relationship rules, similarity thresholds, edge weights, candidate window, batch size, cadence or schema changed.

## 1. Source evidence

- EdgeGeneratorLoop is AppState-managed, waits 60 seconds at boot, then ticks every 30 minutes.
- Each tick reads up to 20 unconnected fountain_insight/synergized beliefs.
- For each source belief, EdgeGenerator reads the source row, up to 100 recent candidate beliefs and existing adjacency, then computes relationship proposals.
- It may persist up to five edges per source belief. An opposition edge is followed by an undo-log record.
- Before this change, the stop Event was checked only between 30-minute waits. An active tick could continue proposing and persisting edges for the rest of the 20-belief batch.

## 2. Bounded correction

- Pass the worker's stop Event into the tick, proposal and persistence stages.
- Check after source/candidate/adjacency reads and between candidate scoring iterations.
- Discard a proposal batch if stop is observed during scoring; do not begin persistence for that source.
- Check between source beliefs so a stop does not start the next proposal batch.
- Check before starting each source-belief persistence batch. Once started, finish the complete bounded batch (at most five edges) and any opposition-edge undo-log pairs; observe stop before the next source belief.
- Return the count of completed edge units when persistence stops early.
- Add deterministic tests for stop after source read, during candidate scoring, after an opposition edge write and between proposal/persistence.

## 3. Boundaries

- Reader calls and pure candidate scoring are synchronous; a current call/iteration must return before stop is observed.
- An edge row already written is not rolled back. The full per-source batch is the bounded commit unit, so once it starts all proposed edges (at most five) and opposition undo-log pairs finish.
- Stop prevents the next source belief's proposal/persistence batch from starting.
- This does not change graph semantics or grant the edge generator authority over actions.

## 4. Validation

Exact-head full-suite CI and baseline verification are required before merge. Tests use mocked Readers/Writers and deterministic Events.
