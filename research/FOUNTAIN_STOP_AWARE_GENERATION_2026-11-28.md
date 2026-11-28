# Fountain generation stop-aware lifecycle — 28 November 2026

**Base:** `kron777/Nex_v5.0` main at `55fd635bd535d15ece3e3878bf1e71621f56fa7c`.  
**Scope:** pass the FountainState stop Event through the central generation path and add cooperative checkpoints around the longest preparation/generation stages and downstream optional work. This is a bounded lifecycle increment, not a claim of fully cancellable or transactional Fountain execution.

## 1. Source evidence

- `FountainState.fountain_loop()` owns the active loop. It calls `FountainGenerator.generate()`, then may spawn a drive probe and write a snapshot. `FountainState.stop()` sets its stop Event, but previously the Event was not passed into `generate()`.
- `FountainGenerator._generate()` assembles readiness/context, builds a substantial prompt, calls the shared VoiceClient (default HTTP timeout 120 seconds, with conditional retry), and then performs multiple telemetry, sense-event, fountain-event, crystallization and optional attachment writes.
- The condenser can also perform a VoiceClient request. It previously ran after the sense-event insert, so a stop during condensing could leave a sense event without its corresponding fountain event.
- The optional substrate-voice route reads an anchor, updates its last-voiced timestamp and inserts a fountain event.
- AppState manages FountainState as a producer and joins its worker within the shared five-second producer budget.

## 2. Bounded correction

- Pass FountainState's existing stop Event into `FountainGenerator.generate()` and `_generate()`.
- Check stop before generation, after readiness/context/prompt preparation, before VoiceClient calls, after each VoiceClient response, before retries and after frame-gate processing.
- If stop arrives during a VoiceClient call, allow that call to return but discard its response before the post-generation write path.
- Move condenser work and EmphasisEngine scoring before the main sense/fountain event persistence pair. If stop arrives during either, abort before the pair begins.
- Add stop checks before optional pre-event side effects, including problem feedback, recursion attribution, L4 signal emission, hot observation and momentum.
- Treat the main sense-event insert and corresponding fountain-event insert as one already-started logical pair: once the sense-event write begins, finish the fountain-event write even if stop arrives mid-pair.
- After the core event pair, skip optional attachments, snapshot, retrieval manifest, crystallization and carryover work if stop is observed.
- Make the substrate-voice route stop-aware between its reads and before its paired anchor-touch/event writes; skip its optional snapshot if stop arrives after the event.
- After generate returns, FountainState skips drive-probe spawning and snapshot writes if stop has been signalled.

## 3. Boundaries and residuals

- VoiceClient calls are not cancellable. A request already in progress can outlive the five-second producer join and the process may take the existing non-clean shutdown path.
- Prompt construction, Reader calls, condenser calls, EmphasisEngine scoring, frame-gate work, crystallizer work and other synchronous helpers are not forcibly interrupted. Stop is observed at their next explicit checkpoint.
- The core sense/fountain event pair is two Writer submissions, not a database transaction. This change does not add rollback or atomicity.
- A pre-event side effect already started (for example a problem-memory observation or recursion-attribution write) may complete before the next checkpoint. Optional post-event work is skipped once stop is observed.
- Crystallizer internals are not passed the stop Event; if crystallization has already begun when stop arrives, it may continue until its call returns.
- The substrate-voice helper's anchor-touch and fountain-event writes are also separate operations; once the touch begins, the paired event is allowed to finish.
- This does not prove complete process/thread quiescence or host-level shutdown behaviour.

## 4. Validation

Exact-head full-suite CI and baseline verification are required before merge. Tests use deterministic Events and mocked VoiceClient calls to verify that stop during prompt assembly prevents speech and stop during speech prevents subsequent sense/fountain writes.

No prompt content, generation temperature, retry count, readiness threshold, feature flag, interval, database schema, frozen S-01–S-25/M1.8 specification, Master Roadmap, Gate 0 or Phase 1 authority changed.
