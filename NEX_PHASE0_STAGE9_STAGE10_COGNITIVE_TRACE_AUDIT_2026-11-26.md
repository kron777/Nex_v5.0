# NEX Phase 0 — Stage 9 / Stage 10 Cognitive Producer–Consumer Trace

**Date:** 26 November 2026  
**Repository:** `kron777/Nex_v5.0`  
**Branch:** `claude/nex-continuity-wire`  
**Audited branch HEAD:** `30787dbbc20a521c5f8399b414aef56165fa8e93`  
**Source baseline:** `de93134f34adac07a3a41c2a05b33720510a2bfc`  
**Status:** Static source audit only. No runtime, database, service, flag, or experiment state was accessed or changed.

The Stage 9 and Stage 10 implementation files and the Theory X lifecycle protocol were checked at both the captured host baseline and current remote continuity branch HEAD. The following source blobs are identical at both refs: `stage9_metacognition/metacognition.py`, `stage10_imagination/novel_association.py`, `diversity/groove.py`, and `theory_x/__init__.py`. This makes the findings below applicable to the current remote branch for those files. The local host checkout remains the separately captured `de93134` snapshot; this audit does not imply it has been updated.

## 1. Stage 9 — Metacognition lifecycle and consumers

### Construction and scheduling

- `run.py:210–219` constructs and registers one `Metacognition` instance.
- The registry in `theory_x/__init__.py` only stores process-lifetime nodes and returns them through `all_nodes()`; it contains no scheduler or tick dispatcher.
- The `SentienceNode` protocol comment explicitly describes `tick()` as being called once per chat turn.
- The normal Chat route calls `state.metacognition.tick()` at `gui/server.py:1417–1420`, then reads `format_for_prompt()` and appends any returned observation to `belief_text`.
- Fountain receives the same instance through `run.py`, but its own injection is separately gated by `NEX5_METACOG_VOICE=1` at `theory_x/stage6_fountain/generator.py:3167–3174`.

**Interpretation:** the implemented detector cadence is chat-turn-driven, not an autonomous background loop. This matches the current lifecycle protocol; it should not be described as continuously monitoring during periods without Chat turns. The optional Fountain path reads the existing observation cache; it does not itself call `tick()`.

### Groove-alert re-emission risk

The producer/consumer path is:

1. `GrooveSpotter.detect_all()` in `theory_x/diversity/groove.py:82+` inserts alert rows into `beliefs.db.groove_alerts`. Its in-memory fingerprints suppress repeated insertion of an unchanged detector result during the same process.
2. The schema defines `acknowledged_at REAL` as nullable (`substrate/schema/beliefs.sql:218–227`); new producer inserts omit it, leaving it NULL.
3. `Metacognition._detect_groove()` (`metacognition.py:251–279`) selects up to three rows from the last 600 seconds where `acknowledged_at IS NULL`.
4. Each Chat turn calls `Metacognition.tick()` (`metacognition.py:133+`), which writes a new `meta_cognition_events` row for every selected alert through `_write_event()` (`metacognition.py:655–675`).
5. The traced `_write_event()` path does not update the originating `groove_alerts.acknowledged_at` field. The reviewed GrooveSpotter, Metacognition, GrooveBreaker and Chat-route paths contain no acknowledgement transition.

**Finding:** absent an acknowledgement performed by an untraced external path, the same still-unacknowledged alert can be converted into repeated duplicate `meta_cognition_events` on successive Chat turns until it ages outside the 600-second lookback. GrooveSpotter's in-memory detector fingerprint prevents repeated alert *creation* for an unchanged window; it does not consume or acknowledge the existing alert row. This is a source-level repeatability risk, not evidence that duplicate rows currently exist in the live database.

The existing `tests/test_metacognition.py` test `test_acknowledged_groove_alert_ignored` verifies that an already-acknowledged input is ignored. It does not verify that processing an unacknowledged alert acknowledges it or prevents duplicate event creation on a second tick.

**Disposition:** preserve as a verified source-level duplicate-event risk pending the authoritative lifecycle/acknowledgement contract. Do not add an acknowledgement write or alter detector semantics before Gate 0 and the required founder approval. An isolated regression test should seed one unacknowledged alert, call `tick()` twice, and assert the intended event/acknowledgement cardinality once that contract is confirmed.

## 2. Stage 10a — Novel Association producer, graph and prompt consumers

### Construction and scheduling

- `run.py:224–235` constructs `NovelAssociation`, starts its daemon loop, then registers it.
- `NovelAssociation.start_loop()` starts a daemon thread; `_loop()` sleeps for the 1,800-second interval before each scan (`novel_association.py:145–163`).
- The normal Chat route reads `format_for_prompt()` at `gui/server.py:1445–1454`. The route marks the selected log row annotated as part of that read.
- The Fountain constructor receives `metacognition` but not `novel_association` (`run.py` Fountain construction); no Novel Association prompt injection is present in the audited Fountain generator. Strong associations can separately write a SelfNarrative entry through the optional narrative reference.

**Interpretation:** Novel Association has an autonomous graph-scan producer and a Chat-only one-shot text consumer. Its annotation is not currently a Fountain injection path.

### Candidate eligibility and graph effect

- `_pull_candidates()` selects beliefs where `confidence >= 0.15`, `branch_id IS NOT NULL`, and `paused = 0` (`novel_association.py:214–251`).
- The query has no tier, locked, or retired/erosion-stage predicate. The module description frames the output as T7 cross-domain topology, but the actual candidate query is broader.
- `_write_association()` inserts a directed `synthesises` edge and a corresponding log row using `INSERT OR IGNORE` (`novel_association.py:253–279`); the schema has a unique edge key and a unique unordered-as-stored pair key for the log.
- `BeliefRetriever.retrieve()` restricts directly retrievable beliefs to `tier <= 6` (`stage3_world_model/retrieval.py:65–116`). Its activation engine traverses `belief_edges`, but returned prompt candidates are drawn from the tier-limited retrieval row map. The Novel Association module's own docstring already acknowledges that its T7 cognitive-effect path through retrieval is incomplete.

**Finding:** the producer's actual tier/lock eligibility is wider than the T7-only description suggests. This is a scope discrepancy requiring an explicit definition of which belief states may participate; it is not automatically a defect because the approved intended population is not established here. Also, T7 rows are not directly returned by the ordinary BeliefRetriever; any indirect influence through multi-hop activation requires separate evidence and must not be claimed merely from edge creation.

### Metric accuracy and annotation delivery

- `_scan()` increments its local `written` count for every cross-branch pair above the similarity threshold after calling `_write_association()`.
- `_write_association()` returns no insert result and uses `INSERT OR IGNORE`; therefore the `edges_written_total` state field counts qualifying pair detections, not necessarily newly inserted edges. A repeated scan can encounter an existing edge/log pair while still incrementing this counter.
- Existing `tests/test_novel_association.py::test_duplicate_pair_insert_ignore` verifies that duplicate log rows are not created, but does not assert that `edges_written_total` reflects actual inserted edges.
- `format_for_prompt()` updates `annotated_at` immediately after reading the row and before the rest of Chat prompt assembly / model completion. This implements at-most-once consumption: a later failure in the Chat turn will not make the same annotation pending again. Whether that is the intended delivery guarantee is not established by the source.

**Disposition:** record the counter name/meaning mismatch and the at-most-once annotation boundary as observability and delivery-contract questions. Do not change metrics, candidate eligibility, or annotation timing before the governing design is confirmed.

## 3. Isolated verification work to queue after authority is clear

1. Metacognition: repeated-tick test for one unacknowledged groove alert; verify exactly how acknowledgement is intended to occur and whether event persistence is idempotent.
2. Metacognition: verify that per-chat-turn evaluation is the approved cadence; retain the current protocol semantics unless an authoritative source requires an autonomous schedule.
3. Novel Association: test candidate eligibility across Tier 1, Tier 6, Tier 7, Tier 8, locked, paused and retired rows; expected eligibility must be defined before asserting a result.
4. Novel Association: test that the public counter reports newly inserted edges (or rename/document it as qualifying detections).
5. Novel Association: inject a failure after annotation but before Chat completion and establish the required at-most-once versus retryable delivery policy.

These are isolated-test proposals only. No test suite was run in this audit environment.

## 4. Authority and safety boundary

This document is evidence-only. It does not amend the frozen S-01–S-25 register, V2.1, Master Roadmap v3.0, the April constitution, Doctrine, Faculty Model, or any runtime contract. It does not constitute Gate 0 approval.

No code behaviour, runtime flag, database, experiment, service, or deployment was changed. Do not implement the candidate remediations, arm optional features, or use live NEX data to validate these findings until the required governing specification and founder Gate 0 approval are available.
