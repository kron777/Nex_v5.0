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

Current `AppState.close()` calls `scheduler.shutdown()` and then closes Writers. It does not call the available `stop_dynamic()` helper or coordinate the other worker families. `run.py` starts the SpeechQueueConsumer, SignalLoop, DiversityLoop and EdgeGeneratorLoop; AppState stores the first three but its close method ignores them, while the EdgeGeneratorLoop is not stored in AppState at all. The decoder stop event is set by the SIGTERM handler but its thread is not joined. Scheduler shutdown signals adapter stop events but does not join their threads; `_AdapterThread` does not retain the thread handle. The dynamic layer has a stop-and-join helper with a 30-second default, but it is not invoked by AppState.close.

Writer.close enqueues a sentinel, joins for up to 10 seconds, then clears its thread reference. Writer.submit has no closed-state guard: a late submission can be queued after the sentinel with no worker left to resolve its Future. The keepalive supervisor's graceful-stop path waits 15 seconds before SIGKILL.

This is a source-level shutdown ordering risk. Producers can still be active while Writers are draining or closed; late writes may be lost or wait indefinitely. A proper fix needs a coordinated global deadline: stop accepting requests, signal all producers, join them, drain Writers, then close databases. The worker join budget must fit inside the supervisor deadline. No live shutdown incident is claimed.

### G-85 — SignalToProblem is an active one-pen bypass with a cross-database commit boundary

**Sources:** `theory_x/stage2_dynamic/__init__.py`; `theory_x/signals/signal_to_problem.py`; `theory_x/signals/prose_stats.py`; `substrate/schema/beliefs.sql`.

The Stage 2 dynamic factory registers `signal_to_problem_loop`. The loop receives a DynamicState containing shared Writers and Readers. Since PR #279, it uses the shared beliefs Writer/Reader for the auxiliary prose-statistics rebuild; the primary `signal_to_problem_tick()` still ignores those handles and opens its own connections.

`signal_to_problem_tick()` opens direct write-capable connections to both `beliefs.db` and `conversations.db`. It adds `signals.actioned_at` with runtime `ALTER TABLE` if absent; that column is not declared in the canonical `beliefs.sql` signals schema. It writes `actioned_at` and `open_problems`, then commits beliefs first and conversations second. A process loss or second-commit failure after the first commit can leave a signal marked actioned without its problem record.

Every 30 ticks (roughly hourly at its 120-second cadence), the loop now calls `prose_stats.build(state.writers["beliefs"], state.readers["beliefs"])`. PR #279 migrated this auxiliary rebuild to one shared-Writer transaction and added `tests/test_signal_to_problem.py` and `tests/test_prose_stats.py`. Those tests cover the auxiliary path; they do not exercise the primary tick's cross-database failure boundary.

This is an omitted active path in the G-61 one-pen audit and corresponds to the earlier G-44 cross-database finding. Do not mechanically route writes through Writers and assume the recovery problem is solved. PR #279 closes the auxiliary prose-statistics direct-write bypass. The founder/design decision must still establish the primary cross-database contract: ordering, idempotent replay, outbox or reconciliation.

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

### G-90 — Social silence is not yet represented as a contextual social act (capability gap)

**Sources:** `theory_x/SOCIAL_PRESENCE_PROTOCOL.md`; `theory_x/stage_social/social_presence.py`; `theory_x/conversation_memory.py`; `theory_x/stage9_metacognition/metacognition.py`; `theory_x/stage6_fountain/generator.py`.

The Social Presence Protocol and isolated module define response-count and average-response-latency metrics, but the module is disabled in current boot (see G-91). ConversationMemory retains a bounded turn history. The two implemented “stillness” mechanisms are different: Fountain detects repeated retrieval overlap and eventually force-fires after a stillness streak; Metacognition writes a time-limited `stillness_log` entry after a groove-event threshold. These are internal generation/pacing signals, not a model of social silence. Fountain also contains natural-language self-reflection about silence, but the reviewed paths do not turn that into a structured social-silence state or classifier.

No reviewed current-main path distinguishes deliberate social silence from technical failure, or interprets silence in relation to duration, relationship, conversational dynamics, emotional circumstances and likely human interpretation. The system has adjacent context signals, but response latency alone is not an interpretation of silence.

This is a capability gap against the founder's stated social-silence design principle, not a claim that a frozen S-01–S-25 requirement is violated. Do not equate retrieval stillness or groove suppression with social silence. A future design should distinguish listening, companionship, respect, familiarity, reflection, restraint, rejection, avoidance and abandonment, while also detecting technical failure and expected-response context.

### G-91 — SocialPresence protocol claims autonomous boot, but current boot disables it (OPEN)

**Sources:** `run.py`; `theory_x/SOCIAL_PRESENCE_PROTOCOL.md`; `theory_x/stage_social/social_presence.py`; `gui/server.py`; `theory_x/stage9_metacognition/metacognition.py`; `tests/test_social_presence.py`.

The protocol says SocialPresence is registered in `run.py`, starts a daemon loop and snapshots every 300 seconds. Current `run.py` explicitly records its removal, sets `_social_presence = None`, and assigns `metacognition._sp = None`. The GUI's `current_summary()` injection and Metacognition's `_sp` consumers are conditional, so they are inactive under this boot path.

The removal comment says the module had no GUI/chat consumers, but current main now contains guarded consumer call sites in `gui/server.py` and Metacognition. The comment's consumer rationale is therefore stale even though the module remains disabled. The isolated SocialPresence unit tests do not establish boot integration or live operation.

**Disposition:** treat SocialPresence metrics and its autonomous loop as disabled on current main. Decide whether to restore it with meaningful consumers, or explicitly mark the protocol deferred/archived. Do not re-enable it merely to make the protocol text true; if restored, add boot-wiring, consumer and shutdown tests.

## 5. RDO capability and authority boundary

The RDO is an external advisory engineering tool, not a NEX runtime faculty. It is not imported into the cognitive boot path.

Its current objective intake requires 1–200 `seed_obligations` and a `reconciliation_signatures` object. The intake adapter does not call an LLM or derive those initial seeds from raw natural-language intent. The extrapolator then applies a bounded rule catalogue (default maximum depth 4) and records a frontier when no rule applies or the depth limit is reached.

Therefore the current RDO is a structured, deterministic expansion/reconciliation/work-package engine after an external human or model supplies the initial obligation/signature interpretation. It is not yet a fully autonomous raw-idea-to-complete-build compiler. That is a capability gap relative to the desired Recursive Extrapolator, not a reason to remove its current boundedness.

The RDO README describes 14 core modules / 3,775 non-comment LOC and a self-check result of “needs review” against its 1,800-LOC heuristic. The README also cautions that its Pareto/priority weights are scaffolding and uncalibrated. Treat work-package rankings as provisional.

OFT is partially implemented in `rdo/tension.py` as a structured node/relationship/system assessment, with verdicts and evidence separated from inference. The founder indicated on 24 November that they believed v1.4 had been approved; v1.4 is the current working specification, while v1.3 remains historical implementation lineage. The raw 47,172-byte v1.4 source is not mounted in the current repository/Library for fresh byte-level comparison, and formal frozen supersession is not recorded in the consolidated NEX register. Do not silently remap historical v1.3 references or ask the founder to re-supply the text by default.

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
7. Extend the RDO objective-intake path so raw objectives can be transformed into traceable seed obligations without pretending that the current rule engine already does this autonomously. Use v1.4 as the current working basis; preserve v1.3 as historical.

## 8. Governance boundary

The consolidated S-01–S-25 register, Master Roadmap, Gate 0 and Phase 1 boundaries remain unchanged. Gate 0 is pending founder review; Phase 1 is not authorized. No NEX cognitive policy, feature flag, live database, experiment, host service or runtime state was changed by this research or by PRs #276–#277.


## 9. Post-snapshot implementation update — PR #279

After the research snapshot above, PR #279 merged as `8d2121d121931d37afcb1c3d23d27e7ccc9145d1`. It routes the scheduled prose-statistics rebuild from `SignalToProblem` through the existing shared beliefs Writer/Reader path and replaces per-token writes with one Writer transaction. The direct builder remains available for comparison/compatibility, but the scheduled loop no longer calls it.

Exact-head CI run `46044361663` passed **2,638 tests, 7 skipped, 45 subtests; baseline OK**. New tests compare Writer/Reader output with the direct builder and assert the scheduled loop calls the shared path. Post-merge main run `46045384807` also passed **2,638 tests, 7 skipped, 45 subtests; baseline OK**. Its mind-map verifier reported 30 nodes, 0 unverified, 14 dark, 2 blocked; the two missing doctrine references and overdue `p13_finitude` marker remain visible warnings.

This closes the auxiliary prose-statistics direct-write bypass only. The primary `signal_to_problem_tick()` path still opens direct write-capable connections to `beliefs.db` and `conversations.db`, dynamically adds `signals.actioned_at`, and commits the two stores separately. G-85/G-61 therefore remain open; the cross-database idempotency/recovery contract is still needed before migrating the primary writes. No cognition policy or runtime state changed.


### RDO objective-context gap — candidate G-91

The intake validator requires and preserves `intent`, `owner`, `scope`, `constraints`, `exclusions`, and `acceptance_criteria`, but `submit_objective()` does not pass those fields into the planning pipeline. It constructs the cycle from `original_text`, top-level `assumptions`, caller-supplied `seed_obligations`, `relationships`, `reconciliation_signatures`, and `max_depth`; `objective_input` on the cycle contains only identity, revision, input digest and repository revision. The full input remains in the append-only revision ledger, but the other context fields are not translated into obligations or checked against proposed work packages.

This is a capability/contract gap, not an execution defect: RDO remains advisory and does not apply the proposed work. However, a caller can supply a constraint or exclusion that is preserved for audit while the resulting work-package graph is not checked against it. The acceptance criteria likewise are not currently used as a completion-verification contract. The current deterministic engine also requires externally supplied seed obligations and reconciliation signatures; it does not compile raw natural-language intent into that initial network by itself.

**Evidence:** `rdo_adapters/objective_intake.py::validate_objective()` validates these fields; `submit_objective()` (around lines 447–504) passes only the fields listed above to `run_cycle()`. `rdo/orchestrator.py::run_cycle()` has no scope/constraint/exclusion/acceptance-criteria inputs. Existing intake tests cover validation, revision integrity, replay and pipeline execution, but do not assert that those contextual fields constrain the generated plan.

**Next step:** define a typed, traceable translation from context to obligations/anti-requirements and a separate acceptance-verification record. Keep free-text constraints visible as unresolved review obligations rather than claiming they are enforced. Treat v1.4 as the current working specification and v1.3 as historical. Do not change objective schema v1 without a specific, traceable design reason.


## 10. Post-snapshot implementation update — PR #280

PR #280 merged as `f03a3d2e7b9c71801e44be73cf728c01cb791c9d`. It serializes Writer submission admission with shutdown, places one sentinel after all accepted requests, rejects late submissions synchronously, retains the worker reference after a join timeout, and preserves explicit restart after a clean close.

Exact-head CI run `46045754339` passed **2,640 tests, 7 skipped, 45 subtests; baseline OK**. Regression tests exercise accepted-request draining, late-submit rejection, timeout behavior, prevention of a second worker while the first remains alive, and explicit restart. Post-merge main CI is in progress.

This closes the Writer-level late-submission/forgotten-worker subproblem within G-84. It does not stop or join all NEX producers: `AppState.close()` still ignores several started loops, the EdgeGeneratorLoop is not retained in AppState, and scheduler adapter threads are not joined. The application-level global shutdown coordinator remains open. No live process or database was touched.
