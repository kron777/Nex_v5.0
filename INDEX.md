# NEX 5.0 — INDEX / DEVELOPMENT MANUAL

**Last verified against:** `main` at `e78773def4549f646257945e5886ec71a7837374`  
**Evidence date:** 27 November 2026  
**Purpose:** first-read guide for development, architecture review and operational investigation.

This is a living orientation document, not a governing specification, roadmap, runtime-state report or proof of cognitive capability. Source code and approved project documents take precedence. When this index conflicts with source, correct this index rather than bending source to fit it.

---

## 1. What NEX is

NEX 5.0 is an experimental, continuously executable cognitive architecture. It coordinates persistent state, sensing, dynamic formation, structured beliefs, attention, self-modelling, memory, metacognition, affect, language-model interaction and external interfaces.

The language model is one component, not the whole system. NEX's longer-term direction includes a reusable, locally operable cognitive layer for robotics. Robotics/cloud deployment, fleet intelligence and production-grade embodied autonomy remain development directions, not capabilities established by this repository snapshot.

NEX does **not** claim to have established consciousness or subjective experience. Implemented functional analogues and observed behaviour do not prove an experiencing subject. Keep claims proportional to evidence.

### Evidence vocabulary

Use these distinctions consistently:

- **Specified:** described in an approved specification or design.
- **Present:** source code or a testable component exists.
- **Boot-wired:** the normal boot path constructs or starts it.
- **Enabled:** its relevant runtime flag/configuration is active in the environment being examined.
- **Consumed:** its output reaches a downstream decision, prompt, retrieval surface, persistence path or user-facing effect.
- **Measured:** a controlled probe or runtime observation demonstrates the claimed effect.
- **Validated:** the effect survives an appropriate falsifier, baseline comparison and regression coverage.

These are not synonyms. A module can be present but dark; boot-wired but disabled by a flag; enabled but not consumed; or consumed without a demonstrated beneficial effect. A unit test of a module alone does not prove end-to-end runtime behaviour.

---

## 2. Authority and development governance

Do not infer project authority from repository convenience or from this index.

- Follow the current user-approved Master Roadmap and its phase gates. The known project position is **Phase 0 / Gate 0 pending founder review**; do not move into Phase 1 without the required explicit approval.
- The consolidated **S-01–S-25 specification/register is frozen**. Do not edit or reinterpret it as part of ordinary documentation maintenance.
- The separate user-authored **NEX v5.0 — DEVELOPMENT PROPOSAL V2.1** is not interchangeable with S-01–S-25. Its exact authoritative original/approval record must be retrieved before relying on its detailed contents.
- Do not substitute the older root `SPECIFICATION.md`, `ARCHITECTURE.md`, `DOCTRINE.md`, a mind map, the DAG, a handover or this index for the governing roadmap or frozen register.
- `mind_map/MIND_MAP.yaml` is explicitly descriptive. It must not gate, score, block or veto runtime action.
- `sentience_dag.json` with `nex_next_dev.py` is a separate development/buildability graph. It is not the Master Roadmap.
- Watcher and the Recursive Development Orchestrator (RDO) are external development/evidence instruments, not NEX runtime faculties. Human authority remains outside consequential project changes.

If an authority document is absent or ambiguous, retrieve it or ask. Do not invent a replacement.

---

## 3. Repository and runtime orientation

### Core entry points

| Path | Role |
|---|---|
| `run.py` | Unified NEX boot sequence and AppState wiring |
| `nex_keepalive.sh` | Single-instance supervisor, restart and standby handling |
| `nex_config.py` | Registry/validation for NEX5 environment flags |
| `substrate/init_db.py` | Six-database schema and migration initialization |
| `substrate/writer.py` | Serialized per-database write queue |
| `gui/server.py` | Flask cockpit and Chat API |
| `theory_x/` | Cognitive faculties, stages and experimental mechanisms |
| `voice/`, `speech/` | Model and speech interfaces |
| `mind_map/MIND_MAP.yaml` | Descriptive source-linked mind map |
| `sentience_dag.json`, `nex_next_dev.py` | Separate development dependency graph/tool |
| `tests/` | Controlled and regression tests |
| `journal/`, `observation_reports/` | Historical investigations and experimental evidence |

### Boot sequence (source-level)

The audited `run.py` sequence initializes the substrate, creates shared Readers/Writers, commits self-location, builds the mode state and sense scheduler, constructs dynamic formation, world model and membrane, then wires supporting faculties, Fountain and the GUI. Speech and numerous additional loops are conditional or separately started.

The six database identities are:

1. `beliefs`
2. `sense`
3. `dynamic`
4. `intel`
5. `conversations`
6. `probes`

Each has its own Reader/Writer path. The 28 sense adapters comprise 4 internal and 24 external adapters in the source inventory. Adapter construction does not prove that every external feed successfully polls, produces observations or influences downstream behaviour.

The Flask cockpit defaults to **127.0.0.1:8765**, configurable through `NEX5_HOST` and `NEX5_PORT`. Do not repeat the historical port-8770 claim. Verify current deployment settings from the host before assuming the listener is available.

### Deployment caution

The repository contains host-specific paths and service assumptions. Do not copy them into another installation without checking the actual checkout, virtual environment, systemd unit, data directory and environment file. A source-level inspection cannot establish which process, flags, services or databases are currently active on the user's machine.

---

## 4. Persistence and data ownership

The one-pen rule is a core persistence invariant: **one canonical Writer per database; all writes to that database go through its Writer**. Readers provide read access. See `substrate/writer.py`, `substrate/reader.py` and `substrate/init_db.py`.

A Writer serializes work for its own database. A transaction callback or multi-statement write can be atomic within that database. It does **not** create an atomic transaction spanning multiple SQLite databases. If one logical operation updates beliefs and conversations, a failure between those commits can leave partial cross-database state. Do not describe cross-database work as globally atomic.

The 27 November mainline includes the merged one-pen migrations for daily-life scheduled activity and canary persistence (#168), affinity (#169), learning-guard subtraction (#180), and Expectations persistence/reconciliation transaction support (#183). Important distinction: the shared-Writer migration does **not** establish that the Expectations reconciler is activated. The tracked launcher sets `NEX5_RECONCILER=1` and `NEX5_EXPECT_LEARN=1`, but the audited `run.py` has no Expectations/reconcile invocation, and `daily_life.py` imports only `record_canaries`; do not infer a live reconciliation loop from those flags. No activation is authorised by this documentation. PR #184 also fixes tied-timestamp pagination for Warrant lineage/arc reads; it does not broaden use-day eligibility or change Warrant policy. The current mainline includes the remaining bounded one-pen migrations: responder (#191), listener/poster (#196), and resumption, identity, Fountain momentum and recursion attribution (#200). #200 passed exact-head full baseline CI (2,539 passed, 7 skipped, 40 subtests) before merge. This closes those identified migration branches, not the repository-wide one-pen audit; every remaining writer path still requires source-to-sink verification.

Do not use direct `sqlite3` writes to live substrate databases as a shortcut. Test fixtures and isolated diagnostic databases are different from production persistence.

---

## 5. Cognitive pathways and integration boundaries

NEX is not a collection of independent modules that all automatically influence one another. Trace each pathway from producer through selection and gates to persistence and downstream consumer.

### Sense and dynamic formation

Sense adapters emit observations into the sense substrate. Stage 2 dynamic formation organises incoming signals, attention and branch/focus state. The source inventory contains many loops, but their successful start, liveness and downstream effect must be checked separately.

### World model and beliefs

The world-model layer retrieves and relates structured beliefs, with source, tier, confidence, provenance, edges and lifecycle state. Belief creation, reinforcement, promotion, pause, demotion, retirement and retrieval are separate operations. Audit eligibility at every consumer; do not assume that a filter in one retrieval path protects all others.

Recent work has identified inactive/paused/retired belief eligibility as a cross-cutting issue across Fountain context, special slots, self-narrative, graph/edge construction, pairing, affinity feedback, reification and other consumers. The G-53 Warrant cursor correction (#184) is merged, but it does not settle eligibility policy. Other corrective PRs must be checked individually for base, merge status and exact-head tests; do not assume branch-only changes affect current `main`.

### Coherence Gate

The Throw-Net trigger path is source-wired but its autonomous monitor is separately gated. `run.py` constructs a shared-Writer `TriggerDetector` and injects it into the Gate; non-Throw-Net REJECTs and Chat gap deflections write trigger rows. The documented 4-REJECT/3-gap thresholds are not enforced by the current consumer: callers ignore the detector's boolean return, `pending_triggers()` selects every unfired row, and `ThrowNetEngine.run_pending()` runs a session for each one. If `NEX5_THROWNET=1` is supplied, even a sub-threshold trigger can therefore launch a session. The monitor is not started unless that flag equals `1`; the tracked keepalive command does not set it, but any parent/systemd environment is unknown. This is a source-level defect and an inactive-by-default path, not evidence of live execution. Do not enable or change its thresholds without the relevant approval.

`theory_x/stage_gate/coherence_gate.py` evaluates ThoughtPackets into ACCEPT, REJECT, HOLD or RESHAPE and records decisions. The current implementation is **fail-open on evaluation exceptions**: an exception is recorded and the packet returns ACCEPT with reason `gate_error_fallback`. This is an availability policy, not a fail-closed safety boundary.

The Gate's documented design intent is universal coverage for generated thoughts, but source review has identified specific producer paths that write beliefs without calling it. These are policy/scope reconciliation findings, not permission to change the Gate or silently classify those paths differently. Read the current source, tests and approved policy before changing coverage.

### Fountain and Chat are different pathways

Fountain is an internally initiated thought/generation path. Chat is an input-driven conversational path through the GUI, membrane/routing, faculty context, voice/tool handling and message persistence. They do not necessarily share the same workspace, retrieval, gates or feature flags.

The Global Workspace implementation in `theory_x/stage_tom/global_workspace.py` arbitrates candidate framing/salience. Its output can lead the focus framing while other contributions remain present; it is not automatically equivalent to selecting or retrieving the body of the thought. Prompt framing, retrieval selection and persistent attention change are different mechanisms.

Check `NEX5_GLOBAL_WORKSPACE`, `NEX5_CHAT_WORKSPACE` and their actual call sites independently. A flag's presence in `nex_config.py` or a launcher is not proof that the corresponding path is active.

---

## 6. Continuity, memory, affect and stakes

The word **continuity** is overloaded. Keep these mechanisms distinct:

1. **Single-subject/process continuity:** single-instance supervision and protection against competing NEX processes.
2. **Cross-restart thought resumption:** `theory_x/memory/resumption.py` promotes real prior beliefs from a recent snapshot for post-boot context; it does not synthesize a new belief or prove uninterrupted subjective experience.
3. **Self-state history:** `theory_x/stage_tom/self_binding.py` composes faculty readings and records a self-state/history.
4. **SelfMindView:** `theory_x/stage_tom/self_mind_view.py` snapshots structured aspects of the system's current mental state; it does not consume the separate self-state history as a continuity mechanism in the audited mainline.
5. **Episodic reconstruction:** `theory_x/memory/episodic.py` is dark by default (`NEX5_EPISODIC=1`), not wired into the normal Fountain/Chat/live loop in the audited source. It can be called manually; its test coverage is not evidence of live episodic operation.
6. **Prompt/content continuity:** `NEX5_CONTINUITY_N` carries prior high-scoring thought content into prompts. This is not same-subject continuity or a no-forked-writer guarantee.

Self-binding is wired into the recursive-self path in Fountain in the audited mainline. The recursive prompt nudge is not evidence of mechanical attention change: the recorded test found P(move | active)=0.333 versus P(move | inactive)=0.337 over n=258. The DAG classifies that particular recursion mechanism as terminal/null; this does not invalidate the separate self-binding/history mechanism.

**Quantitative reading of the recursive-reflection attention probe (reported n=258):** the observed absolute difference is ΔP(move) = 0.333 − 0.337 = −0.004, i.e. −0.4 percentage points. Relative to the inactive-condition rate, this is approximately −1.19%; the observed rate ratio is 0.333 / 0.337 ≈ 0.988. This is a small descriptive difference, not evidence that reflection causes harm or that the conditions are equivalent. The available summary does not provide per-condition sample sizes, raw counts, allocation method, repeated-measures structure or uncertainty intervals, so a confidence interval, significance test and causal estimate cannot be reconstructed from n=258 alone. The result supports the narrower conclusion that this probe did not demonstrate an attention-movement benefit. Follow-up research should recover the original protocol/raw counts and distinguish prompt/self-report changes from measured changes in selection, salience or persistent attention. Do not promote this calculation into a new specification or roadmap gate.

Affect, drives, rāga, readiness, stakes and salience must each be traced to a real behavioural consumer. A scalar that is saturated or only written to a log may be present without materially changing selection. Do not infer a behavioural effect from a prompt label, variable name or module description.

---

## 7. Cost, trace and ledger boundaries

The Cost-and-Trace Ledger (CTL) is an architectural synthesis direction, not one unified live primitive in the audited code. Several separate structures currently carry related but non-identical information, including held tensions, expectations, commitments, undo events, belief warrants, shadow-budget spends, beliefs and episodes.

`theory_x/stage3_world_model/ledger_primitives.py` is explicitly not in the live path and depends on the shadow budget. Its episode consolidation branch is a documented no-op because no existing lossy episodic consolidation function was found.

The M0.5 causal trace overlay is a separate, default-OFF observational sidecar. It records explicit parent-linked events to JSONL, hashes text-bearing content and does not write to substrate databases or participate in decisions. The synthetic Fountain/Chat traces and paired tests are L3 fixture evidence, not live runtime captures. When enabled, synchronous file I/O can affect timing even where tested semantic outputs remain equivalent. Retention/rotation for the sidecar must be checked before any authorised long capture.

---

## 8. Autonomous activity and external effects

NEX contains autonomous and recurring processes in addition to request/response handling. Examples include sensing, Fountain, diversity/edge generation, metacognition, drive/affect updates, prediction, resumption, daily-life routines, speech and optional social integrations.

For every such process, distinguish:
- module exists;
- object is constructed;
- loop is started;
- environment flag permits the activity;
- credentials/network are available;
- external action is dry-run or live;
- action is authorised;
- result is persisted and consumed.

Moltbook components are separate listener, responder and poster pathways. Their persistence migrations have been merged in two steps: responder (#191), then listener/poster (#196). This is a persistence-ownership change, not proof that any Moltbook loop is running or authorised to act. The tracked launcher has been reported with `MOLTBOOK_DRY_RUN=1`, but only host environment and runtime logs can establish actual deployment state. Never infer live posting or interaction from source presence.

Daily-life routines and other autonomous processes require an explicit outbound-side-effect audit before being described as live or safe. Do not activate external actions as part of a source stocktake.

---

## 9. Architecture inventories and status maps

Do not conflate these inventories:

- The 30 entries in `mind_map/MIND_MAP.yaml` are descriptive mind-map nodes; they are not 30 active runtime faculties.
- The `sentience_dag.json` entries are a separate build/dependency graph; they are not the Master Roadmap.
- The 27 stage-named directories and other `theory_x/` packages are filesystem inventory, not proof of instantiated or active faculties.
- Python file counts are repository size, not cognitive capability counts.

The 27 November exact-head verification in PR #185 completed the full baseline (2,527 passed, 7 skipped, 40 subtests) and mind-map verifier: **30 nodes, 0 unverified, 14 dark, 2 blocked**. The earlier 18 source/path-date warnings were cleared by source-anchor corrections. The verifier still reports two absent doctrine references (`VIRTUE_SLATE.md` and `mental_factors_inventory_alobha_spec.txt`) and the overdue `p13_finitude` unblock marker (dated 2026-11-21); these remain explicit and unresolved. The two absent files are not recreated from inference, and the overdue marker is not advanced without source review.

The DAG uses `built`, `live_unproven`, `terminal`, `gap` and `gorge`. `nex_next_dev.py` treats `built`, `live_unproven` and `terminal` prerequisites as satisfied for dependency progression, while surfacing caveats. A terminal/null mechanism is not proof of success; a live_unproven mechanism is not validated.

The DAG contains a status/documentation mismatch worth preserving for review: `L4_teeth` remains labelled `gap` although its note says the retrieval/phrasing frontier was closed on 2026-11-07 and no further work is queued. Verify the intended status with the owner before changing the graph. Do not edit generated mind-map outputs by hand; `MIND_MAP.yaml` is the source for its generated representations.

**DAG consistency snapshot (27 November 2026):** a source-only check of `sentience_dag.json` found 15 nodes and 15 prerequisite edges; status counts were 9 `built`, 2 `terminal`, 2 `gap`, 1 `gorge` and 1 `live_unproven`. All prerequisite references resolved, with no duplicate prerequisite entries or unknown status values. Under the DAG's existing rule, both gap nodes (`L4_stakes` and `L4_teeth`) classify as buildable and both carry a terminal-null caveat through `L3_teeth_test`; no gap node is classified as blocked. The single `live_unproven` node is not a prerequisite of either gap. This is a consistency/inventory result for the descriptive development DAG only, not Master Roadmap progress, proof of implementation efficacy, or authority to change any node status.

---

## 10. Research and evidence practice

Use the source-to-sink method:

1. Identify the producer and the state/event it emits.
2. Follow selection, filtering, arbitration and gate conditions.
3. Identify the database/table and canonical Writer.
4. Follow every consumer and determine whether it can affect output, retrieval, ranking, memory or an external action.
5. Check flags, defaults, boot wiring and host configuration separately.
6. Read tests and determine whether they test a function, an integration boundary or a full production path.
7. Compare against measurements, preregistrations and falsifiers. Look for disconfirming evidence.
8. Record what is verified, inferred, unknown and contradicted.

Prefer controlled experiments and reversible changes. Do not add a new named faculty or duplicate a cognitive twin, genome or event ledger merely because a concept is interesting. First establish whether an existing mechanism already covers the function and where the actual gap lies.

A successful unit test does not establish runtime liveness. A successful boot does not establish cognitive efficacy. A model's first-person self-report does not establish subjective experience.

**Development-tool correction (27 November 2026; merged in PR #228):** source review found that `nex_next_dev.py --buildable` unpacked each `classify()` result as two values although the classifier returns three (`node`, unproven prerequisites, terminal-null prerequisites). The command therefore raised a tuple-unpacking error when a buildable gap was present. The full report also described a `live_unproven` prerequisite as a hard gate, contradicting `sentience_dag.json`'s explicit rule that `built`, `live_unproven` and `terminal` are all dependency-satisfied statuses, with the latter two surfaced as caveats rather than blockers. PR #228 fixes the unpacking, prints both caveat types in `--buildable`, corrects the full-report language and exposes a testable `main(argv)` entry point. Exact-head CI run `46000586294` passed: **2,552 passed, 7 skipped, 45 subtests passed**, baseline OK. This is a developer-tool correction only: no DAG status, runtime code, cognitive behaviour, flags, specifications or roadmap changed.

---

## 11. Current mainline snapshot and open work (27 November 2026)

Mainline inspected: `5d7f4e28eb6760d206eed455429c90e967a5bf10` (27 November 2026, after #189 manual reconciliation, #191 responder, #196 listener/poster, #199 manual refresh and #200 remaining one-pen migrations). Exact-head full baseline CI for #200 passed: 2,539 passed, 7 skipped, 40 subtests; mind-map verifier: 30 nodes, 0 unverified, 14 dark, 2 blocked. These are repository CI/source-verification results only; they do not establish host/runtime state.

Post-snapshot reconciliation recorded in the Phase 0 handoff branch identifies the following merged changes already present in that mainline SHA: #168 (DailyLife/canary Writer routing), #169 (affinity Writer routing), #174 (P13 finitude re-verification), #175 (full-history mind-map verifier guard), #180 (learning-guard Writer routing), #183 (Expectations transaction/Writers), and #184 (Warrant composite pagination cursors). The source reality report and crosswalk carried by PR #188 remain pinned to `ae406fa8`; its handoff reconciles changes through `99ae476`. The later mind-map source-verifier outcome from PR #185 is recorded separately above. Treat each evidence artefact as snapshot-bounded, not as a single fully refreshed audit of `ddb9f15`.

Relevant pull requests and integration state at this update:

- **#187** — INDEX/manual stocktake update; merged after exact-head CI.
- **#185** — consolidated mind-map source re-verification; merged after exact-head full baseline and verifier (2,527 passed, 7 skipped, 40 subtests; 30 nodes, 0 unverified, 14 dark, 2 blocked). Two missing doctrine references and the overdue P13 marker remain unresolved.
- **#188** — Phase 0 evidence-pack carry-forward; merged after exact-head CI. Its report/crosswalk snapshots remain pinned to `ae406fa8`, while the handoff reconciles through `99ae476`. Do not treat these artefacts as a fully refreshed audit of current main.
- **#189** — manual reconciliation after #185/#188; merged.
- **#191** — responder one-pen migration; merged after exact-head full baseline CI.
- **#196** — listener/poster one-pen migration; merged after exact-head full baseline CI. Together, #191 and #196 migrate all three Moltbook loop persistence paths without activating external posting.
- **#200** — ResumptionSeeder, IdentityLoop, Fountain momentum and recursion-attribution one-pen migrations; merged after exact-head CI (2,539 passed, 7 skipped, 40 subtests). This closes the previously outstanding bounded migration PRs #162/#166/#170 and does not prove the global writer audit complete.
- **#198** — superseded by #200 after #199 advanced main; closed without merge.
- **#197** — superseded by #198/#200 after main advanced; closed without merge.
- **#192–#199** — intermediate or documentation carry-forward PRs; #199 is merged, the others are closed/superseded by #200 or the final merged changes.
- **#162, #166, #170, #171–#173** — original stale-base migration branches; closed/superseded. Their old-head CI results are not current-main evidence.
- **#178** — episodic read/write boundary audit; closed after review found its `p8_episodic` mind-map node unchanged from current main. This does not validate episodic runtime activation; it remains dark by default and unwired in the audited live loop.

**External RDO/Watcher status (not NEX roadmap progress):** current `main` contains the RDO Stage 2–7 modules, stage documents and tests. The historical `claude/rdo-stage2…stage7` branches are divergent and roughly 475 commits behind current main; do not merge them or rely on their old test claims. The Stage-7 handoff manifest and independent Watcher source/path verifier are present, but Stage 7's own document says its full objective-to-verified-delivery exit criterion remains incomplete: real objective demonstration, safe test-execution boundary, host-only runtime observation and separate human acceptance remain. Watcher source/path verification does not run tests or establish runtime behaviour. RDO v1.3/v1.4 precedence remains unresolved; no version decision is inferred here.

PRs based on other branches (including the earlier continuity branch) are not automatically part of `main`. Check the base branch and merge commit before describing their changes as current NEX behaviour.

The repository-level Phase 0 evidence pack and the NEX first-read index serve different purposes: the evidence pack records bounded findings and unknowns; this index tells a developer how to orient, investigate and avoid repeating stale assumptions.

---

## 12. Operational checks and session handoff

Before making a runtime claim, inspect the actual host:
- current checkout and commit;
- process tree and single-instance lock;
- systemd unit and supervisor state;
- effective environment flags and configuration;
- listening ports and HTTP health;
- data directory and database paths;
- logs, Writer health and scheduler/loop liveness;
- whether external credentials and integrations are enabled.

Do not run destructive database operations, activate external posting, change live flags or alter runtime services during a read-only stocktake. Obtain explicit approval for consequential live actions.

For each development session, state:
- exact base commit and branch;
- governing documents consulted;
- files and pathways inspected;
- tests run and their scope;
- verified findings versus hypotheses/unknowns;
- code/document changes and rollback path;
- remaining dependencies and required approvals.

**Phase gates require the founder's explicit greenlight.** Present the evidence and wait for the required approval; do not treat a positive review or a technically mergeable PR as phase authorisation.

---

## 13. Living-document protocol

This INDEX is hand-maintained. When the architecture or operating procedure materially changes, update the relevant section in a separate, traceable commit describing what changed and what was learned. Keep it aligned with current source and approved governance documents.

The public `README.md` is the concise project overview and local setup guide. This INDEX is the developer's first-read orientation/manual. Phase 0 evidence documents are audit artefacts, not replacements for either.

When in doubt: the current source and approved governing documents win—not this index.

---

*Last amended: 27 November 2026 — records merged DAG integrity and policy-scan fixes, #223–#226 bounded one-pen migrations, and the #236/#238 SelfPredictionLoop handle integration; G-69/G-71 proposals remain under verification and Gate 0 boundaries.*



---

## 14. DAG prerequisite-reference integrity (27 November 2026)

A source audit found that `classify()` and `topo_sort()` silently ignored prerequisite IDs absent from the DAG's `nodes` mapping. In classification, filtering an unknown prerequisite could make `all([])` pass and incorrectly report a gap as buildable; topological sorting could produce an apparently valid order for an incomplete graph.

The current `sentience_dag.json` snapshot contains 15 nodes and 15 prerequisite edges, with no unresolved references. The latent defect is nevertheless important because a future misspelled or deleted node ID could corrupt the tool's output.

**PR #229 is merged** to `main` as `9002291b1fd36624e895a8635a8b916888442548`. It adds deterministic prerequisite-reference validation to both classification and topological sorting, with regression coverage. Exact-head CI run `46002918341` passed. The change is confined to the DAG developer tool, tests and this manual; it does not change DAG content/status, runtime behaviour, cognitive settings, frozen specifications, roadmap or phase gates.

## 15. DAG status and duplicate-edge integrity (27 November 2026)

A second pass found two additional latent defects in the same developer-tool path:

1. **Unknown or missing status values** could fall through every classifier branch and silently disappear from the report.
2. **Duplicate prerequisite edges** could increment Kahn's indegree more than once while successor traversal decremented only once, creating a false cycle report.

The current graph was checked independently: 15 nodes, 15 edges, no unresolved references, no duplicate edges, and all statuses belong to the five values declared in `sentience_dag.json`. These are latent tool defects, not current graph corruption.

PR #232 is the clean mainline replay of the PR #230 changes and is **merged** as `1d133035dd8337a76f65225e8255bd13b655cf17`. It adds duplicate-edge validation, rejects unknown/missing statuses, and applies shared graph validation before classification and topological sorting. The original PR #230 exact-head CI run `46003289108` passed; the clean mainline replay exact-head run `46004897984` also passed. Four regression tests cover duplicate edges in both paths and unknown/missing statuses.

This work remains limited to `nex_next_dev.py`, its tests and this manual. It does not alter `sentience_dag.json`, runtime code, cognitive behaviour, flags, frozen specifications, roadmap or phase gates. Rollback is by reverting the isolated developer-tool change.


---

## 16. DAG input-shape validation (27 November 2026)

A further developer-tool audit found that reference/status validation could still receive malformed node structures: non-object node definitions, non-list prerequisite containers, non-string prerequisite IDs, empty node IDs, and non-string statuses. These inputs could produce incidental Python exceptions rather than a deterministic graph-validation error.

PR #235 adds fail-fast shape checks before prerequisite-reference, duplicate-edge and status validation, with six focused regression tests. It does not change the current DAG or the meaning of any status or dependency. The change is limited to `nex_next_dev.py`, its tests and this manual; runtime behaviour, cognitive settings, frozen specifications, roadmap and phase gates remain unchanged.


---

## 17. Mind-map policy scan boot-path coverage (27 November 2026)

A source-to-guard audit found that the descriptive-only policy scanner did not cover two paths imported by the normal runtime boot graph: `run.py` imports `strikes.catalogue` and `strikes.protocols`, while `gui/server.py` imports top-level `influence_trace`. The scanner's `RUNTIME_ROOTS` omitted both `strikes/` and `influence_trace.py`.

**PR #233 is merged** with both roots added and a regression test proving that prohibited `mind_map` imports in those paths are detected. Exact-head CI run `46005619584` passed. This was a scan-coverage gap, not evidence that either path had violated the descriptive-only constraint.

No runtime imports, cognitive behaviour, policy semantics, flags, DAG content, frozen specifications, roadmap or phase gates were changed. The policy scanner remains descriptive-only enforcement.

## 18. Additional bounded one-pen migrations (27 November 2026)

Four previously open, independently tested persistence migrations are now merged:

- **PR #223 — WorldBridge:** injects the shared sense Reader and beliefs Writer; Phase-A selection/log-only behaviour is preserved. Exact-head run `45997969694`: 2,550 passed, 7 skipped, 45 subtests.
- **PR #224 — GUI, Compassion and AffectCarry:** routes the reviewed GUI mutations and affect persistence through shared Writers/Readers. Exact-head run `45998065075`: 2,557 passed, 7 skipped, 45 subtests.
- **PR #225 — SelfBinding:** routes current self-state and append-only history persistence through the canonical dynamic Writer. Exact-head run `45998142261`: 2,551 passed, 7 skipped, 45 subtests.
- **PR #226 — Decoder:** places dynamic reads, word-context inserts and cursor advancement inside the canonical dynamic Writer transaction, with sense timing read through the shared Reader. Exact-head run `45998199987`: 2,551 passed, 7 skipped, 45 subtests.

These migrations preserve the existing feature gates and decision logic. They close the four bounded persistence branches only; they do not prove the repository-wide one-pen audit complete or establish host/runtime activation. Cross-database operations remain separate transactions unless explicitly documented otherwise.


---

## 19. Phase 0 follow-up audit and gated SelfPredictionLoop integration (27 November 2026)

The current-main follow-up audit has rechecked G-68 to G-72. G-68 (experimental ProbeRunner safety), G-70 (speech playback trace coverage), and G-69/G-71 (surprise-event and Warrant cursor integrity) remain separately tracked in the verified defect backlog; their proposed corrections are not treated as merged or activated.

G-72 is closed by **PR #236** (commitments canonical Writer/Reader path) and **PR #238** (AppState handle injection through the gated SelfPredictionLoop, self-prediction, owned-belief, commitments and Expectations paths). Exact-head full-suite runs passed: #236 `46006462779` (2,573 passed, 7 skipped, 45 subtests) and #238 `46008022480` (2,584 passed, 7 skipped, 45 subtests).

The `NEX5_SELF_PRED=1` gate and all other feature gates remain unchanged. No loop was started and no cognitive decision logic, cadence, thresholds, frozen specifications, roadmap or phase-gate state was changed. This closes the persistence-ownership integration finding only; it does not certify host activation or a complete repository-wide one-pen census.


---

## 20. Phase 0 continuation: G-68 to G-72 and shared daemon checkpoint schema (27 November 2026)

This section records follow-up work after the previous manual update. It is a remote-repository/source-and-CI stocktake, not a live-host inspection. The current mainline at the time of this update is `36624b7106ebaec801f6d744e87cd37b73279021`.

### Verified integration

- **PR #241 — G-68 to G-72 evidence reconciliation: merged** to main as `36624b7106ebaec801f6d744e87cd37b73279021`. The exact-head PR test run passed before merge. The change updates the Phase 0 follow-up record and handoff; it does not itself close the underlying open findings or authorize behaviour changes.
- The consolidated S-01–S-25 register, roadmap, phase gates and cognitive policy remain unchanged. Gate 0 remains pending founder review; Phase 1 is not authorized.

### Shared dynamic daemon checkpoint schema

A fresh-schema static-SQL compilation failure exposed a missing shared schema declaration for `dynamic.db:daemon_kv.updated_at`. The table is referenced by SurpriseLoop and the Moltbook poster. This is a persistence/schema completeness defect, distinct from the semantics of either worker.

- **PR #243 — shared `daemon_kv` schema and migration: OPEN / CI RUNNING at this update.** Its current head is `b55fe9b731d7353b0b8bb58fac1840bb34536ad1`. It adds the canonical table declaration to `substrate/schema/dynamic.sql`, an additive migration in `substrate/init_db.py`, and fresh-database plus legacy-table preservation regression tests in `tests/test_daemon_kv_migration.py`.
- The migration is additive: the intended legacy behaviour is to add `updated_at` without deleting or rewriting existing key/value checkpoints. The focused tests assert both the fresh schema and preservation of a pre-existing row.
- Do not describe this change as merged, validated or deployed until the exact-head CI result is green and the PR is integrated.

### Dependent PRs and test evidence

- **PR #242 — gated WorldPredictionLoop persistence ownership: OPEN; exact-head CI failed** on the same fresh-schema compilation error: `daemon_kv.updated_at` is absent from its base snapshot. The run reported 2,587 passed, 7 skipped, 45 subtests, and one failure in `tests/test_schema_indexes.py::TestEveryStaticStatementCompilesOnFreshInit`. This is a shared schema prerequisite failure; it does not establish that the AppState handle-injection change itself is defective. Revalidate on current main after #243 is merged. The existing `NEX5_WORLD_PRED` gate and prediction behaviour must remain unchanged.
- **PR #240 — Warrant declared composite-key cursor: OPEN; exact-head CI failed** on the same missing `daemon_kv.updated_at` fresh-schema error (2,583 passed, 7 skipped, 45 subtests, one failure). Its base is stale relative to current main. After #243 is integrated, rebase/replay the cursor-only change on current main and rerun the full suite. Do not broaden Warrant use-day eligibility or alter Warrant policy.
- **PR #239 — SurpriseLoop monotonic event cursor: OPEN; exact-head CI passed.** It proposes tie-safe event paging, retry-safe checkpoint handling and related duplicate-content treatment. Despite green tests, it remains **held for founder Gate 0 review** because it changes which events may enter the belief corpus. Do not merge, deploy or activate it before that approval.
- **PR #243 CI** is still running at the time of writing; the result must be checked before any merge decision. A green result on another PR or on a prior base does not substitute for #243's exact-head result.

### G-70 refinement — speech outcome state versus causal trace

A targeted source recheck refines the wording of G-70. The speech path is not wholly unobservable after enqueue: `speech/queue_consumer.py` updates each queue row through `speaking` and then `spoken`, or `failed` on synthesis/playback exceptions; non-speakable content is marked `suppressed`. `speech/player.py` calls `sounddevice.play(..., blocking=True)` and `sd.wait()`. Therefore a persisted `spoken` status means the playback call returned without raising; it is not independent acoustic confirmation that sound reached a listener.

The remaining G-70 gap is specifically **cross-thread causal trace continuity**: the Fountain trace records the `speech_queue` enqueue Writer delta and queue-row ID, but the consumer does not continue that trace with parent-linked dequeue, synthesis, playback-start/completion or failure events. The queue status columns are operational outcome state, not a substitute for a parent-linked trace. This refinement does not change the finding's OPEN status and does not authorize speech-path changes.

### Development and evidence interpretation

The current work continues the research → bounded implementation → rescan → consequence analysis → documentation cycle. Persistence ownership fixes and schema completeness are kept separate from cognitive-policy changes. A green unit or full-suite result demonstrates only the tested repository state and paths; it does not prove that a feature flag is enabled, a worker is running, a host database has migrated, or a behavioural effect is beneficial.

The shared Writer/Reader one-pen rule remains in force. The six SQLite databases remain separate transaction domains; no cross-database atomicity is implied. No live substrate database, host process, service, credential, external integration or feature flag was inspected or changed during this remote repository work.

### Next bounded actions

1. Complete exact-head CI review for #243; correct any migration/test defects before merging.
2. Once #243 is merged, rebase/revalidate #242 and #240 against current main; preserve their narrow persistence/cursor scopes.
3. Keep #239 held for explicit Gate 0 founder review despite its green CI.
4. Continue the source-to-sink Phase 0 audit and update this manual in the same development cycle as findings and integrations accumulate.
5. Keep unresolved defects, unknown host/runtime facts and approval gates explicit. Do not promote a Phase 0 stocktake into Phase 1 authorization.


## 21. RDO experiment-registry fail-closed boundary and shared-handle review (27 November 2026)

### RDO protected-experiment registry

A new test-only continuation, **PR #245 — RDO fail-closed experiment registry boundary: OPEN / exact-head CI RUNNING**, adds regression coverage for a safety boundary already present on main. Head: `2fe8c360c75fafd956a4c690203c653eafdf4ea0`; exact-head run: `46013089837`.

Source review on main confirms the distinction:

- `watcher.registry.ingest_registry()` returns evidence class `unknown` when the observation-report directory is missing; a successfully read registry is `measured` and contains an `active_or_pending` list.
- `rdo.orchestrator._active_experiments()` returns `None` for unknown/unmeasured evidence, malformed registry data, or read errors. It returns a list (including an empty list) only when the registry is measured and structurally valid.
- `rdo.prioritise.eligibility()` blocks when the registry is `None`; a verified empty list does not create a registry blocker; a matching active experiment blocks the affected obligation.
- Stage 2 and Stage 3 both pass the registry result into the shared `_run_one()` path. PR #245 adds tests that protect this propagation as well as the eligibility distinctions.

The PR is tests-only and uses synthetic evidence. It does not change eligibility logic, experiment state, execution, runtime flags, roadmap or cognitive behaviour. Do not call it validated until its exact-head full-suite result is green. This is a repository-level regression check, not an inspection of live experiment state.

### Shared AppState Reader/Writer concurrency contract — source recheck

The #242 handle-injection review was extended to the underlying substrate primitives. `substrate.reader.Reader` stores a database path and opens/closes a fresh read-only connection for each `read()` / `read_one()` call; it does not share one SQLite connection across daemon threads. `substrate.writer.Writer` serializes submitted requests through a thread-safe queue on its dedicated worker thread; synchronous callers wait on each request's Future. These implementations support sharing the AppState Reader/Writer objects across the WorldPredictionLoop thread without creating a second Writer or a cross-thread SQLite connection. This source review supports the ownership design, but does not prove the host actually starts the gated loop or that its external price/voice services are available. The `NEX5_WORLD_PRED` gate remains OFF by default and unchanged.

### Updated continuation order

1. Finish exact-head CI for #243, #244 and #245; merge only after green results and final diff review.
2. After #243 lands, rebase/revalidate #242 and #240 against current main; preserve their narrow scopes.
3. Keep #239 held for explicit Gate 0 founder review.
4. Continue the Phase 0 source-to-sink audit and keep this manual synchronized with each meaningful code or evidence change.



## 22. Current-main replay and exact-head test reconciliation (27 November 2026)

### Shared schema prerequisite integrated

**PR #243 is merged** to main as `5b95c6caaf6f99a61140ec261412421c08fb01cb`. Its exact-head full-suite CI passed. The canonical `dynamic.db:daemon_kv(key, value, updated_at)` declaration and additive legacy migration are now part of main. Existing checkpoint rows are preserved. This integration does not activate any daemon or alter event-selection policy.

### Dependent work replayed on the corrected base

The original branches #240 and #242 were based before the shared schema prerequisite and their exact-head runs failed on that missing-schema defect. Rather than treating those runs as evidence against the isolated changes, the narrow patches have been replayed on current main:

- **PR #247 — Warrant composite-key cursor current-main replay: OPEN / exact-head full-suite CI RUNNING.** It uses the declared primary keys of `belief_lineage` and `arc_members`, not hidden SQLite rowids that may be remapped by VACUUM. Existing scalar cursors and Warrant policy are preserved.
- **PR #248 — gated WorldPredictionLoop AppState handle current-main replay: OPEN / exact-head full-suite CI RUNNING.** It passes the existing AppState conversations Writer/Reader and beliefs Reader through prediction, calibration, persistence and resolution. The `NEX5_WORLD_PRED` gate remains unchanged and OFF by default; no loop was started.

The original #240 and #242 PRs are superseded by these current-main replays. Their prior CI failures remain historical evidence about the missing schema on their old base, not validation of the replayed heads.

### RDO registry regression: fixture correction

The original **PR #245** exact-head full-suite run failed with **1 failed, 2,592 passed, 7 skipped and 45 subtests passed**. The failing test's synthetic Stage 2 cycle fixture omitted `signature_matches`, a field consumed by the real Stage 2 report after the mocked runner returned. Source review confirmed the production registry boundary itself was not the failure.

**PR #249 — current-main replay and corrected fixture: OPEN / CI status to be checked.** It carries the tests onto the post-#243 mainline and adds the missing `signature_matches=[]` fixture field. The production RDO code is unchanged. The tests continue to distinguish an unavailable/unverified registry (`None`, blocked) from a successfully measured empty registry (`[]`, no registry blocker), and cover active matches plus Stage 2/Stage 3 propagation. No live experiment state is read or modified.

### Manual branch reconciliation

The earlier manual updates #244 and #246 were authored against main before #243 merged. **PR #250** carries their full `INDEX.md` content onto the post-#243 mainline and adds this reconciliation section, so the maintained first-read manual does not omit the now-integrated schema prerequisite or the replayed dependent work.

### Current evidence and next sequence

1. Require exact-head full-suite success and diff review for #247, #248 and #249 before merging.
2. Complete the current-main manual integration in #250; keep its status distinct from runtime activation.
3. Keep #239 held for explicit founder Gate 0 review despite its earlier green CI.
4. Continue the Phase 0 source-to-sink audit; preserve frozen specifications, roadmap, feature gates and cognitive behaviour.
5. Treat host migration, service operation, feature enablement and behavioural benefit as unverified until separately observed and measured.


## 23. Warrant cursor ordering: append-time semantics and older-parent additions (27 November 2026)

A second-pass producer review found that a cursor ordered only by declared primary key is not sufficient for every append path. `theory_x/arcs/detector.py` can add a new `arc_members` row to an already-existing active arc when a later fire joins it. That row has a new `joined_at` but can have an `arc_id` lower than the last key-only cursor. Similarly, a new lineage relation can be recorded for an earlier child ID. A key-only cursor could therefore permanently skip valid new use evidence even though it is immune to hidden-rowid remapping.

**PR #247 was strengthened before merge.** Its current design orders by event time first and uses declared primary-key columns only as deterministic tie-breakers:

- lineage: `(created_at, child_id, parent_id, relationship)`
- arc membership: `(joined_at, arc_id, belief_id)`

This preserves tied-timestamp pagination without relying on hidden rowids and ensures later events for older arcs/children still sort after the saved cursor. The tuple-cursor reader also validates component types and falls back to a replayable default when stored JSON is malformed or type-incompatible.

The expanded regression fixture now advances beyond arc ID 1 to arc ID 2 and child ID 104, then inserts a later event for arc ID 1 and child ID 2. It asserts both events are still consumed. It also forces rowid remapping between pages and exercises malformed cursor data. Current #247 head at this update: `3908a587373e958dbd3faf542d7c3a7d56d50677`; its exact-head CI is queued/running and must pass before merge.

This is an important distinction for future cursor work: a stable identity key solves rowid instability, but does not by itself prove append-order monotonicity. Cursor ordering must be checked against the actual producer's insertion semantics, not inferred from the table's primary key alone.


## 24. WorldPredictionLoop persistence ownership integrated (27 November 2026)

**PR #248 is merged** to main as `a49e0d0e6e048eeed7d5676611b53cf3ce4d286e`. Its exact-head full baseline suite passed: **2,590 passed, 7 skipped and 45 subtests passed** (run `46013847927`). This integrates the gated WorldPredictionLoop's use of AppState-owned conversations Writer/Reader and beliefs Reader through prediction generation, calibration, schema setup, resolution and scorecard paths.

The source review remains as recorded above: Reader opens a fresh read-only connection for each operation; Writer serializes writes on its queue worker. The change removes duplicate per-worker persistence handles from this path. It does **not** set `NEX5_WORLD_PRED`, start the loop, establish availability of the external price/voice endpoints, or demonstrate predictive benefit. The feature gate remains OFF by default.

The manual update is being replayed on this new mainline as **PR #251** so its verified-main SHA and integration history match the current repository. The earlier #250 manual branch was based before #248 merged and is superseded by this current-main documentation replay.

### Remaining exact-head validation

- **PR #247** — Warrant event-time plus stable-key cursors: expanded late-addition/rowid-remap regression suite; exact-head CI still pending.
- **PR #249** — RDO fail-closed registry regression tests: Stage 2 fixture now includes the complete `CycleRecord` field contract; exact-head CI still pending.
- **PR #239** remains held for explicit founder Gate 0 review, regardless of its earlier green CI.


## 25. Post-integration revalidation of Warrant and RDO test branches (27 November 2026)

After #248 merged, the pending #247 and #249 branches were replayed once more so their full-suite results are tested against the actual current mainline, not the pre-#248 base:

- **PR #253 — Warrant event-time plus stable-key cursor, post-#248 replay: OPEN / exact-head CI pending.** It carries the late-addition fix and its rowid/tie/malformed-cursor regression tests onto main `a49e0d0e6e048eeed7d5676611b53cf3ce4d286e`.
- **PR #254 — RDO experiment-registry fail-closed tests, post-#248 replay: OPEN / exact-head CI pending.** It carries the corrected Stage 2 fixture and registry-boundary tests onto the same mainline.

The older #247 and #249 branches are closed as superseded. Their CI outcomes remain historical only; #253 and #254 are now the authoritative branches for any merge decision. The manual is kept on the current-main base in PR #252.


## 26. Warrant cursor query-plan and performance risk (27 November 2026)

The event-time cursor is a correctness improvement, but its production cost is not yet measured. The current beliefs schema indexes `belief_lineage` by parent/child and `arc_members` by belief ID; it does not declare indexes matching the new ordered cursor tuples:

- `belief_lineage(created_at, child_id, parent_id, relationship)`
- `arc_members(joined_at, arc_id, belief_id)`

Without matching indexes, SQLite may need to scan and sort these tables for each Warrant use cycle. The previous timestamp/rowid cursor also lacked an obvious matching composite index, so this is not yet established as a regression; it is an unmeasured cost of the current access path.

No speculative index migration has been added. Before enabling `NEX5_WARRANT_RECORD` on a data-bearing host, measure table row counts, inspect `EXPLAIN QUERY PLAN` for both cursor queries, and time representative cycles against realistic data. Add the composite indexes only if those measurements justify their write/storage overhead. The feature gate remains OFF and no live database was inspected.


## 27. SurpriseLoop loss-safe event delivery: current-main replay and Gate 0 hold (27 November 2026)

A further open contribution, **PR #251**, addresses the SurpriseLoop's timestamp-only cursor and failure checkpointing. Source review confirms that `theory_x/stage_prediction/predictive_substrate.py` writes each resolved `surprise_events` row with its final `actual_content`, `surprise_flag` and `big_surprise` values at insertion time; this supports the event-ID cursor's assumption that eligibility fields are not later filled in for an existing row.

The current-main replay is **PR #255 — SurpriseLoop loss-safe event delivery: OPEN / exact-head CI pending / GATE 0 HOLD**. It is based on post-#248 main. The implementation uses the monotonic `surprise_events.id`, migrates the legacy timestamp boundary by replaying events exactly at the cutoff, writes timestamp and ID checkpoint values together, and stops at the first non-duplicate conversion/write failure so the failing event and later events retry. Only duplicate belief-content collisions are checkpointed as already represented. Ordinary surprise tags are de-duplicated.

**Do not merge or deploy #255 yet.** This is not merely an observability fix: events that were previously skipped can now reach the belief corpus and change downstream retrieval inputs. The PR's own scope statement preserves the Gate 0 requirement. Founder review and explicit approval of that behaviour-impact decision are required. The correction does not change prediction scoring, surprise thresholds, event generation or loop cadence.

The older-base PR #251 is closed as superseded by #255. Its prior exact-head full-suite run passed, but #255 requires its own current-main exact-head validation. Gate 0 remains pending; Phase 1 remains unauthorized.


### SurpriseLoop migration boundary — historical limitation

The old timestamp-only implementation advanced its timestamp checkpoint even after some non-duplicate conversion/write failures. The new migration derives the initial event-ID cursor from the maximum event ID with `triggered_at < legacy_timestamp`; it replays rows exactly at the cutoff and all later rows. It cannot identify older rows that may already have been skipped before migration, and those rows remain outside the replay window. Recovering that older history would require a separate, explicit decision to backfill the belief corpus; it must not be smuggled into this cursor repair.

Source review of `theory_x/stage_prediction/predictive_substrate.py::_verify()` confirms each `surprise_events` row is inserted with its final `actual_content`, `surprise_flag` and `big_surprise` values together. The current event-ID scan therefore does not depend on a later update making an older event eligible. This assumption should be rechecked if the producer contract changes.


## 28. Warrant event cursor integration and subsequent revalidation (27 November 2026)

**PR #253 is merged** to main as `c80d9dbb878ac15a39d6707a9c89ab2a51f8518c`. Its exact-head full baseline suite passed: **2,590 passed, 7 skipped and 45 subtests passed** (run `46014884835`). The Warrant use-day scan now orders lineage and arc membership by event time with declared composite-key tie-breakers, preventing rowid remapping loss and late additions to older active arcs from being skipped. The Warrant gate remains OFF; this is persistence/cursor correctness, not evidence that Warrant is earning or affecting beliefs.

After #253 merged, the remaining pending branches were replayed onto the latest main:

- **PR #256 — RDO registry fail-closed regression tests: OPEN / exact-head CI pending.** Tests only; the complete Stage 2 fixture includes `signature_matches`.
- **PR #257 — SurpriseLoop loss-safe event delivery: OPEN / exact-head CI pending / GATE 0 HOLD.** Event-ID cursor and retry integrity fix; not for merge or deployment until founder approval because newly delivered events can alter belief-corpus inputs.

The older #254 and #255 branches are superseded by these post-#253 replays. The earlier PR #252 manual branch is likewise superseded by this current-main manual replay.


## 29. Dormancy scanner proposal review and older-base work (27 November 2026)

The current-main review confirms the dormancy issue recorded as **G-73** in the refreshed verified-defect backlog:

- `DormancyScanner.scan_incremental()` currently selects the oldest 50 source-eligible beliefs by `created_at` with no cursor. An unchanged oldest cohort can therefore be rescanned repeatedly.
- `DiversityLoop` owns one persistent scanner and invokes it on its loop cadence. `ClockRunner._run_fast()` constructs another scanner inside each fast tick, so that second path does not retain a cursor between ticks. Both paths address the same beliefs population/table; combined runtime work rate has not been measured.
- **PR #102** proposes ID-keyset rotation, wraparound, persistent ClockRunner scanner ownership, and tier/paused/retired filters in scan, dormant selection and reanimation. **PR #145** adds tests for partial-tail wraparound and persistent-instance reuse. Both exact-head suites passed on their own older base, but neither branch has been revalidated on current main.
- The proposal still leaves two independent scanner instances/cursors: DiversityLoop's scanner and ClockRunner's scanner. PR #145 tests persistence of the ClockRunner instance, not single-owner scheduling or combined cadence.
- The proposed final Fountain reanimation fetch rechecks `tier <= 7` and `paused = 0` but does not recheck `erosion_stage != 'retired'`. Add a test for a belief retired between selection and final injection before considering that path fully guarded.

This remains a scan-coverage/ownership and eligibility-contract question, not an observed live incident. Do not merge or replay the behaviour filters or alter maintenance cadence until the current-main rebase, exact-head tests, and Gate 0 policy review are complete. The older documentation branches #142/#144 are superseded by the current-main backlog/handoff update in PR #258; the separate PR #102/#145 code/test proposals remain open for review.


## 30. Warrant lifecycle questions and stale audit-branch reconciliation (27 November 2026)

The refreshed Phase 0 backlog and handoff now also carry two Warrant lifecycle questions verified against current main:

- **G-74 — retired-marker eligibility:** WarrantPass's scoring query and WarrantRecorder's survival query do not filter the independent `erosion_stage='retired'` marker. Normal Harmonizer retirement writes Tier 8; no normal lower-tier retired-marker writer or live such row was established. Confirm whether this marker overrides tier for Warrant scoring/survival before adding filters.
- **G-75 — Recorder versus WarrantPass boot:** normal `run.py` starts WarrantRecorder only behind `NEX5_WARRANT_RECORD=1`. No normal WarrantPass loop construction/start was found in `run.py` or `gui/server.py`; `tools/warrant_validate.py` performs one-shot read-only validation. The tracked keepalive sets the Recorder flag but not `NEX5_WARRANT`; host-effective state remains UNKNOWN because the launcher path blocker and active user systemd unit are unresolved. Record-only operation may be intentional while evidence accrues.

The older documentation branches **#142/#144** were based on a divergent continuity branch and are superseded by the current-main verified backlog/handoff updates in #258. Their useful findings were rechecked against current source and reconciled into the current backlog with corrected dispositions: G-53/G-71 Warrant cursor defects are closed by #253; G-56 EdgeBuilder telemetry was already closed by #157; G-53's former walk-anchor concern is narrowed in current G-54; the other current questions are G-51, G-54, G-55, G-57, G-73, G-74 and G-75. The stale producer-trace document was not merged wholesale because it predates substantial mainline changes.

PR #102 and test-only follow-on #145 remain older-base proposals. Their exact-head CI passed on that older base, but they are not current-main validated. PR #102 changes dormancy scan coverage, retired/paused eligibility and the fast-clock scanner lifecycle; PR #145 tests partial wraparound and ClockRunner scanner reuse. The two independent scanner owners remain, and the final Fountain reanimation query in #102 does not recheck the retired marker. Do not merge these proposals until the current-main replay, end-to-end eligibility tests and Gate 0 policy review are complete.

PR #258 now updates the first-read manual, verified defect backlog and Phase 0 handoff together. It does not alter the frozen specification/register, roadmap, runtime, flags or cognitive behaviour.


## 31. RDO registry regression integration and SurpriseLoop revalidation (27 November 2026)

**PR #256 is merged** to main as `e78773def4549f646257945e5886ec71a7837374`. Its exact-head full baseline suite passed: **2,599 passed, 7 skipped and 45 subtests** (run `46015838864`). It adds tests-only protection for the fail-closed RDO experiment registry: unknown/unreadable/malformed registry state remains blocked, verified-empty remains distinct, active matches block, and Stage 2/Stage 3 propagate the registry into the shared runner. No production RDO eligibility or experiment state changed.

**PR #259 — SurpriseLoop loss-safe event delivery on post-#256 main: OPEN / exact-head CI GREEN / GATE 0 HOLD.** Its exact-head full suite run `46017043819` passed **2,610 passed, 7 skipped, 45 subtests**. It replays the event-ID cursor and retry-safe checkpoint correction after #256 merged. Do not merge or deploy it until founder approval because previously skipped events may enter the belief corpus. Its legacy migration does not recover rows strictly older than the old timestamp cutoff.

The earlier manual PR #258 is superseded by this post-#256 documentation replay. PR #260 carries the full manual, backlog and handoff onto this mainline. PR #102/#145 remain older-base dormancy proposals and are still subject to the G-73 policy/revalidation boundary.


## 32. TimeFetch test inventory and VoiceEngine eligibility consumer (27 November 2026)

A current-source recheck incorporated the useful correction from older PR #143 and extended it through the consumer:

- `tests/test_throw_net_time_fetch.py` does exist. It covers confidence/content-length filters, novel-association matching and similarity ordering, arc type/quality filters, ProblemMemory routing, deduplication/capping and provenance.
- It does not assert exclusion of Tier-8, paused, locked or lower-tier retired belief endpoints, nor current-state eligibility of novel-association endpoints or arc provenance.
- `VoiceEngine._retrieve_candidates()` consumes `TimeFetch.run()` results and enriches belief candidates with tier/reinforce_count but does not recheck paused/locked/retired state. `_score_candidate()` applies a 0.5 tier score to non-T3–T6 candidates rather than excluding them; a sufficiently strong candidate can still clear the 0.6 minimum. `tests/test_voice_engine.py` compares T4 and T8 scores but does not assert hard exclusion.

This remains a policy/coverage gap, not an instruction to change retrieval. Confirm the canonical inactive-belief eligibility contract, then add end-to-end TimeFetch-to-VoiceEngine tests. The stale documentation branch #143 is superseded by the corrected current-main backlog entry G-52 in PR #260; its trace document was not merged wholesale.
