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
