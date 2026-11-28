# Remaining always-on producer shutdown boundaries — 28 November 2026

**Stacked base:** PR #409 head `2608d1c9c44105aaee4dae28e91308cde079e73f`, itself based on main `55fd635bd535d15ece3e3878bf1e71621f56fa7c` after #408.  
**Scope:** cooperative stop checkpoints for the remaining active run.py producers identified in the launcher/ownership census. No scoring formula, cadence, retry policy, prompt, feature flag, schema, shutdown deadline or action authority changed.

## 1. Why this increment exists

The run.py/AppState census maps direct worker starts to registered stop/join owners, but registration alone does not prove an active worker observes stop before starting another read, embedding, playback or Writer operation. This increment traces the remaining always-on and tracked-launcher-enabled workers to their next side effects.

The tracked `nex_keepalive.sh` launch command explicitly enables `NEX5_WARRANT_RECORD=1` and `NEX5_SELF_MAINTAIN_SHADOW=1`. The speech configuration defaults to enabled and the tracked launcher does not override it. DiversityLoop, EdgeGeneratorLoop and SubstrateHarmonic are started directly by `run.py`.

## 2. Source findings and bounded corrections

### SubstrateHarmonic

The 300-second daemon previously read eight stream groups in sequence, scored them and wrote one `substrate_coherence` row without passing its stop Event into `tick()`. It now checks the Event between synchronous stream reads and before scoring/persistence. If stop arrives during one Reader call, that call must return before the next stage is skipped. Direct `tick()` and `_read_all_streams()` calls remain compatible.

### DiversityLoop and its stages

The 60-second loop previously called GrooveSpotter, DormancyScanner and ClockRunner back-to-back without checking stop between them.

- GrooveSpotter now checks between detector stages, before alert/cooldown writes, and between centroid embedding calls.
- DormancyScanner checks after its reads and between candidate writes.
- ClockRunner checks between fast/medium/slow phases. Boost decay checks between per-belief writes; wake-one checks before its single update. The GraderEvolver now checks between grade reads, per-grade retrospective reads, mismatch writes, weight reads and final version persistence.
- The slow GraderEvolver's individual Reader calls and numerical fit are not forcibly cancelled; it returns to a stop checkpoint after the current call.

### EdgeGeneratorLoop

The 30-minute loop processes up to 20 source beliefs and up to 100 candidates per source, then may persist multiple edges. It now checks stop after reads, between candidate comparisons, between source beliefs and before each edge write. An already-started edge write and its associated `log_undo` record are allowed to finish. The persisted count now reports completed edges rather than the original proposal-list length when stop interrupts a batch.

### WarrantRecorder

The enabled recorder has two potentially substantial paths: survival checks over three rotating tier bands, including pairwise conflict comparisons, and use-day aggregation across retrieval, Fountain, synergizer, lineage and arc-member sources (each source query can return up to `_USE_BATCH` rows).

- Stop checks now occur between schema/read stages, source queries, row-processing loops and pairwise conflict comparisons.
- The use-day `INSERT OR IGNORE` rows and summary upserts are chunked. If stop interrupts these idempotent writes, cursors do not advance; a later cycle can safely replay the rows.
- The survival result rows and their cursor update remain one logical completion unit once persistence starts, avoiding an append-only partial batch with an unchanged cursor.
- A single synchronous Reader/Writer call already in progress is not cancelled.

### SelfMaintainShadow

The enabled, log-only hourly worker reads its own seven-day history or interoception snapshots, derives a setpoint, reads candidate overlap and writes one shadow row. It now checks stop between those stages and within the bounded interoception-row loop. It still only records what it *would* pause; it does not pause or otherwise mutate beliefs.

### SpeechQueueConsumer

The consumer's polling/quiet-hour waits now use its stop Event rather than uninterruptible sleeps. It checks stop before beginning a queued item and after local synthesis. If shutdown arrives before playback begins, the item is restored to `pending` so a later clean process can handle it. Playback itself is synchronous and has no cancellation API in the inspected Player; if stop arrives during playback, playback is allowed to finish and the spoken-status write records what actually happened.

The backend's initial `load()` and an in-flight `synth()` or playback call are not forcibly cancelled. They can still outlive the producer join allowance and contribute to a non-clean shutdown report.

## 3. Regression coverage

Added deterministic Event-based tests for:
- stopping SubstrateHarmonic between stream reads;
- stopping DiversityLoop before the next stage, centroid embeddings between calls, and GraderEvolver after a blocked read;
- stopping EdgeGenerator candidate work and edge persistence between edges;
- stopping WarrantRecorder after a blocked source read;
- stopping SelfMaintainShadow after its active-count read and before setpoint/write;
- stopping speech during synthesis, requeueing the item without beginning playback.

## 4. Explicit residual boundaries

This is cooperative stage-boundary control, not process-wide cancellation or an atomic stop/write handshake. Reader calls, schema calls, TTS model loading/synthesis, audio playback, and a Writer call already underway must return before a checkpoint can take effect. A stop arriving during an already-started audio playback is intentionally not treated as if speech had not occurred. The 5-second producer join allowance, 12-second process shutdown budget and 15-second supervisor escalation are unchanged.

The full producer census still does not prove that all dependency-created threads, detached tasks, subprocesses, thread pools, route-spawned work or host-level workers are registered. Actual live thread state and shutdown timing require authorized host evidence.

## 5. Authority

No cognitive interpretation is given execution authority. Mind Aspects remain interpretive; they do not gate, score, block, veto or authorize actions. No typed operation/action authority was added. Frozen S-01–S-25/M1.8, the Master Roadmap, Phase 0/Gate 0 and Phase 1 authority remain untouched.
