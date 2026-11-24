# NEX v5.0 — Verified Defect and Risk Backlog

**Status:** Working Phase 0 evidence backlog — NOT founder-approved  
**Date:** 24 November 2026  
**Repository:** `kron777/Nex_v5.0`  
**Documentation branch:** `phase0/evidence-foundation-draft`  
**PR #49 head at creation:** `ae1b3c8227f11915803fa1a49ca42680748781c1`  
**Source branch used for the newest source audits:** PR #65 head `cffbbc94b5a494247d127abf2720886a08f7a567`  
**Authority:** Founder Sign-Off > Frozen V2.1 Spec > Runtime Truth > Master Roadmap v3.0

This backlog consolidates source-verified findings recorded in `NEX_REPOSITORY_REALITY_REPORT.md`. It is a triage aid for Gate 0 review, not approval to implement fixes. “Source-confirmed” means the described code path is visible in the inspected revision; it does not establish that the path has occurred on the target host. Conditional risks remain conditional. No live exploit, database mutation, flag change, external action or host experiment was performed.

## Evidence-level rules

The roadmap §1.2 defines:
- **L0 — Proposed:** design/hypothesis only; no code proof.
- **L1 — Constructed:** code, schema and unit tests exist; no proof of integrated runtime execution.
- **L2 — Runtime-active:** execution traces prove the code runs in live/simulated operation and emits records.
- **L3 — Operationally consumed:** an end-to-end ID-linked trace proves a downstream decision/context/actuator consumes and changes state based on the output.
- **L4 — Effectively validated:** controlled A/B or multi-arm testing against a frozen baseline demonstrates statistically significant improvement on predeclared metrics without guardrail violations.
- **L5 — Generalised:** independent validation across task families, backends or embodiments.

Roadmap §6.2 asks for L0–L4 labels, while §1.2 defines L0–L5. This internal range conflict is preserved for Founder clarification; this backlog uses no L5 claims. The majority of findings below are L1 source/test evidence only. No finding establishes L3 or L4 behavioural improvement. The fixture trace artifact is L2 simulated evidence for the trace overlay, not a live host trace.

## Priority triage — for Founder review only

Priority labels are proposed ordering by potential impact and exposure, not an approved project severity taxonomy.

### P0 — Security boundary

| ID | Finding | Evidence level | Status / exposure boundary |
|---|---|---:|---|
| DRAFT-015 | Public `/api/chat` can route raw prompt text to `python_exec`; regex import blocking is bypassable through Python built-ins, and the subprocess executes under the NEX process account. The route is exempt from the admin mutation gate. | L1 | Source-confirmed unsandboxed execution path. Default bind is loopback; unauthenticated arbitrary code execution is conditional on a caller being able to reach the service. No exploit was run. |
| DRAFT-016 | `web_fetch` uses `netloc.lstrip("www.")` rather than exact-prefix normalization and follows redirects without revalidating the final destination. | L1 | Source-confirmed allowlist/redirect weakness; SSRF is conditional on a controllable lookalike or permitted-origin redirect. No network request was made. |

**Containment recommendation:** do not expose the service beyond a trusted local boundary until the Python tool is disabled or safely isolated and the web-fetch destination policy is independently verified. This recommendation does not authorize a runtime change.

### P1 — Decision influence, authority and trigger integrity

| ID | Finding | Evidence level | Status / exposure boundary |
|---|---|---:|---|
| DRAFT-008 | WorldBridge documentation describes Phase A as selection/logging only, while the inspected runtime constructs the selector and appends selected event text to Fountain prompts; selector is source-enabled and does not consult the registered bridge flag. | L1 | Source-confirmed documentation/implementation mismatch. Approval intent and live selection frequency UNKNOWN. |
| DRAFT-011 | Empty prediction windows are deliberately stored with surprise score 1.0 and no actual content; the expectations ledger and SurpriseLoop reject them as evidence, but Fountain confidence weighting uses the score alone and can apply the maximum confidence boost. | L1 | Source-confirmed consumer semantic mismatch; weighting is source-default enabled. Host flag and occurrence UNKNOWN. |
| DRAFT-017 | Throw-Net threshold functions return threshold booleans, but CoherenceGate and Chat callers ignore them; the monitor processes every unfired trigger when enabled. | L1 | Source-confirmed threshold-wiring mismatch. Throw-Net monitor is default-OFF; live activation UNKNOWN. |
| DRAFT-020 | FocalSet is described as log-only but its selected beliefs are added to per-session WorkingMemory and injected into the same Chat turn's prompt on a conditional path. FocalSet state is process-global and unsynchronized. | L1 | Source-confirmed prompt influence and cross-session selection coupling; no arbitrary cross-session text leakage was demonstrated. |
| DRAFT-006 | Moltbook dry-run return values can be recorded as approved/posted/sent even when no external POST occurs; a supplied host log shows a loop instantiated in a potentially divergent checkout. | L2 for loop instantiation only | External action and current checkout identity UNKNOWN. Host log is historical; Manus must reconcile checkout identities before activation claims or code correction. |
| DRAFT-023 | ExecutiveControl is constructed/registered but not consumed by api_chat; the route defaults to Philosophical while voice.registers.classify/default_register remain Conversational. | L1 | Source-confirmed route mismatch; code comment marks the Philosophical default as a deliberate edit, but continued approval/intent is unresolved. Unit tests do not cover route integration. |

### P2 — Reliability, measurement and recovery

| ID | Finding | Evidence level | Status / exposure boundary |
|---|---|---:|---|
| DRAFT-009 | Voice and random market predictions fetch separate baselines/timestamps; a failed leg can return a non-error wrapper result with a missing row ID. | L1 | Source-confirmed paired-experiment/accounting gap; live drift and partial-pair frequency UNKNOWN. |
| DRAFT-010 | Calibration consult can label unavailable scorecard data as “none”/unreliable rather than “unknown”; the level is stamped onto a prediction row. | L1 | Source-confirmed evidence-state misclassification; specific failure branch lacks a dedicated test. |
| DRAFT-012 | An accepted provenance retry is evaluated with logging disabled, so the provenance file records the discarded initial draft rather than the final delivered response. | L1 | Source-confirmed measurement gap; conditional on an armed feature and accepted retry. |
| DRAFT-013 | CounterfactualNode repeatedly selects the oldest open problem but does not update its `last_touched_at`; absent external touches/closure, newer problems can be starved. | L1 | Conditional scheduling starvation path; no live incidence. |
| DRAFT-014 | External-input prediction concatenates sense rows before chat messages and truncates to 10 without cross-source chronology; verification includes internal sense streams excluded from prediction. | L1 | Source-confirmed prediction/verification population mismatch; score impact UNKNOWN. |
| DRAFT-018 | An outer Throw-Net cycle failure persists a failed session but returns status complete and marks the trigger fired, preventing pending-query retry. | L1 | Source-confirmed result/retry accounting mismatch; intended consume-on-failure policy unresolved. |
| DRAFT-021 | run.py replaces SnapshotWriter's SIGTERM handler and calls `os._exit`, bypassing the writer's final snapshot and atexit callback. | L1 | Source-confirmed shutdown integration gap; periodic snapshots still occur. |
| DRAFT-022 | ResumptionSeeder consumes a valid snapshot even when promotion/reissue helpers swallow database errors and return zero/partial counts. | L1 | Source-confirmed recovery retry gap; no direct resumption failure test. |

### P3 — Conditional routing, governance and test coverage

| ID | Finding | Evidence level | Status / exposure boundary |
|---|---|---:|---|
| DRAFT-001 | Speech consumer fallback calls `row.get("voice")` on a `sqlite3.Row`, which has no `.get()`; only reached when normal VoiceState resolution is absent/fails. | L1 | Source-confirmed conditional fallback defect; normal startup supplies VoiceState. |
| DRAFT-002 | Natural-language calculation heuristics select `python_exec`, but the original prose query is passed as Python source and normally fails syntax parsing. | L1 | Source-confirmed integration defect; distinct from the unsandboxed-code security issue in DRAFT-015. |
| DRAFT-003 | Membrane classifier uses substring matching for “you”, so “YouTube” is classified as self-inquiry/INSIDE. | L1 | Source-confirmed conditional query-routing defect; runtime frequency UNKNOWN. |
| DRAFT-005 | MIND_MAP descriptive-only constraint was not enforced by the earlier CI check. PR #72 adds a static guard and focused tests; its exact head passed CI, but remains draft/unmerged. | L1 | Proposed governance correction in PR #72; do not mark resolved until merged and verified on the authoritative branch. |
| DRAFT-024 | api_chat passes an empty beliefs list to ToolCaller even after local retrieval; its “no beliefs + factual query” fallback is therefore always eligible. | L1 | Source-confirmed caller/method mismatch; external freshness intent unresolved. No route-level test. This increases web_fetch reachability but does not itself prove SSRF. |

## Top five documentation-versus-code discrepancies

These five are the most material discrepancies identified in the current source pass; the list is a Phase 0 snapshot, not a final severity ranking.

1. **DRAFT-015 — Python tool safety claim vs actual execution:** the public chat path forwards raw prompt text to a Python subprocess; regex import blocking is not a sandbox.
2. **DRAFT-008 — WorldBridge Phase A description vs actual prompt injection:** documentation says selection/logging only, while the inspected generator appends selected event text to the prompt.
3. **DRAFT-020 — FocalSet “log-only” comment vs actual prompt influence:** same-turn FocalSet selections enter WorkingMemory and can be appended to the current prompt.
4. **DRAFT-017 — Throw-Net thresholds vs actual scheduling:** threshold return values are ignored; all unfired trigger rows are processed when the monitor is enabled.
5. **DRAFT-011 — empty-window sentinel vs downstream confidence semantics:** one consumer treats the sentinel as no evidence while another treats its maximum score as novelty.

DRAFT-016 is an additional security boundary weakness; DRAFT-006 is an external-action state-accounting risk; both remain high-priority review items.

## PR/CI snapshot at backlog creation (24 Nov 2026)

| Workstream | Exact head | CI | PR state |
|---|---|---|---|
| PR #49 evidence foundation | `ae1b3c8227f11915803fa1a49ca42680748781c1` | Run `45280433678` in progress | Open, draft, unmerged |
| PR #65 trace/speech integration | `cffbbc94b5a494247d127abf2720886a08f7a567` | Run `45273123963` success | Open, draft, unmerged |
| PR #72 MIND_MAP CI guard | `6aa226a80d623f223ef994ca9d2d49d29f7d1966` | Run `45272386599` success | Open, draft, unmerged |

CI success validates only the tested repository suite at that exact head. It does not establish host runtime behaviour, Gate 0 readiness or live causal influence.

## Phase 0 completion status

| Roadmap item | Current evidence | Status |
|---|---|---|
| M0.1 repository baseline | GitHub repository/PR/source revisions inspected; exact host checkout and local working-tree status not captured. | Partial |
| M0.2 host and test baseline | Target Zorin/Python/SQLite/Ollama/Qwen digest, RAM/VRAM and tokens/sec not measured. Full target-host pytest baseline and `known_failures.txt` reconciliation not performed. | Incomplete |
| M0.3 forward/backward crosswalk | Broad source-to-sink coverage across core loops and optional faculties; remaining faculty-by-faculty closure and all backward consumers still need reconciliation against every governing source. | Partial |
| M0.4 evidence labels/top five | Top five listed above; strict evidence levels applied in the Crosswalk and this backlog, subject to the roadmap's L0–L4/L0–L5 wording conflict. | Partial |
| M0.5 causal trace | `NEX_CAUSAL_TRACE_SAMPLE.json` exists in PR #49 as an isolated fixture artifact with one Chat turn and one Fountain cycle. It is not a live host capture. OFF/ON fixture equivalence is tested; complete host capture and full causal closure remain unestablished. | Partial |

## Gate 0 blockers

1. Exact Frozen V2.1 specification and Founder Sign-Off/approval record remain unlocated in the searched Library/repository material.
2. Founder must reconcile the authority hierarchy and the roadmap's L0–L4 versus L0–L5 evidence-level wording.
3. The target runtime checkout identity and current host state must be established. The Moltbook host log references a potentially divergent checkout; Manus must compare both checkout identities and startup paths before any activation claim or code correction.
4. M0.1/M0.2 host measurements and full test-baseline reconciliation remain incomplete.
5. The forward/backward audit must be closed for every `theory_x/` faculty against `MIND_MAP.yaml`, `sentience_dag.json`, `ARCHITECTURE.md`, `SENTIENCE_PROGRAM.md` and `run.py`.
6. A live host Fountain trace and Chat trace have not been captured.
7. Founder review and approval of the Reality Report, Crosswalk and this verified defect/risk backlog are required before behavioural edits.

**No remediation is authorised by this backlog.** No runtime code, tests, database, flags, host, protected experiment, baseline, tripwire, external action, merge or deployment was changed in producing it. All items remain open for evidence review; some may be downgraded, reclassified or closed after higher-authority reconciliation and approved verification.


### Current update — DRAFT-023 (24 Nov 2026)

The Reality Report and Crosswalk now include DRAFT-023 for ExecutiveControl. The classifier is constructed and registered, but the active Chat route selects Philosophical by default and does not call ExecutiveControl.select(); voice.registers.classify remains a Conversational stub. This is source-confirmed; whether the dated override remains approved is unresolved. See the Reality Report for source hashes and test boundary.


### Latest PR49 status check (24 Nov 2026, before this backlog refresh)

Immediately before this documentation refresh, PR #49 head was 50a8b6adbeb2c722bbd0b57881041e4a3dfa00b5. No workflow run was returned for that head. The earlier run 45280433678 on head ae1b3c8227f11915803fa1a49ca42680748781c1 completed as cancelled. PR #65 exact-head run 45273123963 and PR #72 exact-head run 45272386599 remained successful. This backlog refresh is documentation-only; no new test run is claimed.


### Current update — DRAFT-024 (24 Nov 2026)

The Reality Report and Crosswalk now record that api_chat passes an empty beliefs list to ToolCaller.should_use_tool() even after normal retrieval has assembled local belief context. This makes the documented factual web-fetch fallback eligible regardless of actual local retrieval. Intent may be a deliberate freshness policy; no correction is proposed before acceptance criteria are clarified.


### Current update — DRAFT-025 (24 Nov 2026)

**Stage 2 sense-poll cursor can advance after a swallowed pipeline exception.** The `_sense_poll_loop()` caller advances `last_id` and increments `_pipeline_runs` after every `run_pipeline()` call. The callee catches processing exceptions, records them and returns 0, which is indistinguishable to the caller from a legitimate no-match result. The cursor is periodically persisted, so a failed row may be replayed if the process restarts before a later cursor save, but can be skipped after the cursor advances past it. The pipeline also performs multiple independent log writes and mutates in-memory tree/membrane state before its final Stage F log write, so failure can leave partial effects. This is a source-confirmed processing/retry-accounting gap; no live failure or loss rate was observed. Whether the intended contract is at-most-once, retryable, or best-effort processing requires authoritative acceptance criteria before any remediation.

A related but distinct Stage 2 distillation policy is recorded in the Crosswalk and Reality Report: the loop caps new belief writes at five per pass while advancing its cursor through the fetched batch, which means later candidate rows in that batch are not revisited. The source comment describes this as the intended cap boundary; its alignment with approved policy remains unresolved and is not assigned a defect severity here.


**DRAFT-025 test boundary:** The inspected `tests/test_dynamic.py` cursor tests cover save/load only, not error-to-cursor behaviour or replay boundaries; the internal-stream assertion checks only `hits >= 0`, not absence of state influence. The inspected `tests/test_sense.py` cases cover successful writes, not concrete Adapter.submit() partial-write failure. This is limited to the reviewed test slices.


### Current update — DRAFT-026 (24 Nov 2026)

**Temporal quiet-signal producer/consumer contract mismatch.** Stage 2 consolidation reads the latest `internal.temporal` payload and looks for `seconds_since_last_user_message` to decide whether to run its quiet-triggered decay/prune pass. The built-in Stage 1 `Temporal.poll()` producer inspected for the Stage 1 factory emits clock fields but not this key. The inspected consolidation tests manually insert the expected key into a temporal row, so they do not validate the real producer-to-consumer path. Another writer could supply the field; no complete writer census or live payload inspection has established whether that occurs. Source-level mismatch confirmed for the inspected producer; runtime effect UNKNOWN. No severity or remediation is assigned pending authoritative acceptance criteria and a complete producer census.


### Current update — DRAFT-032 (24 Nov 2026)

**Stage 1 scheduler shutdown does not wait for adapter threads before closing Writers.** _AdapterThread starts a daemon worker without retaining its thread handle; stop() only sets an event. SenseScheduler.shutdown() signals all workers and returns without joining them. AppState.close() then closes the Writers. If a worker is still inside poll() and subsequently reaches Adapter.submit()/Writer.write() after the Writer sentinel has been queued or processed, the request may be enqueued behind the sentinel and never serviced. This is a source-confirmed shutdown interleaving risk, not an observed failure. No shutdown interleaving was induced; target-host exposure is UNKNOWN. No severity or remediation is assigned pending acceptance criteria.

**DRAFT-032 test boundary:** No dedicated test was run or identified in this bounded pass for shutdown during an in-flight adapter poll/write, thread termination/join, or Writer sentinel ordering. Source anchors: theory_x/stage1_sense/scheduler.py, gui/server.py (AppState.close) and substrate/writer.py.

### Current update — DRAFT-033 (24 Nov 2026)

**Some Stage 1 adapters can report partial upstream failure as a clean poll.** ExchangePrices.poll() and CryptoNews.poll() catch individual upstream failures and continue, returning any successful subset (or an empty list) without surfacing those failures to the scheduler. Scheduler last_error=None and last_event_count therefore do not establish that every configured source succeeded. ArxivAI.poll() follows a different contract and lets exceptions reach the scheduler. This is source-confirmed observability asymmetry; no current upstream outage or partial poll was observed. No severity or remediation is assigned.

**DRAFT-033 test boundary:** The reviewed tests/test_sense_extract.py tests extraction/filtering helpers, not per-upstream adapter failures or expected completeness. No adapter test was run in this pass. Source anchors: theory_x/stage1_sense/feeds/exchange_prices.py, feeds/crypto_news.py, feeds/arxiv_ai.py, theory_x/stage1_sense/scheduler.py.

### Current update — DRAFT-034 (24 Nov 2026)

**RSS ingestion lacks a stable item identity/dedup boundary before Stage 2 A–F processing.** The shared parse_rss() helper omits the RSS/Atom entry id/guid, does not inspect Feedparser's bozo parse-warning status, and does not deduplicate across polls. The inspected sense_events schema has no unique source-item key. Stage 2 _sense_poll_loop() consumes each inserted row by database ID and invokes the A–F pipeline without content-level deduplication; the separate belief-distillation loop has its own exact/near-duplicate checks, but that does not make A–F processing idempotent. Repeated feed entries can therefore be processed as separate rows if returned by later polls and matched to branches. This is a conditional source-level risk, not a measured duplicate rate or live repeated state effect. No severity or remediation is assigned.

**DRAFT-034 test boundary:** The reviewed tests/test_sense_extract.py covers payload extraction and filtering, not repeated poll ingestion, GUID preservation, malformed-feed partial parsing, or repeated-row A–F effects. No tests were run in this pass. Source anchors: theory_x/stage1_sense/feeds/_helpers.py, substrate/schema/sense.sql, theory_x/stage2_dynamic/__init__.py and theory_x/stage2_dynamic/pipeline.py.

### PR #49 documentation update status (24 Nov 2026)

Before this backlog update, PR #49 head was 5e1d7515c6b42d643f65495c084047edc4c3b372. The new Stage 1 source-audit findings are documented in the Reality Report and Architecture Crosswalk; this backlog addendum consolidates the three additional review candidates above. PR remains open, draft and unmerged. No exact-head CI result is claimed for the current documentation head unless a matching workflow run is returned separately.


### DRAFT-032 test-coverage clarification — 24 Nov 2026

The reviewed tests/test_sense.py does cover scheduler auto-start: test_starts_running_for_external asserts global_running and adapter enabled immediately after construction. It therefore corroborates the implemented auto-start behaviour and confirms that the paused-by-default package/scheduler prose is stale. However, teardown only calls scheduler.shutdown(), and the direct _AdapterThread test only calls stop(); neither waits for or asserts worker termination before Writer cleanup. The shutdown race remains without a corresponding join/order assertion.


### Current update — DRAFT-030 (24 Nov 2026)

**WorldBridge's documented Phase A boundary no longer matches the active Fountain prompt path.** The WorldBridge selector module/class docs describe Phase A as selection/logging only, with prompt injection deferred to Phase B. The inspected boot path constructs the selector and passes it to Fountain; Fountain calls select_and_log(mark_injected=True) and appends returned formatted selections to the active composition prompt. The selector is therefore a source-level prompt contributor, including eligible qualitative internal sense streams, not merely a diagnostic logger. This may represent an implementation advancement whose docs were not updated; whether it conflicts with the governing design/acceptance contract is unresolved. No severity or remediation is assigned.

**DRAFT-030 test boundary:** tests/test_strikes.py covers feed_activity in the probe/strike context snapshot, not the WorldBridge selector-to-Fountain-prompt path. No WorldBridge integration test was established in this bounded review; this is not a claim that no such test exists anywhere. Source anchors: run.py, theory_x/world_bridge/selector.py, theory_x/stage6_fountain/generator.py and tests/test_strikes.py.

The same source pass found context_snapshot.py reads sense_events for a feed_activity summary; ProbeRunner and StrikeProtocol persist that snapshot for probe/strike records. This is observational capture, not evidence of a Chat/Fountain cognition input.


### DRAFT-030 source qualification — internal streams in WorldBridge

The selector's formatter explicitly converts internal.temporal, internal.meta_awareness and internal.interoception into compact prompt text; internal.proprioception falls through to a short raw JSON snippet. In particular, MetaAwareness's enabled/global-running fields can be presented in Fountain despite the separate SelfModel snapshot not using the fetched MetaAwareness payload. These values remain control-state telemetry, not feed-health or persistence proof. This is a source-path qualification to DRAFT-030, not a separate severity assessment.


### Current update — DRAFT-031 (24 Nov 2026)

**WorldBridge writes directly to beliefs.db outside the One-Pen Writer queue.** SPECIFICATION.md §8 requires exactly one writer thread per database and states that every write must submit to that queue; direct DB writes are bugs. WorldBridgeSelector._log_selection() imports substrate.connect, opens a normal beliefs.db connection and executes an INSERT into world_bridge_log. The selector is constructed by run.py and invoked by Fountain prompt assembly, so this path is reachable in the inspected boot graph. This is source-confirmed divergence from the inspected specification. An approved later exception/superseding rule has not been established; no contention event or live impact is claimed. No severity or remediation is assigned pending Frozen V2.1/Founder authority reconciliation.

**DRAFT-031 test boundary:** tests/test_sense.py's one-pen ratchet checks for literal "import sqlite3" outside substrate. It does not detect the from-substrate-connect plus INSERT pattern. The inspected tests/test_strikes.py verifies context snapshot fields, not WorldBridge's database write route. No contention test or live write trace was run. Source anchors: SPECIFICATION.md §8, theory_x/world_bridge/selector.py, run.py, theory_x/stage6_fountain/generator.py and tests/test_sense.py.


### Current update — DRAFT-027 (24 Nov 2026)

**Harmonizer initial conflict discovery is capped at the first 200 eligible beliefs.** `scan_for_conflicts()` selects Tier 3–7, unlocked, unpaused beliefs ordered by ascending tier with `LIMIT 200`. The module's own dated source comment records a historically measured population above 3,700, more than 600 Tier 3 beliefs, and no Tiers 5–7 reached by this capped scan. The optional `NEX5_HARMONIZER_PARADOX_FIX` path rechecks already-open paradox pairs by ID for escalation; it does not broaden initial discovery. Therefore excluded beliefs may never enter the paradox/incubation workflow through this scan while the lower-tier prefix remains larger than the cap. Historical counts are not current host measurements; current population and flag state are UNKNOWN. Severity and any correction remain subject to the governing specification and Founder review.

### Current update — DRAFT-028 (24 Nov 2026)

**Graph spreading activation does not expand the Stage 3 retrieval candidate set.** `BeliefRetriever.retrieve()` computes graph activation from the top five keyword-scored seeds and blends activation with keyword scores, but final result assembly drops any activated belief ID absent from the original keyword-scored `row_map`. A graph-connected belief with zero query-token overlap is therefore not returned by this path solely because it is connected. The implementation currently uses graph activation to adjust/rerank keyword-matched candidates, not to retrieve graph-only neighbours. Whether candidate expansion is required is an acceptance-contract question; no behaviour change is authorised.


### DRAFT-030 test-inventory qualification — 24 Nov 2026

A recursive tracked-tree spot check at source head 90b4ee4cd4dbee06abfdb54fc8f8111264259831 found no dedicated tests/test_world_bridge*.py module. The inspected tests/test_fountain.py does not reference WorldBridgeSelector/select_and_log/world_bridge_log. tests/test_probe_snapshot.py does explicitly test feed_activity grouping and window behavior. This narrows the evidence to direct snapshot fixture coverage and no dedicated selector test module; it is not a claim that no WorldBridge assertion exists anywhere in the suite.


### Current update — DRAFT-029 (24 Nov 2026)

**BehaviouralSelfModel belief-usage metric inspects response text, not prompt injection.** `BehaviouralSelfModel.observe()` reads the last 100 stored role=`nex` message contents and increments `belief_usage_count` when a generated reply contains `her current beliefs` or `[tier`. The GUI stores the sanitized assistant response in that role; the retrieved belief block is assembled into the system prompt before generation and separately captured as `_retrieved_belief_text`. The metric therefore does not directly measure whether the belief block was injected into the prompt and may undercount or incidentally count. This value is compared to a seeded expectation and may generate a Tier 6 behavioural-observation belief. Runtime magnitude and resulting belief impact are UNKNOWN. If the intended measure is literal prompt inclusion, the current source path does not measure it; acceptance intent must be confirmed before any correction.


### Current update — DRAFT-030 (24 Nov 2026; acceptance question)

**Fountain identity-block treatment suppression fails open on ablation lookup errors.** When `NEX5_IDENTITY_BLOCK=1`, `identity_block._ablation_defers()` returns False if importing `identity_ablation` or reading its current condition raises. The identity block may therefore be appended when treatment status cannot be established. Existing `tests/test_identity_block.py` verifies a readable `reframe` treatment configuration and normal restoration, but the inspected tests do not inject import/config-read failure. This could compromise treatment isolation if the block is enabled during an ablation run. Whether the intended experiment contract is fail-open or fail-closed is UNKNOWN; no correction is authorised absent that contract. Default identity-block flag is OFF in source comments and no target-host flag state was observed.


### Current update — DRAFT-031 (24 Nov 2026; test-coverage gap)

**Fountain → ProblemMemory self-injection loop lacks direct integration coverage in inspected tests.** The source path selects a recent real-question pool only in the input-gap branch, requires at least three eligible candidates, applies per-candidate eight-hour and global 40-minute cooldowns, injects the selected title/description into the Fountain prompt, then records a source-tagged observation only when the emitted thought came from that prompt rather than an alternate emission path. The inspected `tests/test_problem_memory.py`, `tests/test_fountain.py` and `tests/test_problem_self_gate.py` do not cover this end-to-end contract or its cooldown/alternate-emission boundaries. No live impact or observed failure is claimed. This is a Phase 0 evidence/test-coverage gap only; no test or runtime change is authorised by this entry.


### Current update — DRAFT-032 (24 Nov 2026)

**Metacognition re-ingests unacknowledged GrooveSpotter alerts on successive ticks.** `_detect_groove()` reads up to three `groove_alerts` within 600 seconds where `acknowledged_at IS NULL`; `tick()` writes new `meta_cognition_events` for them, but the inspected producer/consumer paths do not update the source alert's acknowledgement state or otherwise record it as consumed. The same alert can therefore produce repeated meta-events on successive chat turns. `_maybe_engage_stillness()` counts groove meta-events over 1,800 seconds and engages stillness at three; repeated ingestion of one source alert could satisfy this threshold without three distinct alerts. `tests/test_metacognition.py` covers ignoring alerts already acknowledged before the tick, but not repeat ticks against one unacknowledged alert, source acknowledgement, or distinct-source thresholding. Runtime occurrence UNKNOWN. No fix authorised pending Phase 0 review and acceptance criteria.


### Current update — DRAFT-033 (24 Nov 2026)

**Metacognition event production has no demonstrated deduplication/decay lifecycle in the inspected chat path.** The chat route calls `tick()` per turn; the inspected boot/runtime path does not schedule `decay()`. The Phase 41 contradiction-rate and keystone-abandonment findings can remain true across multiple turns and have no per-type cooldown or already-open-event guard before `_write_event()`, so repeated unresolved rows are possible. GrooveSpotter repeats are separately tracked as DRAFT-032. Whether another maintenance caller exists outside the inspected path is UNKNOWN. No live row counts or target-host invocation history were examined.


### Current update — DRAFT-034 (24 Nov 2026)

**Throw-Net threshold return values do not gate queued sessions.** The TriggerDetector methods insert every qualifying gate-reject/gap-deflection event and return a boolean only when their same-topic threshold is reached. Both inspected callers ignore that boolean. The pending query selects all `fired=0` rows without checking `threshold_state` or an age cutoff, and the monitor processes every returned row when `NEX5_THROWNET=1`. Thus the documented 4/15-minute and 3/30-minute thresholds do not constrain which logged rows become sessions in the enabled monitor path. The monitor is explicitly retired by default; impact is conditional on the opt-in flag and queued rows. Existing trigger tests verify threshold booleans and that pending returns all unfired rows, but do not verify threshold-gated session eligibility. No host flag or live queue state was inspected. No correction authorised.

### Current update — DRAFT-035 (24 Nov 2026; documentation/callsite discrepancy)

**WorldBridge Phase A “log only” documentation is stale relative to the Fountain callsite.** The selector's module/class docs describe Phase A as no prompt modification and Phase B as future injection, but the generator receives the returned selections and appends them to its composition prompt; the selector is enabled in source and is called with `mark_injected=True`. Prompt assembly is therefore present in the inspected source. Whether the model attends to or acts on the selected content is not established. No runtime change authorised.


### Current update — DRAFT-036 (24 Nov 2026; activation/consumer gap)

**Surprise-event promotion worker is not wired in the inspected main boot path.** PredictiveSubstrate writes flagged rows to dynamic.db `surprise_events`; `theory_x/life/surprise_loop.py` is the separate component that promotes eligible rows to Tier 6 beliefs with `source='surprise'`. Fountain's generator reads that belief source for its six-hour surprise prompt block. The inspected `run.py` starts PredictiveSubstrate but contains no reference to `surprise_loop` or `surprise_tick`. A separately managed external caller is not ruled out; host process inventory is unavailable. AffectState reads raw surprise rows directly, so its arousal path remains distinct. Existing inspected prediction tests verify raw event writes, not the promotion-to-Fountain chain. No runtime change authorised.

### Current update — DRAFT-037 (24 Nov 2026; population-contract question)

**External prediction verification includes internal sense events excluded from prediction construction.** `_predict_external()` forms its centroid from sense streams excluding `internal.%` plus user messages. `_verify_one()` for `external_input` later queries all sense events in the target window without that exclusion, then compares them with the predicted centroid. This permits internal telemetry to count as the actual external observation. The inspected verification tests do not assert the intended exclusion. Whether this is deliberate broader outcome scoring or a scope mismatch remains UNKNOWN; no threshold or code correction proposed.


### Current update — DRAFT-038 (24 Nov 2026; trigger population extension)

**Throw-Net pending queue also admits VoiceEngine user-query misses.** VoiceEngine records every query as `trigger_type='user_query'`; successful substrate replies are marked fired, misses are unfired. The pending query selects every unfired row without filtering trigger_type. If the retired monitor is enabled, user-query misses can therefore be run through ThrowNet just like gate/gap triggers, without any per-topic threshold. This extends DRAFT-034's producer/consumer mismatch. Runtime effect remains conditional on `NEX5_THROWNET=1` and actual pending misses.

### Current update — DRAFT-039 (24 Nov 2026; source-comment/call-path discrepancy)

**VoiceEngine comment claims substrate misses suppress LLM fallback, but inspected chat control flow continues into LLM composition.** In default `use_substrate` mode, `query_reply()` returning None leaves `text=None`; the subsequent `if text is None` branch calls `state.voice.speak()`. The source therefore demonstrates retrieval-first with LLM fallback, not strict substrate-only miss handling. Whether this is a stale comment or a contract regression needs governing acceptance criteria; no change made.

### Current update — DRAFT-040 (24 Nov 2026; dormant producer)

**SelfNarrative rut-notice tick has no demonstrated main-runtime invocation.** Narrative writes from CoherenceGate/NovelAssociation and chat retrieval are wired, but the rut-detection producer is implemented in `SelfNarrative.tick()`. The inspected `run.py` and `gui/server.py` paths neither call that method nor start a SelfNarrative loop. External dispatch is not ruled out, but the inspected Theory X registry does not establish automatic ticking. No claim about live rut notices is made.



### Current update — DRAFT-041 (24 Nov 2026; conditional dry-run state-accounting mismatch)

**Moltbook dry-run responses are treated as completed external actions by the caller loops.** `MoltbookClient` defaults `MOLTBOOK_DRY_RUN` to `1` and returns a structured `{"dry_run": true, ...}` object for non-GET calls without contacting Moltbook. The inspected callers do not branch on that marker:

- `PostLoop.post_tick()` extracts no post ID from the dry-run result, but still inserts `moltbook_posts.status='posted'`, marks the queue row `posted`, and marks other in-window candidates `skipped`.
- `DMResponder._handle_one()` marks the pending reply `sent` after the dry-run `dm_send()` returns normally.
- `DMListenLoop._approve_pending_requests()` records a conversation as `approved=1` after the dry-run approval returns normally.

These local statuses can therefore represent simulated calls as completed external actions. The default dry-run setting makes the condition relevant if these loops are launched without overriding the environment. This is not evidence the loops are currently running: the inspected main `run.py` does not construct/start the Moltbook loops, and the GUI route only reads optional activity tables. The client still loads the credentials file at construction even in dry-run mode.

Test boundary: the only Moltbook-specific test file found is `tests/test_moltbook_optional.py`, which tests optional-table/HUD behaviour and daily-life fallback; it does not exercise the listener, poster or responder action/status paths. No live account, daemon or host state was inspected. Treat as a source-confirmed conditional state-accounting mismatch, not a deployed incident. No correction authorised in Phase 0.

Current source hashes:
- `theory_x/stage7_moltbook/client.py`: `0b60ce8ab9ec2e935c9abb55311235f07e43631e`
- `theory_x/stage7_moltbook/poster.py`: `3acdf141685c28b60ea66102e3fcd2538ab22923`
- `theory_x/stage7_moltbook/listener.py`: `54c5a1d91aa54525c768d0b0c4914d6d830e6d83`
- `theory_x/stage7_moltbook/responder.py`: `0e568897167e458b61701b29e3fcd2538ab22923`
- `run.py`: `73a2c58a4f5f0348135a46eb83d6cdd61db874e7`
- `gui/server.py`: `5ee8b167f386466c383090445c63a84810bbae52`
- `tests/test_moltbook_optional.py`: `6bff5f1a331cd2133396853960e3cb3f9f39c3a6`

### Current update — DRAFT-042 (24 Nov 2026; selection-order/documentation mismatch)

**Moltbook PostLoop's implementation does not follow its documented candidate priority.** `_pick_best()` says it ranks first by highest `word_count`, then by newest `queued_at` among ties. Its actual descending sort key is `(queued_at, word_count)`, making recency the primary criterion and word count only the tie-breaker. This can select a newer shorter thought over an older longer one within the same eligible queue window. No PostLoop-specific test exists in the inspected tree. Whether the code or the stated priority is authoritative remains unresolved; no selection policy is changed in Phase 0.

Source hash: `theory_x/stage7_moltbook/poster.py` `3acdf141685c28b60ea66102e3fcd2538ab22923`.



### Current update — DRAFT-043 (24 Nov 2026; default-on prompt arbitration / empty-surprise candidate)

**GlobalWorkspace can promote an empty prediction-window record into the highest-salience prompt frame.** Fountain enables GlobalWorkspace by default (`NEX5_GLOBAL_WORKSPACE` defaults to `"1"`). Its surprise candidate query accepts any recent row with `surprise_score > 0.3`; unless `NEX5_GW_SURPRISE_NONEMPTY=1`, it does not exclude `actual_content IS NULL` or the empty-window sentinel score. The module's own comment states an empty prediction window scores 1.0 and previously won the workspace with an empty quote. Surprise weight is 1.00, above every other candidate weight in this arbiter (stakes 0.90, momentum 0.55, Bonsai 0.50, drive 0.45). Thus, if such a recent row exists while the filter flag is unset, the empty surprise candidate can win and its framing line is prepended to Fountain's focus block. This is a prompt-influence path, not merely telemetry.

The code contains an opt-in mitigation, `NEX5_GW_SURPRISE_NONEMPTY=1`, but it is default OFF. Host flag state, frequency of empty rows and actual prompt incidence are UNKNOWN. The repository tree contains no dedicated GlobalWorkspace test file; no claim is made about indirect coverage. The intended treatment of empty prediction windows needs acceptance criteria before correction. No runtime change authorised.

Source hashes:
- `theory_x/stage_tom/global_workspace.py`: `54ddab05112702eef34faaa4f24d45139350b349`
- `theory_x/stage6_fountain/generator.py`: `43644876295ffdd649a240f52a7946c666a8579f`



### Current update — DRAFT-044 (24 Nov 2026; SelfBinding drift field is a hardcoded placeholder)

**SelfBinding persists a `drift='clean'` value without reading the value-drift monitor.** The `bind()` implementation contains a comment saying it reads the last logged verdict, but the actual assignment is the literal `drift = "clean"`. That value is written to both `self_state` and `self_state_history`. It is not included in the returned `components` object or the synthesis text. The inspected `recursive_self` caller consumes the returned components (emotion, rāga, attending, etc.), not the drift column. The separate `value_drift_monitor.py` writes to its own `value_drift_log`; no read/join from that log is present in `self_binding.bind()`.

This does not establish that a false clean verdict is injected into the Fountain prompt: the inspected recursive prompt path does not read the drift column, and no production consumer of `self_state.drift` was identified in the bounded caller review. It does establish that the persisted field/history represents a constant placeholder rather than a monitored drift state, despite the comment and faculty description. Whether the column should remain explicitly unknown/placeholder or be connected to the separate monitor requires acceptance criteria. No correction authorised.

Source hashes:
- `theory_x/stage_tom/self_binding.py`: `acbbe02e00723ebc6c5fd13236251f4877259ce5`
- `theory_x/stage_tom/recursive_self.py`: `ada4aeb260a8deb70418c03dc9180f71cddec714`
- `theory_x/stage_tom/value_drift_monitor.py`: `e08a9649bd94e9094b49aeae59aa9f8feeacbff5`
