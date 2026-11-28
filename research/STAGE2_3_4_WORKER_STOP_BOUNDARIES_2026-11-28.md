# Stage 2–4 nested worker shutdown boundaries — 28 November 2026

**Stacked source base:** PR #411 validation head \`ba321c93b6a2179cf0059420c67944c43e35cac6\`, which carries the producer sweep based on main \`55fd635bd535d15ece3e3878bf1e71621f56fa7c\`.  
**Scope:** cooperative stop checkpoints in Stage 2 Dynamic's core loops, Stage 3 World Model's heavy scans and Stage 4 Membrane's behavioural worker. No formulas, cadences, flags, schemas, prompts or shutdown budgets changed.

## 1. Ownership and newly exposed scope

The AppState shutdown registry owns the DynamicState, WorldModelState and MembraneState worker groups. Each group exposes a shared stop Event and tracked threads; this is positive ownership evidence, but does not by itself prove that a worker stops between sub-operations. This increment checks the main Stage 2/3/4 loops at their next safe logical boundaries.

## 2. Stage 2 Dynamic

### Sense polling

The poller reads up to 100 sense events and calls the existing A–F pipeline for each. It now checks stop before admitting each row and after the current pipeline unit. The cursor advances only for the event whose pipeline call completed; the final cursor write still runs on loop exit. An already-started pipeline event is not interrupted mid-operation.

### Sense distillation

The distiller reads up to 1,000 sense rows per pass and can perform title extraction, exact lookup, near-duplicate embedding comparisons and belief insertion. It now checks stop before each row, after title extraction, after exact lookup and after near-duplicate scoring. The in-memory cursor advances only after the row's extraction/dedup/write unit completes. If stop interrupts a row, the saved cursor remains before that row so it can be replayed. \`_is_near_duplicate\` checks stop between embedding comparisons.

### Aperture, snapshot and accumulator

- Aperture recalculation checks stop between tree enumeration/aggregation and membrane recalculation.
- Snapshot checks stop after the tree snapshot write and before tier-count telemetry; tier snapshot rows are checked individually.
- Accumulator checks stop between cadence refresh, Bonsai decay, membrane decay and flush. These in-memory operations remain synchronous and are treated as individual bounded stages.

### Crystallization

Crystallizer checks stop between branches and after each guard read (pipeline content, blacklist, dedup and coherence/intake checks). Once the beliefs row write begins, the corresponding \`crystallization_events\` row is completed as the logical audit pair. Direct method calls without a stop Event preserve their prior call shape.

### Consolidation

The quiet check now observes stop after its Reader call; the loop does not begin decay/prune after shutdown has started. Bonsai decay and prune remain synchronous in-memory passes; they are not forcibly cancelled mid-pass.

### Emergent drives

Pressure scans check stop after the beliefs read and between branch aggregation. Proposal logging checks before each proposal write. Approval application checks between proposals and after the coherence-gate call; once a proposal is admitted, its tree/proposal status work is treated as one logical unit.


### EdgeBuilder

The DynamicState edge-builder is registered and can score up to 30 under-connected beliefs against a pool of 800, using embedding calls before one atomic `write_many_with_counts` batch. It now checks stop between candidate/pool embedding calls and before the final batch. If shutdown interrupts scoring, the accumulated in-memory statements are discarded and no partial edge batch is written. The atomic Writer batch, once started, is allowed to finish.

### Retention

The daily retention worker can have a large first-run catch-up (the documented gate_decisions backlog is millions of rows) and deletes in batches of 250,000. It now checks stop before each count read, after the read and before each DELETE. A DELETE batch already started completes; the next batch is not admitted after stop. The existing retention windows, predicates and batch size are unchanged.

## 3. Stage 3 World Model

### Harmonizer

Conflict scanning now checks stop after the initial read, during tokenization, between belief pairs and between heuristic and semantic scoring. Resolution checks stop before each pair; an already-started paradox mark or resolution is allowed to finish its related writes. Stale-paradox escalation checks between pairs. Cross-domain detection checks between tokenization, pair comparison and edge writes.

### Provenance erosion

The keyset-page erosion pass checks stop before each page, after each page read and between belief rows. An already-started stage update and its undo-log entry are completed together. The next row/page is not admitted after stop.

### Synergizer

The worker checks before pair selection, before VoiceClient invocation, after the VoiceClient returns, after quality/coherence checks and before belief insertion. VoiceClient requests are synchronous and cannot be cancelled by this Event. If stop arrives during the voice request, its result is discarded after return and no new belief is inserted. Pair selection itself remains a bounded synchronous read/embedding operation and is not forcibly cancelled.

### WorldConsolidator

The tracked launcher explicitly sets `NEX5_WORLD_CONSOLIDATE=1`, so this is an active promotion-capable worker, not merely an optional path. Its T7 window read, world-belief filtering, embedding batches, pairwise clustering, duplicate checks and promotion candidates now observe stop between bounded units. A `promoter.corroborate()` operation already started is allowed to finish. The regression test stops during the first embedding and verifies that no promotion begins.

## 4. Stage 4 Membrane

BehaviouralSelfModel checks stop after its conversation read, while computing metrics, between seed comparisons, after each dedup read and after coherence checks. The membrane worker passes its Event through and does not start another divergence write after stop. A belief insert already started is allowed to complete.

## 5. Regression coverage

Added deterministic tests for:
- sense-poll completion and cursor advancement at the current row boundary;
- sense-distillation interruption without advancing beyond an unfinished row;
- crystallizer stopping before the next branch;
- emergent-drive scan stopping after its source read;
- harmonizer stopping between heuristic and semantic pair scoring;
- erosion completing one update/undo pair but not admitting the next row;
- synergizer discarding a VoiceClient result returned after stop;
- behavioural self-model refusing to begin writes after stop during comparison.

## 6. Remaining audit work

This increment does not yet instrument every nested Stage 2 life/add-on loop (witness, pattern, identity, affinity, scorecard, surprise, remember, wonder, fetch, daily-life, focus, signal-to-problem and Moltbook). Those loops are registered under DynamicState, but their in-flight work still needs a source-to-stop boundary audit. Do not infer that these remaining paths are unsafe or safe without checking their exact call sites and effective launch flags.

Synchronous Reader/Writer calls, embedding/model work, VoiceClient calls and already-started logical write pairs are not forcibly cancelled. Host-level process state and actual shutdown timing still require authorized host evidence.

## 7. Authority

Mind Aspects remain interpretive; they do not gate, score, block, veto or authorize actions. No typed operation/action authority was added. Frozen S-01–S-25/M1.8, the Master Roadmap, Phase 0/Gate 0 and Phase 1 authority remain unchanged.
