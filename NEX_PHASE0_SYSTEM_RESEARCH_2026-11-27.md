# NEX 5.0 — Phase 0 System Research Continuation

**Evidence snapshot:** `main` at `14873c10673760b8adbbf6fb0076226d1c97ffa4`  
**Date:** 27 November 2026  
**Method:** remote source inspection, repository history, tests and GitHub Actions evidence.

## 1. Scope and evidence limits

This is a selected-path source audit, not a complete architecture recertification. No local NEX checkout, host service unit, running process, live database, credential, model endpoint or external service was accessed. No NEX runtime was started. Statements about activation refer to tracked boot wiring and launcher configuration, not proof of host-effective state.

Source-level risks below are not claims that an incident has occurred. Distinguish:
- **Verified source fact:** directly visible in current-main code.
- **Conditional risk:** a failure mode implied by source ordering or lifecycle.
- **Policy question:** a behaviour contract that must not be silently decided by implementation.
- **Host/runtime unknown:** requires authorised host evidence.

## 2. Current validation

| Change | Exact-head evidence | Mainline result |
|---|---|---|
| PR #275 — mind-map freshness recheck | Run `46038691720`: 2,632 passed, 7 skipped, 45 subtests; baseline OK | Merged as `49837fd20fd8d2271582c1b3d0012cd0d47ab8bb` |
| PR #276 — exclude generated RDO cycle records from source search | Run `46040900959`: 2,634 passed, 7 skipped, 45 subtests; baseline OK | Merged as `baac6926cacd23e85b44ee847d90cc42babefc61`; post-merge main run `46041833321` also passed 2,634 |
| PR #277 — resolve keepalive checkout relative to script | Run `46042032164`: 2,636 passed, 7 skipped, 45 subtests; baseline OK | Merged as `14873c10673760b8adbbf6fb0076226d1c97ffa4`; merged files are byte-identical to the tested head |

The latest mind-map verifier reports **30 nodes, 0 unverified, 14 dark and 2 blocked**, with no stale-source warnings. Two doctrine references remain missing (`VIRTUE_SLATE.md`, `mental_factors_inventory_alobha_spec.txt`), and the `p13_finitude` unblock marker remains past due. These are still visible warnings, not permission to rearm anything.

## 3. Boot and lifecycle architecture

The tracked boot graph is not a single request loop. `run.py` builds the dynamic layer, world-model layer, membrane and GUI/AppState. The Stage 2 dynamic factory registers multiple loop callables, including `signal_to_problem_loop`. The tracked launcher also sets `NEX5_PROBLEM_SELF_GATE=1` and `NEX5_SIG_QUALITY=1`; this is tracked configuration, not proof of host-effective state. Separate scheduler, diversity, edge-generation, signal and other worker paths add further concurrency.

The important consequence is that lifecycle ownership must be explicit. The presence of a `stop()` or stop-event helper in a worker does not prove the application invokes it, joins the thread, or waits for its in-flight writes before closing shared Writers.

## 4. New source findings

### G-80 — Reanimation is marked consumed before delivery is durable

**Sources:** `theory_x/diversity/reanimate.py` (`wake_one()`, `pop_reanimated()`); `theory_x/stage6_fountain/generator.py` (reanimation cadence).

`wake_one()` selects a dormant belief, writes `reanimated_at` to the database, then stores the selected row in the process-local `_pending_reanimation` variable. `pop_reanimated()` returns that value and clears the variable. Fountain later consumes it on its cadence.

There is no durable pending-delivery record or startup recovery for a row whose `reanimated_at` is already set but whose process-local pending value was never delivered. A process loss between the database update and Fountain consumption can therefore leave the belief marked reanimated with no recoverable handoff. This is an at-most-once delivery window, not an observed loss.

**Next evidence required:** define whether reanimation is at-most-once or recoverable at-least-once; then add a restart/failure-injection test before choosing an outbox, acknowledgement or retry design.

### G-81 — Fountain and ClockRunner count different fire populations

**Sources:** `theory_x/stage6_fountain/generator.py`; `theory_x/diversity/consolidation.py`.

The generator increments `_total_fires` at four output paths, while `notify_fire()` appears only in the normal LLM-generation path. ClockRunner thresholds use the notified fire count; Fountain's reanimation cadence uses `_total_fires`.

The counters therefore do not represent the same event population. This may be intentional, but the word “fire” currently has at least two operational meanings. Define whether it means every generated output or only an LLM fire, then make the counter names, cadence and tests reflect that distinction.

### G-82 — Dormancy scan coverage is folded into G-73, not a separate defect

**Sources:** `theory_x/diversity/dormancy.py`; `theory_x/diversity/consolidation.py`; `theory_x/diversity/loop.py`.

The current scanner selects the first 50 beliefs ordered by creation time and has no persistent cursor. ClockRunner constructs a new scanner in its fast path, while DiversityLoop has a separate scanner instance. That leaves two scanner owners and no demonstrated fairness for rows beyond the first page.

The older PR #102 cursor proposal and PR #145 persistence follow-on are drafts on `claude/nex-continuity-wire`, not current-main fixes. The proposed Fountain lookup in #102 also fails to recheck the retired marker at final injection. Keep this within the existing G-73 scan-coverage/ownership/eligibility review; do not treat the old proposals as approved fixes.

### G-83 — Metacognition can count the same unacknowledged groove alert repeatedly

**Sources:** `theory_x/stage9_metacognition/metacognition.py`; `gui/server.py`.

The Chat route calls `metacognition.tick()`. Its groove detector reads recent `groove_alerts` where `acknowledged_at IS NULL`, then writes corresponding `meta_cognition_events`. The inspected path does not acknowledge the source alert. The stillness detector counts groove event rows in its lookback window rather than distinct source alerts.

Consequently, repeated Chat turns can re-emit the same unacknowledged alert and make one source alert appear to be several observations. That can satisfy the stillness count threshold without three distinct detections. No acknowledgement writer was found in the reviewed GrooveSpotter, GrooveBreaker, Metacognition or GUI paths.

This requires an explicit event/acknowledgement contract and a distinct-source regression test. Do not change stillness thresholds or reflective behaviour before that review.

### G-84 — Shutdown does not quiesce all producers before closing Writers

**Sources:** `gui/server.py:AppState.close()`; `theory_x/stage1_sense/scheduler.py`; `theory_x/stage2_dynamic/__init__.py:stop_dynamic()`; `substrate/writer.py`; `nex_keepalive.sh`.

Current `AppState.close()` calls `scheduler.shutdown()` and then closes Writers. It does not call the available `stop_dynamic()` helper or coordinate the other worker families. Scheduler shutdown signals adapter stop events but does not join their threads. The dynamic layer has a stop-and-join helper with a 30-second default, but it is not invoked by AppState.close.

Writer.close enqueues a sentinel, joins for up to 10 seconds, then clears its thread reference. Writer.submit has no closed-state guard: a late submission can be queued after the sentinel with no worker left to resolve its Future. The keepalive supervisor's graceful-stop path waits 15 seconds before SIGKILL.

This is a source-level shutdown ordering risk. Producers can still be active while Writers are draining or closed; late writes may be lost or wait indefinitely. A proper fix needs a coordinated global deadline: stop accepting requests, signal all producers, join them, drain Writers, then close databases. The worker join budget must fit inside the supervisor deadline. No live shutdown incident is claimed.

### G-85 — SignalToProblem is an active one-pen bypass with a cross-database commit boundary

**Sources:** `theory_x/stage2_dynamic/__init__.py`; `theory_x/signals/signal_to_problem.py`; `theory_x/signals/prose_stats.py`; `substrate/schema/beliefs.sql`.

The Stage 2 dynamic factory registers `signal_to_problem_loop`. The loop receives a DynamicState containing shared Writers and Readers, but the current worker ignores them.

`signal_to_problem_tick()` opens direct write-capable connections to both `beliefs.db` and `conversations.db`. It adds `signals.actioned_at` with runtime `ALTER TABLE` if absent; that column is not declared in the canonical `beliefs.sql` signals schema. It writes `actioned_at` and `open_problems`, then commits beliefs first and conversations second. A process loss or second-commit failure after the first commit can leave a signal marked actioned without its problem record.

Every 30 ticks (roughly hourly at its 120-second cadence), the same loop calls `prose_stats.build_direct()`, which also opens a raw beliefs connection. A Writer/Reader-based `prose_stats.build()` already exists, but the scheduled loop does not use it. No dedicated `tests/test_signal_to_problem.py` or `tests/test_prose_stats.py` exists in the current test tree.

This is an omitted active path in the G-61 one-pen audit and corresponds to the earlier G-44 cross-database finding. Do not mechanically route writes through Writers and assume the recovery problem is solved. The founder/design decision must establish the intended cross-database contract: ordering, idempotent replay, outbox or reconciliation. The auxiliary prose-statistics writer can be migrated separately after its performance and equivalence are tested.

### G-86 — SignalReaper's preservation allowlist has drifted from SignalToProblem

**Sources:** `theory_x/signals/reaper.py`; `theory_x/signals/signal_to_problem.py`.

SignalToProblem currently promotes `2_branch`, `3_branch`, `4_branch` and `advancements_drift`. SignalReaper preserves `2_branch`, `3_branch`, and several older types (`t6_promotion_burst`, `pattern_recognition_burst`, `cross_branch_convergence`, `novel_arc`, `concept_emergence`), but omits the two current types.

The reaper only considers rows older than seven days; SignalToProblem's promotion query looks back six hours. Therefore this mismatch does not establish loss of a currently eligible promotion. It does mean obsolete unconsumed types can be retained indefinitely while current types are not preserved according to the reaper's own stated contract. Align the policy and add a shared allowlist test; do not claim a live data-loss incident.

### G-87 — Moltbook dry-run is not offline and local state can report simulated actions as real

**Sources:** `nex_keepalive.sh`; `theory_x/stage7_moltbook/client.py`, `listener.py`, `poster.py`, `responder.py`.

Current main sets `MOLTBOOK_DRY_RUN=1`. The client suppresses non-GET requests in dry-run, but GET requests still reach the remote service. The listener can still read inbound conversations, filter agents, approve eligible DM requests and write local records. Incoming pending replies are stored with `needs_human=0`.

The poster and responder treat the client's synthetic dry-run response as success and persist local `posted`/`sent` status. Both the poster's candidate query and the responder's related-belief retrieval select recent `fountain_insight` (and, for the responder, `spectrum` and `precipitated_from_sense`) beliefs without tier, paused, locked or retired-state filtering.

Thus dry-run suppresses outbound writes but is neither offline nor a no-ingestion mode, and its local status can overstate what happened externally. If dry-run is disabled, the eligible DM path can send without a human approval step after the agent filter. No external calls were made during this audit; host credentials and effective service configuration remain unknown. This needs a founder decision on external consent, human approval, belief eligibility and simulated-state labels.

### G-88 — Keepalive checkout path hardcoding (CLOSED by PR #277)

The tracked launcher previously hard-coded `/home/rr/Desktop/Desktop/nex5` for its initial directory, Git revision lookup and journal. PR #277 now derives `SCRIPT_DIR` from the script path, with a regression test covering a different working directory and a path containing spaces. It deliberately preserves main's `MOLTBOOK_DRY_RUN=1`; the continuity branch's `=0` setting was not imported.

The source portability defect is closed. The active host systemd unit and whether it invokes this script remain UNKNOWN.

### G-89 — RDO source reconciliation could read its own ignored cycle output (CLOSED by PR #276)

The RDO stores generated cycle records under ignored `rdo/.cycles/`. Both `rdo/reconcile.py::_grep` and `rdo/belief_audit.py::_grep` previously searched that directory, allowing a prior generated plan to appear as a source-signature match on a later cycle. PR #276 excludes `.cycles` in both paths and adds regression tests. The fix is merged and the post-merge main baseline passed 2,634 tests.

This was an evidence-contamination risk, not automatic semantic acceptance: semantic reuse still had a separate review gate.

## 5. RDO capability and authority boundary

The RDO is an external advisory engineering tool, not a NEX runtime faculty. It is not imported into the cognitive boot path.

Its current objective intake requires 1–200 `seed_obligations` and a `reconciliation_signatures` object. The intake adapter does not call an LLM or derive those initial seeds from raw natural-language intent. The extrapolator then applies a bounded rule catalogue (default maximum depth 4) and records a frontier when no rule applies or the depth limit is reached.

Therefore the current RDO is a structured, deterministic expansion/reconciliation/work-package engine after an external human or model supplies the initial obligation/signature interpretation. It is not yet a fully autonomous raw-idea-to-complete-build compiler. That is a capability gap relative to the desired Recursive Extrapolator, not a reason to remove its current boundedness.

The RDO README describes 14 core modules / 3,775 non-comment LOC and a self-check result of “needs review” against its 1,800-LOC heuristic. The README also cautions that its Pareto/priority weights are scaffolding and uncalibrated. Treat work-package rankings as provisional.

OFT is implemented in `rdo/tension.py` as a structured node/relationship/system assessment, with verdicts and evidence separated from inference. The v1.4 reconciliation note records that the founder supplied the original v1.4 text in a prior conversation, but the raw 47,172-byte source is not available in the current repository/Library for fresh comparison. The RDO stage documents use v1.3 §16; some pre-existing source docstrings cite v1.4. The v1.4 reconstruction is explicitly non-normative and incomplete. Version precedence remains unresolved; do not silently remap references, claim formal supersession or ask the founder to re-supply the text by default.

Stage 7's restricted execution path requires exact per-call test allowlists. The newer handoff manifest defaults to `execution_authority=none`; it is a source/evidence handoff, not permission to execute arbitrary commands or alter NEX runtime state. Human acceptance is caller-attributed, not identity-authenticated. Runtime evidence remains unknown.

## 6. Branch and proposal hygiene

PR #102 and PR #145 remain drafts targeting `claude/nex-continuity-wire`, not current main. That branch has advanced 309 commits beyond the original PR base. Its tracked keepalive currently sets `MOLTBOOK_DRY_RUN=0`, whereas current main sets `=1`. PR #102's final Fountain lookup also does not recheck the retired marker. These are useful research leads, not merge-ready current-main fixes. Do not merge the branch or its stacked proposals wholesale; rebase, re-audit and validate each bounded change against current main.

## 7. Recommended next sequence

1. Complete the G-61/G-85 SignalToProblem persistence design, beginning with a written cross-database recovery contract. Consider a separate, semantics-preserving migration of the hourly prose-statistics builder to the existing Writer/Reader path.
2. Design a central shutdown coordinator with one global deadline, producer joins and fail-fast post-close Writer behaviour; reconcile it with the keepalive supervisor's 15-second deadline.
3. Make reanimation handoff durable and test crash/restart windows; define the fire-counter semantics before changing cadence.
4. Define groove-alert acknowledgement/idempotency and distinct-source stillness evidence.
5. Review Moltbook's external consent, dry-run labels and belief eligibility before any live external mode.
6. Continue the faculty producer/consumer and one-pen census; keep G-73 eligibility and scan ownership open pending Gate 0.
7. Extend the RDO objective-intake path so raw objectives can be transformed into traceable seed obligations without pretending that the current rule engine already does this autonomously. Resolve v1.3/v1.4 precedence separately.

## 8. Governance boundary

The consolidated S-01–S-25 register, Master Roadmap, Gate 0 and Phase 1 boundaries remain unchanged. Gate 0 is pending founder review; Phase 1 is not authorized. No NEX cognitive policy, feature flag, live database, experiment, host service or runtime state was changed by this research or by PRs #276–#277.
